# calculator_tab.py
import math

def check_geometry(inputs):
    """
    ตรวจสอบ Geometry (ระยะขอบ, ระยะห่าง) ตาม AISC Spec บท J3
    """
    msgs = []
    
    db = inputs['bolt_dia']
    pitch = inputs['pitch']
    lev = inputs['lev']   # Vertical Edge (Plate)
    leh = inputs['leh_beam'] # Horizontal Edge (Beam)
    
    # 1. Min Spacing (AISC J3.3)
    # Standard = 2.67d, Preferred = 3d
    min_spa = 2.67 * db
    if pitch < min_spa:
        msgs.append(f"❌ Bolt Pitch ({pitch} mm) < Min Allowed ({min_spa:.1f} mm)")
        
    # 2. Min Edge Distance (AISC Table J3.4)
    # Simplified logic for standard bolt sizes
    if db <= 16: min_e = 22
    elif db <= 20: min_e = 26
    elif db <= 22: min_e = 28
    elif db <= 24: min_e = 30
    elif db <= 30: min_e = 38
    else: min_e = 1.25 * db
    
    if lev < min_e:
        msgs.append(f"❌ Plate Vertical Edge ({lev} mm) < Min ({min_e} mm)")
    if leh < min_e: # เช็คระยะขอบบนเอวคานด้วย
        msgs.append(f"❌ Beam Web Horizontal Edge ({leh} mm) < Min ({min_e} mm)")
        
    return msgs

