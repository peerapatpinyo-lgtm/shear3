# calculator.py
import math

def core_calculation(L_m, Fy_ksc, E_gpa, props, method, def_limit=360):
    """
    Core Structural Calculation Function
    Updated: Full AISC 360-16 Compliance (Compactness & Shear check)
    """
    # --- 1. Unit Setup ---
    # ใช้ค่า E ตามมาตรฐานวิศวกรรมในไทย (2.04 x 10^6 ksc) หรือตาม GPa ที่ระบุ
    E_ksc = E_gpa * 10197.162 
    L_cm = L_m * 100.0
    
    # Section Properties (Convert mm to cm)
    D = props['D'] / 10.0
    B = props.get('B', 100) / 10.0 
    tw = props['tw'] / 10.0
    tf = props.get('tf', 10) / 10.0
    Ix = props['Ix']
    Zx = props['Zx']
    
    # Area for Shear (Web Area)
    Aw = D * tw 
    
    # Calculate Iy if missing
    if 'Iy' in props: 
        Iy = props['Iy']
    else: 
        Iy = (2 * tf * B**3 / 12) + ((D - 2*tf) * tw**3 / 12)
    
    Sx = Ix / (D/2)
    
    # --- 2. Compactness Check (AISC Table B4.1b) ---
    # Check Flange Local Buckling
    lambda_f = (B / 2) / tf
    lambda_pf = 0.38 * math.sqrt(E_ksc / Fy_ksc)
    lambda_rf = 1.0 * math.sqrt(E_ksc / Fy_ksc)
    
    # Check Web Local Buckling
    h = D - (2 * tf)
    lambda_w = h / tw
    lambda_pw = 3.76 * math.sqrt(E_ksc / Fy_ksc)
    lambda_rw = 5.70 * math.sqrt(E_ksc / Fy_ksc)
    
    is_compact = (lambda_f <= lambda_pf) and (lambda_w <= lambda_pw)

    # --- 3. LTB Parameters ---
    # Torsional Constant (J)
    J = (1/3) * (2 * B * tf**3 + (D - tf) * tw**3)
    
    # Warping Constant (Cw)
    h0 = D - tf
    Cw = (Iy * h0**2) / 4
    
    # Radius of gyration (ry)
    A_sec = (2 * B * tf) + ((D - 2*tf) * tw)
    ry = math.sqrt(Iy / A_sec)
    
    # r_ts (Effective radius of gyration)
    r_ts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    
    # Lp (Limit for Plastic Yielding)
    Lp_cm = 1.76 * ry * math.sqrt(E_ksc / Fy_ksc)
    
    # Lr (Limit for Inelastic LTB)
    c_factor = 1.0 
    term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy_ksc))
    term2 = (J * c_factor) / (Sx * h0)
    term3 = math.sqrt(1 + math.sqrt(1 + 6.76 * ((0.7 * Fy_ksc / E_ksc) * (Sx * h0 / (J * c_factor)))**2))
    Lr_cm = term1 * math.sqrt(term2 + term3)
    
    # --- 4. Moment Capacity (Mn) ---
    Mp = Fy_ksc * Zx
    Cb = 1.0 
    Lb = L_cm 
    
    # Initial Mn based on LTB
    if Lb <= Lp_cm:
        Mn_ltb = Mp
        zone = "Zone 1 (Yielding)"
    elif Lb <= Lr_cm:
        factor = (Lb - Lp_cm) / (Lr_cm - Lp_cm)
        Mn_calc = Cb * (Mp - (Mp - 0.7 * Fy_ksc * Sx) * factor)
        Mn_ltb = min(Mp, Mn_calc)
        zone = "Zone 2 (Inelastic LTB)"
    else:
        Fcr = ((Cb * math.pi**2 * E_ksc) / (Lb / r_ts)**2) * \
              math.sqrt(1 + 0.078 * (J * c_factor / (Sx * h0)) * (Lb / r_ts)**2)
        Mn_ltb = min(Mp, Fcr * Sx)
        zone = "Zone 3 (Elastic LTB)"

    # Adjust Mn if Non-Compact (AISC F3)
    if lambda_f > lambda_pf:
        if lambda_f <= lambda_rf:
            Mn_flb = Mp - (Mp - 0.7 * Fy_ksc * Sx) * ((lambda_f - lambda_pf)/(lambda_rf - lambda_pf))
        else:
            # Slange Slender
            kc = 4 / math.sqrt(h/tw) if (h/tw) > 0 else 0.4
            Mn_flb = (0.9 * E_ksc * kc * Sx) / (lambda_f**2)
        Mn = min(Mn_ltb, Mn_flb)
        zone += " + Non-Compact Flange"
    else:
        Mn = Mn_ltb

    # --- 5. Shear Capacity (Vn) ---
    # AISC G2.1: Shear Coeff Cv1
    if lambda_w <= 2.24 * math.sqrt(E_ksc / Fy_ksc):
        Cv1 = 1.0
        phi_v_val = 1.00 # Specific case for hot-rolled I-shapes
        omega_v_val = 1.50
    else:
        # สำหรับหน้าตัดที่เอวบาง (กรณีทั่วไปของ H-Beam จะไม่ถึงจุดนี้)
        Cv1 = 1.0 # Simplified for standard SYS sections
        phi_v_val = 0.90
        omega_v_val = 1.67
        
    Vn = 0.60 * Fy_ksc * Aw * Cv1
    
    # --- 6. Design Values (ASD/LRFD) ---
    if method == "ASD":
        omega_v = omega_v_val
        omega_b = 1.67 
        phi_v, phi_b = 0.0, 0.0
        
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        M_des_full = Mp / omega_b
        
        txt_v_method = r"V_{design} = \frac{V_n}{\Omega_v} (\Omega_v=" + f"{omega_v:.2f})"
        txt_m_method = r"M_{design} = \frac{M_n}{\Omega_b} (\Omega_b=1.67)"
    else: # LRFD
        phi_v = phi_v_val
        phi_b = 0.90 
        omega_v, omega_b = 1.0, 1.0
        
        V_des = Vn * phi_v
        M_des = Mn * phi_b
        M_des_full = Mp * phi_b
        
        txt_v_method = r"V_{design} = \phi_v V_n (\phi_v=" + f"{phi_v:.2f})"
        txt_m_method = r"M_{design} = \phi_b M_n (\phi_b=0.90)"
        
    # --- 7. Uniform Load Capacities ---
    ws = (2 * V_des / L_cm) * 100
    wm = (8 * M_des / L_cm**2) * 100
    
    # Deflection Control
    delta_allow = L_cm / def_limit 
    wd = ((384 * E_ksc * Ix * delta_allow) / (5 * L_cm**4)) * 100
    
    # --- 8. Critical Transition Lengths ---
    L_vm_cm = (4 * M_des_full) / V_des
    L_md_cm = (384 * E_ksc * Ix) / (40 * M_des_full * def_limit)

    return {
        "Aw": Aw, "Ix": Ix, "Zx": Zx, "Sx": Sx,
        "L_cm": L_cm, "E_ksc": E_ksc, "Fy": Fy_ksc,
        "Vn": Vn, "Mn": Mn, "Mp": Mp,
        "omega_v": omega_v, "omega_b": omega_b,
        "phi_v": phi_v, "phi_b": phi_b,
        "V_des": V_des, "M_des": M_des, "M_des_full": M_des_full,
        "txt_v_method": txt_v_method, "txt_m_method": txt_m_method,
        "ws": ws, "wm": wm, "wd": wd, 
        "delta": delta_allow, "def_limit": def_limit,
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0,
        "Lp": Lp_cm/100.0, "Lr": Lr_cm/100.0, "Zone": zone, "Lb": Lb/100.0,
        "is_compact": is_compact
    }
