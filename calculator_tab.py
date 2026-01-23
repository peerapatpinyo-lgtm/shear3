import math

# ==============================================================================
# 🧠 CALCULATOR MODULE: SHEAR TAB (DETAILED REPORT VERSION)
# ==============================================================================

MATERIALS = {
    "A36":     {"Fy": 2500, "Fu": 4000},
    "A572-50": {"Fy": 3450, "Fu": 4500},
    "SS400":   {"Fy": 2400, "Fu": 4100},
    "SM490":   {"Fy": 3300, "Fu": 5000},
    "A325":    {"Fnv": 3720, "Fnt": 6200}, 
    "A490":    {"Fnv": 4690, "Fnt": 7800},
    "Gr.8.8":  {"Fnv": 3750, "Fnt": 8000}
}

PHI = {
    "yield": 1.00, "rupture": 0.75, "bolt_shear": 0.75,
    "bearing": 0.75, "block": 0.75, "weld": 0.75
}

def calculate_shear_tab(inputs):
    # --- 1. PREPARE DATA ---
    Vu = float(inputs.get('load', 0))
    t_w = inputs['beam_tw'] / 10.0
    t_p = inputs['plate_t'] / 10.0
    h_p = inputs['plate_h'] / 10.0
    d_b = inputs['bolt_dia'] / 10.0
    w_sz = inputs['weld_sz'] / 10.0
    pitch = inputs['pitch'] / 10.0
    lev = inputs['lev'] / 10.0
    n_rows = int(inputs['n_rows'])
    
    mat_bm = MATERIALS.get(inputs.get('beam_mat', 'A36'), MATERIALS['A36'])
    mat_pl = MATERIALS.get(inputs.get('plate_mat', 'A36'), MATERIALS['A36'])
    mat_bolt = MATERIALS.get(inputs.get('bolt_grade', 'A325'), MATERIALS['A325'])
    
    d_hole = d_b + 0.2 
    results = {}

    # ==========================================================================
    # 1. 🔩 BOLT SHEAR
    # ==========================================================================
    Ab = math.pi * (d_b**2) / 4
    Fnv = mat_bolt['Fnv']
    Rn_bolt = Fnv * Ab * n_rows
    phi_Rn_bolt = PHI['bolt_shear'] * Rn_bolt
    
    results['bolt_shear'] = {
        "title": "1. Bolt Shear Strength (แรงเฉือนสลักเกลียว)",
        "phi_Rn": phi_Rn_bolt,
        "ratio": Vu / phi_Rn_bolt if phi_Rn_bolt > 0 else 999,
        "latex_eq": r"\phi R_n = \phi \times F_{nv} \times A_b \times N_{rows}",
        "calcs": [
            f"Bolt Area (Ab) = π × ({d_b:.2f})² / 4 = {Ab:.2f} cm²",
            f"Nominal Shear (Rn) = {mat_bolt['Fnv']} × {Ab:.2f} × {n_rows} = {Rn_bolt:.0f} kg",
            f"Design Strength (φRn) = {PHI['bolt_shear']} × {Rn_bolt:.0f} = {phi_Rn_bolt:.0f} kg"
        ]
    }

    # ==========================================================================
    # 2. 🧱 BEARING (Plate & Beam)
    # ==========================================================================
    # Helper to generate text for bearing
    def get_bearing_text(comp_name, t, Fu, edge_dist):
        Lc_edge = edge_dist - (d_hole / 2)
        Rn_edge = min(1.2 * Lc_edge * t * Fu, 2.4 * d_b * t * Fu)
        Rn_inner_total = 0
        
        detail_txt = [f"**Check {comp_name} (t={t*10:.0f}mm):**"]
        detail_txt.append(f"- Lc (edge) = {edge_dist} - ({d_hole}/2) = {Lc_edge:.2f} cm")
        
        if n_rows > 1:
            Lc_inner = pitch - d_hole
            Rn_inner_1 = min(1.2 * Lc_inner * t * Fu, 2.4 * d_b * t * Fu)
            Rn_inner_total = Rn_inner_1 * (n_rows - 1)
            detail_txt.append(f"- Lc (inner) = {pitch} - {d_hole} = {Lc_inner:.2f} cm (x{n_rows-1} bolts)")
        
        Rn_total = Rn_edge + Rn_inner_total
        phi_Rn = PHI['bearing'] * Rn_total
        
        detail_txt.append(f"- Rn (Total) = {Rn_edge:.0f} (Edge) + {Rn_inner_total:.0f} (Inner) = {Rn_total:.0f} kg")
        detail_txt.append(f"- φRn = {PHI['bearing']} × {Rn_total:.0f} = {phi_Rn:.0f} kg")
        
        return phi_Rn, detail_txt

    # 2.1 Plate
    phi_bear_pl, txt_pl = get_bearing_text("Plate", t_p, mat_pl['Fu'], lev)
    # 2.2 Beam Web
    phi_bear_bm, txt_bm = get_bearing_text("Beam Web", t_w, mat_bm['Fu'], lev)
    
    if phi_bear_pl < phi_bear_bm:
        bear_val, bear_calcs = phi_bear_pl, txt_pl
        control_txt = "(Plate Controls)"
    else:
        bear_val, bear_calcs = phi_bear_bm, txt_bm
        control_txt = "(Beam Web Controls)"
        
    results['bearing'] = {
        "title": f"2. Bolt Bearing Strength {control_txt}",
        "phi_Rn": bear_val,
        "ratio": Vu / bear_val if bear_val > 0 else 999,
        "latex_eq": r"\phi R_n = \phi (1.2 L_c t F_u \leq 2.4 d t F_u)",
        "calcs": bear_calcs
    }

    # ==========================================================================
    # 3. 📏 SHEAR YIELDING
    # ==========================================================================
    Ag = h_p * t_p
    Rn_y = 0.60 * mat_pl['Fy'] * Ag
    phi_Rn_y = PHI['yield'] * Rn_y
    
    results['shear_yield'] = {
        "title": "3. Shear Yielding (เพลทคราก)",
        "phi_Rn": phi_Rn_y,
        "ratio": Vu / phi_Rn_y if phi_Rn_y > 0 else 999,
        "latex_eq": r"\phi R_n = 1.00 \times 0.60 F_y A_g",
        "calcs": [
            f"Gross Area (Ag) = {h_p} × {t_p} = {Ag:.2f} cm²",
            f"Nominal Strength (Rn) = 0.60 × {mat_pl['Fy']} × {Ag:.2f} = {Rn_y:.0f} kg",
            f"Design Strength (φRn) = 1.00 × {Rn_y:.0f} = {phi_Rn_y:.0f} kg"
        ]
    }

    # ==========================================================================
    # 4. ✂️ SHEAR RUPTURE
    # ==========================================================================
    Anv = (h_p - (n_rows * d_hole)) * t_p
    Rn_r = 0.60 * mat_pl['Fu'] * Anv
    phi_Rn_r = PHI['rupture'] * Rn_r
    
    results['shear_rupture'] = {
        "title": "4. Shear Rupture (เพลทขาด)",
        "phi_Rn": phi_Rn_r,
        "ratio": Vu / phi_Rn_r if phi_Rn_r > 0 else 999,
        "latex_eq": r"\phi R_n = 0.75 \times 0.60 F_u A_{nv}",
        "calcs": [
            f"Net Area (Anv) = [{h_p} - ({n_rows}×{d_hole})] × {t_p} = {Anv:.2f} cm²",
            f"Nominal Strength (Rn) = 0.60 × {mat_pl['Fu']} × {Anv:.2f} = {Rn_r:.0f} kg",
            f"Design Strength (φRn) = 0.75 × {Rn_r:.0f} = {phi_Rn_r:.0f} kg"
        ]
    }

    # ==========================================================================
    # 5. 🔥 WELD STRENGTH
    # ==========================================================================
    Fexx = 4900 # E70
    Rn_weld = 0.707 * w_sz * h_p * 0.60 * Fexx * 2 
    phi_Rn_weld = PHI['weld'] * Rn_weld
    
    results['weld'] = {
        "title": "5. Weld Strength (รอยเชื่อม)",
        "phi_Rn": phi_Rn_weld,
        "ratio": Vu / phi_Rn_weld if phi_Rn_weld > 0 else 999,
        "latex_eq": r"\phi R_n = 0.75 \times 0.707 w L (0.6 F_{exx}) \times 2",
        "calcs": [
            f"Weld Size (w) = {w_sz*10:.0f} mm ({w_sz} cm)",
            f"Weld Length (L) = {h_p} cm (Double Fillet)",
            f"Design Strength (φRn) = {PHI['weld']} × 0.707 × {w_sz} × {h_p} × (0.6×{Fexx}) × 2 = {phi_Rn_weld:.0f} kg"
        ]
    }

    # --- SUMMARY ---
    min_phi_Rn = min(phi_Rn_bolt, bear_val, phi_Rn_y, phi_Rn_r, phi_Rn_weld)
    status = "PASS" if min_phi_Rn >= Vu else "FAIL"
    
    sorted_modes = sorted(results.items(), key=lambda item: item[1]['ratio'], reverse=True)
    
    results['summary'] = {
        "status": status,
        "gov_capacity": min_phi_Rn,
        "gov_mode": sorted_modes[0][1]['title'],
        "utilization": Vu / min_phi_Rn if min_phi_Rn > 0 else 0.0
    }
    
    return results
