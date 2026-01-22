# calculator.py

def core_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # --- 1. Unit Setup ---
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    
    # --- 2. Nominal Capacity (ต้องมีส่วนนี้เพื่อส่งค่ากลับไปแสดงผล) ---
    # Shear: Vn = 0.6 * Fy * Aw
    Vn = 0.60 * Fy_ksc * Aw 
    # Moment: Mn = Fy * Zx
    Mn = Fy_ksc * props['Zx']
    
    # --- 3. Design Factor (ASD vs LRFD) ---
    if method == "ASD":
        omega_v, omega_b = 1.50, 1.67
        phi_v, phi_b = 0.0, 0.0 # ไม่ใช้ใน ASD ใส่ค่า 0 กัน Error
        
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        
        # Text for report
        txt_v_method = r"V_{design} = \frac{V_n}{\Omega_v}"
        txt_m_method = r"M_{design} = \frac{M_n}{\Omega_b}"
        
    else: # LRFD
        phi_v, phi_b = 1.00, 0.90
        omega_v, omega_b = 1.0, 1.0 # ไม่ใช้ใน LRFD ใส่ค่า 1 กัน Error
        
        V_des = Vn * phi_v
        M_des = Mn * phi_b
        
        # Text for report
        txt_v_method = r"V_{design} = \phi_v V_n"
        txt_m_method = r"M_{design} = \phi_b M_n"
        
    # --- 4. Equivalent Uniform Loads (kg/m) ---
    # Shear: w = 2V/L
    ws = (2 * V_des / L_cm) * 100
    # Moment: w = 8M/L^2
    wm = (8 * M_des / L_cm**2) * 100
    # Deflection
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # --- 5. Transition Points ---
    L_vm_cm = (4 * M_des) / V_des
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_des)
    
    # Return Dictionary (ต้องครบตามที่ main.py เรียกใช้)
    return {
        # Inputs & Props
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], 
        "L_cm": L_cm, "E_ksc": E_ksc,
        
        # Nominal (ตัวที่ Error คือบรรทัดนี้ครับ)
        "Vn": Vn, "Mn": Mn,
        
        # Factors
        "omega_v": omega_v, "omega_b": omega_b,
        "phi_v": phi_v, "phi_b": phi_b,
        
        # Design Values
        "V_des": V_des, "M_des": M_des,
        "txt_v_method": txt_v_method, "txt_m_method": txt_m_method,
        
        # Load Limits
        "ws": ws, "wm": wm, "wd": wd, "delta": delta_allow,
        
        # Transitions
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0
    }
