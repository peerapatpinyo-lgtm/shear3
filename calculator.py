# calculator.py
import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Core Structural Calculation Function
    
    Args:
        L_m (float): Span Length (meters) - ระยะช่วงคานจริง
        Fy (float): Yield Strength (ksc)
        E_gpa (float): Modulus of Elasticity (GPa)
        props (dict): Dictionary containing section properties (H-Beam)
        method (str): "ASD" or "LRFD"
        def_limit (int): Denominator for deflection limit (e.g., 360 for L/360)
        Lb_m (float, optional): Unbraced Length (meters). 
                                If None, assumes Unbraced Length = Span Length (Worst case).
    
    Returns:
        dict: Calculation results including capacities (ws, wm, wd), design forces, and critical lengths.
    """
    
    # ----------------------------------------------------
    # 1. Unit Conversion & Constants
    # ----------------------------------------------------
    # L_cm (Span) for External Force & Deflection
    L_cm = L_m * 100.0
    
    # Lb_cm (Unbraced Length) for Moment Capacity (LTB Check)
    # ถ้ามีการระบุ Lb มา ให้ใช้ค่า Lb นั้น แต่ถ้าไม่มี (None) ให้ใช้ความยาวช่วงคาน (L) เป็น Lb
    if Lb_m is not None and Lb_m > 0:
        Lb_cm = Lb_m * 100.0
    else:
        Lb_cm = L_cm 

    E_ksc = E_gpa * 10000  # Convert GPa to ksc
    Cb = 1.0  # Conservative assumption for simply supported beams

    # ----------------------------------------------------
    # 2. Extract Section Properties
    # ----------------------------------------------------
    # ป้องกัน error กรณี data ขาดหายโดยใช้ .get()
    Ix = props.get('Ix', 0)
    Iy = props.get('Iy', 0)
    Zx = props.get('Zx', 0)  # Elastic Modulus
    
    # Fallback for Sx (Plastic Modulus)
    # ใน DB ไทย Zx มักคือ Elastic Modulus (S ใน AISC)
    S_elastic = Zx 
    # ประมาณค่า Plastic Modulus (Z ใน AISC)
    Z_plastic = props.get('Zy', 1.1 * S_elastic) 

    r_x = props.get('rx', 0)
    r_y = props.get('ry', 0)
    
    # Torsional Constant (J)
    # ถ้าใน DB ไม่มี J ให้ประมาณค่า J ≈ 2/3 * b * t^3 (sum of parts) หรือใช้ 0.05 * Ix แบบหยาบๆ
    # เพื่อความชัวร์ ใช้สูตร J ≈ Σ(b*t^3/3)
    d = props.get('D', 0)      # Depth (mm)
    bf = props.get('B', 0)     # Flange Width (mm)
    tf = props.get('t2', 0)    # Flange Thickness (mm)
    tw = props.get('t1', 0)    # Web Thickness (mm)
    
    # Convert dimensions to cm
    d_cm = d / 10.0
    bf_cm = bf / 10.0
    tf_cm = tf / 10.0
    tw_cm = tw / 10.0

    if props.get('Ix', 0) > 0:
        J = props.get('J', props['Ix'] * 0.02) # Fallback J
    else:
        J = 1.0 # Avoid zero error later

    # Calculate Geometric Properties for LTB (AISC F2)
    h0 = max(1.0, d_cm - tf_cm)  # Distance between flange centroids (prevent 0)
    
    # Cw (Warping Constant) ~ (Iy * h0^2) / 4
    Cw = (Iy * (h0 ** 2)) / 4.0
    
    # r_ts calculation
    try:
        if S_elastic > 0:
            r_ts = math.sqrt(math.sqrt(Iy * Cw) / S_elastic)
        else:
            r_ts = r_y
    except:
        r_ts = r_y 

    # ----------------------------------------------------
    # 3. Calculate LTB Limits (Lp, Lr) - AISC 360-16
    # ----------------------------------------------------
    # Lp = 1.76 * ry * sqrt(E/Fy)
    try:
        Lp = 1.76 * r_y * math.sqrt(E_ksc / Fy)
    except:
        Lp = 0

    # Lr calculation
    try:
        term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy))
        J_term = (J * 1.0) / (S_elastic * h0)
        inner_sqrt = math.sqrt((J_term)**2 + 6.76 * ((0.7 * Fy) / E_ksc)**2)
        Lr = term1 * math.sqrt(J_term + inner_sqrt)
    except:
        Lr = Lp * 3.0 # Fallback

    # ----------------------------------------------------
    # 4. Calculate Nominal Moment Capacity (Mn) based on Lb_cm
    # ----------------------------------------------------
    Mp = Fy * Z_plastic
    Mn = 0
    
    # Zone 1: Plastic (Lb <= Lp)
    if Lb_cm <= Lp:
        Mn = Mp
        
    # Zone 2: Inelastic LTB (Lp < Lb <= Lr)
    elif Lb_cm <= Lr:
        if (Lr - Lp) != 0:
            residual_moment = 0.7 * Fy * S_elastic
            Mn = Cb * (Mp - (Mp - residual_moment) * ((Lb_cm - Lp) / (Lr - Lp)))
        else:
            Mn = Mp
        Mn = min(Mn, Mp)
        
    # Zone 3: Elastic LTB (Lb > Lr)
    else:
        try:
            lb_rts = Lb_cm / r_ts
            if lb_rts > 0:
                Fcr = (Cb * (math.pi**2) * E_ksc) / (lb_rts**2) * \
                      math.sqrt(1 + 0.078 * (J / (S_elastic * h0)) * (lb_rts**2))
                Mn = Fcr * S_elastic
            else:
                Mn = Mp
        except:
            Mn = 0.5 * Mp # Fallback
            
        Mn = min(Mn, Mp)

    # Apply Safety Factors
    if method == "ASD":
        M_des = Mn / 1.67
    else:
        M_des = 0.90 * Mn

    # ----------------------------------------------------
    # 5. Calculate Shear Capacity (Vn) - AISC G2
    # ----------------------------------------------------
    Aw = (d_cm * tw_cm)
    Cv = 1.0 
    Vn = 0.6 * Fy * Aw * Cv

    if method == "ASD":
        V_des = Vn / 1.67
    else:
        V_des = 0.90 * Vn

    # ----------------------------------------------------
    # 6. Calculate Uniform Load Capacities (w) [kg/m]
    # ----------------------------------------------------
    # 6.1 Moment Controlled Uniform Load
    if L_cm > 0:
        w_m_kg_cm = (8 * M_des) / (L_cm**2)
        w_m = w_m_kg_cm * 100 
    else:
        w_m = 0

    # 6.2 Shear Controlled Uniform Load
    if L_cm > 0:
        w_s_kg_cm = (2 * V_des) / L_cm
        w_s = w_s_kg_cm * 100 
    else:
        w_s = 0

    # 6.3 Deflection Controlled Uniform Load
    delta_allow = L_cm / def_limit
    if L_cm > 0:
        w_d_kg_cm = (delta_allow * 384 * E_ksc * Ix) / (5 * (L_cm**4))
        w_d = w_d_kg_cm * 100 
    else:
        w_d = 0

    # ----------------------------------------------------
    # 7. Find Critical Transition Lengths
    # ----------------------------------------------------
    # [FIX] ZeroDivisionError Protection
    M_max_pot = Mp / 1.67 if method == "ASD" else 0.9 * Mp
    
    if V_des > 0:
        L_vm = (4 * M_max_pot) / V_des / 100.0 # meters
    else:
        L_vm = 0 # กรณีไม่มีแรงเฉือน (ข้อมูลผิดพลาด) ให้เป็น 0
        
    L_md = 0 # Default placeholder

    # ----------------------------------------------------
    # 8. Return Results
    # ----------------------------------------------------
    return {
        'ws': w_s,
        'wm': w_m,
        'wd': w_d,
        'M_des': M_des,   
        'V_des': V_des,   
        'Mn': Mn,         
        'L_cm': L_cm,
        'Lb_cm': Lb_cm,   
        'E_ksc': E_ksc,
        'Lp': Lp / 100.0,
        'Lr': Lr / 100.0,
        'L_vm': L_vm,
        'L_md': L_md,
    }
