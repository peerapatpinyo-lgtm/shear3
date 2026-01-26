# calculator_tab.py
import math

def calculate_shear_tab(inputs):
    """
    คำนวณ Shear Tab Connection (Single Plate) ตาม AISC 360-16
    รองรับ: Bolt Shear, Bearing, Shear Yield, Shear Rupture, Block Shear, Weld
    รองรับ: ASD / LRFD
    Update: เพิ่ม Reference (AISC Section/Equation)
    """
    
    # 1. UNPACK INPUTS
    # ----------------------------------------------------
    method = inputs.get('method', 'LRFD') 
    Vu = inputs['load']          # Load (kg)
    
    # Beam Properties
    Tw = inputs['beam_tw']       # Beam Web Thickness (mm)
    # Plate Properties
    tp = inputs['plate_t']       # Plate Thickness (mm)
    h_pl = inputs['plate_h']     # Plate Height (mm)
    
    # Bolt Properties
    db = inputs['bolt_dia']      # Bolt Diameter (mm)
    n = inputs['n_rows']         # Number of Bolts
    s = inputs['pitch']          # Pitch (mm)
    lev = inputs['lev']          # Vertical Edge Distance (mm)
    leh = inputs['leh']          # Horizontal Edge Distance (mm) - Plate
    
    # Materials
    mat_bm = inputs['beam_mat']
    mat_pl = inputs['plate_mat']
    grade_bolt = inputs['bolt_grade']
    weld_D = inputs['weld_sz']   # Weld size in mm

    # 2. MATERIAL PROPERTIES DATABASE (ksc)
    # ----------------------------------------------------
    MAT_DB = {
        "SS400": (2400, 4100),
        "A36":   (2500, 4080),
        "SM400": (2400, 4100),
        "A572-50": (3500, 4590),
        "SM520": (3600, 5000)
    }

    Fy_bm, Fu_bm = MAT_DB.get(mat_bm, (2400, 4100))
    Fy_pl, Fu_pl = MAT_DB.get(mat_pl, (2400, 4100))

    BOLT_DB = {
        "A325": 3790,
        "A490": 4780,
        "Gr.8.8": 3800
    }
    Fnv = BOLT_DB.get(grade_bolt, 3790)

    # 3. GEOMETRY PREP
    # ----------------------------------------------------
    dh = db + 2.0  # Hole diameter
    Ab = math.pi * (db**2) / 400.0  # cm2

    # 4. SAFETY FACTORS SETUP (AISC 360-16)
    # ----------------------------------------------------
    factors = {
        'yield':   [1.50, 1.00],
        'rupture': [2.00, 0.75],
        'bolt':    [2.00, 0.75],
        'bearing': [2.00, 0.75],
        'block':   [2.00, 0.75],
        'weld':    [2.00, 0.75]
    }

    def get_capacity_and_sub(Rn, rn_sub_str, mode_key):
        omega, phi = factors[mode_key]
        
        if method == "ASD":
            cap = Rn / omega
            lab = r"R_n / \Omega"
            factor_val = omega
            symbol = "Ω"
            sub_str = f"\\frac{{ {rn_sub_str} }}{{ {omega:.2f} }}"
        else: # LRFD
            cap = phi * Rn
            lab = r"\phi R_n"
            factor_val = phi
            symbol = "φ"
            sub_str = f"{phi:.2f} \\times [{rn_sub_str}]"
            
        return cap, lab, factor_val, symbol, sub_str

    results = {}
    summary_caps = []

    # ============================================
    # MODE 1: BOLT SHEAR
    # Ref: AISC Spec J3.6, Eq J3-1
    # ============================================
    Rn_bolt = Fnv * Ab * n
    rn_sub_bolt = f"{Fnv} \\times {Ab:.2f} \\times {n}"
    cap_bolt, lab_bolt, f_bolt, sym_bolt, sub_bolt = get_capacity_and_sub(Rn_bolt, rn_sub_bolt, 'bolt')
    
    results['bolt_shear'] = {
        'title': "Bolt Shear",
        'ref': "AISC 360-16 Sec. J3.6 (Eq. J3-1)",
        'capacity': cap_bolt,
        'ratio': Vu / cap_bolt,
        'latex_eq': f"{lab_bolt} = {sym_bolt} F_{{nv}} A_b N_{{bolt}}",
        'latex_sub': sub_bolt,
        'calcs': [
            f"Method: {method} ({sym_bolt} = {f_bolt})",
            f"Shear Strength (Fnv): {Fnv} ksc",
            f"Area (Ab): {Ab:.2f} cm² x {n} bolts",
            f"Nominal Rn: {Rn_bolt:,.0f} kg"
        ]
    }
    summary_caps.append(('Bolt Shear', cap_bolt))

    # ============================================
    # MODE 2: BEARING & TEAROUT
    # Ref: AISC Spec J3.10, Eq J3-6a
    # ============================================
    def calc_bearing_detail(thickness, Fu_mat, edge_dist_v, inner_pitch):
        # Edge Bolt
        Lc_edge = edge_dist_v - (dh/2.0)
        Rn_edge_formula = 1.2 * (Lc_edge/10) * (thickness/10) * Fu_mat
        Rn_edge_max = 2.4 * (db/10) * (thickness/10) * Fu_mat
        Rn_edge = min(Rn_edge_formula, Rn_edge_max)
        
        # Inner Bolts
        if n > 1:
            Lc_in = inner_pitch - dh
            Rn_in_formula = 1.2 * (Lc_in/10) * (thickness/10) * Fu_mat
            Rn_in_max = 2.4 * (db/10) * (thickness/10) * Fu_mat
            Rn_in = min(Rn_in_formula, Rn_in_max)
            Rn_total = Rn_edge + (Rn_in * (n-1))
            sub_detail = f"({Rn_edge:.0f}) + {n-1}\\times({Rn_in:.0f})"
        else:
            Rn_total = Rn_edge
            sub_detail = f"{Rn_edge:.0f}"
        return Rn_total, sub_detail

    Rn_br_pl, sub_pl = calc_bearing_detail(tp, Fu_pl, lev, s)
    Rn_br_bm, sub_bm = calc_bearing_detail(Tw, Fu_bm, lev, s)
    
    if Rn_br_pl < Rn_br_bm:
        Rn_br_gov = Rn_br_pl
        gov_br = "Plate"
        rn_sub_br = f"\\text{{Plate: }} {sub_pl}"
    else:
        Rn_br_gov = Rn_br_bm
        gov_br = "Beam Web"
        rn_sub_br = f"\\text{{Beam: }} {sub_bm}"

    cap_br, lab_br, f_br, sym_br, sub_br_final = get_capacity_and_sub(Rn_br_gov, rn_sub_br, 'bearing')
    
    results['bearing'] = {
        'title': f"Bearing & Tearout ({gov_br})",
        'ref': "AISC 360-16 Sec. J3.10 (Eq. J3-6a)",
        'capacity': cap_br,
        'ratio': Vu / cap_br,
        'latex_eq': f"{lab_br} = {sym_br} \\Sigma (1.2 L_c t F_u \leq 2.4 d t F_u)",
        'latex_sub': sub_br_final,
        'calcs': [
            f"Method: {method} ({sym_bolt} = {f_br})",
            f"Plate Capacity: {Rn_br_pl:,.0f} kg",
            f"Beam Web Capacity: {Rn_br_bm:,.0f} kg",
            f"Governing Part: {gov_br}",
            "Note: Calculated as sum of Edge Bolt + Inner Bolts"
        ]
    }
    summary_caps.append(('Bearing', cap_br))

    # ============================================
    # MODE 3: SHEAR YIELDING (Plate)
    # Ref: AISC Spec J4.2, Eq J4-3
    # ============================================
    Ag_pl = (h_pl/10) * (tp/10)
    Rn_yld = 0.6 * Fy_pl * Ag_pl
    rn_sub_yld = f"0.6 \\times {Fy_pl} \\times {Ag_pl:.2f}"
    cap_yld, lab_yld, f_yld, sym_yld, sub_yld = get_capacity_and_sub(Rn_yld, rn_sub_yld, 'yield')
    
    results['shear_yield'] = {
        'title': "Shear Yield (Plate)",
        'ref': "AISC 360-16 Sec. J4.2 (Eq. J4-3)",
        'capacity': cap_yld,
        'ratio': Vu / cap_yld,
        'latex_eq': f"{lab_yld} = {sym_yld} (0.6 F_y A_g)",
        'latex_sub': sub_yld,
        'calcs': [
            f"Method: {method} ({sym_yld} = {f_yld})",
            f"Gross Area (Ag): {Ag_pl:.2f} cm²",
            f"Plate Fy: {Fy_pl} ksc",
            f"Nominal Rn: {Rn_yld:,.0f} kg"
        ]
    }
    summary_caps.append(('Shear Yield', cap_yld))

    # ============================================
    # MODE 4: SHEAR RUPTURE (Plate)
    # Ref: AISC Spec J4.2, Eq J4-4
    # ============================================
    Anv_pl = ((h_pl - (n * dh))/10) * (tp/10)
    Rn_rup = 0.6 * Fu_pl * Anv_pl
    rn_sub_rup = f"0.6 \\times {Fu_pl} \\times {Anv_pl:.2f}"
    cap_rup, lab_rup, f_rup, sym_rup, sub_rup = get_capacity_and_sub(Rn_rup, rn_sub_rup, 'rupture')
    
    results['shear_rupture'] = {
        'title': "Shear Rupture (Plate)",
        'ref': "AISC 360-16 Sec. J4.2 (Eq. J4-4)",
        'capacity': cap_rup,
        'ratio': Vu / cap_rup,
        'latex_eq': f"{lab_rup} = {sym_rup} (0.6 F_u A_{{nv}})",
        'latex_sub': sub_rup,
        'calcs': [
            f"Method: {method} ({sym_rup} = {f_rup})",
            f"Net Area (Anv): {Anv_pl:.2f} cm²",
            f"Plate Fu: {Fu_pl} ksc",
            f"Nominal Rn: {Rn_rup:,.0f} kg"
        ]
    }
    summary_caps.append(('Shear Rupture', cap_rup))

    # ============================================
    # MODE 5: BLOCK SHEAR
    # Ref: AISC Spec J4.3, Eq J4-5
    # ============================================
    def calc_block_shear(t, Fy, Fu, Le_v, Le_h, n_b, pitch):
        L_gv = Le_v + (n_b - 1) * pitch
        Agv = (L_gv/10) * (t/10)
        Anv = ((L_gv - (n_b - 0.5) * dh)/10) * (t/10)
        Ant = ((Le_h - 0.5 * dh)/10) * (t/10)
        Ubs = 1.0
        
        term1 = 0.6 * Fu * Anv + Ubs * Fu * Ant
        term2 = 0.6 * Fy * Agv + Ubs * Fu * Ant
        
        Rn = min(term1, term2)
        
        if term1 < term2:
            sub_str = f"0.6({Fu})({Anv:.2f}) + 1.0({Fu})({Ant:.2f})"
        else:
            sub_str = f"0.6({Fy})({Agv:.2f}) + 1.0({Fu})({Ant:.2f})"
            
        return Rn, Anv, Ant, sub_str
    
    Rn_bs_pl, Anv_p, Ant_p, sub_p = calc_block_shear(tp, Fy_pl, Fu_pl, lev, leh, n, s)
    Rn_bs_bm, Anv_b, Ant_b, sub_b = calc_block_shear(Tw, Fy_bm, Fu_bm, lev, leh, n, s)
    
    if Rn_bs_pl < Rn_bs_bm:
        Rn_bs_gov = Rn_bs_pl
        gov_bs = "Plate"
        rn_sub_bs = sub_p
    else:
        Rn_bs_gov = Rn_bs_bm
        gov_bs = "Beam Web"
        rn_sub_bs = sub_b
    
    cap_bs, lab_bs, f_bs, sym_bs, sub_bs_final = get_capacity_and_sub(Rn_bs_gov, rn_sub_bs, 'block')
    
    results['block_shear'] = {
        'title': f"Block Shear ({gov_bs})",
        'ref': "AISC 360-16 Sec. J4.3 (Eq. J4-5)",
        'capacity': cap_bs,
        'ratio': Vu / cap_bs,
        'latex_eq': f"{lab_bs} = {sym_bs} [0.6 F_u A_{{nv}} + U_{{bs}} F_u A_{{nt}}]",
        'latex_sub': sub_bs_final,
        'calcs': [
            f"Method: {method} ({sym_bs} = {f_bs})",
            f"Control Part: {gov_bs}",
            f"Shear Area (Anv): {Anv_p if gov_bs=='Plate' else Anv_b:.2f} cm²",
            f"Tension Area (Ant): {Ant_p if gov_bs=='Plate' else Ant_b:.2f} cm²",
            "Checked tearing along bolt line (Shear) + toe (Tension)"
        ]
    }
    summary_caps.append(('Block Shear', cap_bs))

    # ============================================
    # MODE 6: WELD STRENGTH
    # Ref: AISC Spec J2.4, Eq J2-3
    # ============================================
    Fexx = 4900 # E70XX
    te = 0.707 * weld_D
    Lw = 2 * h_pl
    Aw = (te/10) * (Lw/10)
    
    Rn_weld = 0.6 * Fexx * Aw
    rn_sub_weld = f"0.6 \\times {Fexx} \\times {Aw:.2f}"
    cap_weld, lab_weld, f_weld, sym_weld, sub_weld = get_capacity_and_sub(Rn_weld, rn_sub_weld, 'weld')
    
    results['weld'] = {
        'title': "Weld Strength",
        'ref': "AISC 360-16 Sec. J2.4 (Eq. J2-3)",
        'capacity': cap_weld,
        'ratio': Vu / cap_weld,
        'latex_eq': f"{lab_weld} = {sym_weld} (0.6 F_{{EXX}} A_w)",
        'latex_sub': sub_weld,
        'calcs': [
            f"Method: {method} ({sym_weld} = {f_weld})",
            f"Weld Size: {weld_D} mm (Throat: {te:.2f} mm)",
            f"Total Length: {Lw} mm (2 sides)",
            f"Effective Area (Aw): {Aw:.2f} cm²"
        ]
    }
    summary_caps.append(('Weld', cap_weld))

    # ============================================
    # SUMMARY
    # ============================================
    min_cap = min(summary_caps, key=lambda x: x[1])
    
    results['summary'] = {
        'status': "PASS" if Vu <= min_cap[1] else "FAIL",
        'gov_mode': min_cap[0],
        'gov_capacity': min_cap[1],
        'utilization': Vu / min_cap[1],
        'method': method
    }

    return results
