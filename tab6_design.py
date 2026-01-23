import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure

# ==========================================
# 📐 HELPER: COMPATIBILITY CHECKER
# ==========================================
def get_max_rows(beam_d, beam_tf, k_dist, margin_top, margin_bot, pitch, lev):
    """คำนวณจำนวนแถวสูงสุดที่เป็นไปได้ในคานนี้"""
    # พื้นที่ใช้งานจริง (T-distance)
    workable_depth = beam_d - (2 * k_dist) 
    # หรือเอาแบบ Safety: Web Depth - Clearances
    available_h = beam_d - (2 * beam_tf) - margin_top - margin_bot
    
    # คำนวณ max rows: h = 2*lev + (n-1)*s
    # available_h >= 2*lev + (n-1)*s
    if available_h <= (2 * lev):
        return 0
    max_n = int(((available_h - (2 * lev)) / pitch) + 1)
    return max(1, max_n)

# ==========================================
# 🏗️ MAIN UI
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🏗️ Detailed Shear Connection Design")
    
    col_input, col_viz = st.columns([1.2, 2.5])

    # ==========================================
    # 🔴 1. INPUT PANEL (DEEP DETAIL)
    # ==========================================
    with col_input:
        
        # --- A. HOST BEAM ---
        with st.expander("1️⃣ Host Beam & Load", expanded=True):
            sec_name = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
            beam = SYS_H_BEAMS[sec_name]
            
            # Unit conversions
            d_factor = 10 if beam['D'] < 100 else 1
            bm_D = beam['D'] * d_factor
            bm_Tw = beam.get('t1', 6.0)
            bm_Tf = beam.get('t2', 9.0)
            k_des = 30 # สมมติค่า k (ระยะโค้ง) หรือดึงจาก DB
            
            st.caption(f"Depth: {bm_D:.0f} | Web: {bm_Tw} | Workable T: {bm_D - 2*k_des:.0f} mm")
            
            Vu_load = st.number_input("Factored Load, Vu (kg)", value=5000.0, step=500.0)

        # --- B. BOLT ASSEMBLY (DETAIL) ---
        with st.expander("2️⃣ Bolt Assembly Spec", expanded=True):
            c1, c2 = st.columns(2)
            bolt_dia = c1.selectbox("Dia.", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"], index=0)
            
            d_b = float(bolt_dia.replace("M",""))
            
            # Detailed Condition
            thread_cond = st.radio("Thread Condition", ["N (Included in Shear)", "X (Excluded)"], index=0, help="N: เกลียวอยู่ในระนาบเฉือน (Capacity ต่ำกว่า)\nX: เกลียวอยู่นอกระนาบเฉือน")
            hole_type = st.selectbox("Hole Type", ["STD (Standard)", "OVS (Oversize)", "SSL (Short Slot)", "LSL (Long Slot)"])
            
            st.info(f"Hole Size: {d_b + (2 if d_b < 24 else 3)} mm")

        # --- C. PLATE & WELD ---
        with st.expander("3️⃣ Plate & Weld", expanded=True):
            plate_grade = st.selectbox("Plate Mat.", ["A36 (Fy=250)", "A572-50 (Fy=345)", "SS400"], index=0)
            c3, c4 = st.columns(2)
            plate_t = c3.selectbox("Thick (tp)", [6, 9, 10, 12, 16, 19, 20, 25], index=3)
            weld_sz = c4.selectbox("Weld (mm)", [4, 5, 6, 8, 10], index=2, help="Fillet weld size at support")

        # --- D. GEOMETRY LAYOUT (CRITICAL) ---
        with st.expander("4️⃣ Layout & Dimensions", expanded=True):
            
            # 1. Pitch & Edge Controls
            st.markdown("**Spacing Constraints:**")
            col_g1, col_g2 = st.columns(2)
            pitch = col_g1.number_input("Pitch (s)", value=int(3*d_b), min_value=int(2.67*d_b), help="Distance center-to-center")
            lev = col_g2.number_input("V-Edge (Lev)", value=int(1.5*d_b), min_value=int(1.25*d_b))
            
            # 2. Row Calculation & Validation
            # คำนวณ Max Rows ที่คานนี้รับได้
            max_rows_allow = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            
            st.markdown(f"**Row Config (Max: {max_rows_allow}):**")
            n_rows = st.number_input("No. of Rows", min_value=2, max_value=max(2, max_rows_allow), value=min(3, max_rows_allow))
            
            # 3. Horizontal Setup
            st.markdown("**Horizontal Setup:**")
            setback = st.slider("Setback (Gap)", 0, 25, 12)
            leh = st.number_input("H-Edge (Leh)", value=40, min_value=int(1.25*d_b))

    # ==========================================
    # 🔵 2. VISUALIZATION & LOGIC
    # ==========================================
    with col_viz:
        # Calculate Derived Dimensions
        pl_h = (2 * lev) + ((n_rows - 1) * pitch)
        pl_w = setback + leh + 40 # +40 for tail clearance
        
        # --- TAB DISPLAY ---
        tab1, tab2 = st.tabs(["🧊 3D Fabrication Model", "📋 Engineering Summary"])
        
        with tab1:
            # 3D DRAWER
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h}
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
            st.plotly_chart(fig, use_container_width=True)
            
            # Quick Check Badge
            if pl_h > (bm_D - 2*bm_Tf):
                st.error(f"🚨 **CRITICAL GEOMETRY ERROR:** Plate height ({pl_h} mm) exceeds Web depth!")
            else:
                st.success(f"✅ Geometry Fits: Plate H {pl_h} mm < Web Clear {bm_D - 2*bm_Tf:.0f} mm")

        with tab2:
            st.markdown("#### ⚙️ Fabrication Specification")
            
            # Summary Table
            summ_data = {
                "Parameter": ["Bolt Spec", "Hole Type", "Threads", "Plate Size", "Weld Size", "Geometry (s / Lev / Leh)"],
                "Value": [
                    f"{n_rows} - {bolt_dia} {bolt_grade}",
                    hole_type,
                    f"Shear Plane: {'Excluded' if 'X' in thread_cond else 'Included'}",
                    f"PL{plate_t} x {pl_w} x {pl_h} mm ({plate_grade.split()[0]})",
                    f"{weld_sz} mm Fillet (E70XX)",
                    f"{pitch} / {lev} / {leh} mm"
                ]
            }
            st.table(pd.DataFrame(summ_data))
            
            st.markdown("---")
            st.info("💡 **Note:** Bolt length to be determined based on Grip = Tw + tp + Washer + Nut + Stickout.")
