import streamlit as st

def render_tab1(c, props, method, Fy, section):
    """
    Function to render Tab 1: Detailed Calculation Sheet (English Version)
    With Data Source Tracing
    """
    
    st.markdown(f"### 📄 Engineering Report: {section} ({method})")
    
    # === [NEW] DATA SOURCE TRACING ===
    # แสดงกล่องสรุปว่าค่าไหนมาจากไหน
    with st.expander("ℹ️ Data Sources & Input Parameters (ที่มาของข้อมูล)", expanded=False):
        ds_c1, ds_c2 = st.columns(2)
        with ds_c1:
            st.markdown("**🔵 User Inputs (ค่าที่คุณกำหนด):**")
            st.code(f"Design Method : {method}\n"
                    f"Yield Strength: {Fy} ksc\n"
                    f"Modulus (E)   : {c['E_ksc']/10197.162:.0f} GPa\n"
                    f"Span Length   : {c['L_cm']/100:.2f} m")
        with ds_c2:
            st.markdown("**🗂️ Database Constants (ค่าจากฐานข้อมูล):**")
            st.caption(f"Retrieved from `database.SYS_H_BEAMS` key: `{section}`")
            st.code(f"Depth (D) : {props['D']} mm\n"
                    f"Web (tw)  : {props['tw']} mm\n"
                    f"Weight    : {props['W']} kg/m\n"
                    f"Inertia   : {props['Ix']} cm4")
    
    st.markdown("---")

    # === 1. PROPERTIES ===
    # เพิ่ม Label บอกชัดเจนว่าดึงมาจาก Database
    st.markdown("#### 1. Geometric Properties")
    st.caption(f"📍 Values retrieved from standard section table for **{section}**")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depth (D)", f"{props['D']} mm", delta="Database", delta_color="off")
    c2.metric("Web (tw)", f"{props['tw']} mm", delta="Database", delta_color="off")
    c3.metric("Web Area (Aw)", f"{c['Aw']:.2f} cm²", delta="Calculated", delta_color="off") # Aw คำนวณใน code
    c4.metric("Modulus (Zx)", f"{props['Zx']:,} cm³", delta="Database", delta_color="off")
    
    st.markdown("---")

    # === 2. SHEAR ===
    st.subheader("2. Shear Capacity Control")
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        st.markdown("**Step 2.1: Nominal Shear Strength ($V_n$)**")
        st.latex(r"V_n = 0.60 \times F_y \times A_w")
        st.write(f"- $F_y$ (Input) = {Fy} ksc")
        st.write(f"- $A_w$ (Calc) = {c['Aw']:.2f} cm²")
        st.latex(rf"\therefore V_n = 0.60 \times {Fy} \times {c['Aw']:.2f} = \mathbf{{{c['Vn']:,.0f}}} \text{{ kg}}")
        
    with col_s2:
        st.markdown("**Step 2.2: Design Shear Strength ($V_{design}$)**")
        st.latex(c['txt_v_method'])
        if method == "ASD":
             st.write(f"Using Safety Factor $\Omega_v = {c['omega_v']:.2f}$ (AISC ASD)")
             st.latex(rf"V_{{design}} = \frac{{{c['Vn']:,.0f}}}{{{c['omega_v']:.2f}}}")
        else:
             st.write(f"Using Resistance Factor $\phi_v = {c['phi_v']:.2f}$ (AISC LRFD)")
             st.latex(rf"V_{{design}} = {c['phi_v']:.2f} \times {c['Vn']:,.0f}")
        st.latex(rf"\therefore V_{{design}} = \mathbf{{{c['V_des']:,.0f}}} \text{{ kg}}")
    
    st.markdown("**Step 2.3: Safe Uniform Load ($w_s$)**")
    st.latex(rf"w_s = \frac{{2 \times {c['V_des']:,.0f}}}{{{c['L_cm']:.0f}}} \times 100 = \mathbf{{{c['ws']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 3. MOMENT ===
    st.subheader("3. Moment Capacity Control")
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        st.markdown("**Step 3.1: Nominal Moment Strength ($M_n$)**")
        st.latex(r"M_n = F_y \times Z_x")
        st.write(f"- $F_y$ (Input) = {Fy} ksc")
        st.write(f"- $Z_x$ (Database) = {props['Zx']:,} cm³")
        st.latex(rf"\therefore M_n = {Fy} \times {props['Zx']} = \mathbf{{{c['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col_m2:
        st.markdown("**Step 3.2: Design Moment Strength ($M_{design}$)**")
        st.latex(c['txt_m_method'])
        if method == "ASD":
             st.write(f"Using Safety Factor $\Omega_b = {c['omega_b']:.2f}$ (AISC ASD)")
             st.latex(rf"M_{{design}} = \frac{{{c['Mn']:,.0f}}}{{{c['omega_b']:.2f}}}")
        else:
             st.write(f"Using Resistance Factor $\phi_b = {c['phi_b']:.2f}$ (AISC LRFD)")
             st.latex(rf"M_{{design}} = {c['phi_b']:.2f} \times {c['Mn']:,.0f}")
        st.latex(rf"\therefore M_{{design}} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3.3: Safe Uniform Load ($w_m$)**")
    st.latex(rf"w_m = \frac{{8 \times {c['M_des']:,.0f}}}{{{c['L_cm']:.0f}^2}} \times 100 = \mathbf{{{c['wm']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Control")
    st.write(f"Allowable Deflection Limit ($L/360$):")
    st.latex(rf"\delta_{{allow}} = \frac{{{c['L_cm']:.0f} \text{{ (User Input)}}}}{{360}} = {c['delta']:.2f} \text{{ cm}}")
    
    st.markdown("**Step 4.1: Convert to Safe Uniform Load ($w_d$)**")
    st.write("Using Properties from Database:")
    st.write(f"- $I_x$ (Inertia) = {props['Ix']:,} cm⁴")
    st.write(f"- $E$ (Modulus) = {c['E_ksc']:,.0f} ksc")
    
    st.latex(rf"w_d = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,} \times {c['delta']:.2f}}}{{5 \times {c['L_cm']:.0f}^4}} \times 100")
    st.latex(rf"\therefore w_d = \mathbf{{{c['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # === 5. CONCLUSION ===
    st.subheader("5. Summary & Design Verification")
    
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
        st.success(f"✅ **Safe Net Load Capacity:**")
        st.metric(label="Net Load (Excluding Beam Weight)", value=f"{net_w:,.0f} kg/m")
        st.caption(f"*Beam self-weight ({props['W']} kg/m) from database deducted.")

    st.markdown("---")

    # === 6. TRANSITION DERIVATION ===
    st.subheader("6. Derivation of Critical Lengths")
    st.write("Critical Length ($L$) is the point where the capacity of two failure modes are **exactly equal**.")

    with st.expander("Show Formula Derivation & Calculation"):
        # CASE 1
        st.markdown("#### 6.1 Shear $\leftrightarrow$ Moment Transition ($L_{v-m}$)")
        st.write("Occurs when Shear Capacity ($w_s$) equals Moment Capacity ($w_m$)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**1. Setup Equation:**")
            st.latex(r"\frac{2 V_{design}}{L} = \frac{8 M_{design}}{L^2}")
            st.write("Solve for $L$:")
            st.latex(r"L = \frac{4 M_{design}}{V_{design}}")
        with c2:
            st.markdown("**2. Substitution:**")
            st.latex(rf"L = \frac{{4 \times {c['M_des']:,.0f}}}{{{c['V_des']:,.0f}}} \text{{ (cm)}}")
            st.latex(rf"L = {c['L_vm']*100:,.2f} \text{{ cm}}")
            st.success(f"Convert to meters = {c['L_vm']:.2f} m")

        st.markdown("---")

        # CASE 2
        st.markdown("#### 6.2 Moment $\leftrightarrow$ Deflection Transition ($L_{m-d}$)")
        st.write("Occurs when Moment Capacity ($w_m$) equals Deflection Limit ($w_d$)")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**1. Setup Equation:**")
            st.write("Where $w_d$ is derived from $\delta = L/360$")
            st.latex(r"\frac{8 M_{design}}{L^2} = \frac{384 E I (L/360)}{5 L^4}")
            st.write("Solve for $L$:")
            st.latex(r"L = \frac{384 E I}{14400 M_{design}}")
        with c4:
            st.markdown("**2. Substitution:**")
            st.latex(rf"L = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,}}}{{14400 \times {c['M_des']:,.0f}}}")
            st.latex(rf"L = {c['L_md']*100:,.2f} \text{{ cm}}")
            st.success(f"Convert to meters = {c['L_md']:.2f} m")

    col_sum1, col_sum2 = st.columns(2)
    col_sum1.info(f"**📍 Shear/Moment Transition:**\n\n $L = {c['L_vm']:.2f}$ m")
    col_sum2.info(f"**📍 Moment/Deflection Transition:**\n\n $L = {c['L_md']:.2f}$ m")
