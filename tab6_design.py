import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
# import calculator # (สมมติว่าคุณมีไฟล์คำนวณ)

# Import Engine วาดรูป
from drawer_3d import create_connection_figure

def render_tab6(method, Fy, E_gpa, def_limit):
    # --- HEADER ---
    st.markdown("""
    <h2 style='text-align: center; color: #2c3e50;'>
        🏗️ Shear Tab Connection Design
    </h2>
    <p style='text-align: center; color: #7f8c8d; font-size: 0.9em;'>
        Interactive 3D Modeling & Capacity Check (AISC 360-16)
    </p>
    <hr>
    """, unsafe_allow_html=True)

    # ==========================================
    # 1. SIDEBAR: CONTROLS & INPUTS
    # ==========================================
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # --- A. BEAM SELECTION ---
        with st.expander("🔹 Beam Selection", expanded=True):
            section_name = st.selectbox("Section Size", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
            
            # Unit Handling (Check if DB is cm or mm)
            d_factor = 10 if props['D'] < 100 else 1
            H_real = props['D'] * d_factor
            Tw_real = props.get('t1', 6.0)
            
            st.caption(f"Depth: {H_real:.0f} mm | Web: {Tw_real} mm")

        # --- B. LOAD ---
        with st.expander("🔹 Design Load", expanded=True):
            Vu_input = st.number_input("Shear Load (Vu) [kg]", value=5000, step=500)

        # --- C. CONNECTION DETAILS ---
        with st.expander("🔹 Connection Detail", expanded=True):
            # Bolt
            bolt_size = st.selectbox("Bolt Size", ["M16", "M20", "M22", "M24"], index=1)
            d_b_mm = float(bolt_size.replace("M",""))
            
            c1, c2 = st.columns(2)
            n_rows = c1.number_input("Rows", 2, 8, 3)
            plate_t = c2.selectbox("Plate T", [6, 9, 12, 16, 19, 25], index=2)
            
            st.markdown("---")
            st.caption("Geometry Adjustments")
            setback = st.slider("Setback (Gap)", 0, 25, 12)
            leh_beam = st.slider("Leh (Beam)", 30, 60, 40)

    # ==========================================
    # 2. CALCULATION LOGIC (PREP)
    # ==========================================
    
    # Auto-Calc Geometry
    pitch = int(3 * d_b_mm)
    lev = int(1.5 * d_b_mm)
    
    # Plate Dimensions
    pl_h = (2 * lev) + ((n_rows - 1) * pitch)
    pl_w_total = setback + leh_beam + 40 # 40mm tail
    
    # --- GEOMETRY CHECK (WARNING SYSTEM) ---
    warnings = []
    # 1. Check Plate Height vs Beam Depth (T-distance approximation)
    k_des = 30 # สมมติระยะโค้ง
    T_dist = H_real - (2 * k_des) 
    if pl_h > T_dist:
        warnings.append(f"⚠️ **Plate Height Issue:** Plate height ({pl_h} mm) exceeds workable web depth (~{T_dist} mm). Reduce rows or pitch.")
    
    # 2. Check Plate Thickness vs Bolt
    if plate_t < (d_b_mm / 2) + 1: # Rule of thumb
        warnings.append(f"⚠️ **Thin Plate:** Plate might be too thin for {bolt_size}. Consider T >= {d_b_mm/2:.0f}mm.")

    # ==========================================
    # 3. MAIN DISPLAY AREA
    # ==========================================
    
    # Layout: Top (Status) -> Middle (3D) -> Bottom (Details)
    
    # --- STATUS BAR ---
    c_stat1, c_stat2, c_stat3 = st.columns(3)
    c_stat1.metric("Design Load (Vu)", f"{Vu_input:,.0f} kg")
    
    # Placeholder Logic for Capacity (เชื่อมกับ calculator.py ของคุณตรงนี้)
    # phi_Vn = calculator.get_capacity(...) 
    phi_Vn = 8500 # สมมติค่า
    ratio = Vu_input / phi_Vn
    
    status_color = "normal" if ratio < 1.0 else "inverse"
    c_stat2.metric("Capacity (φVn)", f"{phi_Vn:,.0f} kg", delta=f"Ratio: {ratio:.2f}", delta_color=status_color)
    
    c_stat3.metric("Plate Size", f"{plate_t} x {pl_w_total} x {pl_h} mm")

    # --- ERROR BANNER ---
    if warnings:
        for w in warnings:
            st.error(w)

    # --- TABS ---
    tab_3d, tab_calc = st.tabs(["🧊 3D Model & Shop Drawing", "📝 Calculation Report"])

    with tab_3d:
        # DATA PACKING FOR DRAWER
        beam_dims = {
            'H': H_real,
            'B': props['B'] * d_factor,
            'Tw': Tw_real,
            'Tf': props.get('t2', 9.0)
        }
        bolt_dims = {
            'dia': d_b_mm,
            'n_rows': n_rows,
            'pitch': pitch,
            'lev': lev,
            'leh_beam': leh_beam
        }
        plate_dims = {
            't': plate_t,
            'w': pl_w_total,
            'h': pl_h
        }
        config = {
            'setback': setback,
            'L_beam_show': H_real * 1.5 # Show proportional length
        }
        
        # CALL DRAWER
        fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"**Drawing Note:** Standard Pitch = {pitch}mm, Lev = {lev}mm (Based on 3db/1.5db)")

    with tab_calc:
        st.markdown("### 📊 Detailed Checks (Example)")
        # ตัวอย่างการแสดงผล Check list
        check_data = {
            "Limit State": ["Bolt Shear", "Plate Bearing", "Plate Shear Yield", "Plate Shear Rupture", "Block Shear"],
            "Capacity (kg)": [12000, 9500, 8500, 10500, 11000],
            "Demand (kg)": [Vu_input] * 5,
            "Ratio": [Vu_input/12000, Vu_input/9500, Vu_input/8500, Vu_input/10500, Vu_input/11000]
        }
        df_check = pd.DataFrame(check_data)
        
        # Style formatting
        def highlight_fail(val):
            color = 'red' if val > 1.0 else 'green'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df_check.style.applymap(highlight_fail, subset=['Ratio'])
            .format({"Capacity (kg)": "{:,.0f}", "Demand (kg)": "{:,.0f}", "Ratio": "{:.2f}"}),
            use_container_width=True
        )
