import streamlit as st
import pandas as pd
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Engine วาดรูปที่แยกไว้
from drawer_3d import create_connection_figure

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ 3D Shop Drawing (Modular)")
    
    # --- 1. INPUTS ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("Rows", 2, 8, 3)
        with c3:
            d_b_mm = float(bolt_size.replace("M",""))
            setback = st.slider("Setback (Gap)", 0, 25, 12)
            plate_t = st.selectbox("Plate T (mm)", [6, 9, 12, 16, 20], index=2)

    # --- 2. DATA PREPARATION (Prepare Dicts for Drawer) ---
    
    # A. Beam Data (Convert to mm)
    d_factor = 10 if props['D'] < 100 else 1
    beam_dims = {
        'H': props['D'] * d_factor,
        'B': props['B'] * d_factor,
        'Tw': props.get('t1', 6.0),
        'Tf': props.get('t2', 9.0)
    }
    
    # B. Bolt & Layout Data
    pitch = int(3 * d_b_mm)
    lev = int(1.5 * d_b_mm)
    leh_beam = 40 # ระยะจากปลายคานถึงรูน็อต
    
    bolt_dims = {
        'dia': d_b_mm,
        'n_rows': n_rows,
        'pitch': pitch,
        'lev': lev,
        'leh_beam': leh_beam
    }
    
    # C. Plate Data
    pl_h = (2 * lev) + ((n_rows - 1) * pitch)
    # ความกว้างเพลท = ช่องว่าง(Gap) + ระยะรู(Leh) + ระยะเผื่อท้าย(Tail)
    pl_w_total = setback + leh_beam + 40 
    
    plate_dims = {
        't': plate_t,
        'w': pl_w_total,
        'h': pl_h
    }
    
    # D. Config Data
    config = {
        'setback': setback,
        'L_beam_show': 400
    }

    # --- 3. CALL DRAWER ENGINE ---
    
    col_viz, col_data = st.columns([3, 1])
    
    with col_viz:
        # เรียกใช้ฟังก์ชันวาดรูปจากไฟล์แยก
        fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
        st.plotly_chart(fig, use_container_width=True)

    with col_data:
        st.info("📊 **Specs:**")
        st.write(f"**Beam:** {beam_dims['H']:.0f}x{beam_dims['B']:.0f}")
        st.write(f"**Plate:** {plate_t}x{pl_h:.0f} mm")
        st.write(f"**Gap:** {setback} mm")
        st.success(f"**Status:** Ready to Detail")
