# calculator_tab.py
import math

def calculate_shear_tab(inputs):
    """
    คำนวณ Shear Tab Connection (Single Plate) ตาม AISC 360-16
    รองรับ: Bolt Shear, Bearing, Shear Yield, Shear Rupture, Block Shear, Weld
    """
    
    # 1. UNPACK INPUTS
    # ----------------------------------------------------
    Vu = inputs['load']          # Factored Load (kg)
    
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
    weld_D = inputs['weld_sz']   # Weld size in 1/16 in or mm (input is mm here)

    # 2. MATERIAL PROPERTIES DATABASE (ksc)
    # ----------------------------------------------------
    # Dictionary: Name -> (Fy, Fu) in ksc
    MAT_DB = {
        "SS400": (2400, 4100),
        "A36":   (2500, 4080),  # Approx 36ksi, 58ksi
        "SM400": (2400, 4100),
        "A572-50": (3500, 4590),
        "SM520": (3600, 5000)
    }

    # Get Beam Props
    Fy_bm, Fu_bm = MAT_DB.get(mat_bm, (2400, 4100))
    
    # Get Plate Props
    Fy_pl, Fu_pl = MAT_DB.get(mat_pl, (2400, 4100))

    # Bolt Shear Strength (Fnv) ksc
    # A325=A325M, A490=A490M (Approx values converted from ksi/MPa)
    # A325-N (Threads included): 372 Mpa ~ 3790 ksc
    # A490-N: 469 MPa ~ 4780 ksc
    # Gr.8.8: Shear strength approx 0.6*800 MPa = 480 MPa ~ 4890 ksc
    BOLT_DB = {
        "A325": 3790,
        "A490": 4780,
        "Gr.8.8": 3800 # Conservative
    }
    Fnv = BOLT_DB.get(grade_bolt, 3790)

    # 3. GEOMETRY PREP
    # ----------------------------------------------------
    # Hole diameter (Standard hole)
    dh = db + 2.0  # mm (Metric standard clearance)
    
    # Bolt Area
    Ab = math.pi * (db**2) / 400.0  # cm2

    # Resistance Factors (Phi) - LRFD
    phi_shear_yield = 1.0
    phi_shear_rupture = 0.75
    phi_bolt = 0.75
    phi_bearing = 0.75
    phi_block = 0.75
    phi_weld = 0.75

    # 4. CALCULATION MODES
    # ----------------------------------------------------
    results = {}
    summary_caps = []

    # ============================================
    # MODE 1: BOLT SHEAR
    # Rn = Fnv * Ab * N_bolts
    # ============================================
    Rn_bolt = Fnv * Ab * n
    phiRn_bolt = phi_bolt * Rn_bolt
    
    results['bolt_shear'] = {
        'title': "Bolt Shear",
        'phi_Rn': phiRn_bolt,
        'ratio': Vu / phiRn_bolt,
        'latex_eq': r"\phi R_n = \phi F_{nv} A_b N_{bolt}",
        'calcs': [
            f"Bolt Grade: {grade_bolt}, Dia: {db} mm",
            f"Shear Strength (Fnv): {Fnv} ksc",
            f"Area (Ab): {Ab:.2f} cm² x {n} bolts",
            f"Nominal Rn: {Rn_bolt:,.0f} kg"
        ]
    }
    summary_caps.append(('Bolt Shear', phiRn_bolt))

    # ============================================
    # MODE 2: BEARING & TEAROUT (Check Both Plate & Beam)
    # Rn = 1.2 * Lc * t * Fu <= 2.4 * d * t * Fu
    # ============================================
    def calc_bearing(thickness, Fu_mat, edge_dist_v, inner_pitch):
        # Edge Bolt
        Lc_edge = edge_dist_v - (dh/2.0)
        Rn_edge = 1.2 * (Lc_edge/10) * (thickness/10) * Fu_mat
        Max_edge = 2.4 * (db/10) * (thickness/10) * Fu_mat
        Rn_edge = min(Rn_edge, Max_edge)
        
        # Inner Bolts
        if n > 1:
            Lc_in = inner_pitch - dh
            Rn_in = 1.2 * (Lc_in/10) * (thickness/10) * Fu_mat
            Max_in = 2.4 * (db/10) * (thickness/10) * Fu_mat
            Rn_in = min(Rn_in, Max_in)
            Rn_total = Rn_edge + (Rn_in * (n-1))
        else:
            Rn_total = Rn_edge
            
        return Rn_total

    # Plate Bearing
    Rn_br_pl = calc_bearing(tp, Fu_pl, lev, s)
    # Beam Bearing (Assume standard edge distance for beam web connection)
    # Usually beam web is continuous, but effective edge distance matters.
    # Conservative: Use same LEV as plate or larger. Let's use LEV.
    Rn_br_bm = calc_bearing(Tw, Fu_bm, lev, s)
    
    phiRn_br = phi_bearing * min(Rn_br_pl, Rn_br_bm)
    gov_br = "Plate" if Rn_br_pl < Rn_br_bm else "Beam Web"
    
    results['bearing'] = {
        'title': f"Bearing & Tearout ({gov_br})",
        'phi_Rn': phiRn_br,
        'ratio': Vu / phiRn_br,
        'latex_eq': r"\phi R_n = \phi (1.2 L_c t F_u \leq 2.4 d t F_u)",
        'calcs': [
            f"Plate Cap: {Rn_br_pl:,.0f} kg",
            f"Beam Web Cap: {Rn_br_bm:,.0f} kg",
            f"Governing Part: {gov_br}",
            "Includes checks for both edge bolts and inner bolts"
        ]
    }
    summary_caps.append(('Bearing', phiRn_br))

    # ============================================
    # MODE 3: SHEAR YIELDING (Plate)
    # Rn = 0.6 * Fy * Ag
    # ============================================
    Ag_pl = (h_pl/10) * (tp/10) # cm2
    Rn_yld = 0.6 * Fy_pl * Ag_pl
    phiRn_yld = phi_shear_yield * Rn_yld
    
    results['shear_yield'] = {
        'title': "Shear Yield (Plate)",
        'phi_Rn': phiRn_yld,
        'ratio': Vu / phiRn_yld,
        'latex_eq': r"\phi R_n = 1.00 \times 0.6 F_y A_g",
        'calcs': [
            f"Gross Area (Ag): {Ag_pl:.2f} cm²",
            f"Plate Fy: {Fy_pl} ksc",
            f"Nominal Rn: {Rn_yld:,.0f} kg"
        ]
    }
    summary_caps.append(('Shear Yield', phiRn_yld))

    # ============================================
    # MODE 4: SHEAR RUPTURE (Plate)
    # Rn = 0.6 * Fu * Anv
    # ============================================
    # Net Area: Cut through vertical line of bolts
    Anv_pl = ((h_pl - (n * dh))/10) * (tp/10)
    Rn_rup = 0.6 * Fu_pl * Anv_pl
    phiRn_rup = phi_shear_rupture * Rn_rup
    
    results['shear_rupture'] = {
        'title': "Shear Rupture (Plate)",
        'phi_Rn': phiRn_rup,
        'ratio': Vu / phiRn_rup,
        'latex_eq': r"\phi R_n = 0.75 \times 0.6 F_u A_{nv}",
        'calcs': [
            f"Net Area (Anv): {Anv_pl:.2f} cm²",
            f"Holes Deducted: {n} x {dh} mm",
            f"Plate Fu: {Fu_pl} ksc",
            f"Nominal Rn: {Rn_rup:,.0f} kg"
        ]
    }
    summary_caps.append(('Shear Rupture', phiRn_rup))

    # ============================================
    # MODE 5: BLOCK SHEAR (Plate & Beam)
    # Rn = 0.6*Fu*Anv + Ubs*Fu*Ant <= 0.6*Fy*Agv + Ubs*Fu*Ant
    # ============================================
    def calc_block_shear(t, Fy, Fu, Le_v, Le_h, n_b, pitch):
        # 1. Gross Shear Area (Agv): Vertical line
        L_gv = Le_v + (n_b - 1) * pitch
        Agv = (L_gv/10) * (t/10)
        
        # 2. Net Shear Area (Anv): Agv minus (n-0.5) holes
        Anv = ((L_gv - (n_b - 0.5) * dh)/10) * (t/10)
        
        # 3. Net Tension Area (Ant): Horizontal line
        # Assuming single column, Ant is from hole center to edge
        Ant = ((Le_h - 0.5 * dh)/10) * (t/10)
        
        # Ubs = 1.0 for uniform stress distribution (typical for flat plates)
        Ubs = 1.0
        
        # Formula J4-5
        term1 = 0.6 * Fu * Anv + Ubs * Fu * Ant
        term2 = 0.6 * Fy * Agv + Ubs * Fu * Ant
        
        Rn = min(term1, term2)
        return Rn, Anv, Ant, Agv

    # Plate Block Shear
    Rn_bs_pl, Anv_p, Ant_p, Agv_p = calc_block_shear(tp, Fy_pl, Fu_pl, lev, leh, n, s)
    
    # Beam Web Block Shear 
    # (Beam LEV usually equals Plate LEV in simple setup, LEH is Leh_beam)
    # Assume Leh_beam = Leh_plate for simplicity (or input)
    Rn_bs_bm, Anv_b, Ant_b, Agv_b = calc_block_shear(Tw, Fy_bm, Fu_bm, lev, leh, n, s) # Using same geom for now
    
    phiRn_bs = phi_block * min(Rn_bs_pl, Rn_bs_bm)
    gov_bs = "Plate" if Rn_bs_pl < Rn_bs_bm else "Beam Web"

    results['block_shear'] = {
        'title': f"Block Shear ({gov_bs})",
        'phi_Rn': phiRn_bs,
        'ratio': Vu / phiRn_bs,
        'latex_eq': r"\phi R_n = \phi [0.6 F_u A_{nv} + U_{bs} F_u A_{nt}]",
        'calcs': [
            "**Governing Limit State:**",
            f"Control Part: {gov_bs}",
            f"Shear Area (Anv): {Anv_p if gov_bs=='Plate' else Anv_b:.2f} cm²",
            f"Tension Area (Ant): {Ant_p if gov_bs=='Plate' else Ant_b:.2f} cm²",
            "Checked tearing along bolt line (Shear) + toe (Tension)"
        ]
    }
    summary_caps.append(('Block Shear', phiRn_bs))

    # ============================================
    # MODE 6: WELD STRENGTH
    # Rn = 0.60 * FEXX * Aw
    # ============================================
    # E70XX -> FEXX = 70 ksi = 4921 ksc (Use 4900)
    Fexx = 4900
    
    # Effective Throat (te) = 0.707 * size
    te = 0.707 * weld_D
    
    # Length of Weld (Double Fillet)
    # Lw = 2 * Plate Height (Simple assumption)
    Lw = 2 * h_pl
    
    # Area
    Aw = (te/10) * (Lw/10) # cm2
    
    Rn_weld = 0.6 * Fexx * Aw
    phiRn_weld = phi_weld * Rn_weld
    
    results['weld'] = {
        'title': "Weld Strength (Double Fillet)",
        'phi_Rn': phiRn_weld,
        'ratio': Vu / phiRn_weld,
        'latex_eq': r"\phi R_n = 0.75 \times 0.6 F_{EXX} A_w",
        'calcs': [
            f"Weld Size: {weld_D} mm",
            f"Effective Throat: {te:.2f} mm",
            f"Total Length: {Lw} mm (2 sides)",
            f"Electrode: E70XX (Fexx = 4900 ksc)"
        ]
    }
    summary_caps.append(('Weld', phiRn_weld))

    # ============================================
    # SUMMARY
    # ============================================
    # Find minimum capacity
    min_cap = min(summary_caps, key=lambda x: x[1])
    
    # Check Status
    status = "PASS" if Vu <= min_cap[1] else "FAIL"
    
    results['summary'] = {
        'status': status,
        'gov_mode': min_cap[0],
        'gov_capacity': min_cap[1],
        'utilization': Vu / min_cap[1]
    }

    return results
