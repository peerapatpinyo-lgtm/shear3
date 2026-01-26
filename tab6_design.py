#tab6_design.py
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

# ==========================================
# 🏗️ MAIN UI RENDERER
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🏗️ Shear Plate Design (Detailed Report)")
    col_input, col_viz = st.columns([1.3, 2.5])

    # --- 1. INPUT SECTION ---
    with col_input:
        with st.expander("1️⃣ Host Beam & Load", expanded=True):
            sec_name = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
            beam = SYS_H_BEAMS[sec_name]
            
            # Extract Beam Props
            d_factor = 10 if beam['D'] < 100 else 1
            bm_D = beam['D'] * d_factor
            bm_Tw = beam.get('t1', 6.0)
            bm_Tf = beam.get('t2', 9.0)
            k_des = 30 
            
            st.caption(f"D:{bm_D:.0f} | Tw:{bm_Tw} | Tf:{bm_Tf}")
            
            # Load & Materials
            c_load, c_mat = st.columns(2)
            Vu_load = c_load.number_input("V_u (kg)", value=5000.0, step=500.0)
            mat_grade = c_mat.selectbox("Mat.", ["A36", "SS400", "A572-50"])

        with st.expander("2️⃣ Bolt & Geometry", expanded=True):
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

    # --- 2. CALCULATION LINK ---
    # Prepare inputs for calculator
    calc_inputs = {
        'load': Vu_load,
        'beam_tw': bm_Tw, 'beam_mat': mat_grade,
        'plate_t': plate_t, 'plate_h': pl_h, 'plate_mat': mat_grade,
        'bolt_dia': d_b, 'bolt_grade': bolt_grade,
        'n_rows': n_rows, 'pitch': pitch,
        'lev': lev, 'leh': leh, 
        'weld_sz': weld_sz
    }
    
    # Run Calculation
    results = calc.calculate_shear_tab(calc_inputs)
    summary = results['summary']

    # --- 3. DISPLAY OUTPUT ---
    with col_viz:
        # Status Box
        status_color = "#2ecc71" if summary['status'] == "PASS" else "#e74c3c"
        st.markdown(f"""
        <div style="background-color: {status_color}; padding: 15px; border-radius: 8px; color: white; margin-bottom: 10px;">
            <h3 style="margin:0;">{summary['status']} (Ratio: {summary['utilization']:.2f})</h3>
            <p style="margin:0;">Load: {Vu_load:,.0f} kg | Capacity: {summary['gov_capacity']:,.0f} kg</p>
            <small>Governing Mode: {summary['gov_mode']}</small>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🧊 3D Model", "📝 Detailed Calc. Sheet"])
        
        with tab1:
            # Prepare Data for Drawer
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz}
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            try:
                fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error Plotting: {e}")

        with tab2:
            st.markdown("#### 📐 Engineering Calculation Report (AISC LRFD)")
            st.markdown("---")
            
            # Loop through modes (Updated to include block_shear)
            modes = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
            
            for mode in modes:
                data = results.get(mode)
                if data:
                    # Header
                    icon = "✅" if data['ratio'] <= 1.0 else "❌"
                    # ใช้ Expander แสดงผล เพื่อความสะอาดตา
                    with st.expander(f"{icon} {data['title']} (Ratio: {data['ratio']:.2f})", expanded=False):
                        
                        # 1. แสดงสูตร LaTeX
                        if 'latex_eq' in data:
                            st.latex(data['latex_eq'])
                        
                        # 2. แสดงขั้นตอนการแทนค่า
                        st.markdown("**Calculation Steps:**")
                        if 'calcs' in data:
                            for step in data['calcs']:
                                st.markdown(f"- {step}")
                        elif 'desc' in data: # Fallback เผื่อกรณีไฟล์ไม่ตรงกัน
                            st.markdown(f"- {data['desc']}")
                        
                        # 3. สรุปผล
                        res_color = "green" if data['ratio'] <= 1.0 else "red"
                        sign = '≥' if data['ratio'] <= 1.0 else '<'
                        st.markdown(f"""
                        <div style="background-color: rgba(0,0,0,0.05); padding: 8px; border-radius: 4px; border-left: 4px solid {res_color};">
                            <b>Result:</b> φRn = {data['phi_Rn']:.0f} kg {sign} Vu ({Vu_load:.0f} kg)
                        </div>
                        """, unsafe_allow_html=True)
