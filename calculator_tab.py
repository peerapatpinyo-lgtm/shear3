# calculator_tab.py
import math

def check_geometry(inputs):
    """
    ตรวจสอบมิติทางกายภาพตามมาตรฐาน AISC (Geometry Checks)
    คืนค่า: list ของ error messages (ถ้าว่างแปลว่าผ่าน)
    """
    errors = []
    warnings = []
    
    db = inputs['bolt_dia']
    pitch = inputs['pitch']
    lev = inputs['lev'] # Vertical Edge
    leh = inputs['leh_beam'] # Horizontal Edge
    tp = inputs['plate_t']
    weld = inputs['weld_sz']

    # 1. Min Spacing (AISC J3.3) -> Standard 2.67d, Preferred 3d
    min_spacing = 2.67 * db
    if pitch < min_spacing:
        errors.append(f"❌ Bolt Pitch ({pitch} mm) < Min Spacing ({min_spacing:.1f} mm)")

    # 2. Min Edge Distance (AISC Table J3.4)
    # Simplified lookup based on AISC Table J3.4
    if db <= 16: min_edge = 22
    elif db <= 20: min_edge = 26
    elif db <= 22: min_edge = 28
    elif db <= 24: min_edge = 30
    elif db <= 30: min_edge = 38
    else: min_edge = 1.25 * db
    
    if lev < min_edge:
        errors.append(f"❌ Vertical Edge ({lev} mm) < Min Edge ({min_edge} mm)")
    if leh < min_edge:
        errors.append(f"❌ Horizontal Edge ({leh} mm) < Min Edge ({min_edge} mm)")

    # 3. Weld Limitations (AISC J2.2b)
    # Min weld size based on thinner part joined
    # Assume connecting to beam web >= plate thickness usually
    t_min_part = tp # conservative
    if t_min_part <= 6: min_w = 3
    elif t_min_part <= 13: min_w = 5
    elif t_min_part <= 19: min_w = 6
    else: min_w = 8
    
    if weld < min_w:
        warnings.append(f"⚠️ Weld Size ({weld} mm) < AISC Min ({min_w} mm) for {t_min_part}mm plate")
    
    # Max weld size (AISC J2.2b): Max = t - 2mm (if t >= 6mm)
    max_w = max(tp - 2, tp) 
    if weld > max_w:
        errors.append(f"❌ Weld Size ({weld} mm) > Max Allowed ({max_w} mm)")

    return errors, warnings

