import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure

# ==========================================
# 📐 HELPER
# ==========================================
def get_max_rows(beam_d, beam_tf, k_dist, margin_top, margin_bot, pitch, lev):
    workable_depth = beam_d - (2 * k_dist) 
    available_h = beam_d - (2 * beam_tf) - margin_top - margin_bot
    if available_h <= (2 * lev): return 0
    max_n = int(((available_h - (2 * lev)) / pitch) + 1)
    return max(0, max_n)

# ==========================================
# 🏗️ MAIN UI
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🏗️ Shear Plate Design (Professional)")
    col_input, col_viz = st.columns([1.3, 2.5])

    # --- 1. INPUT ---
    with col_input:
        with st.expander("1️⃣ Host Beam", expanded=True):
            sec_name = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
            beam = SYS_H_BEAMS[sec_name]
            d_factor = 10 if beam['D'] < 100 else 1
            bm_D = beam['D'] * d_factor
            bm_Tw = beam.get('t1', 6.0)
            bm_Tf = beam.get('t2', 9.0)
            k_des = 30 
            st.caption(f"D:{bm_D:.0f} | Tw:{bm_Tw}")
            Vu_load = st.number_input("Factored Load (kg)", value=5000.0, step=500.0)

        with st.expander("2️⃣ Bolt & Geometry", expanded=True):
            c1, c2 = st.columns(2)
            bolt_dia = c1.selectbox("Dia.", ["M16", "M20", "M22", "M24"], index=1)
            d_b = float(bolt_dia.replace("M",""))
            
            # Geometry
            pitch = st.number_input("Pitch (s)", value=int(3*d_b), min_value=int(2.67*d_b))
            lev = st.number_input("V-Edge (Lev)", value=int(1.5*d_b))
            
            # Row Logic
            max_rows = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            n_rows = st.number_input("Rows", min_value=2, max_value=max(2, max_rows), value=max(2, min(3, max_rows)))
            if max_rows < 2: st.warning("⚠️ Beam too small!")
            
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
            plate_t = c3.selectbox("Thick", [6, 9, 10, 12, 16], index=2)
            weld_sz = c4.selectbox("Weld", [4, 6, 8, 10], index=1)
            
            pl_h = (2 * lev) + ((n_rows - 1) * pitch)

    # --- 2. VIZ ---
    with col_viz:
        tab1, tab2 = st.tabs(["🧊 3D Model", "📋 Summary"])
        
        with tab1:
            # Pack Data
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz} # <-- ส่ง weld_sz ไปด้วย
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            # Draw
            try:
                fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Error Plotting: {e}")
                st.info("💡 โปรดตรวจสอบว่าไฟล์ drawer_3d.py ถูกต้องหรือไม่")

        with tab2:
            st.write(f"**Plate:** {pl_w}x{pl_h}x{plate_t} mm")
            st.write(f"**Weld:** {weld_sz} mm Fillet")
            st.write(f"**Weight:** {(pl_w*pl_h*plate_t*7.85e-6):.2f} kg")
