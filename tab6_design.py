import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🛠️ Design Check & Connection (Professional)")
    st.caption(f"Standard: **AISC 360-16 ({method})** | Design Checks: Shear, Moment, Deflection, and Bolt Connection")

    # --- 1. Selection Section ---
    col1, col2 = st.columns([1, 2])
    with col1:
        section_name = st.selectbox(
            "Select Section Size:",
            options=list(SYS_H_BEAMS.keys()),
            index=0
        )
    
    props = SYS_H_BEAMS[section_name]
    w_sw = props['W']  # Self-Weight

    # --- 2. Calculate Net Capacity ---
    c_ref = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
    L_vm = c_ref['L_vm']
    
    if L_vm > 0:
        w_gross_capacity = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 
    else:
        w_gross_capacity = 0
        
    w_net_capacity = max(0, w_gross_capacity - w_sw)
    w_75_external = 0.75 * w_net_capacity
    
    with col2:
        st.info(f"""
        **Load Scenario:**
        * Gross Capacity: {w_gross_capacity:,.0f} kg/m
        * Net External Capacity: **{w_net_capacity:,.0f}** kg/m (Less SW)
        * **Target Design Load (75%): {w_75_external:,.0f} kg/m**
        """)

    st.markdown("---")

    # --- 3. Beam Design Check ---
    st.subheader("1. 🏗️ Beam Analysis")
    
    # Slider Setup
    default_val = 6.0
    if w_75_external > 0:
        try:
            w_total_sim = w_75_external + w_sw
            val_limit = np.sqrt((8 * c_ref['M_des']) / (w_total_sim / 100)) / 100
            default_val = min(max(float(val_limit), 1.0), 15.0)
        except: pass

    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        span_input = st.slider("Span Length (m):", 1.0, 15.0, default_val, 0.1)
    with col_inp2:
        load_input = st.number_input("External Load (kg/m):", value=float(int(w_75_external)), step=100.0)

    # --- Calculation Logic ---
    w_total_check = load_input + w_sw 
    L_use = span_input
    
    # Demand
    V_u = (w_total_check * L_use) / 2          # kg (Shear at Support)
    M_u = (w_total_check * L_use**2) / 8 * 100 # kg-cm
    
    # Capacity
    c_check = core_calculation(L_use, Fy, E_gpa, props, method, def_limit)
    V_n_beam = c_check['V_des']
    M_n_beam = c_check['M_des']
    
    # Ratios
    ratio_v = V_u / V_n_beam
    ratio_m = M_u / M_n_beam
    
    beam_pass = ratio_v <= 1.0 and ratio_m <= 1.0
    
    col_b1, col_b2, col_b3 = st.columns(3)
    col_b1.metric("Shear Ratio", f"{ratio_v:.2f}", delta="PASS" if ratio_v <=1 else "FAIL", delta_color="inverse")
    col_b2.metric("Moment Ratio", f"{ratio_m:.2f}", delta="PASS" if ratio_m <=1 else "FAIL", delta_color="inverse")
    col_b3.metric("Reaction (Vu)", f"{V_u:,.0f} kg")

    st.markdown("---")

    # ==============================================================================
    # 🔩 SECTION 2: CONNECTION DESIGN (PROFESSIONAL GRADE)
    # ==============================================================================
    st.subheader("2. 🔩 Connection Design (Bolt & Plate)")
    st.caption("Reference: **AISC 360-16 Chapter J3** | Simple Shear Connection (Shear Tab)")

    # --- INPUTS ---
    col_conn1, col_conn2 = st.columns([1, 1.5])
    with col_conn1:
        st.markdown("**Configuration**")
        bolt_grade = st.selectbox("Bolt Grade:", ["A325 (High Strength)", "A307 (Ordinary)"], index=0)
        bolt_size = st.selectbox("Bolt Size:", ["M12", "M16", "M20", "M22", "M24"], index=1)
        bolt_rows = st.number_input("Number of Bolts:", min_value=1, max_value=10, value=3)
        plate_t_mm = st.selectbox("Plate Thickness (mm):", [6, 9, 12, 16, 20, 25], index=1)
        
        # Determine Ultimate Strength (Fu) based on input Fy
        # NOTE: Standard Structural Steel approx:
        # SS400 (Fy=2400) -> Fu=4000
        # SM520 (Fy=3500) -> Fu=5200
        Fu_beam = 4000 if Fy < 3000 else 5200 
        Fu_plate = 4000 # Conservative assumption for Plate (SS400)

    # --- ENGINEERING CALCULATIONS ---
    
    # 1. Properties
    bolt_dia_map = {"M12": 1.2, "M16": 1.6, "M20": 2.0, "M22": 2.2, "M24": 2.4} # cm
    d_b = bolt_dia_map[bolt_size]
    A_b = (np.pi * d_b**2) / 4 # cm2
    
    # Nominal Shear Stress (Fnv) [AISC Table J3.2]
    # Unit: ksc (kg/cm2)
    if "A325" in bolt_grade:
        Fnv = 3720 # ~54 ksi
        bolt_type_str = "A325 (Group A)"
    else:
        Fnv = 1880 # ~27 ksi
        bolt_type_str = "A307"

    # 2. Safety Factors
    if method == "ASD":
        omega = 2.00
        phi = 1.00 # Not used
        SF_text = r"\Omega = 2.00"
        def get_cap(Rn): return Rn / omega
    else: # LRFD
        phi = 0.75
        omega = 1.00 # Not used
        SF_text = r"\phi = 0.75"
        def get_cap(Rn): return phi * Rn

    # 3. Check Bolt Shear (AISC J3.6)
    Rn_shear_bolt = Fnv * A_b  # Nominal Strength
    Rc_shear_bolt = get_cap(Rn_shear_bolt) # Design/Allowable Strength

    # 4. Check Bearing (AISC J3.10)
    # Requires checking BOTH Beam Web and Plate
    
    # 4.1 Beam Web Bearing
    raw_tw = props.get('tw', props.get('t1', 6.0))
    t_web = raw_tw / 10 # cm
    # AISC Eq J3-6a: Rn = 2.4 * d * t * Fu (Limit by deformation)
    Rn_bear_web = 2.4 * d_b * t_web * Fu_beam
    Rc_bear_web = get_cap(Rn_bear_web)

    # 4.2 Plate Bearing
    t_plate = plate_t_mm / 10 # cm
    Rn_bear_plate = 2.4 * d_b * t_plate * Fu_plate
    Rc_bear_plate = get_cap(Rn_bear_plate)

    # 5. Determine Controlling Limit Per Bolt
    Rc_min_per_bolt = min(Rc_shear_bolt, Rc_bear_web, Rc_bear_plate)
    
    # Identify Mode
    fail_mode = ""
    if Rc_min_per_bolt == Rc_shear_bolt: fail_mode = "Bolt Shear (น็อตขาด)"
    elif Rc_min_per_bolt == Rc_bear_web: fail_mode = "Web Bearing (เอวคานฉีก)"
    else: fail_mode = "Plate Bearing (เพลทรูเจาะฉีก)"

    # 6. Total Capacity & Ratio
    total_capacity = Rc_min_per_bolt * bolt_rows
    conn_ratio = V_u / total_capacity
    
    # --- OUTPUT DISPLAY ---
    with col_conn2:
        st.markdown("### 📊 Analysis Results")
        
        status_color = "green" if conn_ratio <= 1.0 else "red"
        status_text = "PASS" if conn_ratio <= 1.0 else "FAIL"
        
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; border: 2px solid {status_color}; background-color: rgba(0,0,0,0.05);">
            <h3 style="color:{status_color}; margin:0;">{status_text} (Ratio: {conn_ratio:.2f})</h3>
            <p style="margin:5px 0;"><b>Demand (Vu):</b> {V_u:,.0f} kg</p>
            <p style="margin:5px 0;"><b>Capacity (Rn/{'Ω' if method=='ASD' else 'φ'}):</b> {total_capacity:,.0f} kg</p>
            <p style="font-size:0.9em; color:gray;">Controlled by: <b>{fail_mode}</b></p>
        </div>
        """, unsafe_allow_html=True)

    # --- DETAILED CALCULATION SHEET (Expanded) ---
    with st.expander("📘 View Detailed Calculation Sheet (รายการคำนวณละเอียด)"):
        st.markdown(f"### Connection Design Calculation ({method})")
        st.markdown(f"**Design Force ($V_u$):** {V_u:,.0f} kg")
        st.markdown("---")
        
        # 1. Bolt Shear
        st.markdown("**1. Bolt Shear Strength (AISC J3.6)**")
        st.latex(r"R_n = F_{nv} A_b")
        st.markdown(f"""
        * Bolt: {bolt_size} ({bolt_type_str})
        * Area ($A_b$): {A_b:.2f} cm²
        * Shear Stress ($F_{{nv}}$): {Fnv} ksc
        * $R_n = {Fnv} \\times {A_b:.2f} = {Rn_shear_bolt:,.0f}$ kg/bolt
        * **Capacity:** {Rc_shear_bolt:,.0f} kg/bolt (Safety Factor applied)
        """)

        # 2. Bearing Web
        st.markdown("**2. Bearing Strength at Beam Web (AISC J3.10)**")
        st.latex(r"R_n = 2.4 d t_{web} F_{u,beam}")
        st.markdown(f"""
        * Web Thickness ($t_w$): {t_web*10:.1f} mm
        * Beam Ultimate Strength ($F_u$): {Fu_beam} ksc
        * $R_n = 2.4 \\times {d_b} \\times {t_web:.2f} \\times {Fu_beam} = {Rn_bear_web:,.0f}$ kg/bolt
        * **Capacity:** {Rc_bear_web:,.0f} kg/bolt
        """)

        # 3. Bearing Plate
        st.markdown("**3. Bearing Strength at Connection Plate**")
        st.latex(r"R_n = 2.4 d t_{plate} F_{u,plate}")
        st.markdown(f"""
        * Plate Thickness ($t_p$): {t_plate*10:.1f} mm
        * Plate Ultimate Strength ($F_u$): {Fu_plate} ksc
        * $R_n = 2.4 \\times {d_b} \\times {t_plate:.2f} \\times {Fu_plate} = {Rn_bear_plate:,.0f}$ kg/bolt
        * **Capacity:** {Rc_bear_plate:,.0f} kg/bolt
        """)

        # 4. Summary
        st.markdown("---")
        st.markdown("**4. Summary**")
        st.latex(r"R_{total} = \min(R_{shear}, R_{bear,web}, R_{bear,plate}) \times N_{bolts}")
        st.markdown(f"""
        * Min Capacity per bolt: **{Rc_min_per_bolt:,.0f} kg** (Mode: {fail_mode})
        * Number of Bolts: {bolt_rows}
        * **Total Capacity:** {Rc_min_per_bolt:,.0f} $\\times$ {bolt_rows} = **{total_capacity:,.0f} kg**
        """)
        
        if conn_ratio > 1.0:
            st.warning("⚠️ **Correction Required:** The connection capacity is insufficient. Try increasing bolt diameter, bolt count, or plate thickness.")
