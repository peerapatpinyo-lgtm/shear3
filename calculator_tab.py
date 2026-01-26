# calculator_tab.py
import math

def check_geometry(inputs):
    """ ตรวจสอบระยะมิติต่างๆ (Geometry Checks) """
    msgs = []
    db = inputs['bolt_dia']
    pitch = inputs['pitch']
    lev = inputs['lev']
    leh = inputs['leh_beam']
    
    # 1. Min Spacing
    min_spa = 2.67 * db
    if pitch < min_spa:
        msgs.append(f"❌ Bolt Pitch ({pitch} mm) < Min ({min_spa:.1f} mm)")
        
    # 2. Min Edge
    if db <= 16: min_e = 22
    elif db <= 20: min_e = 26
    elif db <= 24: min_e = 30
    else: min_e = 1.25 * db
    
    if lev < min_e: msgs.append(f"❌ Vertical Edge ({lev} mm) < Min ({min_e} mm)")
    if leh < min_e: msgs.append(f"❌ Horizontal Edge ({leh} mm) < Min ({min_e} mm)")
        
    return msgs

def calculate_shear_tab(inputs):
    """ คำนวณกำลังรับน้ำหนักละเอียด พร้อมแสดงวิธีทำ (Substitution) """
    res = {}
    
    # 0. Geometry Check
    geo_errs = check_geometry(inputs)
    if geo_errs: return {'critical_error': True, 'errors': geo_errs}

    # 1. Setup Variables
    method = inputs['method']
    Vu = inputs['load']
    
    # Units conversion (mm -> cm)
    tp = inputs['plate_t'] / 10.0
    h_pl = inputs['plate_h'] / 10.0
    tw_bm = inputs['beam_tw'] / 10.0
    db = inputs['bolt_dia'] / 10.0
    Ab = (math.pi * db**2) / 4.0
    n = inputs['n_rows']
    
    # Materials
    Fy_pl = 2500 if inputs['plate_mat'] == 'SS400' else 2530
    Fu_pl = 4100 if inputs['plate_mat'] == 'SS400' else 4080
    Fy_bm = inputs['beam_fy']
    Fu_bm = 4000 if Fy_bm <= 2500 else 4500
    
    # Safety Factors & Latex Strings
    if method == "ASD":
        Om_v = 1.50; Om_r = 2.00; Om_f = 1.67
        # Format: Allowable = Rn / Omega
        # ใช้ \genfrac{}{}{}{}{Rn}{\Omega} หรือ \frac แบบปกติ
        txt_sf_shear = r"\Omega = 1.50"
        txt_sf_rup   = r"\Omega = 2.00"
        txt_sf_flex  = r"\Omega = 1.67"
        
        # Factors for calculation
        f_shear = 1/1.50
        f_rup   = 1/2.00
        f_flex  = 1/1.67
        
        design_sym = "R_a" # Allowable Strength
    else:
        # LRFD
        Phi_v = 1.00; Phi_r = 0.75; Phi_f = 0.90
        txt_sf_shear = r"\phi = 1.00"
        txt_sf_rup   = r"\phi = 0.75"
        txt_sf_flex  = r"\phi = 0.90"
        
        f_shear = 1.00
        f_rup   = 0.75
        f_flex  = 0.90
        
        design_sym = r"\phi R_n"

    # ==========================================
    # 1. BOLT SHEAR
    # ==========================================
    Fnv = 4690 if "A490" in inputs['bolt_grade'] else 3720
    Rn_bolt = Fnv * Ab * n
    Cap_bolt = Rn_bolt * f_rup
    
    res['bolt_shear'] = {
        'title': '1. Bolt Shear Strength',
        'ref': 'AISC J3.6',
        'formula': r"R_n = F_{nv} A_b n",
        'subst': rf"{Fnv}\text{{ ksc}} \times {Ab:.2f}\text{{ cm}}^2 \times {n}\text{{ bolts}}",
        'rn': Rn_bolt,
        'factor_txt': txt_sf_rup,
        'design_val': Cap_bolt,
        'ratio': Vu / Cap_bolt
    }

    # ==========================================
    # 2. BEARING (Check Plate & Web)
    # ==========================================
    # Calculate Distances
    lc_pl = (inputs['lev']/10.0) - (db/2 + 0.1) # Edge dist
    lc_in = (inputs['pitch']/10.0) - (db + 0.2) # Inner dist
    
    # Plate Capacity
    rn_pl_unit = min(1.2*lc_pl*tp*Fu_pl, 2.4*db*tp*Fu_pl) # Edge Bolt
    rn_pl_in_unit = min(1.2*lc_in*tp*Fu_pl, 2.4*db*tp*Fu_pl) # Inner Bolts
    Rn_pl = rn_pl_unit + rn_pl_in_unit*(n-1)
    
    # Web Capacity
    lc_wb = (inputs['leh_beam']/10.0) - (db/2 + 0.1)
    rn_wb_unit = min(1.2*lc_wb*tw_bm*Fu_bm, 2.4*db*tw_bm*Fu_bm)
    rn_wb_in_unit = min(1.2*lc_in*tw_bm*Fu_bm, 2.4*db*tw_bm*Fu_bm)
    Rn_wb = rn_wb_unit + rn_wb_in_unit*(n-1)
    
    # Compare
    if Rn_pl < Rn_wb:
        Rn_bear = Rn_pl
        ctrl = "Plate"
        # Create detailed subst string for the controlling case
        sub_str = rf"R_{{edge}} + (n-1)R_{{in}} = {rn_pl_unit:.0f} + {n-1}({rn_pl_in_unit:.0f})"
    else:
        Rn_bear = Rn_wb
        ctrl = "Beam Web"
        sub_str = rf"R_{{edge}} + (n-1)R_{{in}} = {rn_wb_unit:.0f} + {n-1}({rn_wb_in_unit:.0f})"
        
    Cap_bear = Rn_bear * f_rup

    res['bearing'] = {
        'title': f'2. Bolt Bearing Strength ({ctrl})',
        'ref': 'AISC J3.10',
        'formula': r"R_n = n \times \min(1.2 l_c t F_u, 2.4 d t F_u)",
        'subst': sub_str + r"\text{ (kg)}",
        'rn': Rn_bear,
        'factor_txt': txt_sf_rup,
        'design_val': Cap_bear,
        'ratio': Vu / Cap_bear
    }

    # ==========================================
    # 3. SHEAR YIELD
    # ==========================================
    Ag = h_pl * tp
    Rn_y = 0.60 * Fy_pl * Ag
    Cap_y = Rn_y * f_shear
    
    res['shear_yield'] = {
        'title': '3. Plate Shear Yielding',
        'ref': 'AISC J4.2',
        'formula': r"R_n = 0.60 F_y A_g",
        'subst': rf"0.60 \times {Fy_pl}\text{{ ksc}} \times {Ag:.2f}\text{{ cm}}^2",
        'rn': Rn_y,
        'factor_txt': txt_sf_shear,
        'design_val': Cap_y,
        'ratio': Vu / Cap_y
    }

    # ==========================================
    # 4. SHEAR RUPTURE
    # ==========================================
    d_hole = db + 0.2
    Anv = Ag - (n * d_hole * tp)
    Rn_rup = 0.60 * Fu_pl * Anv
    Cap_rup = Rn_rup * f_rup
    
    res['shear_rup'] = {
        'title': '4. Plate Shear Rupture',
        'ref': 'AISC J4.2',
        'formula': r"R_n = 0.60 F_u A_{nv}",
        'subst': rf"0.60 \times {Fu_pl}\text{{ ksc}} \times {Anv:.2f}\text{{ cm}}^2",
        'rn': Rn_rup,
        'factor_txt': txt_sf_rup,
        'design_val': Cap_rup,
        'ratio': Vu / Cap_rup
    }
    
    # ==========================================
    # 5. BLOCK SHEAR
    # ==========================================
    # U-Shape Tearout
    leh_pl = (inputs['plate_w']/10.0) - (inputs['leh_beam']/10.0)
    Ant = (leh_pl - 0.5*d_hole) * tp
    Agv = ((n-1)*(inputs['pitch']/10.0) + (inputs['lev']/10.0)) * tp
    Anv_bs = Agv - ((n-0.5)*d_hole * tp)
    
    # Terms
    T1 = 0.6 * Fu_pl * Anv_bs
    T2 = 1.0 * Fu_pl * Ant
    T3 = 0.6 * Fy_pl * Agv
    
    Rn_bs = min(T1 + T2, T3 + T2)
    Cap_bs = Rn_bs * f_rup
    
    res['block_shear'] = {
        'title': '5. Block Shear Rupture',
        'ref': 'AISC J4.3',
        'formula': r"R_n = \min(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, \dots)",
        'subst': rf"\min({T1:.0f} + {T2:.0f}, {T3:.0f} + {T2:.0f})\text{{ kg}}",
        'rn': Rn_bs,
        'factor_txt': txt_sf_rup,
        'design_val': Cap_bs,
        'ratio': Vu / Cap_bs
    }

    # ==========================================
    # 6. WELD (Simplified Output)
    # ==========================================
    # Using previous eccentric logic but better text
    w_sz = inputs['weld_sz'] / 10.0
    ex = (inputs['plate_w']/10.0) - leh_pl
    te = 0.707 * w_sz
    Lw = h_pl
    Aw = 2 * Lw * te
    Sw = (2 * te * Lw**2) / 6.0
    
    fv = Vu / Aw
    fb = (Vu * ex) / Sw
    fr = math.sqrt(fv**2 + fb**2)
    
    Fexx = 4920 # E70
    Fnw = 0.60 * Fexx
    F_allow = Fnw * f_rup
    
    res['weld'] = {
        'title': '6. Weld Strength (Eccentric)',
        'ref': 'AISC Manual Part 8',
        'formula': r"f_{resultant} = \sqrt{f_v^2 + f_b^2} \leq \phi F_{nw}",
        'subst': rf"\sqrt{{{fv:.1f}}^2 + {fb:.1f}^2} = {fr:.2f}\text{{ ksc}}",
        'rn': F_allow, # In this case, Rn is actually allow stress
        'factor_txt': r"F_{allow}", 
        'design_val': Vu / (fr/F_allow) if fr > 0 else 99999, # Back calc load capacity
        'ratio': fr / F_allow
    }

    return res
