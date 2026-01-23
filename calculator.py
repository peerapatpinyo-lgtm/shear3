# calculator.py
import math

def core_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # --- 1. Unit Setup ---
    E_ksc = E_gpa * 10197.162
    G_ksc = E_ksc / 2.6 # Shear Modulus (approx E/2(1+v))
    L_cm = L_m * 100.0
    
    # ดึงค่าจาก Database (ต้องมี B และ tf แล้ว)
    D = props['D'] / 10.0 # cm
    B = props['B'] / 10.0 # cm (Width)
    tw = props['tw'] / 10.0 # cm
    tf = props['tf'] / 10.0 # cm
    
    # คำนวณ Section Properties เพิ่มเติมสำหรับ LTB
    # Aw (Shear Area)
    Aw = D * tw 
    
    # Iy (Inertia y-axis) - ถ้าใน DB ไม่มี ให้คำนวณเอง
    if 'Iy' in props:
        Iy = props['Iy']
    else:
        Iy = (2 * tf * B**3 / 12) + ((D - 2*tf) * tw**3 / 12)
    
    # Sx (Elastic Modulus) - จำเป็นสำหรับ LTB (Zx คือ Plastic)
    Sx = props['Ix'] / (D/2)
    
    # ry (Radius of gyration y-axis)
    A_sec = (2 * B * tf) + ((D - 2*tf) * tw)
    ry = math.sqrt(Iy / A_sec)
    
    # J (Torsional Constant) - Approximation
    J = (1/3) * (2 * B * tf**3 + (D - tf) * tw**3)
    
    # h0 (Distance between flange centroids)
    h0 = D - tf
    
    # Cw (Warping Constant) - Approx for I-shape
    Cw = (Iy * h0**2) / 4

    # --- 2. LTB Parameters (AISC Chapter F) ---
    # r_ts (Effective Radius of Gyration)
    r_ts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    
    # Lp (Limiting length for yielding)
    Lp_cm = 1.76 * ry * math.sqrt(E_ksc / Fy_ksc)
    
    # Lr (Limiting length for inelastic LTB)
    # สมการเต็มของ AISC F2-6
    c = 1.0 # For doubly symmetric I-shape
    term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy_ksc))
    term2 = (J * c) / (Sx * h0)
    term3 = math.sqrt(1 + math.sqrt(1 + 6.76 * ((0.7 * Fy_ksc / E_ksc) * (Sx * h0 / (J * c)))**2))
    Lr_cm = term1 * math.sqrt(term2 + term3)
    
    # --- 3. Moment Capacity with LTB (Mn) ---
    Mp = Fy_ksc * props['Zx']
    
    # สมมติ Cb = 1.0 (Conservative for simple span)
    Cb = 1.0
    
    # ตรวจสอบ Zone
    Lb = L_cm # สมมติไม่มีค้ำยันด้านข้างเลยตลอดความยาวคาน (Unbraced Length = Span)
    
    if Lb <= Lp_cm:
        # Zone 1: Plastic Yielding
        Mn_ltb = Mp
        zone = "Zone 1 (Yielding)"
    elif Lb <= Lr_cm:
        # Zone 2: Inelastic LTB
        # Mn = Cb [Mp - (Mp - 0.7FySx)((Lb-Lp)/(Lr-Lp))] <= Mp
        factor = (Lb - Lp_cm) / (Lr_cm - Lp_cm)
        Mn_calc = Cb * (Mp - (Mp - 0.7 * Fy_ksc * Sx) * factor)
        Mn_ltb = min(Mp, Mn_calc)
        zone = "Zone 2 (Inelastic LTB)"
    else:
        # Zone 3: Elastic LTB
        # Fcr = ...
        Fcr = ((Cb * math.pi**2 * E_ksc) / (Lb / r_ts)**2) * \
              math.sqrt(1 + 0.078 * (J * c / (Sx * h0)) * (Lb / r_ts)**2)
        Mn_ltb = min(Mp, Fcr * Sx)
        zone = "Zone 3 (Elastic LTB)"
        
    # Mn สุดท้ายต้องเลือกค่าต่ำสุดระหว่าง Yielding (Mp) กับ LTB
    # แต่ในสูตรข้างบนเรา clamp ไว้ที่ Mp แล้ว ดังนั้นใช้ Mn_ltb ได้เลย
    Mn = Mn_ltb

    # --- 4. Shear Capacity (Vn) ---
    Vn = 0.60 * Fy_ksc * Aw 
    
    # --- 5. Design Values (ASD/LRFD) ---
    if method == "ASD":
        omega_v, omega_b = 1.50, 1.67
        phi_v, phi_b = 0.0, 0.0
        
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        
        txt_v_method = r"V_{design} = \frac{V_n}{\Omega_v}"
        txt_m_method = r"M_{design} = \frac{M_n}{\Omega_b}"
        
    else: # LRFD
        phi_v, phi_b = 1.00, 0.90
        omega_v, omega_b = 1.0, 1.0
        
        V_des = Vn * phi_v
        M_des = Mn * phi_b
        
        txt_v_method = r"V_{design} = \phi_v V_n"
        txt_m_method = r"M_{design} = \phi_b M_n"
        
    # --- 6. Uniform Loads & Deflection ---
    ws = (2 * V_des / L_cm) * 100
    wm = (8 * M_des / L_cm**2) * 100
    
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # --- 7. Transition Points (Updated for Graph) ---
    # *หมายเหตุ: L_vm และ L_md จะเปลี่ยนไปตาม Lb ด้วยถ้าเราคิด LTB แบบละเอียด
    # แต่เพื่อความง่ายในการพล็อต Tab 2 เราจะคืนค่าเดิมที่ Base บน Mp
    # หรือจะส่ง Lp, Lr ไปพล็อตเส้นประในกราฟก็ได้
    
    L_vm_cm = (4 * M_des) / V_des # ค่าโดยประมาณ
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_des)

    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], "Sx": Sx,
        "L_cm": L_cm, "E_ksc": E_ksc, "Fy": Fy_ksc,
        
        "Vn": Vn, "Mn": Mn, "Mp": Mp,
        "omega_v": omega_v, "omega_b": omega_b,
        "phi_v": phi_v, "phi_b": phi_b,
        
        "V_des": V_des, "M_des": M_des,
        "txt_v_method": txt_v_method, "txt_m_method": txt_m_method,
        
        "ws": ws, "wm": wm, "wd": wd, "delta": delta_allow,
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0,
        
        # LTB Specific Returns
        "Lp": Lp_cm/100.0, "Lr": Lr_cm/100.0, "Zone": zone, "Lb": Lb/100.0
    }
