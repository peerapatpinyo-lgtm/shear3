# calculator_tab.py
import math

def calculate_shear_tab(inputs):
    """
    คำนวณ Shear Tab Connection (Single Plate) ตาม AISC 360-16
    รองรับ: Bolt Shear, Bearing, Shear Yield, Shear Rupture, Block Shear, Weld
    รองรับ: ASD / LRFD
    """
    
    # 1. UNPACK INPUTS
    # ----------------------------------------------------
    method = inputs.get('method', 'LRFD') # Default to LRFD if not found
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
    # Dictionary structure: [Omega (ASD), Phi (LRFD)]
    factors = {
        'yield':   [1.50, 1.00],
        'rupture': [2.00, 0.75],
        'bolt':    [2.00, 0.75],
        'bearing': [2.00, 0.75],
        'block':   [2.00, 0.75],
        'weld':    [2.00, 0.75]
    }

    def get_capacity(Rn, mode_key):
        omega, phi = factors[mode_key]
        if method == "ASD":
            cap = Rn / omega
            lab = r"R_n / \Omega"
            factor_val = omega
            symbol = "Ω"
        else: # LRFD
            cap = phi * Rn
            lab = r"\phi R_n"
            factor_val = phi
            symbol = "φ"
        return cap, lab, factor_val, symbol

    results = {}
    summary_caps = []

    # ============================================
    # MODE 1: BOLT SHEAR
    # Rn = Fnv * Ab * N_bolts
    # ============================================
    Rn_bolt = Fnv * Ab * n
    cap_bolt, lab_bolt, f_bolt, sym_bolt = get_capacity(Rn_bolt, 'bolt')
    
    results['bolt_shear'] = {
        'title': "Bolt Shear",
        'capacity': cap_bolt,
        'ratio': Vu / cap_bolt,
        'latex_eq': f"{lab_bolt} = {sym_bolt} F_{{nv}} A_b N_{{bolt}}",
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
    # ============================================
    def calc_bearing(thickness, Fu_mat, edge_dist_v, inner_pitch):
        Lc_edge = edge_dist_v - (dh/2.0)
        Rn_edge = min(1.2 * (Lc_edge/10) * (thickness/10) * Fu_mat, 
                      2.4 * (db/10) * (thickness/10) * Fu_mat)
        
        if n > 1:
            Lc_in = inner_pitch - dh
            Rn_in = min(1.2 * (Lc_in/10) * (thickness/10) * Fu_mat,
                        2.4 * (db/10) * (thickness/10) * Fu_mat)
            return Rn_edge + (Rn_in * (n-1))
        else:
            return Rn_edge

    Rn_br_pl = calc_bearing(tp, Fu_pl, lev, s)
    Rn_br_bm = calc_bearing(Tw, Fu_bm, lev, s)
    
    Rn_br_gov = min(Rn_br_pl, Rn_br_bm)
    gov_br = "Plate" if Rn_br_pl < Rn_br_bm else "Beam Web"
    
    cap_br, lab_br, f_br, sym_br = get_capacity(Rn_br_gov, 'bearing')
    
    results['bearing'] = {
        'title': f"Bearing & Tearout ({gov_br})",
        'capacity': cap_br,
        'ratio': Vu / cap_br,
        'latex_eq': f"{lab_br} = {sym_br} (1.2 L_c t F_u \leq 2.4 d t F_u)",
        'calcs': [
            f"Method: {method} ({sym_bolt} = {f_br})",
            f"Plate Rn: {Rn_br_pl:,.0f} kg",
            f"Beam Web Rn: {Rn_br_bm:,.0f} kg",
            f"Governing Part: {gov_br}"
        ]
    }
    summary_caps.append(('Bearing', cap_br))

    # ============================================
    # MODE 3: SHEAR YIELDING (Plate)
    # Rn = 0.6 * Fy * Ag
    # ============================================
    Ag_pl = (h_pl/10) * (tp/10)
    Rn_yld = 0.6 * Fy_pl * Ag_pl
    cap_yld, lab_yld, f_yld, sym_yld = get_capacity(Rn_yld, 'yield')
    
    results['shear_yield'] = {
        'title': "Shear Yield (Plate)",
        'capacity': cap_yld,
        'ratio': Vu / cap_yld,
        'latex_eq': f"{lab_yld} = {sym_yld} (0.6 F_y A_g)",
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
    # Rn = 0.6 * Fu * Anv
    # ============================================
    Anv_pl = ((h_pl - (n * dh))/10) * (tp/10)
    Rn_rup = 0.6 * Fu_pl * Anv_pl
    cap_rup, lab_rup, f_rup, sym_rup = get_capacity(Rn_rup, 'rupture')
    
    results['shear_rupture'] = {
        'title': "Shear Rupture (Plate)",
        'capacity': cap_rup,
        'ratio': Vu / cap_rup,
        'latex_eq': f"{lab_rup} = {sym_rup} (0.6 F_u A_{{nv}})",
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
    # ============================================
    def calc_block_shear(t, Fy, Fu, Le_v, Le_h, n_b, pitch):
        L_gv = Le_v + (n_b - 1) * pitch
        Agv = (L_gv/10) * (t/10)
        Anv = ((L_gv - (n_b - 0.5) * dh)/10) * (t/10)
        Ant = ((Le_h - 0.5 * dh)/10) * (t/10)
        Ubs = 1.0
        
        term1 = 0.6 * Fu * Anv + Ubs * Fu * Ant
        term2 = 0.6 * Fy * Agv + Ubs * Fu * Ant
        return min(term1, term2), Anv, Ant
    
    Rn_bs_pl, Anv_p, Ant_p = calc_block_shear(tp, Fy_pl, Fu_pl, lev, leh, n, s)
    Rn_bs_bm, Anv_b, Ant_b = calc_block_shear(Tw, Fy_bm, Fu_bm, lev, leh, n, s)
    
    Rn_bs_gov = min(Rn_bs_pl, Rn_bs_bm)
    gov_bs = "Plate" if Rn_bs_pl < Rn_bs_bm else "Beam Web"
    
    cap_bs, lab_bs, f_bs, sym_bs = get_capacity(Rn_bs_gov, 'block')
    
    results['block_shear'] = {
        'title': f"Block Shear ({gov_bs})",
        'capacity': cap_bs,
        'ratio': Vu / cap_bs,
        'latex_eq': f"{lab_bs} = {sym_bs} [0.6 F_u A_{{nv}} + U_{{bs}} F_u A_{{nt}}]",
        'calcs': [
            f"Method: {method} ({sym_bs} = {f_bs})",
            f"Control Part: {gov_bs}",
            f"Shear Area (Anv): {Anv_p if gov_bs=='Plate' else Anv_b:.2f} cm²",
            f"Tension Area (Ant): {Ant_p if gov_bs=='Plate' else Ant_b:.2f} cm²"
        ]
    }
    summary_caps.append(('Block Shear', cap_bs))

    # ============================================
    # MODE 6: WELD STRENGTH
    # ============================================
    Fexx = 4900 # E70XX
    te = 0.707 * weld_D
    Lw = 2 * h_pl
    Aw = (te/10) * (Lw/10)
    
    Rn_weld = 0.6 * Fexx * Aw
    cap_weld, lab_weld, f_weld, sym_weld = get_capacity(Rn_weld, 'weld')
    
    results['weld'] = {
        'title': "Weld Strength",
        'capacity': cap_weld,
        'ratio': Vu / cap_weld,
        'latex_eq': f"{lab_weld} = {sym_weld} (0.6 F_{{EXX}} A_w)",
        'calcs': [
            f"Method: {method} ({sym_weld} = {f_weld})",
            f"Weld Size: {weld_D} mm (Throat: {te:.2f} mm)",
            f"Total Length: {Lw} mm"
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
