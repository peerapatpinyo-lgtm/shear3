import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🛠️ Design Check (Using 75% Load Scenario)")
    st.caption("ตรวจสอบหน้าตัดโดยใช้น้ำหนักบรรทุกจากจุดที่มีประสิทธิภาพสูงสุด (75% Efficiency)")

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
    
    # --- 2. Calculate Reference Load (Based on Tab 5 Logic) ---
    # เราหา Load ที่จุด Shear Limit (จุดที่แข็งแรงที่สุดทางทฤษฎี)
    c_ref = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
    L_vm = c_ref['L_vm']
    
    if L_vm > 0:
        w_max_cap = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 # kg/m
    else:
        w_max_cap = 0
        
    w_75_target = 0.75 * w_max_cap # Load ที่เราต้องการ Test (External Load)
    
    with col2:
        st.info(f"""
        **Load Scenario (External Load):**
        * Max Capacity Point: **{w_max_cap:,.0f}** kg/m (ที่ระยะ {L_vm:.2f} ม.)
        * **Design Load (75%): {w_75_target:,.0f} kg/m** (ค่าที่จะนำมาตรวจสอบ)
        """)

    st.markdown("---")

    # --- 3. User Input: Span Length ---
    # คำนวณ Default Slider ให้พอดีกับ Limit
    if w_75_target > 0:
        # ประมาณระยะที่รับได้รับไหว (โดยไม่รวม SW คร่าวๆ) เพื่อตั้งค่า Slider
        try:
            val_limit = np.sqrt((8 * c_ref['M_des']) / (w_75_target / 100)) / 100
        except:
            val_limit = 6.0
    else:
        val_limit = 6.0

    # ป้องกัน Slider Error กรณีค่าเกินขอบเขต
    default_val = float(val_limit)
    if default_val > 12.0: default_val = 12.0
    if default_val < 1.0: default_val = 1.0

    span_input = st.slider(
        "Adjust Span Length (m):",
        min_value=1.0,
        max_value=15.0,
        value=default_val,
        step=0.1,
        help="ปรับระยะพาดเพื่อดูผลลัพธ์ (ค่าน้ำหนักบรรทุกคงที่)"
    )

    # --- 4. Perform Detailed Check (Rigorous Math) ---
    
    # [FIX 1] Total Load = External Load + Self Weight
    w_sw = props['W']          # kg/m (Self Weight)
    w_total = w_75_target + w_sw # kg/m (Total Load for Physics)
    L_use = span_input
    
    # [FIX 2] Demand Calculation (With Total Load)
    # Shear (V_u) - kg
    V_u = (w_total * L_use) / 2          
    
    # Moment (M_u) - kg-cm
    # w(kg/m) * L^2(m^2) / 8 = kg-m -> *100 -> kg-cm
    M_u = (w_total * L_use**2) / 8 * 100 
    
    # Deflection (Delta_u) - cm
    # 5wL^4 / 384EI
    # w ต้องเป็น kg/cm -> w_total / 100
    # L ต้องเป็น cm    -> L_use * 100
    # E ต้องเป็น ksc
    E_ksc = c_ref['E_ksc'] # [FIX 3] Use calculated E (not hardcoded)
    I_x = props['Ix']      # cm^4
    
    if I_x > 0:
        delta_u = (5 * (w_total/100) * (L_use*100)**4) / (384 * E_ksc * I_x)
    else:
        delta_u = 999.9

    # [FIX 4] Get Capacities (At exact span L_use)
    # เรียก core calculation ใหม่ด้วยระยะ span จริง เพื่อเช็ค LTB (Lateral Torsional Buckling)
    c_check = core_calculation(L_use, Fy, E_gpa, props, method, def_limit)
    
    V_n = c_check['V_des'] # kg
    M_n = c_check['M_des'] # kg-cm
    delta_allow = (L_use * 100) / def_limit # cm

    # --- 5. Ratios & Display ---
    ratio_v = V_u / V_n if V_n > 0 else 999
    ratio_m = M_u / M_n if M_n > 0 else 999
    ratio_d = delta_u / delta_allow if delta_allow > 0 else 999
    
    def get_status(ratio):
        if ratio > 1.0: return "red", "❌ FAIL"
        if ratio > 0.9: return "orange", "⚠️ WARNING"
        return "green", "✅ PASS"

    color_v, text_v = get_status(ratio_v)
    color_m, text_m = get_status(ratio_m)
    color_d, text_d = get_status(ratio_d)

    st.markdown("#### 🏁 Analysis Results (Includes Self-Weight)")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.markdown(f"**Shear Check (V)**")
        st.progress(min(ratio_v, 1.0))
        st.markdown(f"Status: :{color_v}[{text_v}]")
        st.caption(f"Demand ($V_u$): {V_u:,.0f} kg")
        st.caption(f"Capacity ($V_n$): {V_n:,.0f} kg")
        st.caption(f"Ratio: **{ratio_v:.2f}**")

    with col_res2:
        st.markdown(f"**Moment Check (M)**")
        st.progress(min(ratio_m, 1.0))
        st.markdown(f"Status: :{color_m}[{text_m}]")
        st.caption(f"Demand ($M_u$): {M_u/100:,.0f} kg-m")
        st.caption(f"Capacity ($M_n$): {M_n/100:,.0f} kg-m")
        st.caption(f"Ratio: **{ratio_m:.2f}**")

    with col_res3:
        st.markdown(f"**Deflection Check (Δ)**")
        st.progress(min(ratio_d, 1.0))
        st.markdown(f"Status: :{color_d}[{text_d}]")
        st.caption(f"Actual: {delta_u:.2f} cm")
        st.caption(f"Limit (L/{def_limit}): {delta_allow:.2f} cm")
        st.caption(f"Ratio: **{ratio_d:.2f}**")

    # --- 6. Interaction Visualization ---
    st.markdown("---")
    
    # Bar Chart for Ratios
    fig = go.Figure()
    categories = ['Shear', 'Moment', 'Deflection']
    ratios = [ratio_v, ratio_m, ratio_d]
    colors = ['#d9534f' if r > 1 else ('#f0ad4e' if r > 0.9 else '#5cb85c') for r in ratios]
    
    fig.add_trace(go.Bar(
        y=categories,
        x=ratios,
        orientation='h',
        marker_color=colors,
        text=[f"{r*100:.1f}%" for r in ratios],
        textposition='auto',
    ))
    
    # Add Limit Line
    fig.add_shape(type="line", x0=1, y0=-0.5, x1=1, y1=2.5,
                  line=dict(color="Red", width=3, dash="dash"))
    fig.add_annotation(x=1, y=2.8, text="LIMIT (1.0)", showarrow=False, font=dict(color="red"))

    fig.update_layout(
        title=f"Unity Check Ratios @ Span {L_use} m",
        xaxis_title="Utilization Ratio (Demand / Capacity)",
        yaxis_title="Criteria",
        xaxis=dict(range=[0, max(1.2, max(ratios)*1.1)]),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary Box
    final_pass = max(ratios) <= 1.0
    
    if final_pass:
        st.success(f"✅ **PASSED**: หน้าตัด {section_name} สามารถรับน้ำหนัก {w_75_target:,.0f} kg/m (+Self Weight) ที่ระยะ {L_use} เมตร ได้อย่างปลอดภัย")
    else:
        fail_causes = []
        if ratio_v > 1: fail_causes.append("Shear")
        if ratio_m > 1: fail_causes.append("Moment")
        if ratio_d > 1: fail_causes.append("Deflection")
        st.error(f"❌ **FAILED**: หน้าตัด {section_name} ไม่ผ่านการตรวจสอบที่ระยะ {L_use} เมตร (สาเหตุ: {', '.join(fail_causes)})")
        
        # Recommendation Logic
        if "Deflection" in fail_causes and len(fail_causes) == 1:
             st.warning("💡 **คำแนะนำ:** ปัญหาเกิดจากการแอ่นตัวเพียงอย่างเดียว ลองพิจารณาลดระยะ Span เล็กน้อย หรือเปลี่ยนเกณฑ์ Deflection Limit")
        elif "Moment" in fail_causes:
             st.warning("💡 **คำแนะนำ:** รับโมเมนต์ดัดไม่ไหว จำเป็นต้องเพิ่มขนาดหน้าตัด หรือลดระยะ Span ลง")
