# calculator.py
import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine (AISC 360-16 / EIT Compliant)
    """
    # --- 1. Setup & Unit Conversion ---
    L = L_m * 100        # m -> cm
    if Lb_m is None:
        Lb = L           # Default Lb = Span
    else:
        Lb = Lb_m * 100
        
    # 1 GPa = 10197.16 kg/cm2
    E = E_gpa * 10197.16 
    
    # Dimensions (mm -> cm)
    D = props['D'] / 10.0
    B = props['B'] / 10.0
    tw = props['tw'] / 10.0
    tf = props['tf'] / 10.0
    
    # Properties
    Ix = props['Ix']
    Iy = props['Iy']
    Sx = props['Sx_table'] # Elastic Modulus from Table
    A = props['A']
    
    # Calculate Plastic Modulus (Zx)
    h_web = D - (2 * tf)
    Zx = (B * tf * (D - tf)) + (tw * (h_web**2) / 4)
    
    # Derived Geometrics
    r = props.get('r', tf) / 10.0 
    ho = D - tf
    ry = math.sqrt(Iy / A)
    
    # Torsional Constant (J)
    J = props.get('J', 0.4 * (B*tf**3 + (D-tf)*tw**3))
    Cw = (Iy * ho**2) / 4
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)

    # --- 2. Compactness ---
    Mp = Fy * Zx
    
    # --- 3. Shear Calculation ---
    Cv = 1.0 
    Aw = D * tw
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- 4. Moment Calculation (LTB) ---
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    c_const = 1.0
    term_sqrt = math.sqrt(((J*c_const)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2)
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J*c_const)/(Sx*ho) + term_sqrt)
    
    Cb = 1.14 
    
    Zone = ""
    if Lb <= Lp:
        Mn_ltb = Mp
        Zone = "Zone 1 (Plastic)"
    elif Lb > Lp and Lb <= Lr:
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp)/(Lr - Lp)))
        Mn_ltb = min(Mn_ltb, Mp)
        Zone = "Zone 2 (Inelastic)"
    else:
        Fcr = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * math.sqrt(1 + 0.078 * (J*c_const)/(Sx*ho) * (Lb/rts)**2)
        Mn_ltb = Fcr * Sx
        Mn_ltb = min(Mn_ltb, Mp)
        Zone = "Zone 3 (Elastic)"
        
    Mn = min(Mp, Mn_ltb)
    
    # --- 5. Apply Method Factors ---
    omega_v = 1.50
    omega_b = 1.67
    phi_v = 1.00
    phi_b = 0.90
    
    if method == "ASD":
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        txt_v = r"V_n / \Omega_v"
        txt_m = r"M_n / \Omega_b"
    else: # LRFD
        V_des = phi_v * Vn
        M_des = phi_b * Mn
        txt_v = r"\phi_v V_n"
        txt_m = r"\phi_b M_n"

    # --- 6. Capacity to Uniform Load Conversion & Net Load ---
    
    # Shear & Moment
    w_shear_cap = (2 * V_des) / (L/100)        # kg/m
    w_moment_cap = (8 * M_des) / ((L/100)**2)  # kg/m
    
    # Deflection Limit
    delta_allow = L / def_limit
    
    # [FIXED] - Multiply by 100 to convert kg/cm -> kg/m
    w_defl_cap = ((delta_allow * 384 * E * Ix) / (5 * L**4)) * 100
    
    # Beam Weight (kg/m)
    w_beam = props['W']
    
    if method == "LRFD":
        # Strength Checks: Deduct FACTORED Dead Load
        factored_dead_load = 1.2 * w_beam
        ws_net = max(0, w_shear_cap - factored_dead_load)
        wm_net = max(0, w_moment_cap - factored_dead_load)
        
        # Serviceability Check: Deduct UNFACTORED Dead Load
        wd_net = max(0, w_defl_cap - w_beam)
    else:
        # ASD: Deduct UNFACTORED Dead Load
        factored_dead_load = 1.0 * w_beam
        ws_net = max(0, w_shear_cap - factored_dead_load)
        wm_net = max(0, w_moment_cap - factored_dead_load)
        wd_net = max(0, w_defl_cap - w_beam)

    # Transition Points calculation
    if V_des > 0:
        L_vm = (4 * M_des / V_des) / 100
    else: 
        L_vm = 0
        
    K_defl = (384 * E * Ix) / (5 * def_limit)
    if M_des > 0:
        L_md = (K_defl / (8 * M_des)) / 100
    else:
        L_md = 0

    return {
        'E_ksc': E,
        'L_cm': L,
        'Lb': Lb/100,
        
        # Properties
        'Sx': Sx,
        'Zx': Zx,
        'Aw': Aw,
        'Ix': Ix,
        
        # Capacities
        'Vn': Vn, 'V_des': V_des, 
        'Mp': Mp, 'Mn': Mn, 'M_des': M_des, 'M_des_full': M_des,
        'Cv': Cv, # <--- FIXED: Changed from 'cv' to 'Cv' to match tab1_details.py
        
        # Factors text
        'txt_v_method': txt_v, 'txt_m_method': txt_m,
        'omega_v': omega_v, 'phi_v': phi_v,
        'omega_b': omega_b, 'phi_b': phi_b,
        
        # LTB
        'Lp': Lp/100, 'Lr': Lr/100, 'Zone': Zone,
        
        # Deflection
        'delta': delta_allow,
        
        # LOADS (Gross & Net)
        'ws_gross': w_shear_cap,
        'wm_gross': w_moment_cap,
        'wd_gross': w_defl_cap,
        'w_beam': w_beam,
        'factored_dead_load': factored_dead_load,
        
        # Net Results
        'ws_net': ws_net,
        'wm_net': wm_net,
        'wd_net': wd_net,
        
        'L_vm': L_vm, 'L_md': L_md
    }
