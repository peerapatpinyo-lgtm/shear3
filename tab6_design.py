# tab6_design.py
import streamlit as st
import pandas as pd
import numpy as np
import math
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc 

# ==========================================
# 📐 HELPER FUNCTIONS
# ==========================================
def get_max_rows(beam_d, beam_tf, k_dist, margin_top, margin_bot, pitch, lev):
    """คำนวณจำนวนแถวน็อตสูงสุดที่เป็นไปได้"""
    workable_depth = beam_d - (2 * k_dist) 
    available_h = beam_d - (2 * beam_tf) - margin_top - margin_bot
    if available_h <= (2 * lev): return 0
    max_n = int(((available_h - (2 * lev)) / pitch) + 1)
    return max(0, max_n)

def get_material_Fu(Fy):
    """ประมาณค่า Fu จาก Fy (สำหรับตรวจสอบ Bearing)"""
    # SS400/A36 (Fy ~2400) -> Fu ~4000-4100
    # SM520 (Fy ~3500-3600) -> Fu ~5000-5200
    if Fy <= 2500: return 4000 # ksc (SS400)
    elif Fy <= 3000: return 4500 # ksc (A572 Gr.50 approx)
    else: return 5000 # ksc (SM520)

def calculate_beam_shear_capacity(beam, Fy, method):
    d_mm = beam['D']
    tw_mm = beam.get('t1', 6.0)
    Aw = (d_mm * tw_mm) / 100.0 # cm2
    Vn = 0.6 * Fy * Aw # kg
    if method == "ASD": return Vn / 1.67
    else: return 0.9 * Vn

def get_aisc_min_values(d_b):
    """คืนค่า Min Edge, Min Spacing"""
    min_spacing = 2.67 * d_b
    pref_spacing = 3.0 * d_b
    
    if d_b <= 16: min_edge = 22
    elif d_b <= 20: min_edge = 26
    elif d_b <= 22: min_edge = 28
    elif d_b <= 24: min_edge = 30
    elif d_b <= 30: min_edge = 38
    else: min_edge = 1.25 * d_b 
    return int(min_edge), round(min_spacing, 1), round(pref_spacing, 1)

def get_min_weld_size(part_t_mm):
    """AISC Table J2.4 Min Size of Fillet Welds"""
    if part_t_mm <= 6: return 3
    elif part_t_mm <= 13: return 5
    elif part_t_mm <= 19: return 6
    else: return 8

# [Logic เดิม] Calculate Eccentric Weld Stress
def calculate_eccentric_weld(load_kg, e_mm, L_mm, weld_sz_mm, method):
    e_cm = e_mm / 10.0
    L_cm = L_mm / 10.0
    w_cm = weld_sz_mm / 10.0
    te = 0.707 * w_cm
    
    Aw = 2 * (te * L_cm)
    Sw = (te * (L_cm**2)) / 3.0 
    
    fv = load_kg / Aw 
    Moment = load_kg * e_cm 
    fb = Moment / Sw 
    fr = math.sqrt(fv**2 + fb**2) 
    
    Fexx = 4921 # 70 ksi
    Fnw = 0.6 * Fexx
    
    if method == "ASD":
        F_limit = Fnw / 2.00
    else:
        F_limit = 0.75 * Fnw
        
    cap_load = (F_limit / fr) * load_kg if fr > 0 else 0
    ratio = fr / F_limit if F_limit > 0 else 999
    
    return {
        'title': 'Weld (Eccentric Check)',
        'capacity': cap_load,
        'ratio': ratio,
        'ref': 'AISC Part 8 (Elastic Vector)',
        'latex_eq': r'f_r = \sqrt{f_v^2 + f_b^2} \leq \phi F_{nw}',
        'latex_sub': fr'f_v = {fv:.2f}, f_b = {fb:.2f} \text{{ (ksc)}}',
        'calcs': [
            f"Eccentricity (e) = {e_mm} mm",
            f"Resultant Stress = {fr:.2f} ksc (Limit {F_limit:.2f})"
        ]
    }

