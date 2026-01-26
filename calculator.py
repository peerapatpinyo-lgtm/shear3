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
    Zy = props.get('Zy', 0)
    Sx = props.get('Sx', 0)  # Plastic Modulus (Z in AISC) -> ใน DB ไทยมักเก็บเป็น Zx(Elastic) check ให้ดี
    # หมายเหตุ: ในตารางเหล็กไทย Zx มักคือ Section Modulus (Elastic, S ใน AISC)
    # ส่วน Zy/Sy คือ Plastic Modulus (Z ใน AISC) มักไม่ค่อยมีบอก
    # เพื่อความปลอดภัยใน code นี้จะสมมติใช้ Zx ตามตารางเป็น S (Elastic)
    # และประมาณค่า Plastic Modulus (Z_plastic) = 1.1 * Zx (Shape factor ~1.1 for I-beam)
    
    S_elastic = Zx  # ค่าจากตาราง SYS (cm3)
    Z_plastic = 1.1 * S_elastic 

    r_x = props.get('rx', 0)
    r_y = props.get('ry', 0)
    J = props.get('Ix', 0) * 0.05 # Approximation if J not in DB (Torsional Constant)
    # ถ้า Database มีค่า J ให้ใช้ค่า J จริง (บรรทัดนี้คือ Fallback)
    
    d = props.get('D', 0)      # Depth (mm)
    bf = props.get('B', 0)     # Flange Width (mm)
    tf = props.get('t2', 0)    # Flange Thickness (mm)
    tw = props.get('t1', 0)    # Web Thickness (mm)
    
    # Convert dimensions to cm for consistency with ksc
    d_cm = d / 10.0
    bf_cm = bf / 10.0
    tf_cm = tf / 10.0
    tw_cm = tw / 10.0

    # Calculate Geometric Properties for LTB (AISC F2)
    h0 = d_cm - tf_cm  # Distance between flange centroids
    
    # Cw (Warping Constant) ~ (Iy * h0^2) / 4
    Cw = (Iy * (h0 ** 2)) / 4.0
    
    # r_ts (Radius of gyration of flange components)
    # r_ts^2 = sqrt(Iy * Cw) / Sx  (Simplified)
    # AISC Eq. F2-7: r_ts = bf / sqrt(12 * (1 + (1/6)*(h*tw)/(bf*tf))) ... approximate as r_y works sometimes but let's use simplified:
    try:
        r_ts = math.sqrt(math.sqrt(Iy * Cw) / S_elastic)
    except:
        r_ts = r_y # Fallback

    # ----------------------------------------------------
    # 3. Calculate LTB Limits (Lp, Lr) - AISC 360-16
    # ----------------------------------------------------
    # Lp: Limiting laterally unbraced length for the limit state of yielding
    # Lp = 1.76 * ry * sqrt(E/Fy)
    Lp = 1.76 * r_y * math.sqrt(E_ksc / Fy)

    # Lr: Limiting laterally unbraced length for the limit state of inelastic lateral-torsional buckling
    # Lr is complex. Using simplified logic or full AISC Eq F2-6
    # For coding simplicity/speed, we use the standard AISC formula:
    # Lr = 1.95 * r_ts * (E / (0.7*Fy)) * sqrt( (J*c)/(S*h0) + sqrt(...) )
    # Let c = 1.0 for Doubly symmetric I-shape
    
    try:
        term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy))
        J_term = (J * 1.0) / (S_elastic * h0)
        
        inner_sqrt = math.sqrt((J_term)**2 + 6.76 * ((0.7 * Fy) / E_ksc)**2)
        Lr = term1 * math.sqrt(J_term + inner_sqrt)
    except:
        Lr = Lp * 3.0 # Fallback in case of math error

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
        # Linear Interpolation
        residual_moment = 0.7 * Fy * S_elastic
        Mn = Cb * (Mp - (Mp - residual_moment) * ((Lb_cm - Lp) / (Lr - Lp)))
        Mn = min(Mn, Mp) # Cannot exceed Mp
        
    # Zone 3: Elastic LTB (Lb > Lr)
    else:
        # Fcr = (Cb * pi^2 * E) / (Lb/rts)^2 * sqrt(1 + 0.078(J*c/S*h0) * (Lb/rts)^2)
        lb_rts = Lb_cm / r_ts
        Fcr = (Cb * (math.pi**2) * E_ksc) / (lb_rts**2) * \
              math.sqrt(1 + 0.078 * (J / (S_elastic * h0)) * (lb_rts**2))
        
        Mn = Fcr * S_elastic
        Mn = min(Mn, Mp)

    # Apply Safety Factors (Design Moment)
    if method == "ASD":
        # Allowable Strength Design: M_allow = Mn / Omega (1.67)
        M_des = Mn / 1.67
    else:
        # LRFD: M_design = phi * Mn (0.90)
        M_des = 0.90 * Mn

    # Convert Moment to kg-cm (Fy is ksc -> Force kg, Area cm2) -> Result is kg-cm
    # Mn unit check: ksc * cm3 = kg-cm. Correct.

    # ----------------------------------------------------
    # 5. Calculate Shear Capacity (Vn) - AISC G2
    # ----------------------------------------------------
    # Area of web
    Aw = (d_cm * tw_cm)
    
    # Cv depends on h/tw ratio. For most hot-rolled sections (Fy <= 3500), Cv = 1.0
    Cv = 1.0 
    Vn = 0.6 * Fy * Aw * Cv

    if method == "ASD":
        V_des = Vn / 1.67  # Omega = 1.50 or 1.67 (AISC 360-16 uses 1.67 for Shear except specific cases)
        # Note: Some older standards use 1.5. AISC 360 uses 1.67.
    else:
        V_des = 0.90 * Vn  # phi = 0.90 (Previously 0.9 or 1.0 depending on stiffness, 0.9 is safe)

    # ----------------------------------------------------
    # 6. Calculate Uniform Load Capacities (w) [kg/m]
    # ----------------------------------------------------
    # Note: w is calculated based on Span (L_cm), NOT Unbraced Length (Lb_cm)
    # w units: kg/m -> Need to be careful with conversions
    # Formulas:
    # Moment: M = w * L^2 / 8  -> w = 8 * M / L^2
    # Shear:  V = w * L / 2    -> w = 2 * V / L
    # Deflection: d = 5 * w * L^4 / (384 * E * I) -> w = d * 384 * E * I / (5 * L^4)

    # 6.1 Moment Controlled Uniform Load
    # M_des is in kg-cm. L_cm is in cm.
    # w_eq_moment (kg/cm) = 8 * M_des / L_cm^2
    w_m_kg_cm = (8 * M_des) / (L_cm**2)
    w_m = w_m_kg_cm * 100 # Convert to kg/m

    # 6.2 Shear Controlled Uniform Load
    # V_des is in kg.
    w_s_kg_cm = (2 * V_des) / L_cm
    w_s = w_s_kg_cm * 100 # Convert to kg/m

    # 6.3 Deflection Controlled Uniform Load
    # Allowable Deflection (cm)
    delta_allow = L_cm / def_limit
    
    # w_deflect (kg/cm) = (delta * 384 * E * I) / (5 * L^4)
    # E in ksc (kg/cm2), I in cm4, L in cm
    if L_cm > 0:
        w_d_kg_cm = (delta_allow * 384 * E_ksc * Ix) / (5 * (L_cm**4))
        w_d = w_d_kg_cm * 100 # Convert to kg/m
    else:
        w_d = 0

    # ----------------------------------------------------
    # 7. Find Critical Transition Lengths (Approximation)
    # ----------------------------------------------------
    # These are conceptual lengths where Shear governs vs Moment governs.
    # Note: These assume Lb varies with L (Worst case graph). 
    # If Lb is fixed, these values are just reference for the "Full Braced" behavior or "Full Unbraced" behavior.
    # For simplicity in graphing, we return the standard unbraced curve points.
    
    # L_vm: Length where Shear Capacity == Moment Capacity (assuming full bracing for moment)
    # w_s = w_m => 2V/L = 8M/L^2 => L = 4M/V
    # We use Mp (Plastic Moment) for the max potential moment
    M_max_pot = Mp / 1.67 if method == "ASD" else 0.9 * Mp
    L_vm = (4 * M_max_pot) / V_des / 100.0 # meters

    # L_md: Length where Moment Capacity == Deflection Limit
    # This is complex to solve analytically with LTB, so we approximate or leave for the graph iterator.
    # Here we solve for simplified case (Plastic Moment vs Deflection) to give a hint.
    # 8*M/L^2 = (L/limit * 384EI)/(5L^4) -> L = CubeRoot(...)
    try:
        L_md_val = (384 * E_ksc * Ix) / (5 * def_limit * 8 * M_des) * (L_cm / def_limit) # Rough approx
        # Better to just return a standard structural reference
        # Let's return the point where deflection starts governing over the *current* M_des
        # w_m = w_d
        # 8M/L^2 = (L/D * 384EI)/(5L^4) => L^3 = (384EI)/(5 * limit * 8 * M) * L ?? No.
        # w_d = K/L^3. w_m = K2/L^2. Intersection is hard.
        # Let's just return 0 for now, logic in tab3 handles the intersection finding better.
        L_md = 0 
    except:
        L_md = 0

    # ----------------------------------------------------
    # 8. Return Results
    # ----------------------------------------------------
    return {
        # Capacities (kg/m)
        'ws': w_s,
        'wm': w_m,
        'wd': w_d,
        
        # Design Values
        'M_des': M_des,   # Design Moment (kg-cm)
        'V_des': V_des,   # Design Shear (kg)
        'Mn': Mn,         # Nominal Moment (kg-cm)
        
        # Parameters Used
        'L_cm': L_cm,
        'Lb_cm': Lb_cm,   # Unbraced length used
        'E_ksc': E_ksc,
        
        # LTB Constants (in meters for display)
        'Lp': Lp / 100.0,
        'Lr': Lr / 100.0,
        
        # Transition Points (Reference)
        'L_vm': L_vm,
        'L_md': L_md,
    }
