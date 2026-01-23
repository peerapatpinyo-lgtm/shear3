import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🛠️ Design Check (Using 75% Load Scenario)")
    st.caption("นำค่าน้ำหนักจาก Tab 5 (ที่ 75% Efficiency) มาตรวจสอบหน้าตัดแบบละเอียด พร้อมดู Ratio การรับแรง")

    # --- 1. Selection Section ---
    col1, col2 = st.columns([1, 2])
    with col1:
        # เลือกหน้าตัด
        section_name = st.selectbox(
            "Select Section Size:",
            options=list(SYS_H_BEAMS.keys()),
            index=0
        )
    
    props = SYS_H_BEAMS[section_name]
    
    # --- 2. Calculate Reference Load (The 75% Logic) ---
    # ใช้ Logic เดียวกับ Tab 5 เพื่อหา w_75 ของหน้าตัดนี้
    c_ref = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
    L_vm = c_ref['L_vm']
    
    if L_vm > 0:
        w_max = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 # kg/m
    else:
        w_max = 0
        
    w_75_ref = 0.75 * w_max # นี่คือค่า Load 75% ที่เราจะเอามาใช้
    
    with col2:
        st.info(f"""
        **Load Scenario Calculation:**
        * Max Load (Shear Limit): **{w_max:,.0f}** kg/m
        * **Design Load (75%): {w_75_ref:,.0f} kg/m** (ค่าที่นำมาออกแบบ)
        """)

    st.markdown("---")

    # --- 3. User Input: Span Length ---
    # ให้ผู้ใช้เลือกระยะ Span ที่ต้องการจะเช็ค (โดยใช้ Load 75% นี้)
    
    # คำนวณ Span ที่ 75% ของ Tab 5 เพื่อมาเป็นค่า Default/Max ของ Slider
    if w_75_ref > 0:
        L_75_limit = np.sqrt((8 * c_ref['M_des']) / (w_75_ref / 100)) / 100
    else:
        L_75_limit = 10.0

    span_input = st.slider(
        "Adjust Span Length (m):",
        min_value=1.0,
        max_value=12.0,
        value=float(L_75_limit), # Default ที่จุด Limit พอดี
        step=0.1,
        help="เลื่อนเพื่อดูว่าถ้าระยะเปลี่ยนไป ผลการออกแบบจะเป็นอย่างไร"
    )

    # --- 4. Perform Detailed Check ---
    # คำนวณ Demand (แรงที่เกิดขึ้นจริง)
    w_use = w_75_ref # kg/m
    L_use = span_input # m
    
    # Analysis (Simple Beam Uniform Load)
    V_u = (w_use * L_use) / 2          # kg (Shear Demand)
    M_u = (w_use * L_use**2) / 8 * 100 # kg-cm (Moment Demand)
    
    # Deflection Calculation (Elastic)
    # 5wL^4 / 384EI
    E_ksc = E_gpa * 10000 # convert GPa -> ksc approx
    I_x = props['Ix']     # cm^4
    delta_u = (5 * (w_use/100) * (L_use*100)**4) / (384 * 2.04e6 * I_x) # ใช้ E=2.04e6 ksc (Steel standard)
    
    # Get Capacities (Strength)
    # เรียก core อีกรอบด้วยความยาวจริง เพื่อเช็คพวก LTB หรือ parameters ที่ขึ้นกับความยาว
    c_check = core_calculation(L_use, Fy, E_gpa, props, method, def_limit)
    
    V_n = c_check['V_des'] # kg
    M_n = c_check['M_des'] # kg-cm
    delta_allow = (L_use * 100) / def_limit # cm

    # --- 5. Display Dashboard ---
    
    # Ratios
    ratio_v = V_u / V_n
    ratio_m = M_u / M_n
    ratio_d = delta_u / delta_allow
    
    # Helper function for status color
    def get_status(ratio):
        if ratio > 1.0: return "red", "❌ FAIL"
        if ratio > 0.9: return "orange", "⚠️ WARNING"
        return "green", "✅ PASS"

    color_v, text_v = get_status(ratio_v)
    color_m, text_m = get_status(ratio_m)
    color_d, text_d = get_status(ratio_d)

    st.markdown("#### 🏁 Analysis Results")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    # Card 1: Shear
    with col_res1:
        st.markdown(f"**Shear Check (V)**")
        st.progress(min(ratio_v, 1.0), text=f"Ratio: {ratio_v:.2f}")
        st.markdown(f":{color_v}[{text_v}]")
        st.caption(f"Demand: {V_u:,.0f} kg")
        st.caption(f"Capacity: {V_n:,.0f} kg")

    # Card 2: Moment
    with col_res2:
        st.markdown(f"**Moment Check (M)**")
        st.progress(min(ratio_m, 1.0), text=f"Ratio: {ratio_m:.2f}")
        st.markdown(f":{color_m}[{text_m}]")
        st.caption(f"Demand: {M_u/100:,.0f} kg-m")
        st.caption(f"Capacity: {M_n/100:,.0f} kg-m")

    # Card 3: Deflection
    with col_res3:
        st.markdown(f"**Deflection Check (Δ)**")
        st.progress(min(ratio_d, 1.0), text=f"Ratio: {ratio_d:.2f}")
        st.markdown(f":{color_d}[{text_d}]")
        st.caption(f"Actual: {delta_u:.2f} cm")
        st.caption(f"Limit (L/{def_limit}): {delta_allow:.2f} cm")

    # --- 6. Interaction Diagram (Visual Check) ---
    st.markdown("---")
    st.markdown("#### 📈 Interaction Visualization")
    
    # สร้างกราฟแสดงตำแหน่งจุดใช้งานเทียบกับ Capacity
    fig = go.Figure()
    
    categories = ['Shear', 'Moment', 'Deflection']
    ratios = [ratio_v, ratio_m, ratio_d]
    
    fig.add_trace(go.Bar(
        x=ratios,
        y=categories,
        orientation='h',
        marker=dict(
            color=[
                '#d9534f' if r > 1 else ('#f0ad4e' if r > 0.9 else '#5cb85c') 
                for r in ratios
            ]
        ),
        text=[f"{r*100:.1f}%" for r in ratios],
        textposition='auto',
    ))
    
    # Add Limit Line at 1.0
    fig.add_shape(
        type="line",
        x0=1, y0=-0.5, x1=1, y1=2.5,
        line=dict(color="Red", width=3, dash="dash"),
    )
    fig.add_annotation(x=1, y=2.5, text="Limit (100%)", showarrow=False, yshift=10)

    fig.update_layout(
        title=f"Unity Check Ratios (Span {L_use} m @ {w_use:,.0f} kg/m)",
        xaxis_title="Utilization Ratio (Demand / Capacity)",
        xaxis=dict(range=[0, max(1.2, max(ratios)*1.1)]),
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 7. Conclusion ---
    final_status = "PASSED" if max(ratios) <= 1.0 else "FAILED"
    final_color = "success" if final_status == "PASSED" else "error"
    
    if final_status == "PASSED":
        st.success(f"✅ หน้าตัด {section_name} สามารถรับน้ำหนัก {w_use:,.0f} kg/m ที่ระยะ {L_use} เมตร ได้อย่างปลอดภัย")
    else:
        st.error(f"❌ หน้าตัด {section_name} **ไม่ผ่าน** การตรวจสอบที่ระยะ {L_use} เมตร (โปรดลดระยะ หรือ เปลี่ยนหน้าตัด)")
