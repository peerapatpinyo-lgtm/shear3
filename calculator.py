# calculator.py
import math

def core_calculation(L_m, Fy, E_gpa, props, method="ASD", def_limit=360, Lb_m=None):
    """
    Core Structural Calculation Function
    """
    
    # ----------------------------------------------------
    # 1. Unit Conversion & Constants
    # ----------------------------------------------------
    L_cm = L_m * 100.0
    
    # Check Lb (Unbraced Length)
    if Lb_m is not None and Lb_m > 0:
        Lb_cm = Lb_m * 100.0
    else:
        Lb_cm = L_cm 

    E_ksc = E_gpa * 10000 
    Cb = 1.0 

    # ----------------------------------------------------
    # 2. Extract Section Properties
    # ----------------------------------------------------
    # Extract raw data
    Ix = props.get('Ix', 0)
    Iy = props.get('Iy', 0)
    
    # --- Mapping Definitions ---
    # ใน Database SYS: 'Zx' มักหมายถึง Elastic Section Modulus (S ในตำรา AISC)
    # เราจะ map ให้ตรงกับตัวแปรทางวิศวกรรมสากล
    S_elastic = props.get('Zx', 0) 
    
    # Plastic Modulus (Z): ถ้าไม่มีใน DB ให้ประมาณค่า Z ≈ 1.1 * S
    Z_plastic = props.get('Zy', 1.1 * S_elastic) 

    r_x = props.get('rx', 0)
    r_y = props.get('ry', 0)
    
    d = props.get('D', 0)      
    bf = props.get('B', 0)     
    tf = props.get('t2', 0)    
    tw = props.get('t1', 0)    
    
    d_cm = d / 10.0
    bf_cm = bf / 10.0
    tf_cm = tf / 10.0
    tw_cm = tw / 10.0

    # Torsional Constant (J)
    if props.get('Ix', 0) > 0:
        # Fallback approximation for J if not in DB
        J = props.get('J', props['Ix'] * 0.02) 
    else:
        J = 1.0 

    # Calculate Geometric Properties for LTB
    h0 = max(1.0, d_cm - tf_cm) 
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
    # 3. Calculate LTB Limits (Lp, Lr)
    # ----------------------------------------------------
    # Lp
    try:
        Lp = 1.76 * r_y * math.sqrt(E_ksc / Fy)
    except:
        Lp = 0

    # Lr
    try:
        term1 = 1.95 * r_ts * (E_ksc / (0.7 * Fy))
        J_term = (J * 1.0) / (S_elastic * h0)
        inner_sqrt = math.sqrt((J_term)**2 + 6.76 * ((0.7 * Fy) / E_ksc)**2)
        Lr = term1 * math.sqrt(J_term + inner_sqrt)
    except:
        Lr = Lp * 3.0 # Fallback

    # ----------------------------------------------------
    # 4. Calculate Nominal Moment Capacity (Mn)
    # ----------------------------------------------------
    Mp = Fy * Z_plastic
    Mn = 0
    
    # Zone 1: Plastic
    if Lb_cm <= Lp:
        Mn = Mp
        
    # Zone 2: Inelastic LTB
    elif Lb_cm <= Lr:
        if (Lr - Lp) != 0:
            residual_moment = 0.7 * Fy * S_elastic
            Mn = Cb * (Mp - (Mp - residual_moment) * ((Lb_cm - Lp) / (Lr - Lp)))
        else:
            Mn = Mp
        Mn = min(Mn, Mp)
        
    # Zone 3: Elastic LTB
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
            Mn = 0.5 * Mp 
            
        Mn = min(Mn, Mp)

    # Design Moment
    if method == "ASD":
        M_des = Mn / 1.67
    else:
        M_des = 0.90 * Mn

    # ----------------------------------------------------
    # 5. Calculate Shear Capacity (Vn)
    # ----------------------------------------------------
    Aw = (d_cm * tw_cm)
    Cv = 1.0 
    Vn = 0.6 * Fy * Aw * Cv

    if method == "ASD":
        V_des = Vn / 1.67
    else:
        V_des = 0.90 * Vn

    # ----------------------------------------------------
    # 6. Calculate Uniform Load Capacities (w)
    # ----------------------------------------------------
    # 6.1 Moment Controlled
    if L_cm > 0:
        w_m = ((8 * M_des) / (L_cm**2)) * 100 
    else:
        w_m = 0

    # 6.2 Shear Controlled
    if L_cm > 0:
        w_s = ((2 * V_des) / L_cm) * 100 
    else:
        w_s = 0

    # 6.3 Deflection Controlled
    delta_allow = L_cm / def_limit
    if L_cm > 0:
        w_d = ((delta_allow * 384 * E_ksc * Ix) / (5 * (L_cm**4))) * 100 
    else:
        w_d = 0

    # ----------------------------------------------------
    # 7. Find Critical Transition Lengths
    # ----------------------------------------------------
    M_max_pot = Mp / 1.67 if method == "ASD" else 0.9 * Mp
    
    if V_des > 0:
        L_vm = (4 * M_max_pot) / V_des / 100.0 
    else:
        L_vm = 0 
        
    L_md = 0 

    # ----------------------------------------------------
    # 8. Return Results (FIXED: Added Section Props)
    # ----------------------------------------------------
    return {
        # Capacities
        'ws': w_s,
        'wm': w_m,
        'wd': w_d,
        'M_des': M_des,   
        'V_des': V_des,   
        'Mn': Mn,         
        
        # Section Props (Added to fix KeyError)
        'Sx': S_elastic, 
        'Zx': Z_plastic,
        'Ix': Ix,
        'Iy': Iy,
        
        # Parameters
        'L_cm': L_cm,
        'Lb_cm': Lb_cm,   
        'E_ksc': E_ksc,
        
        # LTB info
        'Lp': Lp / 100.0,
        'Lr': Lr / 100.0,
        'L_vm': L_vm,
        'L_md': L_md,
    }
