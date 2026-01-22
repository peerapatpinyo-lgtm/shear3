# calculator.py

def core_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # 1. Unit Setup
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    
    # 2. Nominal Capacity
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * props['Zx']
    
    # 3. Design Factor (ASD vs LRFD)
    if method == "ASD":
        val_v, val_b = 1.50, 1.67
        V_des = Vn / val_v
        M_des = Mn / val_b
        txt_v = r"\frac{V_n}{1.50}"
        txt_m = r"\frac{M_n}{1.67}"
    else: # LRFD
        val_v, val_b = 1.00, 0.90
        V_des = Vn * val_v
        M_des = Mn * val_b
        txt_v = r"1.00 \cdot V_n"
        txt_m = r"0.90 \cdot M_n"
        
    # 4. Equivalent Uniform Loads (kg/m)
    # Shear: V = wL/2 -> w = 2V/L
    ws = (2 * V_des / L_cm) * 100
    # Moment: M = wL^2/8 -> w = 8M/L^2
    wm = (8 * M_des / L_cm**2) * 100
    # Deflection: delta = 5wL^4/384EI -> w = 384EI(delta)/5L^4
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 5. Transition Points (Critical Lengths)
    # Point where Shear governs -> Moment governs
    L_vm_cm = (4 * M_des) / V_des
    # Point where Moment governs -> Deflection governs
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_des)
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'],
        "V_des": V_des, "M_des": M_des,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta": delta_allow,
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0,
        "txt_v": txt_v, "txt_m": txt_m
    }
