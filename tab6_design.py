import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure

# ==========================================
# 📐 HELPER: CALCULATION
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
    return max(0, max_n)

# ==========================================
# 🏗️ MAIN UI
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🏗️ Shear Plate Design (Professional)")
    
    col_input, col_viz = st.columns([1.3, 2.5]) # ขยายช่อง Input นิดนึง

    # ==========================================
    # 🔴 1. INPUT PANEL
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
            k_des = 30 
            
            st.caption(f"Depth: {bm_D:.0f} | Tw: {bm_Tw} | Workable: {bm_D - 2*k_des:.0f}")
            Vu_load = st.number_input("Factored Load (kg)", value=5000.0, step=500.0)

        # --- B. BOLT ASSEMBLY ---
        with st.expander("2️⃣ Bolt Assembly", expanded=True):
            c1, c2 = st.columns(2)
            bolt_dia = c1.selectbox("Dia.", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"], index=0)
            d_b = float(bolt_dia.replace("M",""))
            
            thread_cond = st.radio("Threads", ["N (Included)", "X (Excluded)"], horizontal=True)
            hole_type = st.selectbox("Hole Type", ["STD", "OVS", "SSL", "LSL"])

        # --- C. GEOMETRY (PITCH & EDGE) ---
        with st.expander("3️⃣ Connection Geometry", expanded=True):
            st.markdown("**Bolt Spacing:**")
            cg1, cg2 = st.columns(2)
            pitch = cg1.number_input("Pitch (s)", value=int(3*d_b), min_value=int(2.67*d_b))
            lev = cg2.number_input("V-Edge (Lev)", value=int(1.5*d_b), min_value=int(1.25*d_b))
            
            # Row Calculation with Safety Check
            max_rows_physical = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            
            st.markdown(f"**Rows (Max {max_rows_physical}):**")
            
            # Smart Widget Constraints to prevent Crash
            w_min = 2
            w_max = max(2, max_rows_physical)
            w_def = max(2, min(3, max_rows_physical))
            
            n_rows = st.number_input("No. of Rows", min_value=w_min, max_value=w_max, value=w_def)
            
            if max_rows_physical < 2:
                st.warning(f"⚠️ Beam too shallow for 2 rows!")

            st.markdown("---")
            st.markdown("**Horizontal Layout:**")
            setback = st.slider("Setback (c)", 0, 25, 12, help="Gap between beam end and support")
            leh = st.number_input("H-Edge (Leh)", value=40, min_value=int(1.25*d_b), help="Distance from hole to beam end")

        # --- D. PLATE DIMENSIONS & WELD ---
        with st.expander("4️⃣ Plate & Weld Size", expanded=True):
            st.markdown("#### Plate Width Control")
            
            # Calculate Min Width Required
            min_tail_edge = int(1.25 * d_b) # ระยะขอบหลังรูน็อต (ฝั่งเชื่อม)
            min_width_req = setback + leh + min_tail_edge
            
            width_mode = st.radio("Width Mode", ["Auto (Min)", "Manual (Flat Bar)"], horizontal=True)
            
            if width_mode == "Auto (Min)":
                pl_w = min_width_req
                st.info(f"Auto Width = {pl_w} mm (Edge Tail = {min_tail_edge} mm)")
            else:
                # ให้เลือกจากขนาด Standard Flat Bar
                std_widths = [75, 90, 100, 125, 150, 180, 200, 250]
                # หาค่าที่ใกล้เคียงที่สุดที่เป็นไปได้
                rec_idx = 0
                for i, w in enumerate(std_widths):
                    if w >= min_width_req:
                        rec_idx = i
                        break
                
                pl_w = st.selectbox("Select Flat Bar Width (mm)", std_widths, index=rec_idx)
                
                # Check actual tail edge distance
                actual_tail_edge = pl_w - setback - leh
                if actual_tail_edge < d_b:
                    st.error(f"❌ Width {pl_w} mm is too small! Tail edge = {actual_tail_edge} mm")
                else:
                    st.success(f"Tail Edge Distance = {actual_tail_edge} mm")

            st.markdown("---")
            c3, c4 = st.columns(2)
            plate_t = c3.selectbox("Thick (tp)", [6, 9, 10, 12, 16, 19, 25], index=3)
            weld_sz = c4.selectbox("Weld (mm)", [4, 5, 6, 8, 10], index=2)
            
            # Height Calculation
            pl_h = (2 * lev) + ((n_rows - 1) * pitch)
            st.caption(f"Plate Height = {pl_h} mm (Auto derived from Lev & Pitch)")

    # ==========================================
    # 🔵 2. VISUALIZATION
    # ==========================================
    with col_viz:
        
        # --- TAB DISPLAY ---
        tab1, tab2 = st.tabs(["🧊 3D Fabrication Model", "📋 Engineering Summary"])
        
        with tab1:
            # 3D DRAWER
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            
            # [IMPORTANT] Pack weld_sz into plate_dims for drawing
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz}
            
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
            st.plotly_chart(fig, use_container_width=True)
            
            # Geometry Check Banner
            if pl_h > (bm_D - 2*bm_Tf):
                st.error(f"🚨 Plate Height ({pl_h} mm) exceeds Web Depth!")
            else:
                pass # OK

        with tab2:
            st.markdown("#### ⚙️ Fabrication Specification")
            
            # Summary Table
            summ_data = {
                "Item": ["Bolt", "Hole", "Thread", "Plate (WxHxt)", "Weld Size", "Tail Edge Dist."],
                "Spec": [
                    f"{n_rows} - {bolt_dia} {bolt_grade}",
                    hole_type,
                    f"{'Excluded' if 'X' in thread_cond else 'Included'}",
                    f"PL {pl_w} x {pl_h} x {plate_t} mm",
                    f"{weld_sz} mm Fillet (E70XX)",
                    f"{pl_w - setback - leh} mm"
                ]
            }
            st.table(pd.DataFrame(summ_data))
            
            # Material Weight Calculation
            weight_kg = (pl_w/1000) * (pl_h/1000) * (plate_t/1000) * 7850
            st.info(f"💡 **Material Take-off:** 1 Plate ≈ {weight_kg:.2f} kg")
