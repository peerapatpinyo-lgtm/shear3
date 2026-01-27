#tab1_details.py
import streamlit as st

def render_tab1(c, props, method, Fy, section):
    """
    Function to render Tab 1: Detailed Calculation Sheet
    Updated to support dynamic Deflection Limit (L/180, L/240, L/360)
    """
    
    st.markdown(f"### 📄 Engineering Report: {section} ({method})")
    
    # === [NEW] DATA SOURCE TRACING ===
    with st.expander("ℹ️ Data Sources & Input Parameters", expanded=False):
        ds_c1, ds_c2 = st.columns(2)
        with ds_c1:
            st.markdown("**🔵 User Inputs:**")
            st.code(f"Design Method : {method}\n"
                    f"Yield Strength: {Fy} ksc\n"
                    f"Modulus (E)   : {c['E_ksc']/10197.162:.0f} GPa\n"
                    f"Span Length   : {c['L_cm']/100:.2f} m\n"
                    f"Deflect Limit : L/{c.get('def_limit', 360)}")
        with ds_c2:
            st.markdown("**🗂️ Database Constants:**")
            st.caption(f"Retrieved from `database.SYS_H_BEAMS` key: `{section}`")
            st.code(f"Depth (D) : {props['D']} mm\n"
                    f"Web (tw)  : {props['tw']} mm\n"
                    f"Weight    : {props['W']} kg/m\n"
                    f"Inertia   : {props['Ix']} cm4")
    
    st.markdown("---")

    # === 1. PROPERTIES ===
    st.markdown("#### 1. Geometric Properties")
    st.caption(f"📍 Values retrieved from standard section table for **{section}**")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depth (D)", f"{props['D']} mm", delta="Database", delta_color="off")
    c2.metric("Width (B)", f"{props.get('B', 100)} mm", delta="Database", delta_color="off")
    c3.metric("Flange (tf)", f"{props.get('tf', 10)} mm", delta="Database", delta_color="off")
    c4.metric("Web (tw)", f"{props['tw']} mm", delta="Database", delta_color="off")
    
    c1b, c2b, c3b, c4b = st.columns(4)
    c1b.metric("Inertia (Ix)", f"{props['Ix']:,} cm4")
    c2b.metric("Plastic Mod (Zx)", f"{props['Zx']:,} cm3")
    c3b.metric("Elastic Mod (Sx)", f"{c['Sx']:.1f} cm3", delta="Calculated", delta_color="off")
    c4b.metric("Unbraced Length", f"{c['Lb']:.2f} m", help="Assumed equal to Span Length")
    
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

    # === 3. MOMENT (WITH LTB) ===
    st.subheader("3. Moment Capacity Control (Include LTB)")
    
    # 3.1 Check LTB Zone
    st.markdown("**Step 3.1: Check Lateral-Torsional Buckling (LTB) Zone**")
    st.write("Determine the unbraced length ($L_b$) zone:")
    
    lz1, lz2, lz3 = st.columns(3)
    lz1.metric("Limit Lp (Yield)", f"{c['Lp']:.2f} m", help="Zone 1 Limit")
    lz2.metric("Limit Lr (Elastic)", f"{c['Lr']:.2f} m", help="Zone 2 Limit")
    
    # Color condition for Zone
    if "Zone 1" in c['Zone']: z_color = "green"
    elif "Zone 2" in c['Zone']: z_color = "orange"
    else: z_color = "red"
    
    lz3.markdown(f"Current State:\n\n:{z_color}[**{c['Zone']}**]")
    
    if c['Lb'] <= c['Lp']:
        st.success(f"✅ Full Plastic Moment Capacity ($L_b \le L_p$)")
    elif c['Lb'] <= c['Lr']:
        st.warning(f"⚠️ Inelastic Buckling Zone ($L_p < L_b \le L_r$). Capacity Reduced.")
    else:
        st.error(f"🛑 Elastic Buckling Zone ($L_b > L_r$). Capacity Significantly Reduced.")
    
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        st.markdown("**Step 3.2: Nominal Moment Strength ($M_n$)**")
        st.write(f"- $M_p$ (Plastic Limit) = {c['Mp']:,.0f} kg-cm")
        st.write(f"- $M_n$ (Calculated with LTB) = {c['Mn']:,.0f} kg-cm")
        st.latex(rf"\therefore M_n = \mathbf{{{c['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col_m2:
        st.markdown("**Step 3.3: Design Moment Strength ($M_{design}$)**")
        st.latex(c['txt_m_method'])
        if method == "ASD":
             st.write(f"Using Safety Factor $\Omega_b = {c['omega_b']:.2f}$ (AISC ASD)")
             st.latex(rf"M_{{design}} = \frac{{{c['Mn']:,.0f}}}{{{c['omega_b']:.2f}}}")
        else:
             st.write(f"Using Resistance Factor $\phi_b = {c['phi_b']:.2f}$ (AISC LRFD)")
             st.latex(rf"M_{{design}} = {c['phi_b']:.2f} \times {c['Mn']:,.0f}")
        st.latex(rf"\therefore M_{{design}} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3.4: Safe Uniform Load ($w_m$)**")
    st.latex(rf"w_m = \frac{{8 \times {c['M_des']:,.0f}}}{{{c['L_cm']:.0f}^2}} \times 100 = \mathbf{{{c['wm']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Control")
    
    # [UPDATED Logic] Fetch selected Limit
    limit_val = c.get('def_limit', 360) 
    
    st.write(f"Allowable Deflection Limit (**L/{limit_val}**):")
    st.latex(rf"\delta_{{allow}} = \frac{{{c['L_cm']:.0f} \text{{ (Span)}}}}{{{limit_val}}} = \mathbf{{{c['delta']:.2f}}} \text{{ cm}}")
    
    st.markdown("**Step 4.1: Convert to Safe Uniform Load ($w_d$)**")
    st.write(f"Using $I_x = {props['Ix']:,}$ cm⁴ and $E = {c['E_ksc']:,.0f}$ ksc")
    
    st.latex(rf"w_d = \frac{{384 \times E \times I_x \times \delta_{{allow}}}}{{5 \times L^4}} \times 100")
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
        elif c['wm'] == final_w: ctrl = f"Moment Control ({c['Zone']})"
        else: ctrl = f"Deflection Control (L/{limit_val})"
        
        st.info(f"**Governing Case:** {ctrl}")
        st.write(f"- Shear Capacity: {c['ws']:,.0f} kg/m")
        st.write(f"- Moment Capacity: {c['wm']:,.0f} kg/m")
        st.write(f"- Deflection Limit: {c['wd']:,.0f} kg/m")
    
    with res_col2:
        st.success(f"✅ **Safe Net Load Capacity:**")
        st.metric(label="Net Load (Excluding Beam Weight)", value=f"{net_w:,.0f} kg/m")
        st.caption(f"*Beam self-weight ({props['W']} kg/m) deducted.")

    st.markdown("---")

    # === 6. TRANSITION DERIVATION ===
    st.subheader("6. Derivation of Critical Lengths")
    st.caption("Critical Length ($L$) is where the capacity of two failure modes are exactly equal.")

    with st.expander("Show Formula Derivation & Calculation"):
        # CASE 1: Shear vs Moment
        st.markdown("#### 6.1 Shear $\leftrightarrow$ Moment Transition ($L_{v-m}$)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Setup Equation:**")
            st.latex(r"L = \frac{4 M_{full}}{V_{design}}")
        with c2:
            st.markdown("**Substitution:**")
            # Using M_des_full to ensure consistency with the table
            st.latex(rf"L = \frac{{4 \times {c['M_des_full']:,.0f}}}{{{c['V_des']:,.0f}}} = {c['L_vm']*100:,.1f} \text{{ cm}}")
            st.success(f"= {c['L_vm']:.2f} m")

        st.markdown("---")

        # CASE 2: Moment vs Deflection (UPDATED Dynamic Formula)
        st.markdown("#### 6.2 Moment $\leftrightarrow$ Deflection Transition ($L_{m-d}$)")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Setup Equation:**")
            st.write(f"Equating Moment ($w_m$) and Deflection ($w_d$) at $L/{limit_val}$:")
            # Using M_full in formula
            st.latex(rf"L = \frac{{384 E I}}{{40 \times M_{{full}} \times {limit_val}}}")
        
        with c4:
            st.markdown("**Substitution:**")
            # Using M_des_full to ensure consistency with the table
            denom_val = 40 * c['M_des_full'] * limit_val
            st.latex(rf"L = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,}}}{{{denom_val:,.0f}}}")
            st.latex(rf"L = {c['L_md']*100:,.1f} \text{{ cm}}")
            st.success(f"= {c['L_md']:.2f} m")

    col_sum1, col_sum2 = st.columns(2)
    col_sum1.info(f"**📍 Shear/Moment Switch:** $L = {c['L_vm']:.2f}$ m")
    col_sum2.info(f"**📍 Moment/Deflection Switch:** $L = {c['L_md']:.2f}$ m")