# [NEW] Calculate Beam Web Bearing
def calculate_web_bearing(load_kg, d_b, n_bolts, tw_mm, Fy, method):
    Fu = get_material_Fu(Fy)
    # Rn = 2.4 * d * t * Fu (Consider deformation at bolt hole)
    # Note: Assuming standard edge distance on beam web is sufficient
    rn_per_bolt = 2.4 * (d_b/10.0) * (tw_mm/10.0) * Fu 
    Rn_total = rn_per_bolt * n_bolts
    
    if method == "ASD":
        cap = Rn_total / 2.00 # Omega = 2.00
    else:
        cap = 0.75 * Rn_total # Phi = 0.75
        
    ratio = load_kg / cap
    
    return {
        'title': 'Bearing on Beam Web',
        'capacity': cap,
        'ratio': ratio,
        'ref': 'AISC J3.10 (Bearing)',
        'latex_eq': r'R_n = n \times 2.4 d t_w F_u',
        'calcs': [
            f"Beam Web (Tw) = {tw_mm} mm",
            f"Beam Fu (Est.) = {Fu} ksc",
            f"Nominal/Bolt = {rn_per_bolt:,.0f} kg",
            f"Total Capacity = {cap:,.0f} kg"
        ]
    }

# ==========================================
# 🏗️ MAIN UI RENDERER
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Shear Plate Design ({method} Method)")
    
    if section_name not in SYS_H_BEAMS:
        section_name = list(SYS_H_BEAMS.keys())[0]
        
    beam = SYS_H_BEAMS[section_name]
    d_factor = 10 if beam['D'] < 100 else 1
    bm_D = beam['D'] * d_factor
    bm_Tw = beam.get('t1', 6.0)
    bm_Tf = beam.get('t2', 9.0)
    k_des = 30 

    ld_ratio = (span_m * 1000) / bm_D
    is_deep_beam = False
    
    col_input, col_viz = st.columns([1.3, 2.5])

    # --- INPUT SECTION ---
    with col_input:
        with st.expander("1️⃣ Beam Info & Load Verification", expanded=True):
            st.info(f"📌 **Current Beam:** `{section_name}`")
            st.markdown(f"- **D:** {bm_D:.0f} mm | **Tw:** {bm_Tw} mm")

            if ld_ratio < 4.0:
                is_deep_beam = True
                st.warning(f"⚠️ Deep Beam (L/D={ld_ratio:.2f})")
            
            st.markdown("---")
            st.markdown("##### 📥 Shear Load Input")
            beam_shear_cap = calculate_beam_shear_capacity(beam, Fy, method)
            v_75_percent = 0.75 * beam_shear_cap
            
            load_mode = st.radio("Select Load Source:", 
                                 [f"Auto (75% of Capacity)", "Manual Input"],
                                 horizontal=True)
            
            if "Auto" in load_mode:
                load_label = "Va" if method == "ASD" else "Vu"
                st.info(f"ℹ️ Beam Cap: {beam_shear_cap:,.0f} kg")
                Vu_load = v_75_percent
                st.markdown(f"<div style='padding:8px; background:#e8f4f8; border-radius:4px;'><b>Design Load:</b> {Vu_load:,.0f} kg</div>", unsafe_allow_html=True)
            else:
                Vu_load = st.number_input(f"Design Load ({method}) [kg]", value=5000.0, step=500.0)
            
            mat_grade = st.selectbox("Plate Mat.", ["A36", "SS400", "A572-50"])

        with st.expander("2️⃣ Bolt & Connection Details", expanded=True):
            c1, c2 = st.columns(2)
            bolt_dia = c1.selectbox("Dia.", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            d_b = float(bolt_dia.replace("M",""))
            
            pitch = st.number_input("Pitch (s)", value=int(3*d_b), min_value=int(2.67*d_b))
            lev = st.number_input("V-Edge (Lev)", value=int(1.5*d_b))
            
            max_rows = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            n_rows = st.number_input("Rows", min_value=2, max_value=max(2, max_rows), value=max(2, min(3, max_rows)))
            
            st.markdown("---")
            setback = st.slider("Setback", 0, 25, 12)
            leh = st.number_input("H-Edge (Leh)", value=40)

        with st.expander("3️⃣ Plate & Weld", expanded=True):
            min_w = setback + leh + int(1.25*d_b)
            w_mode = st.radio("Width", ["Auto", "Manual"], horizontal=True)
            if w_mode == "Auto":
                pl_w = min_w
            else:
                pl_w = st.selectbox("Flat Bar (mm)", [75, 90, 100, 125, 150, 200], index=2)
                if pl_w < min_w: st.error(f"Too narrow! Min: {min_w}")

            c3, c4 = st.columns(2)
            plate_t = c3.selectbox("Thick", [6, 9, 10, 12, 16, 20], index=2)
            weld_sz = c4.selectbox("Weld", [4, 6, 8, 10], index=1)
            
            pl_h = (2 * lev) + ((n_rows - 1) * pitch)

    # --- CALCULATION ---
    # 1. Standard Checks (Plate, Bolt, Weld Shear)
    calc_inputs = {
        'method': method, 'load': Vu_load,
        'beam_tw': bm_Tw, 'beam_mat': mat_grade,
        'plate_t': plate_t, 'plate_h': pl_h, 'plate_mat': mat_grade,
        'bolt_dia': d_b, 'bolt_grade': bolt_grade,
        'n_rows': n_rows, 'pitch': pitch,
        'lev': lev, 'leh': leh, 'weld_sz': weld_sz
    }
    results = calc.calculate_shear_tab(calc_inputs)
    
    # 2. [ADDED] Eccentric Weld Check
    eccentricity = max(0, pl_w - leh)
    weld_ecc_res = calculate_eccentric_weld(Vu_load, eccentricity, pl_h, weld_sz, method)
    results['weld_eccentric'] = weld_ecc_res

    # 3. [ADDED] Beam Web Bearing Check (CRITICAL)
    web_bearing_res = calculate_web_bearing(Vu_load, d_b, n_rows, bm_Tw, Fy, method)
    results['web_bearing'] = web_bearing_res

    # 4. Re-evaluate Summary
    all_ratios = [results[k]['ratio'] for k in results if 'ratio' in results[k] and k != 'summary']
    max_ratio = max(all_ratios)
    
    results['summary']['utilization'] = max_ratio
    results['summary']['status'] = "FAIL" if max_ratio > 1.0 else "PASS"
    
    # Update Governing Mode
    if web_bearing_res['ratio'] == max_ratio:
        results['summary']['gov_mode'] = "Beam Web Bearing"
        results['summary']['gov_capacity'] = web_bearing_res['capacity']
    elif weld_ecc_res['ratio'] == max_ratio:
        results['summary']['gov_mode'] = "Weld (Eccentric)"
        results['summary']['gov_capacity'] = weld_ecc_res['capacity']

    summary = results['summary']

    # --- DISPLAY OUTPUT ---
    with col_viz:
        # Header Status
        status_color = "#2ecc71" if summary['status'] == "PASS" else "#e74c3c"
        header_text = summary['status']
        if is_deep_beam:
             header_text += " (Deep Beam Warning)"
             if summary['status'] == "PASS": status_color = "#f39c12" 
        
        st.markdown(f"""
        <div style="background-color: {status_color}; padding: 15px; border-radius: 8px; color: white; margin-bottom: 10px;">
            <h3 style="margin:0;">{header_text} (Ratio: {summary['utilization']:.2f})</h3>
            <p style="margin:0;">Load: {Vu_load:,.0f} kg | Capacity: {summary['gov_capacity']:,.0f} kg</p>
            <small>Governing: {summary['gov_mode']}</small>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🏗️ Constr. Check (Site)", "📝 Engineering Calc", "📊 Summary"])
        
        # === TAB 1: SITE & CONSTRUCTION CHECK ===
        with tab1:
            # 1. AISC Min Geometry
            min_e, min_s, pref_s = get_aisc_min_values(d_b)
            
            # 2. Min Weld Size (AISC J2.4)
            # Compare with Thicker Part (Usually Plate, but safest to check Plate T)
            req_min_weld = get_min_weld_size(plate_t)
            chk_weld = "✅" if weld_sz >= req_min_weld else f"❌ Min {req_min_weld}mm"
            
            # 3. Rotation Check (Ductility)
            # Rule: t_plate <= db/2 + 2mm
            max_t_rot = (d_b / 2) + 2.0
            chk_rot = "✅" if plate_t <= max_t_rot else f"⚠️ Rigid ({plate_t} > {max_t_rot}mm)"

            st.markdown(f"""
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                <h5 style="margin:0; color:#495057;">👷 Construction & Ductility Check</h5>
                <table style="width:100%; text-align:center; font-size:0.9em;">
                    <tr style="background-color:#e9ecef;"><th>Check Item</th><th>Actual</th><th>Limit/Req.</th><th>Status</th></tr>
                    <tr><td align="left">Edge Dist.</td><td>{lev} mm</td><td>≥ {min_e} mm</td><td>{"✅" if lev>=min_e else "❌ FAIL"}</td></tr>
                    <tr><td align="left">Spacing</td><td>{pitch} mm</td><td>≥ {min_s} mm</td><td>{"✅" if pitch>=min_s else "❌ FAIL"}</td></tr>
                    <tr style="border-top:2px solid #ddd;"><td align="left"><b>Weld Size</b></td><td><b>{weld_sz} mm</b></td><td>≥ {req_min_weld} mm</td><td>{chk_weld}</td></tr>
                    <tr><td align="left"><b>Rotation</b> (Flexibility)</td><td>t={plate_t} mm</td><td>Max {max_t_rot:.1f} mm</td><td>{chk_rot}</td></tr>
                </table>
                <small style="color:gray;">*Weld Size based on AISC Table J2.4 (Thicker Part)<br>*Rotation check ensures simple shear behavior.</small>
            </div>
            """, unsafe_allow_html=True)

            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz}
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            try:
                fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error Plotting: {e}")

        # === TAB 2: DETAILED CALC ===
        with tab2:
            st.markdown(f"#### 📐 Engineering Calculation ({method})")
            
            # เรียงลำดับ: เช็ค Bearing Web ก่อนเลย เพราะมักจะตายที่ตรงนี้
            modes = ['web_bearing', 'weld_eccentric', 'bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
            
            for mode in modes:
                data = results.get(mode)
                if data:
                    icon = "✅" if data['ratio'] <= 1.0 else "❌"
                    # Highlight Web Bearing specifically
                    title_style = "color:#d9534f; font-weight:bold;" if mode == 'web_bearing' and data['ratio'] > 1.0 else ""
                    
                    with st.expander(f"{icon} {data['title']} (Ratio: {data['ratio']:.2f})", expanded=(data['ratio']>1.0)):
                        st.markdown(f"**Ref:** `{data.get('ref', '-')}`")
                        if 'latex_eq' in data: st.latex(data['latex_eq'])
                        if 'calcs' in data:
                            for step in data['calcs']: st.markdown(f"- {step}")
                        
                        res_color = "green" if data['ratio'] <= 1.0 else "red"
                        sign = '≥' if data['ratio'] <= 1.0 else '<'
                        cap_txt = "Rn/Ω" if method == "ASD" else "φRn"
                        st.markdown(f"<span style='color:{res_color}'><b>Check:</b> {cap_txt} = {data['capacity']:,.0f} {sign} {Vu_load:,.0f} kg</span>", unsafe_allow_html=True)

        # === TAB 3: SUMMARY ===
        with tab3:
            st.markdown("### 📊 Engineering Summary")
            
            # Show Critical Check (Web Bearing)
            wb = results['web_bearing']
            wb_status = "PASS" if wb['ratio'] <= 1.0 else "FAIL"
            wb_color = "green" if wb_status == "PASS" else "red"
            
            st.markdown(f"""
            <div style="padding:10px; border:1px solid {wb_color}; border-left: 5px solid {wb_color}; margin-bottom:15px; background:rgba(0,0,0,0.02)">
                <strong style="color:{wb_color}">Critical Check: Beam Web Bearing</strong><br>
                Beam Web Thickness: {bm_Tw} mm <br>
                Status: <b>{wb_status}</b> (Ratio {wb['ratio']:.2f})
            </div>
            """, unsafe_allow_html=True)
            
            summary_data = []
            for m in modes:
                d = results.get(m)
                if d:
                    emoji = "✅ PASS" if d['ratio'] <= 1.0 else "❌ FAIL"
                    summary_data.append({"Item": d['title'], "Ratio": f"{d['ratio']:.2f}", "Result": emoji})
            st.table(pd.DataFrame(summary_data))
