import math

# ==========================================
# 1. MATERIAL DATABASE
# ==========================================
MATERIALS_DB = {
    "SS400":    {"Fy": 2400, "Fu": 4100},
    "A36":      {"Fy": 2500, "Fu": 4000},
    "SM520":    {"Fy": 3600, "Fu": 5300},
    "A572-50":  {"Fy": 3500, "Fu": 4500},
    "A992":     {"Fy": 3500, "Fu": 4500}
}

BOLT_DB = {
    "A325":   {"Fnv": 3720, "Fnt": 6200},
    "A490":   {"Fnv": 4690, "Fnt": 7800},
    "Gr.8.8": {"Fnv": 3800, "Fnt": 5600}
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_phi_omega(method, check_type):
    if method == "LRFD":
        if check_type == "yield": return 1.00, 1.00
        if check_type == "rupture": return 0.75, 1.00
        if check_type == "shear_bolt": return 0.75, 1.00
        if check_type == "bearing": return 0.75, 1.00
        if check_type == "weld": return 0.75, 1.00
    else: # ASD
        if check_type == "yield": return 1.00, 1.50
        if check_type == "rupture": return 1.00, 2.00
        if check_type == "shear_bolt": return 1.00, 2.00
        if check_type == "bearing": return 1.00, 2.00
        if check_type == "weld": return 1.00, 2.00
    return 1.0, 1.0

def format_result(title, Rn, cap, ratio, ref, latex_eq, latex_sub, status_pass):
    return {
        "title": title,
        "Rn": Rn,
        "capacity": cap,
        "ratio": ratio,
        "status": "PASS" if status_pass else "FAIL",
        "ref": ref,
        "latex_eq": latex_eq,
        "latex_sub": latex_sub,
        "calcs": []
    }

# ==========================================
# 3. MAIN CALCULATION
# ==========================================
def calculate_shear_tab(inputs):
    # Unpack
    method = inputs['method']
    Vu = inputs['load']
    
    # Material
    mat_bm_name = inputs.get('beam_mat', 'SS400')
    mat_pl_name = inputs.get('plate_mat', 'SS400')
    
    mat_bm = MATERIALS_DB.get(mat_bm_name, MATERIALS_DB["SS400"])
    mat_pl = MATERIALS_DB.get(mat_pl_name, MATERIALS_DB["SS400"])
    
    Fy_bm, Fu_bm = mat_bm['Fy'], mat_bm['Fu']
    Fy_pl, Fu_pl = mat_pl['Fy'], mat_pl['Fu']

    # Geometry
    tp = inputs['plate_t'] / 10.0
    h_pl = inputs['plate_h'] / 10.0
    tw_bm = inputs['beam_tw'] / 10.0
    
    # Bolt
    db_mm = inputs['bolt_dia']
    db = db_mm / 10.0
    n_rows = inputs['n_rows']
    bolt_grade = inputs['bolt_grade']
    Fnv_bolt = BOLT_DB.get(bolt_grade, BOLT_DB["A325"])['Fnv']
    
    # Dimensions
    lev = inputs['lev'] / 10.0
    dh = db + 0.2
    
    results = {}
    
    # --- 1. BOLT SHEAR ---
    Ab = math.pi * (db**2) / 4
    Rn_bolt_shear = Fnv_bolt * Ab * n_rows
    phi, omega = get_phi_omega(method, "shear_bolt")
    Cap_bolt = phi * Rn_bolt_shear if method == "LRFD" else Rn_bolt_shear / omega
    
    results['bolt_shear'] = format_result(
        "Bolt Shear", Rn_bolt_shear, Cap_bolt, Vu/Cap_bolt, "AISC J3.6",
        r"R_n = F_{nv} A_b N_b",
        fr"{Fnv_bolt} \times {Ab:.2f} \times {n_rows}",
        Vu <= Cap_bolt
    )

    # --- 2. BEARING ---
    # Simplified Bearing Logic for debugging stability
    Rn_br_pl = n_rows * (2.4 * db * tp * Fu_pl)
    Rn_br_web = n_rows * (2.4 * db * tw_bm * Fu_bm)
    Rn_bearing = min(Rn_br_pl, Rn_br_web)
    
    phi, omega = get_phi_omega(method, "bearing")
    Cap_br = phi * Rn_bearing if method == "LRFD" else Rn_bearing / omega
    
    results['bearing'] = format_result(
        "Bearing", Rn_bearing, Cap_br, Vu/Cap_br, "AISC J3.10",
        r"R_n = 2.4 d t F_u",
        fr"Min(Plate, Web)",
        Vu <= Cap_br
    )

    # --- 3. SHEAR YIELD ---
    Ag = h_pl * tp
    Rn_y = 0.60 * Fy_pl * Ag
    phi, omega = get_phi_omega(method, "yield")
    Cap_y = phi * Rn_y if method == "LRFD" else Rn_y / omega
    
    results['shear_yield'] = format_result(
        "Plate Shear Yield", Rn_y, Cap_y, Vu/Cap_y, "AISC J4.2",
        r"R_n = 0.60 F_y A_g",
        fr"0.60 \times {Fy_pl} \times {Ag:.2f}",
        Vu <= Cap_y
    )

    # --- 4. SHEAR RUPTURE ---
    Anv = (h_pl - (n_rows * (dh + 0.16))) * tp
    Rn_rup = 0.60 * Fu_pl * Anv
    phi, omega = get_phi_omega(method, "rupture")
    Cap_rup = phi * Rn_rup if method == "LRFD" else Rn_rup / omega
    
    results['shear_rupture'] = format_result(
        "Plate Shear Rupture", Rn_rup, Cap_rup, Vu/Cap_rup, "AISC J4.2",
        r"R_n = 0.60 F_u A_{nv}",
        fr"0.60 \times {Fu_pl} \times {Anv:.2f}",
        Vu <= Cap_rup
    )
    
    # --- 5. WELD ---
    D_weld = inputs['weld_sz'] / 10.0
    Fexx = 4900
    Aw_eff = 2 * h_pl * (0.707 * D_weld)
    Rn_weld = 0.60 * Fexx * Aw_eff
    phi, omega = get_phi_omega(method, "weld")
    Cap_weld = phi * Rn_weld if method == "LRFD" else Rn_weld / omega
    
    results['weld'] = format_result(
        "Weld Strength", Rn_weld, Cap_weld, Vu/Cap_weld, "AISC J2.4",
        r"R_n = 0.60 F_{EXX} A_w",
        fr"0.60 \times {Fexx} \times {Aw_eff:.2f}",
        Vu <= Cap_weld
    )

    # Summary
    max_ratio = 0.0
    gov_mode = ""
    for k, v in results.items():
        if isinstance(v, dict) and 'ratio' in v:
            if v['ratio'] > max_ratio:
                max_ratio = v['ratio']
                gov_mode = v['title']
            
    results['summary'] = {
        "status": "PASS" if max_ratio <= 1.0 else "FAIL",
        "utilization": max_ratio,
        "gov_mode": gov_mode
    }
    
    return results
