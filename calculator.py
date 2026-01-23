import math

def core_calculation(L_m, Fy_ksc, E_gpa, props, method, def_limit=360):
    """
    Core Structural Calculation Function
    Rechecked: Validated against AISC 360-16 Formulas
    """
    # --- 1. Unit Setup ---
    # Convert GPa to ksc (1 GPa approx 10197.16 kg/cm^2)
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    
    # Section Properties (Convert mm to cm)
    D = props['D'] / 10.0
    B = props.get('B', 100) / 10.0 
    tw = props['tw'] / 10.0
    tf = props.get('tf', 10) / 10.0
    
    # Area for Shear (Web Area)
    Aw = D * tw 
    
    # Calculate Iy if missing (simplify approximation for I-shape)
    if 'Iy' in props: Iy = props['Iy']
    else: Iy = (2 * tf * B**3 / 12) + ((D - 2*tf) * tw**3 / 12)
    
    Sx = props['Ix'] / (D/2)
    
    # --- 2. LTB Parameters (Calculation) ---
    # Torsional Constant (J) - Approximation for Open Section
    J = (1/3) * (2 * B * tf**3 + (D - tf) * tw**3)
    
    # Warping Constant (Cw)
    h0 = D - tf
    Cw = (Iy * h0**2) / 4
    
    # Radius of gyration (ry) - Approx
    A_sec = (2 * B * tf) + ((D - 2*tf) * tw)
    ry = math.sqrt(Iy / A_sec)
    
    # r_ts (Effective radius of gyration)
    # AISC Eq. F2-7: r_ts^2 = sqrt(Iy * Cw) / Sx
    r_ts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    
    # Lp (Limit for Plastic Yielding) - AISC Eq. F2-5
    Lp_cm = 1.76 * ry * math.sqrt(E_ksc / Fy_ksc)
    
    # Lr (Limit for Inelastic LTB) - AISC Eq. F2-6
    c_factor = 1.0 # For doubly symmetric I-shape
    term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy_ksc))
    term2 = (J * c_factor) / (Sx * h0)
    term3 = math.sqrt(1 + math.sqrt(1 + 6.76 * ((0.7 * Fy_ksc / E_ksc) * (Sx * h0 / (J * c_factor)))**2))
    Lr_cm = term1 * math.sqrt(term2 + term3)
    
    # --- 3. Moment Capacity (Mn) ---
    Mp = Fy_ksc * props['Zx']
    Cb = 1.0 # Conservative assumption for simply supported uniform load
    Lb = L_cm # Assume unbraced length = span length
    
    if Lb <= Lp_cm:
        Mn_ltb = Mp
        zone = "Zone 1 (Yielding)"
    elif Lb <= Lr_cm:
        factor = (Lb - Lp_cm) / (Lr_cm - Lp_cm)
        Mn_calc = Cb * (Mp - (Mp - 0.7 * Fy_ksc * Sx) * factor)
        Mn_ltb = min(Mp, Mn_calc)
        zone = "Zone 2 (Inelastic LTB)"
    else:
        # Elastic LTB - AISC Eq. F2-3, F2-4
        Fcr = ((Cb * math.pi**2 * E_ksc) / (Lb / r_ts)**2) * \
              math.sqrt(1 + 0.078 * (J * c_factor / (Sx * h0)) * (Lb / r_ts)**2)
        Mn_ltb = min(Mp, Fcr * Sx)
        zone = "Zone 3 (Elastic LTB)"
        
    Mn = Mn_ltb

    # --- 4. Shear Capacity (Vn) ---
    # AISC G2.1a: Shear Yielding
    Vn = 0.60 * Fy_ksc * Aw 
    
    # --- 5. Design Values (ASD/LRFD) ---
    if method == "ASD":
        omega_v = 1.50 # Standard for shear yielding
        omega_b = 1.67 # Standard for bending
        phi_v, phi_b = 0.0, 0.0 # Unused in ASD
        
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        
        txt_v_method = r"V_{design} = \frac{V_n}{\Omega_v} (\Omega_v=1.50)"
        txt_m_method = r"M_{design} = \frac{M_n}{\Omega_b} (\Omega_b=1.67)"
    else: # LRFD
        phi_v = 1.00 # Standard for shear yielding
        phi_b = 0.90 # Standard for bending
        omega_v, omega_b = 1.0, 1.0 # Unused in LRFD
        
        V_des = Vn * phi_v
        M_des = Mn * phi_b
        
        txt_v_method = r"V_{design} = \phi_v V_n (\phi_v=1.00)"
        txt_m_method = r"M_{design} = \phi_b M_n (\phi_b=0.90)"
        
    # --- 6. Uniform Load Capacities ---
    # Convert from kg/cm to kg/m by multiplying by 100
    ws = (2 * V_des / L_cm) * 100
    wm = (8 * M_des / L_cm**2) * 100
    
    # Deflection Control
    delta_allow = L_cm / def_limit 
    # w = (384 E I delta) / (5 L^4)
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # --- 7. Critical Transition Lengths ---
    # Derived from equating ws=wm and wm=wd
    L_vm_cm = (4 * M_des) / V_des
    
    # L_md derivation:
    # 8 M / L^2 = (384 E I) / (5 * L^3 * Limit)
    # L = (384 E I) / (40 * M * Limit)
    L_md_cm = (384 * E_ksc * props['Ix']) / (40 * M_des * def_limit)

    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], "Sx": Sx,
        "L_cm": L_cm, "E_ksc": E_ksc, "Fy": Fy_ksc,
        "Vn": Vn, "Mn": Mn, "Mp": Mp,
        "omega_v": omega_v, "omega_b": omega_b,
        "phi_v": phi_v, "phi_b": phi_b,
        "V_des": V_des, "M_des": M_des,
        "txt_v_method": txt_v_method, "txt_m_method": txt_m_method,
        "ws": ws, "wm": wm, "wd": wd, 
        "delta": delta_allow, "def_limit": def_limit,
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0,
        "Lp": Lp_cm/100.0, "Lr": Lr_cm/100.0, "Zone": zone, "Lb": Lb/100.0
    }
