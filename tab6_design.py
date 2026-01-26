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

def calculate_beam_shear_capacity(beam, Fy, method):
    d_mm = beam['D']
    tw_mm = beam.get('t1', 6.0)
    Aw = (d_mm * tw_mm) / 100.0 # cm2
    Vn = 0.6 * Fy * Aw # kg
    
    if method == "ASD":
        v_cap = Vn / 1.67
    else:
        v_cap = 0.9 * Vn
    return v_cap

def get_aisc_min_values(d_b):
    min_spacing = 2.67 * d_b
    pref_spacing = 3.0 * d_b
    
    if d_b <= 16: min_edge = 22
    elif d_b <= 20: min_edge = 26
    elif d_b <= 22: min_edge = 28
    elif d_b <= 24: min_edge = 30
    elif d_b <= 27: min_edge = 34
    elif d_b <= 30: min_edge = 38
    else: min_edge = 1.25 * d_b 
        
    return int(min_edge), round(min_spacing, 1), round(pref_spacing, 1)

# [NEW] Calculate Eccentric Weld Stress (Elastic Method)
def calculate_eccentric_weld(load_kg, e_mm, L_mm, weld_sz_mm, method):
    # 1. Geometry & Properties
    e_cm = e_mm / 10.0
    L_cm = L_mm / 10.0
    w_cm = weld_sz_mm / 10.0
    
    # Effective Throat (0.707 * size)
    te = 0.707 * w_cm
    
    # Section Properties (Double Fillet Weld treated as lines)
    # Area of weld throat
    Aw = 2 * (te * L_cm)  # cm2
    
    # Section Modulus (Sw) for 2 vertical lines
    # I = 2 * (te * L^3 / 12)
    # c = L / 2
    # Sw = I / c = 2 * (te * L^2 / 6) = te * L^2 / 3
    Sw = (te * (L_cm**2)) / 3.0 # cm3
    
    # 2. Stresses
    # Direct Shear (fv)
    fv = load_kg / Aw # ksc
    
    # Bending Stress due to Eccentricity (fb) = M / Sw
    Moment = load_kg * e_cm # kg-cm
    fb = Moment / Sw # ksc
    
    # Resultant Stress (Vector Sum)
    fr = math.sqrt(fv**2 + fb**2) # ksc
    
    # 3. Capacity Limit (E70XX Electrode)
    Fexx = 4921 # ksc (70 ksi)
    Fnw = 0.6 * Fexx # Nominal Strength
    
    if method == "ASD":
        # Omega = 2.00
        F_limit = Fnw / 2.00
        cap_load = (F_limit / fr) * load_kg # Back-calculate capacity load
    else:
        # Phi = 0.75
        F_limit = 0.75 * Fnw
        cap_load = (F_limit / fr) * load_kg
        
    ratio = fr / F_limit
    
    # Prepare Detail Object
    return {
        'title': 'Eccentric Weld Check',
        'capacity': cap_load,
        'ratio': ratio,
        'ref': 'AISC Part 8 (Elastic Method)',
        'latex_eq': r'f_r = \sqrt{f_v^2 + f_b^2} \leq \phi F_{nw}',
        'latex_sub': fr'f_v = \frac{{P}}{{A_w}}, \quad f_b = \frac{{P \cdot e}}{{S_w}}',
        'calcs': [
            f"Eccentricity (e) = {e_mm} mm (Plate Width - Leh)",
            f"Weld Length (L) = {L_mm} mm",
            f"Direct Shear (fv) = {fv:.2f} ksc",
            f"Bending Stress (fb) = {fb:.2f} ksc (Moment = {Moment:,.0f} kg-cm)",
            f"Resultant Stress (fr) = {fr:.2f} ksc",
            f"Limit Stress ({method}) = {F_limit:.2f} ksc"
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
            st.markdown(f"- **Depth:** {bm_D:.0f} mm | **Span:** {span_m} m")

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
    # 1. Main Checks
    calc_inputs = {
        'method': method,
        'load': Vu_load,
        'beam_tw': bm_Tw, 'beam_mat': mat_grade,
        'plate_t': plate_t, 'plate_h': pl_h, 'plate_mat': mat_grade,
        'bolt_dia': d_b, 'bolt_grade': bolt_grade,
        'n_rows': n_rows, 'pitch': pitch,
        'lev': lev, 'leh': leh, 
        'weld_sz': weld_sz
    }
    
    results = calc.calculate_shear_tab(calc_inputs)
    
    # 2. [NEW] Add Eccentric Weld Check Manually
    # Eccentricity e = Distance from Weld Line to Bolt Line
    eccentricity = pl_w - leh 
    if eccentricity < 0: eccentricity = 0 # Safety
    
    weld_ecc_res = calculate_eccentric_weld(Vu_load, eccentricity, pl_h, weld_sz, method)
    results['weld_eccentric'] = weld_ecc_res # Inject into results dict

    # 3. Re-evaluate Summary Status
    # หาค่า Ratio สูงสุดใหม่ รวมตัวที่เพิ่งเพิ่มเข้าไป
    all_ratios = [results[k]['ratio'] for k in results if 'ratio' in results[k] and k != 'summary']
    max_ratio = max(all_ratios)
    
    # Update Summary Dict
    results['summary']['utilization'] = max_ratio
    if max_ratio > 1.0:
        results['summary']['status'] = "FAIL"
    
    # หาตัวที่ Gov ใหม่ (เผื่อ Weld Eccentric เป็นตัว Gov)
    if weld_ecc_res['ratio'] == max_ratio:
        results['summary']['gov_mode'] = "Weld (Eccentric)"
        results['summary']['gov_capacity'] = weld_ecc_res['capacity']

    summary = results['summary']

    # --- DISPLAY OUTPUT ---
    with col_viz:
        status_color = "#2ecc71" if summary['status'] == "PASS" else "#e74c3c"
        header_text = summary['status']
        if is_deep_beam:
             header_text += " (Deep Beam Alert)"
             if summary['status'] == "PASS": status_color = "#f39c12" 
        
        st.markdown(f"""
        <div style="background-color: {status_color}; padding: 15px; border-radius: 8px; color: white; margin-bottom: 10px;">
            <h3 style="margin:0;">{header_text} (Ratio: {summary['utilization']:.2f})</h3>
            <p style="margin:0;">Load: {Vu_load:,.0f} kg | Capacity: {summary['gov_capacity']:,.0f} kg</p>
            <small>Governing: {summary['gov_mode']}</small>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🧊 3D Model & Constr.", "📝 Detailed Calc.", "📊 Exec. Summary"])
        
        # === TAB 1 ===
        with tab1:
            min_e, min_s, pref_s = get_aisc_min_values(d_b)
            chk_edge = "✅" if lev >= min_e else "❌ FAIL"
            chk_space = "✅" if pitch >= min_s else "❌ FAIL"
            
            st.markdown(f"""
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                <h5 style="margin:0; color:#495057;">👷 Construction Check (AISC J3.3)</h5>
                <table style="width:100%; text-align:center; font-size:0.9em;">
                    <tr style="background-color:#e9ecef;"><th>Check</th><th>Actual</th><th>Limit</th><th>Status</th></tr>
                    <tr><td align="left">Edge Dist</td><td>{lev}</td><td>≥ {min_e}</td><td>{chk_edge}</td></tr>
                    <tr><td align="left">Spacing</td><td>{pitch}</td><td>≥ {min_s}</td><td>{chk_space}</td></tr>
                </table>
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

        # === TAB 2 ===
        with tab2:
            st.markdown(f"#### 📐 Calculation Report ({method})")
            
            # เรียงลำดับใหม่ ให้ Weld Eccentric ขึ้นมาก่อนถ้ามัน Fail
            modes = ['weld_eccentric', 'bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
            
            for mode in modes:
                data = results.get(mode)
                if data:
                    icon = "✅" if data['ratio'] <= 1.0 else "❌"
                    with st.expander(f"{icon} {data['title']} (Ratio: {data['ratio']:.2f})", expanded=False):
                        st.markdown(f"**Ref:** `{data.get('ref', 'AISC 360-16')}`")
                        if 'latex_eq' in data: st.latex(data['latex_eq'])
                        if 'latex_sub' in data: st.latex(data['latex_sub'])
                        if 'calcs' in data:
                            for step in data['calcs']: st.markdown(f"- {step}")
                        
                        res_color = "green" if data['ratio'] <= 1.0 else "red"
                        sign = '≥' if data['ratio'] <= 1.0 else '<'
                        cap_txt = "Rn/Ω" if method == "ASD" else "φRn"
                        st.markdown(f"<span style='color:{res_color}'><b>Check:</b> {cap_txt} = {data['capacity']:,.0f} {sign} {Vu_load:,.0f} kg</span>", unsafe_allow_html=True)

        # === TAB 3 ===
        with tab3:
            st.markdown("### 📊 Engineering Summary")
            st.info("📌 Design Configuration")
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.markdown(f"**Beam:** {section_name}<br>D={bm_D:.0f} mm", unsafe_allow_html=True)
            with sc2: st.markdown(f"**Bolts:** {n_rows}x M{d_b:.0f}<br>Pitch: {pitch}", unsafe_allow_html=True)
            with sc3: st.markdown(f"**Plate:** {pl_h:.0f}x{pl_w}x{plate_t}<br>Weld: {weld_sz} mm", unsafe_allow_html=True)
            
            st.markdown("---")
            st.success("📌 Check Results")
            summary_data = []
            for m in modes:
                d = results.get(m)
                if d:
                    emoji = "✅ PASS" if d['ratio'] <= 1.0 else "❌ FAIL"
                    summary_data.append({"Item": d['title'], "Ratio": f"{d['ratio']:.2f}", "Result": emoji})
            st.table(pd.DataFrame(summary_data))