def calculate_shear_tab(inputs):
    """
    Ultimate Calculation Logic for Shear Tab Connection
    Includes: Shear, Bearing, Block Shear, Weld Eccentricity, AND Plate Flexure.
    """
    results = {}
    
    # --- 0. Geometry Check ---
    geo_errors, geo_warnings = check_geometry(inputs)
    results['geometry'] = {'errors': geo_errors, 'warnings': geo_warnings}
    
    # If Critical Errors, stop calculation or flag it
    if geo_errors:
        results['critical_error'] = True
        return results # Return early with errors
    else:
        results['critical_error'] = False

    # --- 1. Unpack & Factors ---
    method = inputs['method'] 
    Vu = inputs['load']
    
    # Plate
    Fy_pl = 2500 if inputs['plate_mat'] == 'SS400' else (2530 if inputs['plate_mat'] == 'A36' else 3500)
    Fu_pl = 4100 if inputs['plate_mat'] == 'SS400' else (4080 if inputs['plate_mat'] == 'A36' else 4570)
    tp_cm = inputs['plate_t'] / 10.0
    h_pl_cm = inputs['plate_h'] / 10.0
    
    # Beam Web
    Fy_bm = inputs['beam_fy']
    Fu_bm = 4000 if Fy_bm <= 2500 else 4500
    tw_bm_cm = inputs['beam_tw'] / 10.0
    
    # Bolt
    db = inputs['bolt_dia']
    db_cm = db / 10.0
    Ab = (math.pi * db_cm**2) / 4
    n_rows = inputs['n_rows']
    
    # Factors
    if method == "ASD":
        omega = 1.67; omega_v = 1.50; omega_r = 2.00; omega_w = 2.00; omega_b = 1.67
        phi = 1.0   ; phi_v = 1.0   ; phi_r = 1.0   ; phi_w = 1.0   ; phi_b = 1.0
        txt = "1/\Omega"
    else:
        omega = 1.0 ; omega_v = 1.0 ; omega_r = 1.0 ; omega_w = 1.0 ; omega_b = 1.0
        phi = 0.90  ; phi_v = 1.00  ; phi_r = 0.75  ; phi_w = 0.75  ; phi_b = 0.90
        txt = "\phi"

    # ==========================================
    # CHECK 1: BOLT SHEAR
    # ==========================================
    Fnv = 4690 if "A490" in inputs['bolt_grade'] else (3720 if "A325" in inputs['bolt_grade'] else 2500)
    Rn_bolt = Fnv * Ab * n_rows
    cap_bolt = Rn_bolt / omega_r if method == "ASD" else phi_r * Rn_bolt
    
    results['bolt_shear'] = {
        'title': '1. Bolt Shear',
        'ref': 'AISC J3.6',
        'eq': r'R_n = F_{nv} A_b n',
        'sub': f'{Fnv} \\times {Ab:.2f} \\times {n_rows} = {Rn_bolt:,.0f}',
        'cap': cap_bolt, 'ratio': Vu/cap_bolt
    }

    # ==========================================
    # CHECK 2: BEARING (Governing)
    # ==========================================
    # Plate Bear
    lc_pl = inputs['lev']/10.0 - (db_cm/2 + 0.1)
    rn_pl = min(1.2*lc_pl*tp_cm*Fu_pl, 2.4*db_cm*tp_cm*Fu_pl) # Edge
    rn_pl_in = min(1.2*(inputs['pitch']/10.0 - db_cm - 0.2)*tp_cm*Fu_pl, 2.4*db_cm*tp_cm*Fu_pl) # Inner
    Rn_bear_pl = rn_pl + rn_pl_in*(n_rows-1)
    
    # Web Bear
    lc_wb = inputs['leh_beam']/10.0 - (db_cm/2 + 0.1)
    rn_wb = min(1.2*lc_wb*tw_bm_cm*Fu_bm, 2.4*db_cm*tw_bm_cm*Fu_bm)
    rn_wb_in = min(1.2*(inputs['pitch']/10.0 - db_cm - 0.2)*tw_bm_cm*Fu_bm, 2.4*db_cm*tw_bm_cm*Fu_bm)
    Rn_bear_wb = rn_wb + rn_wb_in*(n_rows-1)
    
    Rn_bear = min(Rn_bear_pl, Rn_bear_wb)
    ctrl = "Plate" if Rn_bear_pl < Rn_bear_wb else "Beam Web"
    cap_bear = Rn_bear / omega_r if method == "ASD" else phi_r * Rn_bear
    
    results['bearing'] = {
        'title': f'2. Bolt Bearing ({ctrl})',
        'ref': 'AISC J3.10',
        'eq': r'R_n = \sum \min(1.2 l_c t F_u, 2.4 d t F_u)',
        'sub': f'Min({Rn_bear_pl:,.0f}, {Rn_bear_wb:,.0f})',
        'cap': cap_bear, 'ratio': Vu/cap_bear
    }

    # ==========================================
    # CHECK 3: SHEAR YIELD (PLATE)
    # ==========================================
    Ag = h_pl_cm * tp_cm
    Rn_y = 0.60 * Fy_pl * Ag
    cap_y = Rn_y / omega_v if method == "ASD" else phi_v * Rn_y
    
    results['shear_yield'] = {
        'title': '3. Plate Shear Yield',
        'ref': 'AISC J4.2',
        'eq': r'R_n = 0.60 F_y A_g',
        'sub': f'0.6 \\times {Fy_pl} \\times {Ag:.2f} = {Rn_y:,.0f}',
        'cap': cap_y, 'ratio': Vu/cap_y
    }

    # ==========================================
    # CHECK 4: SHEAR RUPTURE (PLATE)
    # ==========================================
    d_hole = db_cm + 0.2
    Anv = Ag - (n_rows * d_hole * tp_cm)
    Rn_rup = 0.60 * Fu_pl * Anv
    cap_rup = Rn_rup / omega_r if method == "ASD" else phi_r * Rn_rup
    
    results['shear_rup'] = {
        'title': '4. Plate Shear Rupture',
        'ref': 'AISC J4.2',
        'eq': r'R_n = 0.60 F_u A_{nv}',
        'sub': f'0.6 \\times {Fu_pl} \\times {Anv:.2f} = {Rn_rup:,.0f}',
        'cap': cap_rup, 'ratio': Vu/cap_rup
    }

    # ==========================================
    # CHECK 5: BLOCK SHEAR
    # ==========================================
    leh_pl = (inputs['plate_w']/10.0) - (inputs['leh_beam']/10.0)
    Ant = (leh_pl - 0.5*d_hole) * tp_cm
    Agv = ((n_rows-1)*(inputs['pitch']/10.0) + (inputs['lev']/10.0)) * tp_cm
    Anv_bs = Agv - ((n_rows-0.5)*d_hole*tp_cm)
    
    Rn_bs = min(0.6*Fu_pl*Anv_bs + 1.0*Fu_pl*Ant, 0.6*Fy_pl*Agv + 1.0*Fu_pl*Ant)
    cap_bs = Rn_bs / omega_r if method == "ASD" else phi_r * Rn_bs
    
    results['block_shear'] = {
        'title': '5. Block Shear',
        'ref': 'AISC J4.3',
        'eq': r'R_n = \min(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, ...)',
        'sub': f'Min(...) = {Rn_bs:,.0f}',
        'cap': cap_bs, 'ratio': Vu/cap_bs
    }
    
    # ==========================================
    # CHECK 6: WELD (ECCENTRIC)
    # ==========================================
    # Using Elastic Method (Conservative & Traceable)
    ex = (inputs['plate_w']/10.0) - leh_pl # Distance weld to bolt line
    te = 0.707 * (inputs['weld_sz']/10.0)
    Lw = h_pl_cm
    Aw = 2 * Lw * te
    Sw = (2 * te * Lw**2) / 6.0 # Section Modulus of weld line
    
    fv = Vu / Aw
    fb = (Vu * ex) / Sw
    fr = math.sqrt(fv**2 + fb**2)
    
    Fexx = 4920
    Fnw = 0.60 * Fexx
    Fall = Fnw / omega_w if method == "ASD" else phi_w * Fnw
    ratio_w = fr / Fall
    cap_w = Vu / ratio_w if ratio_w > 0 else 999999
    
    results['weld'] = {
        'title': '6. Weld Strength (Eccentric)',
        'ref': 'AISC Part 8',
        'eq': r'f_r = \sqrt{f_v^2 + f_b^2} \le \phi F_{nw}',
        'sub': f'e={ex:.1f}cm, f_r={fr:.1f} ksc, F_{{all}}={Fall:,.0f}',
        'cap': cap_w, 'ratio': ratio_w
    }

    # ==========================================
    # CHECK 7: PLATE FLEXURE (BENDING) - NEW!
    # ==========================================
    # The plate acts as a cantilever beam from weld to bolt line
    # Eccentricity e = distance from weld to Center of Gravity of bolts
    # Moment Mu = Vu * e
    
    Mu = Vu * ex # kg-cm
    
    # 7.1 Flexural Yielding (Mn = Fy * Z) -> Z of rectangular plate = t*h^2 / 4
    Z_gross = (tp_cm * h_pl_cm**2) / 4.0
    Mn_y = Fy_pl * Z_gross
    cap_m_y = Mn_y / omega if method == "ASD" else phi_b * Mn_y
    load_cap_my = cap_m_y / ex if ex > 0 else 999999
    
    results['flex_yield'] = {
        'title': '7. Plate Flexural Yielding',
        'ref': 'AISC Manual Part 15 / F11',
        'eq': r'M_n = F_y Z_{gross}',
        'sub': f'Z={Z_gross:.1f} cm^3, M_n={Mn_y:,.0f} kg-cm',
        'cap': load_cap_my, 'ratio': Vu/load_cap_my
    }
    
    # 7.2 Flexural Rupture (Mn = Fu * S_net)
    # S_net = I_net / c
    # This is complex to calc exactly, used simplified approach:
    # S_net approx = S_gross - (Sum of holes * dist^2 ...)
    # Simplified conservative: S_net = (t * (h - n*d_hole)^2) / 6 (Approximation)
    # Better Approx: Deduct holes from Section Modulus
    S_gross = (tp_cm * h_pl_cm**2) / 6.0
    # Deduct inertia of holes? Let's use simplified Z_net for Plastic or S_net for Elastic?
    # AISC Part 15 says check Rupture on S_net.
    # Let's use conservative Z_net approx = Z_gross * (Anv/Ag)
    Z_net = Z_gross * (Anv / Ag) 
    Mn_rup = Fu_pl * Z_net
    cap_m_r = Mn_rup / omega if method == "ASD" else phi_b * Mn_rup
    load_cap_mr = cap_m_r / ex if ex > 0 else 999999
    
    results['flex_rup'] = {
        'title': '8. Plate Flexural Rupture',
        'ref': 'AISC Manual Part 15',
        'eq': r'M_n = F_u Z_{net}',
        'sub': f'Z_{{net}}={Z_net:.1f} cm^3, M_n={Mn_rup:,.0f}',
        'cap': load_cap_mr, 'ratio': Vu/load_cap_mr
    }

    return results
