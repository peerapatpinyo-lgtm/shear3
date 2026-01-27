import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Main Beam Calculation Engine
    Lb_m: Unbraced Length (m). If None, defaults to L_m (Span)
    """
    # 1. Unit Conversion
    L = L_m * 100       # m -> cm (Total Span)
    
    # [Logic Update] Handle Unbraced Length
    if Lb_m is None:
        Lb = L          # Default: Unbraced length = Span
    else:
        Lb = Lb_m * 100 # m -> cm
        
    E = E_gpa * 10000   # GPa -> ksc
    
    # Properties
    Zx = props['Zx']
    Sx = props['Sx']
    Ix = props['Ix']
    ry = props['ry']
    D = props['D']
    t1 = props['tw']
    t2 = props['tf']
    bf = props['B']
    r = props.get('r', 0) # radius
    h = D - 2*t2 - 2*r    # clear web depth
    J = props.get('J', 0.4 * (bf*t2**3 + (D-t2)*t1**3)) # Approx if not in DB
    
    # --- 2. Shear Capacity (Vn) ---
    Aw = D * t1
    Cv = 1.0 # For rolled shapes with h/tw <= 2.24 sqrt(E/Fy)
    Vn = 0.6 * Fy * Aw * Cv
    
    # --- 3. Moment Capacity (Mn) ---
    # 3.1 Yielding
    Mp = Fy * Zx
    
    # 3.2 Lateral-Torsional Buckling (LTB) using Lb
    Lp = 1.76 * ry * math.sqrt(E/Fy)
    
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx) if 'Cw' in props and 'Iy' in props else bf/4 # Simplified approximation
    ho = D - t2
    c = 1.0
    if 'J' in props and 'Sx' in props:
       J_val = props['J']
    else:
       J_val = 1.0 # Dummy fallback
       
    # Simplified Lr for Rolled Sections (AISC F2-6)
    # Note: Using simplified logic for brevity, recommend full AISC F2 equations for production
    Lr = 1.95 * rts * (E/(0.7*Fy)) * math.sqrt((J_val*c)/(Sx*ho) + math.sqrt(((J_val*c)/(Sx*ho))**2 + 6.76*((0.7*Fy)/E)**2))
    # Fallback approximation if complex props missing
    if Lr < Lp: Lr = 4.0 * Lp 

    Mn_ltb = Mp
    if Lb <= Lp:
        Mn_ltb = Mp
    elif Lb > Lp and Lb <= Lr:
        Cb = 1.0 # Conservative
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp)/(Lr - Lp)))
        Mn_ltb = min(Mn_ltb, Mp)
    else:
        # Elastic Buckling
        Fcr = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * math.sqrt(1 + 0.078 * (J_val*c)/(Sx*ho) * (Lb/rts)**2)
        Mn_ltb = Fcr * Sx
        Mn_ltb = min(Mn_ltb, Mp)
        
    # Governing Mn
    Mn = min(Mp, Mn_ltb)
    
    # --- 4. Apply Safety Factors ---
    if method == "ASD":
        Omega_v = 1.67 if (h/t1) <= 2.24*math.sqrt(E/Fy) else 1.50 # Simplified
        Omega_v = 1.50 # Common for rolled I-beams shear
        Omega_b = 1.67
        
        V_des = Vn / Omega_v
        M_des = Mn / Omega_b
    else: # LRFD
        Phi_v = 1.00 # Shear yielding
        Phi_b = 0.90
        
        V_des = Phi_v * Vn
        M_des = Phi_b * Mn

    # --- 5. Convert to Distributed Load (w) ---
    # Shear Control: V_u = wL/2 -> w = 2V/L
    w_shear = (2 * V_des) / (L/100) 
    
    # Moment Control: M_u = wL^2/8 -> w = 8M/L^2
    w_moment = (8 * M_des) / ((L/100)**2)
    
    # Deflection Control
    # delta = 5wL^4 / (384EI) -> w = delta * 384EI / 5L^4
    delta_allow = L / def_limit
    w_defl = (delta_allow * 384 * E * Ix) / (5 * L**4)
    
    return {
        'ws': w_shear,
        'wm': w_moment,
        'wd': w_defl,
        'V_des': V_des,
        'M_des': M_des,
        'L_vm': 0, # Placeholder for intersection points
        'L_md': 0,
        'E_ksc': E,
        'Lb_used': Lb/100 # return Lb used in calculation
    }
