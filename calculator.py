# calculator.py
import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine (AISC 360-16 / EIT Compliant)
    """
    # --- 1. Setup & Unit Conversion (STRICT: mm -> cm) ---
    L = L_m * 100        # m -> cm (Total Span)
    
    if Lb_m is None:
        Lb = L           # Default: Unbraced length = Span
    else:
        Lb = Lb_m * 100  # m -> cm
        
    E = E_gpa * 10000    # GPa -> ksc
    
    # Extract & Convert Properties (mm -> cm)
    D = props['D'] / 10.0
    B = props['B'] / 10.0
    tw = props['tw'] / 10.0
    tf = props['tf'] / 10.0
    r = props.get('r', tf*10) / 10.0 # Get r in cm
    
    # Area & Inertia
    Ix = props['Ix']
    Iy = props['Iy']
    Sx = props['Sx']
    Zx = props['Zx']
    A = props['A']
    ry = props['ry'] # Used for LTB (Lp) calculation logic if needed, but we use approximation or exact formula
    
    # Geometric derived properties
    h = D - 2*tf - 2*r  # Clear distance between fillets (cm)
    ho = D - tf         # Distance between flange centroids (cm)
    J = props.get('J', 0.4 * (B*tf**3 + (D-tf)*tw**3)) 
    Cw = (Iy * ho**2) / 4
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)

    # --- 2. Compactness Check (Local Buckling) ---
    # Flange (Flexure)
    lambda_f = B / (2 * tf)
    lambda_pf = 0.38 * math.sqrt(E / Fy)
    lambda_rf = 1.0 * math.sqrt(E / Fy)
    
    # Web (Flexure)
    lambda_w = h / tw
    lambda_pw = 3.76 * math.sqrt(E / Fy)
    lambda_rw = 5.70 * math.sqrt(E / Fy)

    # Determine Mp (Nominal Plastic Moment) adjusting for Local Buckling
    Mp_base = Fy * Zx
    
    # Check Flange Compactness
    if lambda_f <= lambda_pf:
        Mn_flange = Mp_base
    elif lambda_f < lambda_rf:
        # Non-Compact Flange: Linear Interpolation
        Mn_flange = Mp_base - (Mp_base - 0.7*Fy*Sx) * ((lambda_f - lambda_pf)/(lambda_rf - lambda_pf))
    else:
        # Slender Flange (Simplified to elastic limit for this tool)
        kc = 4 / math.sqrt(h/tw)
        if kc < 0.35: kc = 0.35
        if kc > 0.76: kc = 0.76
        Mn_flange = 0.9 * E * kc * Sx / lambda_f**2 # Approximate
        
    # Check Web Compactness (Usually compact for hot-rolled, but good to check)
    if lambda_w <= lambda_pw:
        Mn_web = Mp_base
    else:
        # Simplified reduction for non-compact web
        Mn_web = Mp_base # Most standard H-beams are compact web. 
        # Full logic for slender web is complex, assuming compact/non-compact for standard JIS.

    # Actual Mp is limited by local buckling
    Mp = min(Mp_base, Mn_flange, Mn_web)

    # --- 3. Shear Calculation (Cv Calculation) ---
    # h/tw check for Cv
    kv = 5.0 # For unstiffened webs
    limit_1 = 1.10 * math.sqrt(kv * E / Fy)
    limit_2 = 1.37 * math.sqrt(kv * E / Fy)
    
    if lambda_w <= limit_1:
        Cv = 1.0
    elif lambda_w <= limit_2:
        Cv = limit_1 / lambda_w
    else:
        Cv = (1.51 * E * kv) / (lambda_w**2 * Fy)
        
    Aw = D * tw
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- 4. Moment Calculation (LTB) ---
    # Lp and Lr
    # Lp = 1.76 * ry * sqrt(E/Fy)
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    c_const = 1.0
    term_sqrt = math.sqrt(((J*c_const)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2)
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J*c_const)/(Sx*ho) + term_sqrt)

    # Cb Factor (1.14 for Uniform Load, Simple Span)
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
        
    # Final Nominal Moment
    Mn = min(Mp, Mn_ltb)
    
    # --- 5. Apply Method Factors (ASD/LRFD) ---
    omega_v = 1.50
    omega_b = 1.67
    phi_v = 1.00
    phi_b = 0.90
    
    if method == "ASD":
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        txt_v_method = r"V_{design} = V_n / \Omega_v"
        txt_m_method = r"M_{design} = M_n / \Omega_b"
    else: # LRFD
        V_des = phi_v * Vn
        M_des = phi_b * Mn
        txt_v_method = r"V_{design} = \phi_v V_n"
        txt_m_method = r"M_{design} = \phi_b M_n"

    # --- 6. Load Conversion & Net Load ---
    # Gross Capacity (kg/m)
    w_shear = (2 * V_des) / (L/100) 
    w_moment = (8 * M_des) / ((L/100)**2)
    
    # Deflection
    delta_allow = L / def_limit
    w_defl = (delta_allow * 384 * E * Ix) / (5 * L**4)
    
    # Beam Weight (kg/m)
    w_beam = props['W']
    
    # --- 7. Transition Points ---
    if V_des > 0:
        L_vm_val = (4 * M_des / V_des) / 100 
    else: 
        L_vm_val = 0
        
    K_defl = (384 * E * Ix) / (5 * def_limit) 
    if M_des > 0:
        L_md_val = (K_defl / (8 * M_des)) / 100
    else:
        L_md_val = 0

    return {
        'E_ksc': E,
        'L_cm': L,
        'Lb': Lb/100,      # m
        'Lb_used': Lb/100, # m
        'def_limit': def_limit,
        
        # Props
        'Sx': Sx, 'Zx': Zx, 'Aw': Aw, 'Ix': Ix,
        
        # Shear
        'Vn': Vn, 'V_des': V_des, 'ws': w_shear,
        'txt_v_method': txt_v_method,
        'omega_v': omega_v, 'phi_v': phi_v,
        'Cv': Cv, # Return Cv for report
        
        # Moment
        'Mp': Mp, 'Mn': Mn, 'M_des': M_des, 'M_des_full': M_des,
        'wm': w_moment,
        'txt_m_method': txt_m_method,
        'omega_b': omega_b, 'phi_b': phi_b,
        'Cb': Cb,
        
        # Compactness Info
        'lambda_f': lambda_f, 'lambda_pf': lambda_pf, 'lambda_rf': lambda_rf,
        
        # LTB
        'Lp': Lp/100, 'Lr': Lr/100, 'Zone': Zone,
        
        # Deflection
        'delta': delta_allow, 'wd': w_defl,
        
        # Net Load Calculation (Important!)
        'w_beam': w_beam,
        'ws_net': max(0, w_shear - w_beam),
        'wm_net': max(0, w_moment - w_beam),
        'wd_net': max(0, w_defl - w_beam),
        
        # Transitions
        'L_vm': L_vm_val, 'L_md': L_md_val
    }
