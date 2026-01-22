import streamlit as st

def render_tab1(c, props, method, Fy, section):
    """
    ฟังก์ชันสำหรับแสดงผล Tab 1: รายการคำนวณละเอียด
    รับค่า:
    - c: ผลลัพธ์การคำนวณ (Dictionary)
    - props: คุณสมบัติหน้าตัด (Dictionary)
    - method: วิธีการออกแบบ (ASD/LRFD)
    - Fy: กำลังจุดคราก
    - section: ชื่อหน้าตัด (String)
    """
    
    st.markdown(f"### 📄 Engineering Report: {section} ({method})")
    st.markdown("---")

    # === 1. PROPERTIES ===
    st.markdown("#### 1. Geometric Properties (คุณสมบัติหน้าตัด)")
    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Depth (D):** {props['D']} mm")
    c2.write(f"**Web (tw):** {props['tw']} mm")
    c3.write(f"**Area Web ($A_w$):** {c['Aw']:.2f} cm²")
    c4.write(f"**Plastic Modulus ($Z_x$):** {props['Zx']:,} cm³")
    st.markdown("---")

    # === 2. SHEAR ===
    st.subheader("2. Shear Capacity (กำลังรับแรงเฉือน)")
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        st.markdown("**Step 2.1: Nominal Shear Strength ($V_n$)**")
        st.latex(r"V_n = 0.60 \times F_y \times A_w")
        st.latex(rf"V_n = 0.60 \times {Fy} \times {c['Aw']:.2f}")
        st.latex(rf"\therefore V_n = \mathbf{{{c['Vn']:,.0f}}} \text{{ kg}}")
        
    with col_s2:
        st.markdown("**Step 2.2: Design Shear Strength ($V_{design}$)**")
        st.latex(c['txt_v_method'])
        if method == "ASD":
             st.latex(rf"V_{{design}} = \frac{{{c['Vn']:,.0f}}}{{{c['omega_v']:.2f}}}")
        else:
             st.latex(rf"V_{{design}} = {c['phi_v']:.2f} \times {c['Vn']:,.0f}")
        st.latex(rf"\therefore V_{{design}} = \mathbf{{{c['V_des']:,.0f}}} \text{{ kg}}")
    
    st.markdown("**Step 2.3: Equivalent Uniform Load ($w_s$)**")
    st.write("แปลงเป็นน้ำหนักแผ่ปลอดภัย (Uniform Load) จากสูตร $V = wL/2$")
    st.latex(rf"w_s = \frac{{2 V_{{design}}}}{{L}} \times 100 (\text{{unit conv.}})")
    st.latex(rf"w_s = \frac{{2 \times {c['V_des']:,.0f}}}{{{c['L_cm']:.0f}}} \times 100 = \mathbf{{{c['ws']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 3. MOMENT ===
    st.subheader("3. Moment Capacity (กำลังรับโมเมนต์ดัด)")
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        st.markdown("**Step 3.1: Nominal Moment Strength ($M_n$)**")
        st.latex(r"M_n = F_y \times Z_x")
        st.latex(rf"M_n = {Fy} \times {props['Zx']}")
        st.latex(rf"\therefore M_n = \mathbf{{{c['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col_m2:
        st.markdown("**Step 3.2: Design Moment Strength ($M_{design}$)**")
        st.latex(c['txt_m_method'])
        if method == "ASD":
             st.latex(rf"M_{{design}} = \frac{{{c['Mn']:,.0f}}}{{{c['omega_b']:.2f}}}")
        else:
             st.latex(rf"M_{{design}} = {c['phi_b']:.2f} \times {c['Mn']:,.0f}")
        st.latex(rf"\therefore M_{{design}} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3.3: Equivalent Uniform Load ($w_m$)**")
    st.write("แปลงเป็นน้ำหนักแผ่ปลอดภัย จากสูตร $M = wL^2/8$")
    st.latex(rf"w_m = \frac{{8 M_{{design}}}}{{L^2}} \times 100")
    st.latex(rf"w_m = \frac{{8 \times {c['M_des']:,.0f}}}{{{c['L_cm']:.0f}^2}} \times 100 = \mathbf{{{c['wm']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Limit (ระยะแอ่นตัว)")
    st.write(f"ระยะแอ่นตัวที่ยอมให้ ($L/360$):")
    st.latex(rf"\delta_{{allow}} = \frac{{{c['L_cm']:.0f}}}{{360}} = {c['delta']:.2f} \text{{ cm}}")
    
    st.markdown("**Step 4.1: Convert to Uniform Load ($w_d$)**")
    st.write("คำนวณน้ำหนักแผ่ที่ทำให้เกิดระยะแอ่นเท่ากับค่าที่ยอมให้ จากสูตร $\delta = \\frac{5wL^4}{384EI}$")
    st.latex(r"w_d = \frac{384 E I \delta_{allow}}{5 L^4} \times 100")
    st.latex(rf"w_d = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,} \times {c['delta']:.2f}}}{{5 \times {c['L_cm']:.0f}^4}} \times 100")
    st.latex(rf"\therefore w_d = \mathbf{{{c['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # === 5. CONCLUSION ===
    st.subheader("5. Summary (สรุปผลการคำนวณ)")
    
    final_w = min(c['ws'], c['wm'], c['wd'])
    net_w = max(0, final_w - props['W'])
    
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        if c['ws'] == final_w: ctrl = "Shear Control"
        elif c['wm'] == final_w: ctrl = "Moment Control"
        else: ctrl = "Deflection Control"
        
        st.info(f"**Governing Case:** {ctrl}")
        st.write(f"- Shear Capacity: {c['ws']:,.0f} kg/m")
        st.write(f"- Moment Capacity: {c['wm']:,.0f} kg/m")
        st.write(f"- Deflection Limit: {c['wd']:,.0f} kg/m")
    
    with res_col2:
        st.success(f"✅ **Safe Net Load (รับน้ำหนักปลอดภัยสุทธิ):**")
        st.metric(label="Net Load (Exclude beam weight)", value=f"{net_w:,.0f} kg/m")
        st.caption(f"*หักน้ำหนักคาน {props['W']} kg/m ออกแล้ว")

    st.markdown("---")

    # === 6. TRANSITION DERIVATION ===
    st.subheader("6. Derivation of Critical Lengths (ที่มาของระยะจุดเปลี่ยน)")
    st.write("ระยะจุดเปลี่ยนคือระยะ $L$ ที่ความสามารถในการรับน้ำหนักของ 2 กรณีมีค่า **เท่ากันพอดี**")

    with st.expander("ดูวิธีพิสูจน์สูตรและการคำนวณ (Click to Show Derivation)"):
        # CASE 1
        st.markdown("#### 6.1 จุดเปลี่ยน Shear $\leftrightarrow$ Moment ($L_{v-m}$)")
        st.write("เกิดเมื่อน้ำหนักบรรทุกปลอดภัยจากแรงเฉือน ($w_s$) เท่ากับ โมเมนต์ ($w_m$)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**1. ตั้งสมการ:**")
            st.latex(r"\frac{2 V_{design}}{L} = \frac{8 M_{design}}{L^2}")
            st.write("ย้ายข้างหาค่า $L$:")
            st.latex(r"L = \frac{4 M_{design}}{V_{design}}")
        with c2:
            st.markdown("**2. แทนค่าจริง:**")
            st.latex(rf"L = \frac{{4 \times {c['M_des']:,.0f}}}{{{c['V_des']:,.0f}}} \text{{ (cm)}}")
            st.latex(rf"L = {c['L_vm']*100:,.2f} \text{{ cm}}")
            st.success(f"แปลงเป็นเมตร = {c['L_vm']:.2f} m")

        st.markdown("---")

        # CASE 2
        st.markdown("#### 6.2 จุดเปลี่ยน Moment $\leftrightarrow$ Deflection ($L_{m-d}$)")
        st.write("เกิดเมื่อน้ำหนักบรรทุกปลอดภัยจากโมเมนต์ ($w_m$) เท่ากับ ระยะแอ่น ($w_d$)")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**1. ตั้งสมการ:**")
            st.write("โดยที่ $w_d$ มาจาก $\delta = L/360$")
            st.latex(r"\frac{8 M_{design}}{L^2} = \frac{384 E I (L/360)}{5 L^4}")
            st.write("จัดรูปสมการหาค่า $L$:")
            st.latex(r"L = \frac{384 E I}{14400 M_{design}}")
        with c4:
            st.markdown("**2. แทนค่าจริง:**")
            st.latex(rf"L = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,}}}{{14400 \times {c['M_des']:,.0f}}}")
            st.latex(rf"L = {c['L_md']*100:,.2f} \text{{ cm}}")
            st.success(f"แปลงเป็นเมตร = {c['L_md']:.2f} m")

    col_sum1, col_sum2 = st.columns(2)
    col_sum1.info(f"**📍 จุดตัด Shear/Moment:**\n\n $L = {c['L_vm']:.2f}$ m")
    col_sum2.info(f"**📍 จุดตัด Moment/Deflection:**\n\n $L = {c['L_md']:.2f}$ m")
