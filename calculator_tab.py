# calculator_tab.py
import math

def check_geometry(inputs):
    msgs = []
    db, pitch, lev, leh = inputs['bolt_dia'], inputs['pitch'], inputs['lev'], inputs['leh_beam']
    min_spa = 2.67 * db
    if pitch < min_spa: msgs.append(f"Bolt Pitch ({pitch}mm) < Min ({min_spa:.1f}mm)")
    min_e = 22 if db <= 16 else (26 if db <= 20 else 30)
    if lev < min_e: msgs.append(f"V-Edge ({lev}mm) < Min ({min_e}mm)")
    if leh < min_e: msgs.append(f"H-Edge ({leh}mm) < Min ({min_e}mm)")
    return msgs

def calculate_shear_tab(inputs):
    res = {}
    geo_errs = check_geometry(inputs)
    if geo_errs: return {'critical_error': True, 'errors': geo_errs}

    # 1. Setup Data
    meth, Vu = inputs['method'], inputs['load']
    tp, h_pl, tw_bm, db = inputs['plate_t']/10, inputs['plate_h']/10, inputs['beam_tw']/10, inputs['bolt_dia']/10
    Ab, n = (math.pi * db**2)/4, inputs['n_rows']
    Fy_pl, Fu_pl = 2500, 4100  # SS400
    Fu_bm = 4000 if inputs['beam_fy'] <= 2500 else 4500
    
    # Factors & Symbols
    is_asd = (meth == "ASD")
    f_shear = 1/1.50 if is_asd else 1.00
    f_rup = 1/2.00 if is_asd else 0.75
    sf_txt = "1.50" if is_asd else "1.00"
    rf_txt = "2.00" if is_asd else "0.75"

    # --- Case 1: Bolt Shear ---
    Fnv = 4690 if "A490" in inputs['bolt_grade'] else 3720
    Rn_bolt = Fnv * Ab * n
    res['bolt_shear'] = {
        'title': '1. Bolt Shear Strength', 'ref': 'AISC J3.6',
        'formula': r"R_n = F_{nv} A_b n",
        'subst': rf"{Fnv}\text{{ ksc}} \times {Ab:.2f}\text{{ cm}}^2 \times {n}\text{{ bolts}}",
        'rn': Rn_bolt, 'sf': sf_txt if is_asd else "1.00",
        'design_val': Rn_bolt * f_shear, 'ratio': Vu / (Rn_bolt * f_shear)
    }

    # --- Case 2: Bearing (Simplified for display) ---
    lc_pl = (inputs['lev']/10) - (db/2 + 0.1)
    rn_unit = min(1.2*lc_pl*tp*Fu_pl, 2.4*db*tp*Fu_pl)
    Rn_bear = rn_unit * n # Simplified
    res['bearing'] = {
        'title': '2. Bolt Bearing', 'ref': 'AISC J3.10',
        'formula': r"R_n = \sum (1.2 l_c t F_u \le 2.4 d t F_u)",
        'subst': rf"{n}\text{{ bolts}} \times {rn_unit:.0f}\text{{ kg/bolt}}",
        'rn': Rn_bear, 'sf': rf_txt,
        'design_val': Rn_bear * f_rup, 'ratio': Vu / (Rn_bear * f_rup)
    }

    # --- Case 3: Shear Yield ---
    Ag = h_pl * tp
    Rn_y = 0.60 * Fy_pl * Ag
    res['shear_yield'] = {
        'title': '3. Plate Shear Yielding', 'ref': 'AISC J4.2',
        'formula': r"R_n = 0.60 F_y A_g",
        'subst': rf"0.6 \times {Fy_pl}\text{{ ksc}} \times {Ag:.2f}\text{{ cm}}^2",
        'rn': Rn_y, 'sf': sf_txt,
        'design_val': Rn_y * f_shear, 'ratio': Vu / (Rn_y * f_shear)
    }

    # --- Case 4: Shear Rupture ---
    Anv = Ag - (n * (db + 0.2) * tp)
    Rn_r = 0.60 * Fu_pl * Anv
    res['shear_rup'] = {
        'title': '4. Plate Shear Rupture', 'ref': 'AISC J4.2',
        'formula': r"R_n = 0.60 F_u A_{nv}",
        'subst': rf"0.6 \times {Fu_pl}\text{{ ksc}} \times {Anv:.2f}\text{{ cm}}^2",
        'rn': Rn_r, 'sf': rf_txt,
        'design_val': Rn_r * f_rup, 'ratio': Vu / (Rn_r * f_rup)
    }

    return res
