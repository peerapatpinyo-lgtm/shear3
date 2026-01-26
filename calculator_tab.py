# calculator_tab.py
import math

def calculate_shear_tab(inputs):
    """
    Advanced Calculation Logic for Shear Tab Connection
    Returns detailed step-by-step trace for engineering report.
    """
    # 1. Unpack Inputs & Material Properties
    # ==========================================
    method = inputs['method'] # ASD / LRFD
    Vu = inputs['load']
    
    # Plate Props
    Fy_pl = 2500 if inputs['plate_mat'] == 'SS400' else (2530 if inputs['plate_mat'] == 'A36' else 3500)
    Fu_pl = 4100 if inputs['plate_mat'] == 'SS400' else (4080 if inputs['plate_mat'] == 'A36' else 4570)
    t_pl = inputs['plate_t'] / 10.0 # cm
    h_pl = inputs['plate_h'] / 10.0 # cm
    
    # Beam Props
    Fy_bm = inputs['beam_fy']
    Fu_bm = 4000 if Fy_bm <= 2500 else (4500 if Fy_bm <= 3000 else 5000) # Approx
    tw_bm = inputs['beam_tw'] / 10.0 # cm
    
    # Bolt Props
    db = inputs['bolt_dia'] # mm
    db_cm = db / 10.0
    Ab = (math.pi * (db_cm)**2) / 4 # cm2
    n_rows = inputs['n_rows']
    
    # Geometry
    lev = inputs['lev'] / 10.0 # cm
    pitch = inputs['pitch'] / 10.0 # cm
    leh_bm = inputs['leh_beam'] / 10.0 # cm (Distance to beam edge)
    
    # Factors
    if method == "ASD":
        omega = 1.67; omega_v = 1.50; omega_r = 2.00; omega_w = 2.00
        phi = 1.0   ; phi_v = 1.0   ; phi_r = 1.0   ; phi_w = 1.0
        txt_sf = "1 / \Omega"
    else:
        omega = 1.0 ; omega_v = 1.0 ; omega_r = 1.0 ; omega_w = 1.0
        phi = 0.90  ; phi_v = 1.00  ; phi_r = 0.75  ; phi_w = 0.75
        txt_sf = "\phi"

    results = {}

    # ==========================================
    # CHECK 1: BOLT SHEAR (แรงเฉือนในสลักเกลียว)
    # Ref: AISC Specification J3.6
    # ==========================================
    # Fnv estimation (ksc)
    if "A325" in inputs['bolt_grade']: Fnv = 3720
    elif "A490" in inputs['bolt_grade']: Fnv = 4690
    else: Fnv = 2500 # Gr 8.8

    Rn_bolt = Fnv * Ab * n_rows
    cap_bolt = (Rn_bolt / omega_r) if method == "ASD" else (phi_r * Rn_bolt)
    
    results['bolt_shear'] = {
        'title': '1. Bolt Shear Strength',
        'ref': 'AISC Spec J3.6',
        'formula': r"R_n = F_{nv} A_b n_{bolts}",
        'subst': f"{Fnv} \\times {Ab:.2f} \\times {n_rows} = {Rn_bolt:,.0f} \text{{ kg}}",
        'design_eq': r"R_{design} = " + txt_sf + r" R_n",
        'design_val': cap_bolt,
        'ratio': Vu / cap_bolt
    }

    # ==========================================
    # CHECK 2: BOLT BEARING (แรงแบกทานที่รูเจาะ)
    # Ref: AISC Specification J3.10
    # ==========================================
    # Case A: On Plate
    lc_edge_pl = lev - (db_cm/2 + 0.1) # +1mm tolerance
    lc_inner_pl = pitch - (db_cm + 0.2)
    
    rn_edge_pl = min(1.2 * lc_edge_pl * t_pl * Fu_pl, 2.4 * db_cm * t_pl * Fu_pl)
    rn_inner_pl = min(1.2 * lc_inner_pl * t_pl * Fu_pl, 2.4 * db_cm * t_pl * Fu_pl)
    Rn_bear_pl = rn_edge_pl + (rn_inner_pl * (n_rows - 1))
    
    # Case B: On Beam Web
    lc_edge_bm = leh_bm - (db_cm/2 + 0.1)
    rn_edge_bm = min(1.2 * lc_edge_bm * tw_bm * Fu_bm, 2.4 * db_cm * tw_bm * Fu_bm)
    rn_inner_bm = min(1.2 * lc_inner_pl * tw_bm * Fu_bm, 2.4 * db_cm * tw_bm * Fu_bm)
    Rn_bear_bm = rn_edge_bm + (rn_inner_bm * (n_rows - 1))
    
    # Governing
    Rn_bear = min(Rn_bear_pl, Rn_bear_bm)
    ctrl_elem = "Plate" if Rn_bear_pl < Rn_bear_bm else "Beam Web"
    cap_bear = (Rn_bear / omega_r) if method == "ASD" else (phi_r * Rn_bear)

    results['bearing'] = {
        'title': f'2. Bolt Bearing ({ctrl_elem} Controls)',
        'ref': 'AISC Spec J3.10',
        'formula': r"R_n = \sum \min(1.2 l_c t F_u, 2.4 d t F_u)",
        'subst': f"Plate ({Rn_bear_pl:,.0f}) vs Web ({Rn_bear_bm:,.0f})",
        'design_eq': r"R_{design} = " + txt_sf + r" R_n",
        'design_val': cap_bear,
        'ratio': Vu / cap_bear
    }

    # ==========================================
    # CHECK 3: SHEAR YIELDING (แรงเฉือนคราก)
    # Ref: AISC Specification J4.2
    # ==========================================
    Ag = h_pl * t_pl
    Rn_y = 0.60 * Fy_pl * Ag
    cap_y = (Rn_y / omega_v) if method == "ASD" else (phi_v * Rn_y)

    results['shear_yield'] = {
        'title': '3. Shear Yielding (Plate)',
        'ref': 'AISC Spec J4.2',
        'formula': r"R_n = 0.60 F_y A_g",
        'subst': f"0.60 \\times {Fy_pl} \\times {Ag:.2f} = {Rn_y:,.0f} \text{{ kg}}",
        'design_eq': r"R_{design} = " + txt_sf + r" R_n",
        'design_val': cap_y,
        'ratio': Vu / cap_y
    }

    # ==========================================
    # CHECK 4: SHEAR RUPTURE (แรงเฉือนขาด)
    # Ref: AISC Specification J4.2
    # ==========================================
    d_hole = db_cm + 0.2 # Standard hole + 2mm
    Anv = Ag - (n_rows * d_hole * t_pl)
    Rn_rup = 0.60 * Fu_pl * Anv
    cap_rup = (Rn_rup / omega_r) if method == "ASD" else (phi_r * Rn_rup)

    results['shear_rup'] = {
        'title': '4. Shear Rupture (Plate)',
        'ref': 'AISC Spec J4.2',
        'formula': r"R_n = 0.60 F_u A_{nv}",
        'subst': f"0.60 \\times {Fu_pl} \\times {Anv:.2f} = {Rn_rup:,.0f} \text{{ kg}}",
        'design_eq': r"R_{design} = " + txt_sf + r" R_n",
        'design_val': cap_rup,
        'ratio': Vu / cap_rup
    }

    # ==========================================
    # CHECK 5: BLOCK SHEAR (แรงเฉือนทะลุผ่านบล็อก)
    # Ref: AISC Specification J4.3
    # ==========================================
    # Assume U-Shape block shear (most common for single column bolts)
    # Tension area (horizontal from last bolts to edge)
    leh_pl = (inputs['plate_w'] / 10.0) - (inputs['leh_beam'] / 10.0) # approx remaining width
    Ant = (leh_pl - 0.5 * d_hole) * t_pl
    # Shear area (vertical along bolt line)
    Agv = ((n_rows - 1) * pitch + lev) * t_pl
    Anv_bs = Agv - ((n_rows - 0.5) * d_hole * t_pl)
    
    # Ubs = 1.0 for uniform tension
    Rn_bs = min(0.6*Fu_pl*Anv_bs + 1.0*Fu_pl*Ant, 0.6*Fy_pl*Agv + 1.0*Fu_pl*Ant)
    cap_bs = (Rn_bs / omega_r) if method == "ASD" else (phi_r * Rn_bs)

    results['block_shear'] = {
        'title': '5. Block Shear Rupture',
        'ref': 'AISC Spec J4.3',
        'formula': r"R_n = \min(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, 0.6 F_y A_{gv} + U_{bs} F_u A_{nt})",
        'subst': f"A_{{gv}}={Agv:.2f}, A_{{nv}}={Anv_bs:.2f}, A_{{nt}}={Ant:.2f} cm^2",
        'design_eq': r"R_{design} = " + txt_sf + r" R_n",
        'design_val': cap_bs,
        'ratio': Vu / cap_bs
    }

    # ==========================================
    # CHECK 6: WELD (ECCENTRIC) (รอยเชื่อมรับแรงเยื้องศูนย์)
    # Ref: AISC Part 8 (Elastic Method for simplicity & clarity)
    # ==========================================
    w_sz = inputs['weld_sz'] / 10.0 # cm
    L_w = h_pl # Weld length = Plate height
    
    # Elastic Vector Analysis
    # Eccentricity e = Distance from weld line to bolt line
    e_x = (inputs['plate_w'] / 10.0) - leh_pl # Distance weld to bolts (approx w - leh)
    
    # Properties of weld group (Double Fillet - treating as lines)
    # Aw = 2 * L * te
    te = 0.707 * w_sz
    Aw = 2 * L_w * te
    # Sw = 2 * (te * L^2 / 6) = te * L^2 / 3
    Sw = (te * L_w**2) / 3.0
    
    # Stresses
    fv = Vu / Aw # Direct Shear
    Moment = Vu * e_x
    fb = Moment / Sw # Bending Stress
    fr = math.sqrt(fv**2 + fb**2) # Resultant
    
    # Capacity
    Fexx = 4920 # E70XX (ksc)
    Fnw = 0.60 * Fexx
    F_allow = (Fnw / omega_w) if method == "ASD" else (phi_w * Fnw)
    
    # Check Ratio
    weld_ratio = fr / F_allow
    
    # Back-calculate Capacity for display (Load that makes ratio=1)
    cap_weld = Vu / weld_ratio if weld_ratio > 0 else 999999

    results['weld'] = {
        'title': '6. Weld Strength (Eccentric)',
        'ref': 'AISC Part 8 (Elastic Method)',
        'formula': r"f_r = \sqrt{f_v^2 + f_b^2} \leq \phi F_{nw}",
        'subst': f"e={e_x:.1f}cm, f_v={fv:.1f}, f_b={fb:.1f} \\rightarrow f_r={fr:.1f} ksc",
        'design_eq': r"F_{allow} = " + f"{F_allow:,.0f} ksc",
        'design_val': cap_weld,
        'ratio': weld_ratio
    }
    
    return results
