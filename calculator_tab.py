import math

def check_geometry(inputs):
    """ตรวจสอบระยะห่างโบลต์และระยะขอบตามมาตรฐาน"""
    msgs = []
    db, pitch, lev, leh = inputs['bolt_dia'], inputs['pitch'], inputs['lev'], inputs['leh_beam']
    
    # Min spacing = 2.67 * dia
    min_spa = 2.67 * db
    if pitch < min_spa: 
        msgs.append(f"Bolt Pitch ({pitch}mm) < Min ({min_spa:.1f}mm)")
    
    # Min Edge distance (AISC Table J3.4)
    min_e = 22 if db <= 16 else (26 if db <= 20 else 30)
    if lev < min_e: 
        msgs.append(f"V-Edge ({lev}mm) < Min ({min_e}mm)")
    if leh < min_e: 
        msgs.append(f"H-Edge ({leh}mm) < Min ({min_e}mm)")
    return msgs

def calculate_shear_tab(inputs):
    """คำนวณกำลังรับแรงเฉือนของจุดต่อ Single Plate"""
    res = {}
    
    # เรียกใช้ check_geometry (ต้องประกาศไว้ด้านบน)
    geo_errs = check_geometry(inputs)
    if geo_errs: 
        return {'critical_error': True, 'errors': geo_errs}

    # --- Setup Data & Units (mm to cm) ---
    meth, Vu = inputs['method'], inputs['load']
    tp = inputs['plate_t'] / 10
    h_pl = inputs['plate_h'] / 10
    tw_bm = inputs['beam_tw'] / 10
    db = inputs['bolt_dia'] / 10
    Ab = (math.pi * db**2) / 4
    n = inputs['n_rows']
    
    Fy_pl, Fu_pl = 2500, 4100  # SS400
    # กำหนด Fu ของคานตามเกรด Fy
    Fu_bm = 4000 if inputs['beam_fy'] <= 2500 else 4500
    
    # --- ปรับปรุง Safety Factors ตาม AISC 360-16 ---
    is_asd = (meth == "ASD")
    
    # Yielding: Phi=1.00, Omega=1.50
    f_yield = 1/1.50 if is_asd else 1.00
    sf_yield_txt = "1.50" if is_asd else "1.00"
    
    # Critical (Bolt, Bearing, Rupture): Phi=0.75, Omega=2.00
    f_critical = 1/2.00 if is_asd else 0.75
    sf_critical_txt = "2.00" if is_asd else "0.75"

    # --- 1. Bolt Shear Strength ---
    Fnv = 4690 if "A490" in inputs['bolt_grade'] else 3720
    Rn_bolt = Fnv * Ab * n
    res['bolt_shear'] = {
        'title': '1. Bolt Shear Strength',
        'formula': r"R_n = F_{nv} A_b n",
        'subst': rf"{Fnv}\text{{ ksc}} \times {Ab:.2f}\text{{ cm}}^2 \times {n}\text{{ bolts}}",
        'rn': Rn_bolt, 
        'sf': sf_critical_txt,
        'design_val': Rn_bolt * f_critical, 
        'ratio': Vu / (Rn_bolt * f_critical)
    }

    # --- 2. Bolt Bearing (on Plate) ---
    lc_pl = (inputs['lev']/10) - (db/2 + 0.1)
    rn_unit = min(1.2 * lc_pl * tp * Fu_pl, 2.4 * db * tp * Fu_pl)
    Rn_bear = rn_unit * n
    res['bearing'] = {
        'title': '2. Bolt Bearing',
        'formula': r"R_n = \sum (1.2 l_c t F_u \le 2.4 d t F_u)",
        'subst': rf"{n}\text{{ bolts}} \times {rn_unit:.0f}\text{{ kg/bolt}}",
        'rn': Rn_bear, 
        'sf': sf_critical_txt,
        'design_val': Rn_bear * f_critical, 
        'ratio': Vu / (Rn_bear * f_critical)
    }

    # --- 3. Plate Shear Yielding ---
    Ag = h_pl * tp
    Rn_y = 0.60 * Fy_pl * Ag
    res['shear_yield'] = {
        'title': '3. Plate Shear Yielding',
        'formula': r"R_n = 0.60 F_y A_g",
        'subst': rf"0.6 \times {Fy_pl}\text{{ ksc}} \times {Ag:.2f}\text{{ cm}}^2",
        'rn': Rn_y, 
        'sf': sf_yield_txt,
        'design_val': Rn_y * f_yield, 
        'ratio': Vu / (Rn_y * f_yield)
    }

    # --- 4. Plate Shear Rupture ---
    Anv = Ag - (n * (db + 0.2) * tp)
    Rn_r = 0.60 * Fu_pl * Anv
    res['shear_rup'] = {
        'title': '4. Plate Shear Rupture',
        'formula': r"R_n = 0.60 F_u A_{nv}",
        'subst': rf"0.6 \times {Fu_pl}\text{{ ksc}} \times {Anv:.2f}\text{{ cm}}^2",
        'rn': Rn_r, 
        'sf': sf_critical_txt,
        'design_val': Rn_r * f_critical, 
        'ratio': Vu / (Rn_r * f_critical)
    }

    return res
