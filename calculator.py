import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine
    Lb_m: Unbraced Length (m). If None, defaults to L_m (Span)
    """
    # 1. Unit Conversion
    L = L_m * 100       # m -> cm (Total Span)
    
    # Handle Unbraced Length (Lb)
    if Lb_m is None:
        Lb = L          # Default: Unbraced length = Span
    else:
        Lb = Lb_m * 100 # m -> cm
        
    E = E_gpa * 10000   # GPa -> ksc
    
    # --- [Step 1] Robust Property Extraction ---
    # ดึงค่าพื้นฐาน
    D = props['D']
    Ix = props['Ix']
    
    # 1.1 หา Sx (Elastic Modulus): ถ้าไม่มีใน DB ให้คำนวณจาก Ix / (D/2)
    if 'Sx' in props:
        Sx = props['Sx']
    else:
        Sx = Ix / (D / 2)
        
    # 1.2 หา Zx (Plastic Modulus): ถ้าไม่มี ให้ประมาณค่า
    if 'Zx' in props:
        Zx = props['Zx']
    else:
        Zx = 1.12 * Sx

    # 1.3 ดึงค่าอื่นๆ พร้อมตัวแปรสำรอง (Fallback)
    ry = props.get('ry', props.get('B', 10)/4) 
    t1 = props['tw']
    t2 = props['tf']
    bf = props['B']
    r = props.get('r', 0) 
    h = D - 2*t2 - 2*r    
    
    # Torsional Constant (J)
    J = props.get('J', 0.4 * (bf*t2**3 + (D-t2)*t1**3)) 
    
    # --- [Step 2] Shear Capacity (Vn) ---
    Aw = D * t1
    Cv = 1.0 # For rolled shapes
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- [Step 3] Moment Capacity (Mn) ---
    Mp = Fy * Zx
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    # LTB Parameters
    Iy = props.get('Iy', (2*t2*bf**3)/12 + ((D-2*t2)*t1**3)/12)
    Cw = (Iy * (D - t2)**2) / 4
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    
    ho = D - t2
    c_const = 1.0
    
    # Lr Calculation (AISC F2)
    term_sqrt = math.sqrt(((J*c_const)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2)
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J*c_const)/(Sx*ho) + term_sqrt)

    Mn_ltb = Mp
    if Lb <= Lp:
        Mn_ltb = Mp
    elif Lb > Lp and Lb <= Lr:
        Cb = 1.0 
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp)/(Lr - Lp)))
        Mn_ltb = min(Mn_ltb, Mp)
    else:
        Cb = 1.0
        Fcr = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * math.sqrt(1 + 0.078 * (J*c_const)/(Sx*ho) * (Lb/rts)**2)
        Mn_ltb = Fcr * Sx
        Mn_ltb = min(Mn_ltb, Mp)
        
    Mn = min(Mp, Mn_ltb)
    
    # --- [Step 4] Apply Safety Factors ---
    if method == "ASD":
        Omega_v = 1.50 
        Omega_b = 1.67
        V_des = Vn / Omega_v
        M_des = Mn / Omega_b
    else: # LRFD
        Phi_v = 1.00 
        Phi_b = 0.90
        V_des = Phi_v * Vn
        M_des = Phi_b * Mn

    # --- [Step 5] Convert to Distributed Load (w) ---
    # Shear Control: w = 2V/L
    w_shear = (2 * V_des) / (L/100) 
    
    # Moment Control: w = 8M/L^2
    w_moment = (8 * M_des) / ((L/100)**2)
    
    # Deflection Control
    delta_allow = L / def_limit
    w_defl = (delta_allow * 384 * E * Ix) / (5 * L**4)
    
    # --- [Step 6] Calculate Transition Points (for Tab 4 & Graph) ---
    if V_des > 0:
        L_vm_val = (4 * M_des / V_des) / 100 
    else: 
        L_vm_val = 0
        
    K_defl = (384 * E * Ix) / (5 * def_limit) 
    if M_des > 0:
        L_md_val = (K_defl / (8 * M_des)) / 100
    else:
        L_md_val = 0
    
    # --- [IMPORTANT] Return Dictionary with ALL Keys ---
    return {
        # Results
        'ws': w_shear,
        'wm': w_moment,
        'wd': w_defl,
        'V_des': V_des,
        'M_des': M_des,
        
        # Graph Limits
        'L_vm': L_vm_val, 
        'L_md': L_md_val, 
        
        # Material & Geometry
        'E_ksc': E,
        'L_cm': L,             # <-- Required by tab1_details.py (Line 19)
        'Lb': Lb / 100,        # <-- Required by tab1_details.py (Line 45) [Unit: m]
        'Lb_used': Lb / 100,   # <-- Required by app.py (for caption) [Unit: m]
        
        # Section Properties (returned for display consistency)
        'Ix': Ix,
        'Sx': Sx,
        'Zx': Zx
    }
