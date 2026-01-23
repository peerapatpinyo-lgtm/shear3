import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🛠️ Design Check & Connection")
    st.caption("ตรวจสอบหน้าตัดและออกแบบจุดต่อ (Bolt & Plate) โดยใช้ Load ที่ 75% Efficiency")

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
        * Max External Capacity: **{w_net_capacity:,.0f}** kg/m
        * **Design Load (75%): {w_75_external:,.0f} kg/m** (ค่าแนะนำ)
        """)

    st.markdown("---")

    # --- 3. Beam Design Check ---
    st.subheader("1. Beam Analysis")
    
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
    
    # Display Beam Status (Simplified)
    beam_pass = ratio_v <= 1.0 and ratio_m <= 1.0
    if beam_pass:
        st.success(f"✅ Beam OK! (Shear: {ratio_v:.2f}, Moment: {ratio_m:.2f})")
    else:
        st.error(f"❌ Beam Fail! (Shear: {ratio_v:.2f}, Moment: {ratio_m:.2f})")

    st.markdown("---")

    # ==============================================================================
    # 🔩 NEW SECTION: CONNECTION DESIGN (BOLT & PLATE)
    # ==============================================================================
    st.subheader("2. 🔩 Connection Design (Shear Plate)")
    st.caption(f"ออกแบบจุดต่อรับแรงเฉือน (Reaction Force: **{V_u:,.0f} kg**) ที่หัวเสา")

    col_conn1, col_conn2 = st.columns([1, 1.5])

    with col_conn1:
        st.markdown("**Bolt Configuration**")
        bolt_grade = st.selectbox("Bolt Grade:", ["A325 (High Strength)", "A307 (Ordinary)", "Grade 8.8"], index=0)
        bolt_size = st.selectbox("Bolt Size:", ["M12", "M16", "M20", "M22", "M24"], index=1)
        bolt_rows = st.number_input("Number of Bolts (Rows):", min_value=1, max_value=10, value=3)
        plate_t = st.selectbox("Plate Thickness (mm):", [6, 9, 12, 16, 20, 25], index=1)

    # --- Connection Calculation ---
    # 1. Bolt Properties
    bolt_dia_map = {"M12": 1.2, "M16": 1.6, "M20": 2.0, "M22": 2.2, "M24": 2.4} # cm
    d_b = bolt_dia_map[bolt_size]
    A_b = (np.pi * d_b**2) / 4 # cm2
    
    # Shear Strength (Fnv) approx
    if bolt_grade == "A307 (Ordinary)":
        Fnv = 1880 # ksc (approx 27 ksi)
    else: # A325 or 8.8
        Fnv = 3720 # ksc (approx 54 ksi)

    # 2. Bolt Shear Capacity (per bolt)
    # Single Shear Plane (สมมติเป็น Single Plate หรือ Shear Tab)
    if method == "ASD":
        omega = 2.0
        phi = 1.0 # not used
        Rn_shear_bolt = (Fnv * A_b) / omega
    else: # LRFD
        phi = 0.75
        Rn_shear_bolt = phi * (Fnv * A_b)

    # 3. Bearing Capacity (At Beam Web & Plate)
    # เราต้องเช็คว่า รูเจาะที่ "เอวคาน (Web)" หรือ "Plate" อะไรบางกว่ากัน
    t_web = props['t1'] / 10 # mm -> cm
    t_plate = plate_t / 10   # mm -> cm
    t_min = min(t_web, t_plate) # ใช้ตัวที่บางที่สุดคำนวณ (Critical)

    # Bearing Formula: Rn = 2.4 * d * t * Fu (Standard AISC)
    # สมมติ Fu เหล็ก = 4000 ksc (SS400/A36)
    Fu_steel = 4000 
    
    if method == "ASD":
        omega_br = 2.0
        Rn_bearing = (2.4 * d_b * t_min * Fu_steel) / omega_br
    else:
        phi_br = 0.75
        Rn_bearing = phi_br * (2.4 * d_b * t_min * Fu_steel)

    # 4. Total Capacity
    capacity_per_bolt = min(Rn_shear_bolt, Rn_bearing)
    total_conn_capacity = capacity_per_bolt * bolt_rows

    ratio_conn = V_u / total_conn_capacity

    # --- Result Display ---
    with col_conn2:
        st.markdown("**📋 Analysis Result**")
        
        # Status Card
        if ratio_conn <= 1.0:
            st.success(f"✅ **PASS** (Ratio: {ratio_conn:.2f})")
        else:
            st.error(f"❌ **FAIL** (Ratio: {ratio_conn:.2f})")
            st.caption("👉 ลองเพิ่มจำนวนน็อต หรือ ขนาดน็อต")

        st.markdown("---")
        st.markdown(f"**Reaction Force ($V_u$):** `{V_u:,.0f} kg`")
        
        col_res_a, col_res_b = st.columns(2)
        with col_res_a:
            st.caption("🔩 Bolt Shear Cap.")
            st.markdown(f"**{Rn_shear_bolt:,.0f}** kg/bolt")
        with col_res_b:
            st.caption(f"🛡️ Bearing Cap. (t={t_min*10:.1f}mm)")
            st.markdown(f"**{Rn_bearing:,.0f}** kg/bolt")
            
        st.markdown(f"**Total Capacity ({bolt_rows} bolts):** `{total_conn_capacity:,.0f} kg`")

    # --- Visual Summary (Timeline Style) ---
    st.markdown("---")
    st.caption("💡 Note: Bearing Capacity คำนวณจากความหนาที่น้อยที่สุดระหว่าง Web คาน กับ Plate")
    
    # Simple Text Visualization
    check_web = "⚠️ Web บางกว่า Plate" if t_web < t_plate else "✅ Web หนาพอ"
    st.info(f"""
    **🔍 Geometry Check:**
    * Beam Web: {t_web*10:.1f} mm ({check_web})
    * Connection Plate: {t_plate*10:.1f} mm
    * Bolt: {bolt_size} (Grade: {bolt_grade.split()[0]}) x {bolt_rows} ตัว
    """)
