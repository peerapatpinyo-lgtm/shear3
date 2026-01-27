import math

def core_calculation(L, Fy, E_gpa, props, method, def_limit, Lb_m=None):
    """
    Core Structural Calculation for H-Beam
    Returns a dictionary with all analysis results.
    """
    # 1. Setup Parameters
    # Convert inputs to consistent units (kg, cm)
    E_ksc = E_gpa * 10000 
    L_cm = L * 100
    
    # Unbraced Length
    if Lb_m is None:
        Lb = L_cm # Default: Lb = Span
    else:
        Lb = Lb_m * 100

    # Section Properties
    A = props['A']
    D = props['D']
    B = props['B']
    tw = props['tw']
    tf = props['tf']
    rx = props['rx']
    ry = props['ry']
    Sx = props['Sx']
    Zx = props.get('Zx', Sx * 1.1) # Use Zx from DB or est.
    Ix = props['Ix']
    Iy = props['Iy']
    rT = props.get('rT', ry * 1.2) # Est if missing
    ho = D - tf
    J = props.get('J', (2*B*tf**3 + (D-2*tf)*tw**3)/3) # Torsion const
    Cw = props.get('Cw', (Iy * ho**2) / 4) # Warping const

    # 2. Shear Capacity (Vn)
    h_tw = (D - 2*tf) / tw
    kv = 5.0 # For unstiffened webs
    
    # Cv Calculation (AISC 360-16)
    limit1 = 1.10 * math.sqrt(kv * E_ksc / Fy)
    limit2 = 1.37 * math.sqrt(kv * E_ksc / Fy)
    
    if h_tw <= limit1:
        Cv = 1.0
    elif h_tw <= limit2:
        Cv = limit1 / h_tw
    else:
        Cv = (1.51 * E_ksc * kv) / (h_tw**2 * Fy)
        
    Vn = 0.6 * Fy * A * Cv # Nominal Shear
    
    # Apply Safety Factor
    if method == "ASD":
        omega_v = 1.67
        V_des = Vn / omega_v
    else: # LRFD
        phi_v = 0.90
        V_des = phi_v * Vn

    # 3. Moment Capacity (Mn)
    # 3.1 Yielding (Plastic Moment)
    Mp = Fy * Zx
    
    # 3.2 Lateral-Torsional Buckling (LTB) parameters
    # Lp (Limit for Plastic)
    Lp = 1.76 * ry * math.sqrt(E_ksc / Fy)
    
    # Lr (Limit for Inelastic)
    # c factor simplified
    c_factor = 1.0 
    # Sxc is Sx for doubly symmetric
    r_ts = math.sqrt(math.sqrt(Iy * Cw) / Sx) # Approx rts
    
    term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy))
    term2 = (J * c_factor) / (Sx * ho)
    term3 = math.sqrt(term2**2 + 6.76 * ((0.7 * Fy) / E_ksc)**2)
    Lr = term1 * math.sqrt(term2 + term3)
    
    # Calculate Mn based on Lb zone
    Cb = 1.0 # Conservative assumption for uniform load
    
    if Lb <= Lp:
        # Zone 1: Plastic
        Mn = Mp
    elif Lb <= Lr:
        # Zone 2: Inelastic LTB
        Mn = Cb * (Mp - (Mp - 0.7 * Fy * Sx) * ((Lb - Lp) / (Lr - Lp)))
        Mn = min(Mn, Mp)
    else:
        # Zone 3: Elastic LTB
        Fcr = ((Cb * math.pi**2 * E_ksc) / (Lb / r_ts)**2) * \
              math.sqrt(1 + 0.078 * (J * c_factor / (Sx * ho)) * (Lb / r_ts)**2)
        Mn = Fcr * Sx
        Mn = min(Mn, Mp)
        
    # Apply Safety Factor
    if method == "ASD":
        omega_b = 1.67
        M_des = Mn / omega_b
    else: # LRFD
        phi_b = 0.90
        M_des = phi_b * Mn

    # 4. Limits Calculation
    # Lengths where capacity transitions occur (for graph visualization)
    # L_vm: Length where Shear controls vs Moment (Approx)
    # V_des = 4 * M_des / L -> L = 4 * M_des / V_des
    if V_des > 0:
        L_vm = (4 * M_des / V_des) / 100 # m
    else:
        L_vm = 0
        
    # L_md: Length where Deflection controls (Approx)
    # 5 w L^4 / 384 EI = L/def_lim -> w = ...
    # This is complex to solve exactly, we return approximations or just use plot data
    L_md = 10.0 # Placeholder, graph calculates real intersection

    # 5. Load Conversion (Uniform Load w)
    # We calculate 'w' that causes V_des, M_des, and Deflection Limit
    
    # 5.1 Gross Capacity in kg/cm FIRST (to avoid unit confusion)
    if L_cm > 0:
        # Shear: V = wL/2 -> w = 2V/L
        w_shear_kcm = (2 * V_des) / L_cm
        
        # Moment: M = wL^2/8 -> w = 8M/L^2
        w_moment_kcm = (8 * M_des) / (L_cm**2)
        
        # Deflection: delta = 5wL^4 / 384EI
        delta_allow = L_cm / def_limit
        w_defl_kcm = (delta_allow * 384 * E_ksc * Ix) / (5 * L_cm**4)
    else:
        w_shear_kcm = w_moment_kcm = w_defl_kcm = 0

    # 5.2 Convert to kg/m (Gross)
    w_shear = w_shear_kcm * 100
    w_moment = w_moment_kcm * 100
    w_defl = w_defl_kcm * 100
    
    # Beam Weight
    w_beam = props['W'] # kg/m

    # 6. Net Load Logic (Subtracting Beam Weight)
    if method == "LRFD":
        # Factored Dead Load = 1.2 * Beam Weight
        w_dead_factored = 1.2 * w_beam
        
        # Strength Limits (Shear & Moment) -> Subtract Factored Weight
        ws_net = max(0, w_shear - w_dead_factored)
        wm_net = max(0, w_moment - w_dead_factored)
        
        # Service Limit (Deflection) -> Subtract Unfactored Weight (Standard Practice)
        wd_net = max(0, w_defl - w_beam)
        
    else: # ASD
        # Unfactored Dead Load
        ws_net = max(0, w_shear - w_beam)
        wm_net = max(0, w_moment - w_beam)
        wd_net = max(0, w_defl - w_beam)

    # 7. Return Results
    # IMPORTANT: Must include keys 'ws', 'wm', 'wd' for Tab 3 to work!
    return {
        # Gross Capacities (kg/m)
        'ws': w_shear,
        'wm': w_moment,
        'wd': w_defl,
        
        # Net Capacities (kg/m) - Safe superimposed load
        'ws_net': ws_net,
        'wm_net': wm_net,
        'wd_net': wd_net,
        
        # Design Strengths
        'V_des': V_des, # kg
        'M_des': M_des, # kg-cm
        'Mn': Mn,
        'Vn': Vn,
        
        # Parameters
        'Lb_used': Lb / 100, # m
        'Cb': Cb,
        'Lp': Lp / 100, # m
        'Lr': Lr / 100, # m
        'E_ksc': E_ksc,
        
        # Graph Helpers
        'L_vm': L_vm,
        'L_md': L_md
    }
