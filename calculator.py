import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine
    Lb_m: Unbraced Length (m). If None, defaults to L_m (Span)
    """
    # 1. Unit Conversion
    L = L_m * 100       # m -> cm (Total Span)
    
    # Handle Unbraced Length
    if Lb_m is None:
        Lb = L          # Default: Unbraced length = Span
    else:
        Lb = Lb_m * 100 # m -> cm
        
    E = E_gpa * 10000   # GPa -> ksc
    
    # --- [FIX] Robust Property Extraction ---
    # ดึงค่า D และ Ix ก่อน เพราะต้องใช้คำนวณ Sx หากข้อมูลขาดหาย
    D = props['D']
    Ix = props['Ix']
    
    # 1. หา Sx (Elastic Modulus): ถ้าไม่มีใน DB ให้คำนวณจาก Ix / (D/2)
    if 'Sx' in props:
        Sx = props['Sx']
    else:
        Sx = Ix / (D / 2)
        
    # 2. หา Zx (Plastic Modulus): ถ้าไม่มี ให้ประมาณค่าเป็น 1.12 * Sx (Shape factor for I-beam)
    if 'Zx' in props:
        Zx = props['Zx']
    else:
        Zx = 1.12 * Sx

    # 3. ดึงค่าอื่นๆ พร้อมตัวแปรสำรอง (Fallback)
    ry = props.get('ry', props.get('B', 10)/4) # ถ้าไม่มี ry ให้ประมาณจาก B/4
    t1 = props['tw']
    t2 = props['tf']
    bf = props['B']
    r = props.get('r', 0) 
    
    # Clear web depth
    h = D - 2*t2 - 2*r    
    
    # Torsional Constant (J): ประมาณค่าหากไม่มี
    J = props.get('J', 0.4 * (bf*t2**3 + (D-t2)*t1**3)) 
    
    # --- 2. Shear Capacity (Vn) ---
    Aw = D * t1
    Cv = 1.0 # For rolled shapes with h/tw <= 2.24 sqrt(E/Fy)
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- 3. Moment Capacity (Mn) ---
    # 3.1 Yielding
    Mp = Fy * Zx
    
    # 3.2 Lateral-Torsional Buckling (LTB) using Lb
    # LTB Parameters
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    # Warping constant approximation (Cw) for rts calculation if needed
    Iy = props.get('Iy', (2*t2*bf**3)/12 + ((D-2*t2)*t1**3)/12) # คำนวณ Iy คร่าวๆ ถ้าไม่มี
    Cw = (Iy * (D - t2)**2) / 4
    
    # Effective Radius of Gyration (rts)
    # สูตรเต็ม: rts = sqrt(sqrt(Iy*Cw)/Sx)
    # สูตรย่อ: rts ~ bf / sqrt(12 * (1 + (1/6)*(h*tw)/(bf*tf))) แต่ใช้ bf/4 ง่ายกว่าสำหรับกรณีข้อมูลไม่ครบ
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    
    ho = D - t2
    c_const = 1.0
    
    # Lr Calculation (Simplified for Rolled I-Shape)
    # Term 1
    term_sqrt = math.sqrt(((J*c_const)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2)
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J*c_const)/(Sx*ho) + term_sqrt)

    Mn_ltb = Mp
    
    # AISC F2 Logic
    if Lb <= Lp:
        # Zone 1: Plastic Moment
        Mn_ltb = Mp
    elif Lb > Lp and Lb <= Lr:
        # Zone 2: Inelastic LTB
        Cb = 1.0 # Conservative assumption
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp)/(Lr - Lp)))
        Mn_ltb = min(Mn_ltb, Mp)
    else:
        # Zone 3: Elastic LTB
        Cb = 1.0
        Fcr = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * math.sqrt(1 + 0.078 * (J*c_const)/(Sx*ho) * (Lb/rts)**2)
        Mn_ltb = Fcr * Sx
        Mn_ltb = min(Mn_ltb, Mp)
        
    # Governing Mn
    Mn = min(Mp, Mn_ltb)
    
    # --- 4. Apply Safety Factors ---
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

    # --- 5. Convert to Distributed Load (w) ---
    # Shear Control: w = 2V/L
    w_shear = (2 * V_des) / (L/100) 
    
    # Moment Control: w = 8M/L^2
    w_moment = (8 * M_des) / ((L/100)**2)
    
    # Deflection Control: w = delta * 384EI / 5L^4
    delta_allow = L / def_limit
    w_defl = (delta_allow * 384 * E * Ix) / (5 * L**4)
    
    return {
        'ws': w_shear,
        'wm': w_moment,
        'wd': w_defl,
        'V_des': V_des,
        'M_des': M_des,
        'L_vm': 0, 
        'L_md': 0,
        'E_ksc': E,
        'Lb_used': Lb/100 
    }