def calculate_shear_tab(inputs):
    """
    คำนวณกำลังรับน้ำหนักครบทุก Limit States
    """
    res = {}
    
    # --- 0. Geometry Check ---
    geo_errs = check_geometry(inputs)
    if geo_errs:
        return {'critical_error': True, 'errors': geo_errs}
        
    # --- 1. Parameters & Properties ---
    method = inputs['method']
    Vu = inputs['load']
    
    # Factors (ASD vs LRFD)
    if method == "ASD":
        # Omega Values
        Om_v = 1.50 # Shear Yield
        Om_r = 2.00 # Rupture / Bolts / Weld
        Om_f = 1.67 # Flexure
        
        # Design Strings for LaTeX
        txt_yield = r"\frac{R_n}{1.50}"
        txt_rup   = r"\frac{R_n}{2.00}"
        txt_flex  = r"\frac{M_n}{1.67}"
        
        # Numeric Factors for Calculation
        f_yield = 1.0/1.50
        f_rup   = 1.0/2.00
        f_flex  = 1.0/1.67
    else: # LRFD
        # Phi Values
        Phi_v = 1.00 # Shear Yield
        Phi_r = 0.75 # Rupture / Bolts / Weld
        Phi_f = 0.90 # Flexure
        
        # Design Strings
        txt_yield = r"1.00 R_n"
        txt_rup   = r"0.75 R_n"
        txt_flex  = r"0.90 M_n"
        
        # Numeric
        f_yield = 1.00
        f_rup   = 0.75
        f_flex  = 0.90

    # Dimensions & Materials
    # Plate
    Fy_pl = 2500 if inputs['plate_mat'] == 'SS400' else (2530 if inputs['plate_mat'] == 'A36' else 3500)
    Fu_pl = 4100 if inputs['plate_mat'] == 'SS400' else (4080 if inputs['plate_mat'] == 'A36' else 4570)
    tp = inputs['plate_t'] / 10.0 # cm
    h_pl = inputs['plate_h'] / 10.0 # cm
    
    # Beam Web
    Fy_bm = inputs['beam_fy']
    Fu_bm = 4000 if Fy_bm <= 2500 else 4500 # Approx
    tw_bm = inputs['beam_tw'] / 10.0 # cm
    
    # Bolt
    db = inputs['bolt_dia'] / 10.0 # cm
    Ab = (math.pi * db**2) / 4.0
    n = inputs['n_rows']
    
    # ==========================================
    # CASE 1: BOLT SHEAR (AISC J3.6)
    # ==========================================
    # Fnv: A325=3720 ksc, A490=4690 ksc, Gr8.8 ~ A325
    Fnv = 4690 if "A490" in inputs['bolt_grade'] else 3720
    Rn_bolt = Fnv * Ab * n
    Cap_bolt = Rn_bolt * f_rup
    
    res['bolt_shear'] = {
        'title': '1. Bolt Shear Strength',
        'ref': 'AISC Spec J3.6',
        'eq_code': r"R_n = F_{nv} A_b n_b",
        'subst': f"{Fnv} \\times {Ab:.2f} \\times {n} = {Rn_bolt:,.0f} kg",
        'eq_design': r"\phi R_n" if method=="LRFD" else r"\frac{R_n}{\Omega}",
        'design_val': Cap_bolt,
        'ratio': Vu / Cap_bolt
    }

    # ==========================================
    # CASE 2: BOLT BEARING (AISC J3.10)
    # Check BOTH Plate and Beam Web -> Take Min
    # ==========================================
    # 2.1 Plate Bearing
    lc_pl_edge = (inputs['lev']/10.0) - (db/2 + 0.1) # Hole margin approx 1mm
    lc_pl_in = (inputs['pitch']/10.0) - (db + 0.2)
    
    # Capacity per bolt (Edge vs Inner)
    rn_pl_e = min(1.2*lc_pl_edge*tp*Fu_pl, 2.4*db*tp*Fu_pl)
    rn_pl_i = min(1.2*lc_pl_in*tp*Fu_pl, 2.4*db*tp*Fu_pl)
    Rn_bear_pl = rn_pl_e + (rn_pl_i * (n - 1))
    
    # 2.2 Beam Web Bearing
    lc_wb_edge = (inputs['leh_beam']/10.0) - (db/2 + 0.1)
    rn_wb_e = min(1.2*lc_wb_edge*tw_bm*Fu_bm, 2.4*db*tw_bm*Fu_bm)
    rn_wb_i = min(1.2*lc_pl_in*tw_bm*Fu_bm, 2.4*db*tw_bm*Fu_bm) # Pitch same for web
    Rn_bear_wb = rn_wb_e + (rn_wb_i * (n - 1))
    
    # Governing
    if Rn_bear_pl < Rn_bear_wb:
        ctrl = "Plate Controls"
        Rn_bear = Rn_bear_pl
        subst_txt = f"Plate ({Rn_bear_pl:,.0f}) < Web ({Rn_bear_wb:,.0f})"
    else:
        ctrl = "Beam Web Controls"
        Rn_bear = Rn_bear_wb
        subst_txt = f"Web ({Rn_bear_wb:,.0f}) < Plate ({Rn_bear_pl:,.0f})"
        
    Cap_bear = Rn_bear * f_rup

    res['bearing'] = {
        'title': f'2. Bolt Bearing ({ctrl})',
        'ref': 'AISC Spec J3.10',
        'eq_code': r"R_n = \sum \min(1.2 l_c t F_u, 2.4 d t F_u)",
        'subst': subst_txt,
        'eq_design': txt_rup, # Use string defined above
        'design_val': Cap_bear,
        'ratio': Vu / Cap_bear
    }

    # ==========================================
    # CASE 3: SHEAR YIELDING (AISC J4.2)
    # Plate Only (Web usually governed by beam shear)
    # ==========================================
    Ag = h_pl * tp
    Rn_y = 0.60 * Fy_pl * Ag
    Cap_y = Rn_y * f_yield
    
    res['shear_yield'] = {
        'title': '3. Plate Shear Yielding',
        'ref': 'AISC Spec J4.2',
        'eq_code': r"R_n = 0.60 F_y A_g",
        'subst': f"0.60 \\times {Fy_pl} \\times {Ag:.2f} = {Rn_y:,.0f} kg",
        'eq_design': txt_yield,
        'design_val': Cap_y,
        'ratio': Vu / Cap_y
    }

    # ==========================================
    # CASE 4: SHEAR RUPTURE (AISC J4.2)
    # ==========================================
    d_hole = db + 0.2
    Anv = Ag - (n * d_hole * tp)
    Rn_rup = 0.60 * Fu_pl * Anv
    Cap_rup = Rn_rup * f_rup
    
    res['shear_rup'] = {
        'title': '4. Plate Shear Rupture',
        'ref': 'AISC Spec J4.2',
        'eq_code': r"R_n = 0.60 F_u A_{nv}",
        'subst': f"0.60 \\times {Fu_pl} \\times {Anv:.2f} = {Rn_rup:,.0f} kg",
        'eq_design': txt_rup,
        'design_val': Cap_rup,
        'ratio': Vu / Cap_rup
    }
    
    # ==========================================
    # CASE 5: BLOCK SHEAR (AISC J4.3)
    # Plate U-Shape Tearout
    # ==========================================
    # Geometry
    leh_pl = (inputs['plate_w']/10.0) - (inputs['leh_beam']/10.0)
    Ant = (leh_pl - 0.5*d_hole) * tp
    Agv = ((n-1)*(inputs['pitch']/10.0) + (inputs['lev']/10.0)) * tp
    Anv_bs = Agv - ((n-0.5)*d_hole * tp)
    
    Rn_bs_1 = 0.6*Fu_pl*Anv_bs + 1.0*Fu_pl*Ant # Fracture dominant
    Rn_bs_2 = 0.6*Fy_pl*Agv + 1.0*Fu_pl*Ant    # Yield dominant
    Rn_bs = min(Rn_bs_1, Rn_bs_2)
    Cap_bs = Rn_bs * f_rup
    
    res['block_shear'] = {
        'title': '5. Block Shear Rupture',
        'ref': 'AISC Spec J4.3',
        'eq_code': r"R_n = \min(0.6 F_u A_{nv} + U_{bs} F_u A_{nt}, ...)",
        'subst': f"Min({Rn_bs_1:,.0f}, {Rn_bs_2:,.0f}) = {Rn_bs:,.0f} kg",
        'eq_design': txt_rup,
        'design_val': Cap_bs,
        'ratio': Vu / Cap_bs
    }

    # ==========================================
    # CASE 6: PLATE FLEXURE (AISC Part 9/15)
    # Due to Eccentricity (Yielding & Rupture)
    # ==========================================
    ex = (inputs['plate_w']/10.0) - leh_pl # Distance Weld to Bolt Line
    Mu = Vu * ex
    
    # 6.1 Yielding
    Z_gross = (tp * h_pl**2) / 4.0
    Mn_y = Fy_pl * Z_gross
    Cap_my = Mn_y * f_flex
    
    # 6.2 Rupture (Approximate Z_net)
    Z_net = Z_gross * (Anv / Ag) # Simplified conservative
    Mn_r = Fu_pl * Z_net
    Cap_mr = Mn_r * f_flex
    
    # Governing Moment Cap
    Cap_m = min(Cap_my, Cap_mr)
    # Convert Moment Cap back to Load Cap for display consistency
    Cap_flex_load = Cap_m / ex if ex > 0 else 999999
    
    res['plate_flex'] = {
        'title': '6. Plate Flexure (Eccentricity)',
        'ref': 'AISC Manual Part 15',
        'eq_code': r"M_n = \min(F_y Z_{gross}, F_u Z_{net})",
        'subst': f"M_u = {Mu:,.0f} kg-cm (e={ex:.1f}cm)",
        'eq_design': txt_flex,
        'design_val': Cap_flex_load,
        'ratio': Vu / Cap_flex_load
    }

    # ==========================================
    # CASE 7: WELD STRENGTH (AISC Part 8)
    # Eccentric Method (Elastic Vector)
    # ==========================================
    w_sz = inputs['weld_sz'] / 10.0
    te = 0.707 * w_sz
    Lw = h_pl
    
    # Section Properties of Weld Group (Line)
    Aw = 2 * Lw * te
    Sw = (2 * te * Lw**2) / 6.0
    
    # Stresses
    fv = Vu / Aw
    fb = (Vu * ex) / Sw
    fr = math.sqrt(fv**2 + fb**2)
    
    # Limit
    Fexx = 4920 # E70
    Fnw = 0.60 * Fexx
    F_allow = Fnw * f_rup # Use same Phi/Omega as rupture/bolts
    
    ratio_w = fr / F_allow
    Cap_weld_equiv = Vu / ratio_w if ratio_w > 0 else 999999
    
    res['weld'] = {
        'title': '7. Weld Strength (Eccentric)',
        'ref': 'AISC Manual Part 8',
        'eq_code': r"f_r = \sqrt{f_v^2 + f_b^2} \leq \phi F_{nw}",
        'subst': f"f_r = {fr:.2f} ksc (Allow: {F_allow:.0f})",
        'eq_design': txt_rup, # Generic phi/omega label
        'design_val': Cap_weld_equiv,
        'ratio': ratio_w
    }

    return res
