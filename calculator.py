import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine
    Returns a dictionary with ALL keys required by tab1_details.py
    """
    # --- 1. Setup & Unit Conversion ---
    L = L_m * 100       # m -> cm (Total Span)
    
    if Lb_m is None:
        Lb = L          # Default: Unbraced length = Span
    else:
        Lb = Lb_m * 100 # m -> cm
        
    E = E_gpa * 10000   # GPa -> ksc
    
    # --- 2. Property Extraction (Robust) ---
    D = props['D']
    Ix = props['Ix']
    tw = props['tw']
    tf = props['tf']
    bf = props['B']
    
    # Sx & Zx Logic
    if 'Sx' in props:
        Sx = props['Sx']
    else:
        Sx = Ix / (D / 2)
        
    if 'Zx' in props:
        Zx = props['Zx']
    else:
        Zx = 1.12 * Sx

    # Derived Geom
    ry = props.get('ry', bf/4) 
    r = props.get('r', 0) 
    h = D - 2*tf - 2*r    
    J = props.get('J', 0.4 * (bf*tf**3 + (D-tf)*tw**3)) 
    
    # --- 3. Shear Calculation ---
    Aw = D * tw  # <--- [Required by Tab 1]
    Cv = 1.0
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- 4. Moment Calculation ---
    Mp = Fy * Zx
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    # LTB Parameters
    Iy = props.get('Iy', (2*tf*bf**3)/12 + ((D-2*tf)*tw**3)/12)
    Cw = (Iy * (D - tf)**2) / 4
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
    ho = D - tf
    c_const = 1.0
    
    term_sqrt = math.sqrt(((J*c_const)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2)
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J*c_const)/(Sx*ho) + term_sqrt)

    # Determine Zone & Mn
    Zone = ""
    if Lb <= Lp:
        Mn_ltb = Mp
        Zone = "Zone 1 (Plastic)"
    elif Lb > Lp and Lb <= Lr:
        Cb = 1.0 
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp)/(Lr - Lp)))
        Mn_ltb = min(Mn_ltb, Mp)
        Zone = "Zone 2 (Inelastic)"
    else:
        Cb = 1.0
        Fcr = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * math.sqrt(1 + 0.078 * (J*c_const)/(Sx*ho) * (Lb/rts)**2)
        Mn_ltb = Fcr * Sx
        Mn_ltb = min(Mn_ltb, Mp)
        Zone = "Zone 3 (Elastic)"
        
    Mn = min(Mp, Mn_ltb)
    
    # --- 5. Apply Method Factors (ASD/LRFD) ---
    # เตรียมตัวแปรให้ครบ เพื่อไม่ให้ Tab 1 Error
    omega_v = 1.50
    omega_b = 1.67
    phi_v = 1.00
    phi_b = 0.90
    
    if method == "ASD":
        V_des = Vn / omega_v
        M_des = Mn / omega_b
        # Text for report
        txt_v_method = r"V_{design} = \frac{V_n}{\Omega_v}"
        txt_m_method = r"M_{design} = \frac{M_n}{\Omega_b}"
    else: # LRFD
        V_des = phi_v * Vn
        M_des = phi_b * Mn
        # Text for report
        txt_v_method = r"V_{design} = \phi_v V_n"
        txt_m_method = r"M_{design} = \phi_b M_n"

    # --- 6. Uniform Load Conversion ---
    w_shear = (2 * V_des) / (L/100) 
    w_moment = (8 * M_des) / ((L/100)**2)
    
    # Deflection
    delta_allow = L / def_limit
    w_defl = (delta_allow * 384 * E * Ix) / (5 * L**4)
    
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

    # --- RETURN DICTIONARY (MUST MATCH TAB 1 REQUIREMENTS) ---
    return {
        # Input/Config
        'E_ksc': E,
        'L_cm': L,
        'Lb': Lb/100,          # m
        'Lb_used': Lb/100,     # m
        'def_limit': def_limit,
        
        # Section Props
        'Sx': Sx,
        'Zx': Zx,
        'Aw': Aw,              # <--- Fixed KeyError
        
        # Shear
        'Vn': Vn,
        'V_des': V_des,
        'ws': w_shear,
        'txt_v_method': txt_v_method, # <--- Fixed KeyError
        'omega_v': omega_v,           # <--- Fixed KeyError (passed even if LRFD)
        'phi_v': phi_v,               # <--- Fixed KeyError (passed even if ASD)
        
        # Moment
        'Mp': Mp,
        'Mn': Mn,
        'M_des': M_des,
        'M_des_full': M_des,   # <--- Fixed KeyError (Used in Derivation)
        'wm': w_moment,
        'txt_m_method': txt_m_method, # <--- Fixed KeyError
        'omega_b': omega_b,
        'phi_b': phi_b,
        
        # LTB info
        'Lp': Lp/100,          # m
        'Lr': Lr/100,          # m
        'Zone': Zone,          # <--- Fixed KeyError
        
        # Deflection
        'delta': delta_allow,  # <--- Fixed KeyError
        'wd': w_defl,
        
        # Transitions
        'L_vm': L_vm_val,
        'L_md': L_md_val
    }
