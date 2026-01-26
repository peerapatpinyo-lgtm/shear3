# tab6_design.py
import streamlit as st
import pandas as pd
import numpy as np
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
    """คำนวณ Shear Capacity ของคาน (Vn/Omega หรือ Phi*Vn) เพื่อใช้เป็นฐาน 75%"""
    # 1. Properties
    d_mm = beam['D']
    tw_mm = beam.get('t1', 6.0)
    
    # 2. Area Web (cm2)
    Aw = (d_mm * tw_mm) / 100.0 # convert mm2 to cm2
    
    # 3. Nominal Shear Strength (Vn) = 0.6 * Fy * Aw
    # (อ้างอิง AISC G2 สำหรับ I-shape members)
    Vn = 0.6 * Fy * Aw # unit: kg
    
    # 4. Design Capacity
    if method == "ASD":
        # Omega = 1.67 (Standard for Shear)
        v_cap = Vn / 1.67
    else:
        # Phi = 0.9 (Standard for Shear usually 0.9 or 1.0 depending on cv, use 0.9 for conservative design)
        v_cap = 0.9 * Vn
        
    return v_cap

# ==========================================
# 🏗️ MAIN UI RENDERER
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Shear Plate Design ({method} Method)")
    
    # 1. ดึงข้อมูลจาก Database
    if section_name not in SYS_H_BEAMS:
        section_name = list(SYS_H_BEAMS.keys())[0]
        
    beam = SYS_H_BEAMS[section_name]
    
    # Extract Beam Props
    d_factor = 10 if beam['D'] < 100 else 1
    bm_D = beam['D'] * d_factor
    bm_Tw = beam.get('t1', 6.0)
    bm_Tf = beam.get('t2', 9.0)
    k_des = 30 

    # 2. Deep Beam Check
    ld_ratio = (span_m * 1000) / bm_D
    is_deep_beam = False
    
    col_input, col_viz = st.columns([1.3, 2.5])

    # --- INPUT SECTION ---
    with col_input:
        with st.expander("1️⃣ Beam Info & Load Verification", expanded=True):
            st.info(f"📌 **Current Beam:** `{section_name}`")
            
            st.markdown(f"""
            - **Depth (D):** {bm_D:.0f} mm
            - **Web (Tw):** {bm_Tw} mm
            - **Span (L):** {span_m} m
            """)

            # Logic แจ้งเตือน Deep Beam
            if ld_ratio < 4.0:
                is_deep_beam = True
                st.warning(f"⚠️ **Deep Beam Warning!** (L/D = {ld_ratio:.2f})")
                st.markdown("""
                <small style="color: #856404;">
                Span-to-depth ratio < 4. Standard beam theory allows only approximate results.
                <b>Recommendation:</b> Verify with Strut-and-Tie Model.
                </small>
                """, unsafe_allow_html=True)
            else:
                st.success(f"✅ Geometry OK (L/D = {ld_ratio:.2f})")

            st.markdown("---")
            
            # [UPDATED] Load Input Selection
            st.markdown("##### 📥 Shear Load Input")
            
            # คำนวณ Capacity ของคานเตรียมไว้
            beam_shear_cap = calculate_beam_shear_capacity(beam, Fy, method)
            v_75_percent = 0.75 * beam_shear_cap
            
            load_mode = st.radio("Select Load Source:", 
                                 [f"Auto (75% of Capacity)", "Manual Input"],
                                 horizontal=True)
            
            if "Auto" in load_mode:
                # กรณีเลือก Auto
                load_label = "Va (ASD)" if method == "ASD" else "Vu (LRFD)"
                st.info(f"ℹ️ **Beam Capacity:** {beam_shear_cap:,.0f} kg")
                Vu_load = v_75_percent
                st.markdown(f"""
                <div style="padding:10px; background-color:#e8f4f8; border-radius:5px; border:1px solid #b8daff;">
                    <b>Design Load ({load_label}):</b> <br>
                    <span style="font-size:20px; color:#004085; font-weight:bold;">{Vu_load:,.0f} kg</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                # กรณีเลือก Manual (ของเดิม)
                load_label = "Va (kg)" if method == "ASD" else "Vu (kg)"
                Vu_load = st.number_input(load_label, value=5000.0, step=500.0)
            
            # Material Grade
            mat_grade = st.selectbox("Plate Mat.", ["A36", "SS400", "A572-50"])

        with st.expander("2️⃣ Bolt & Connection Details", expanded=True):
            c1, c2 = st.columns(2)
            bolt_dia = c1.selectbox("Dia.", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            d_b = float(bolt_dia.replace("M",""))
            
            # Geometry
            pitch = st.number_input("Pitch (s)", value=int(3*d_b), min_value=int(2.67*d_b))
            lev = st.number_input("V-Edge (Lev)", value=int(1.5*d_b))
            
            # Row Logic
            max_rows = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            n_rows = st.number_input("Rows", min_value=2, max_value=max(2, max_rows), value=max(2, min(3, max_rows)))
            
            st.markdown("---")
            setback = st.slider("Setback", 0, 25, 12)
            leh = st.number_input("H-Edge (Leh)", value=40)

        with st.expander("3️⃣ Plate & Weld", expanded=True):
            # Width Logic
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

    # --- CALCULATION LINK ---
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
    summary = results['summary']

    # --- DISPLAY OUTPUT ---
    with col_viz:
        # Status Box
        status_color = "#2ecc71" if summary['status'] == "PASS" else "#e74c3c"
        header_text = summary['status']
        
        # Adjust Header for Deep Beam Warning
        if is_deep_beam:
             header_text += " (⚠️ Deep Beam Warning)"
             if summary['status'] == "PASS":
                 status_color = "#f39c12" 
        
        st.markdown(f"""
        <div style="background-color: {status_color}; padding: 15px; border-radius: 8px; color: white; margin-bottom: 10px;">
            <h3 style="margin:0;">{header_text} (Ratio: {summary['utilization']:.2f})</h3>
            <p style="margin:0;">Load: {Vu_load:,.0f} kg | Capacity: {summary['gov_capacity']:,.0f} kg</p>
            <small>Governing Mode: {summary['gov_mode']} ({method})</small>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["🧊 3D Model", "📝 Detailed Calc. Sheet", "📊 Executive Summary"])
        
        # === TAB 1: 3D MODEL ===
        with tab1:
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz}
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            try:
                fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error Plotting: {e}")

        # === TAB 2: DETAILED CALCULATION ===
        with tab2:
            st.markdown(f"#### 📐 Engineering Calculation Report ({method})")
            
            if is_deep_beam:
                st.warning(f"""
                **Design Alert:**
                Beam Span ({span_m} m) / Depth ({bm_D/1000:.2f} m) = **{ld_ratio:.2f}** (< 4.0).
                Classified as **Deep Beam**. Flexural assumptions may not apply.
                Ensure connection detailing accounts for non-linear shear distribution (Strut-and-Tie).
                """)
            
            st.caption("Step-by-step verification with AISC References.")
            st.markdown("---")
            
            modes = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
            
            for mode in modes:
                data = results.get(mode)
                if data:
                    icon = "✅" if data['ratio'] <= 1.0 else "❌"
                    with st.expander(f"{icon} {data['title']} (Ratio: {data['ratio']:.2f})", expanded=False):
                        st.markdown(f"**Reference:** `{data.get('ref', 'AISC 360-16')}`")
                        
                        st.markdown("**1. Formula:**")
                        if 'latex_eq' in data: st.latex(data['latex_eq'])
                        
                        st.markdown("**2. Substitution:**")
                        if 'latex_sub' in data: st.latex(data['latex_sub'])
                        
                        st.markdown("**3. Parameters:**")
                        if 'calcs' in data:
                            for step in data['calcs']: st.markdown(f"- {step}")
                        
                        res_color = "green" if data['ratio'] <= 1.0 else "red"
                        sign = '≥' if data['ratio'] <= 1.0 else '<'
                        cap_symbol = "Rn/Ω" if method == "ASD" else "φRn"
                        
                        st.markdown(f"""
                        <div style="background-color: rgba(0,0,0,0.05); padding: 8px; border-radius: 4px; border-left: 4px solid {res_color}; margin-top: 10px;">
                            <b>Answer:</b> {cap_symbol} = <b>{data['capacity']:,.0f} kg</b> {sign} Load ({Vu_load:,.0f} kg)
                        </div>
                        """, unsafe_allow_html=True)

        # === TAB 3: EXECUTIVE SUMMARY ===
        with tab3:
            st.markdown("### 📊 Design Specification & Verification Summary")
            st.markdown("---")
            
            # PART 1: MATERIAL & SPECIFICATIONS
            st.info("📌 1. Design Configuration (รายการประกอบแบบ)")
            
            sc1, sc2, sc3 = st.columns(3)
            
            with sc1:
                st.markdown("##### 🏗️ Host Beam")
                st.markdown(f"""
                - **Section:** `{section_name}`
                - **Depth:** {bm_D:.0f} mm
                - **Span:** {span_m} m
                - **L/D Ratio:** {ld_ratio:.2f}
                - **Mat:** {mat_grade}
                """)
                if is_deep_beam:
                    st.error("⚠️ Deep Beam (Check STM)")
                
            with sc2:
                st.markdown("##### 🔩 Bolts")
                st.markdown(f"""
                - **Size:** M{d_b:.0f} ({bolt_grade})
                - **Qty:** {n_rows} Rows (1 Col)
                - **Total:** {n_rows} Bolts
                - **Pitch:** {pitch} mm
                """)
                
            with sc3:
                st.markdown("##### ⬜ Plate & Weld")
                st.markdown(f"""
                - **Plate Size:** {pl_h:.0f} x {pl_w} mm
                - **Thickness:** {plate_t} mm
                - **Weld:** {weld_sz} mm (Fillet)
                - **Mat:** {mat_grade}
                """)

            st.markdown("---")
            
            # PART 2: ENGINEERING CHECKLIST
            st.success("📌 2. Engineering Verification Checklist")
            
            summary_data = []
            modes_chk = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
            
            for m in modes_chk:
                d = results.get(m)
                if d:
                    cap_val = f"{d['capacity']:,.0f}"
                    ratio_val = d['ratio']
                    status_emoji = "✅ PASS" if ratio_val <= 1.0 else "❌ FAIL"
                    
                    summary_data.append({
                        "Check Item": d['title'],
                        "Capacity (kg)": cap_val,
                        "Demand (kg)": f"{Vu_load:,.0f}",
                        "Ratio": f"{ratio_val:.2f}",
                        "Result": status_emoji
                    })
            
            df_sum = pd.DataFrame(summary_data)
            st.table(df_sum)
            
            # Overall Conclusion
            final_res = summary['status']
            if final_res == "PASS" and is_deep_beam:
                final_color = "orange"
                note_text = "PASS (See Warning)"
                sub_note = "Check Deep Beam requirements (Strut-and-Tie)"
            elif final_res == "PASS":
                final_color = "green"
                note_text = "PASS"
                sub_note = ""
            else:
                final_color = "red"
                note_text = "FAIL"
                sub_note = ""

            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border: 2px solid {final_color}; border-radius: 10px; background-color: rgba(0,0,0,0.02);">
                <h2 style="color: {final_color}; margin:0;">OVERALL RESULT: {note_text}</h2>
                <p>Governing Limit State: <b>{summary['gov_mode']}</b> (Ratio {summary['utilization']:.2f})</p>
                <small style="color:{final_color};">{sub_note}</small>
            </div>
            """, unsafe_allow_html=True)
