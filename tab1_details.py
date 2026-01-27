import streamlit as st

def render_tab1(c, props, method, Fy, section):
    """
    Function to render Tab 1: Detailed Calculation Sheet
    Fixed to match updated calculator.py keys (ws_gross, ws_net, etc.)
    """
    
    st.markdown(f"### 📄 Engineering Report: {section} ({method})")
    
    # === DATA SOURCE TRACING ===
    with st.expander("ℹ️ Data Sources & Input Parameters", expanded=False):
        ds_c1, ds_c2 = st.columns(2)
        with ds_c1:
            st.markdown("**🔵 User Inputs:**")
            st.code(f"Design Method : {method}\n"
                    f"Yield Strength: {Fy} ksc\n"
                    f"Modulus (E)   : {c['E_ksc']/10197.16:.0f} GPa\n"
                    f"Span Length   : {c['L_cm']/100:.2f} m\n"
                    f"Deflect Limit : L/{c.get('def_limit', 360)}")
        with ds_c2:
            st.markdown("**🗂️ Database Constants:**")
            st.caption(f"Retrieved from `database.SYS_H_BEAMS` key: `{section}`")
            st.code(f"Depth (D) : {props['D']} mm\n"
                    f"Web (tw)  : {props['tw']} mm\n"
                    f"Weight    : {props['W']} kg/m\n"
                    f"Inertia   : {props['Ix']} cm4")
    
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
    
    # Use calculated Zx from 'c'
    c2b.metric("Plastic Mod (Zx)", f"{c['Zx']:.1f} cm3", help="Calculated Plastic Modulus for Strength (Mp)")
    
    c3b.metric("Elastic Mod (Sx)", f"{c['Sx']:.1f} cm3", help="Elastic Modulus for Yield/Deflection")
    c4b.metric("Unbraced Length", f"{c['Lb']:.2f} m", help="Assumed equal to Span Length")
    
    st.markdown("---")

    # === 2. SHEAR ===
    st.subheader("2. Shear Capacity Control")
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        st.markdown("**Step 2.1: Nominal Shear Strength ($V_n$)**")
        st.latex(r"V_n = 0.60 \times F_y \times A_w \times C_v")
        st.write(f"- $F_y$ = {Fy} ksc")
        st.write(f"- $A_w$ = {c['Aw']:.2f} cm²")
        st.write(f"- $C_v$ = {c['Cv']:.2f}")
        st.latex(rf"\therefore V_n = 0.60 \times {Fy} \times {c['Aw']:.2f} \times {c['Cv']:.2f} = \mathbf{{{c['Vn']:,.0f}}} \text{{ kg}}")
        
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
    
    st.markdown("**Step 2.3: Safe Uniform Load (Gross) ($w_s$)**")
    # [FIX] Use ws_gross
    st.latex(rf"w_s = \frac{{2 \times {c['V_des']:,.0f}}}{{{c['L_cm']:.0f}}} \times 100 = \mathbf{{{c['ws_gross']:,.0f}}} \text{{ kg/m}}")
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

    st.markdown("**Step 3.4: Safe Uniform Load (Gross) ($w_m$)**")
    # [FIX] Use wm_gross
    st.latex(rf"w_m = \frac{{8 \times {c['M_des']:,.0f}}}{{{c['L_cm']:.0f}^2}} \times 100 = \mathbf{{{c['wm_gross']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Control")
    
    limit_val = c.get('def_limit', 360) 
    
    st.write(f"Allowable Deflection Limit (**L/{limit_val}**):")
    st.latex(rf"\delta_{{allow}} = \frac{{{c['L_cm']:.0f} \text{{ (Span)}}}}{{{limit_val}}} = \mathbf{{{c['delta']:.2f}}} \text{{ cm}}")
    
    st.markdown("**Step 4.1: Convert to Safe Uniform Load (Gross) ($w_d$)**")
    st.write(f"Using $I_x = {props['Ix']:,}$ cm⁴ and $E = {c['E_ksc']:,.0f}$ ksc")
    
    st.latex(rf"w_d = \frac{{384 \times E \times I_x \times \delta_{{allow}}}}{{5 \times L^4}} \times 100")
    st.latex(rf"w_d = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,} \times {c['delta']:.2f}}}{{5 \times {c['L_cm']:.0f}^4}} \times 100")
    # [FIX] Use wd_gross
    st.latex(rf"\therefore w_d = \mathbf{{{c['wd_gross']:,.0f}}} \text{{ kg/m}}")
    
    st.caption("⚠️ **Note:** This calculated load ($w_d$) is a **Service Load (Unfactored)**. Do not apply load factors to this value.")
    
    st.markdown("---")

    # === 5. CONCLUSION ===
    st.subheader("5. Summary & Design Verification")
    
    # [FIX] Retrieve NET values directly from calculator (Single Source of Truth)
    net_shear_strength = c['ws_net']
    net_moment_strength = c['wm_net']
    net_deflection_service = c['wd_net']
    
    # Ensure no negative values (calculator handles this, but safety check)
    net_shear_strength = max(0, net_shear_strength)
    net_moment_strength = max(0, net_moment_strength)
    net_deflection_service = max(0, net_deflection_service)
    
    # Calculate Governing Net Safe Load
    net_safe_load = min(net_shear_strength, net_moment_strength, net_deflection_service)
    
    # Determine governing case
    if net_safe_load == net_shear_strength:
        ctrl = "Shear Control"
        icon = "⛓️"
    elif net_safe_load == net_moment_strength:
        ctrl = f"Moment Control ({c['Zone']})"
        icon = "🔄"
    else:
        ctrl = f"Deflection Control (L/{limit_val})"
        icon = "📉"
        
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.info(f"**Governing Case:** {icon} {ctrl}")
        st.markdown("**Net Load Capabilities (Beam Weight Deducted):**")
        st.write(f"- Shear Limit: {net_shear_strength:,.0f} kg/m")
        st.write(f"- Moment Limit: {net_moment_strength:,.0f} kg/m")
        st.write(f"- Deflection Limit: {net_deflection_service:,.0f} kg/m")
        
        if method == "LRFD":
            st.caption(f"⚠️ **Note (LRFD):** Shear/Moment limits have {c['factored_dead_load']:.1f} kg/m ($1.2D$) deducted. Deflection has {props['W']} kg/m ($1.0D$) deducted.")
        else:
            st.caption(f"ℹ️ **Note (ASD):** All limits have {props['W']} kg/m ($1.0D$) deducted.")
    
    with res_col2:
        st.success(f"✅ **Safe Net Superimposed Load:**")
        st.metric(label="Max Uniform Load", value=f"{net_safe_load:,.0f} kg/m")
        st.caption(f"This is the maximum additional load you can place on the beam that satisfies both Strength and Serviceability.")

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
            st.latex(rf"L = \frac{{4 \times {c['M_des_full']:,.0f}}}{{{c['V_des']:,.0f}}} = {c['L_vm']*100:,.1f} \text{{ cm}}")
            st.success(f"= {c['L_vm']:.2f} m")

        st.markdown("---")

        # CASE 2: Moment vs Deflection
        st.markdown("#### 6.2 Moment $\leftrightarrow$ Deflection Transition ($L_{m-d}$)")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Setup Equation:**")
            st.write(f"Equating Moment ($w_m$) and Deflection ($w_d$) at $L/{limit_val}$:")
            st.latex(rf"L = \frac{{384 E I}}{{40 \times M_{{full}} \times {limit_val}}}")
        
        with c4:
            st.markdown("**Substitution:**")
            # Calculate denom for display
            denom_val = 40 * c['M_des_full'] * limit_val
            st.latex(rf"L = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,}}}{{{denom_val:,.0f}}}")
            st.latex(rf"L = {c['L_md']*100:,.1f} \text{{ cm}}")
            st.success(f"= {c['L_md']:.2f} m")

    col_sum1, col_sum2 = st.columns(2)
    col_sum1.info(f"**📍 Shear/Moment Switch:** $L = {c['L_vm']:.2f}$ m")
    col_sum2.info(f"**📍 Moment/Deflection Switch:** $L = {c['L_md']:.2f}$ m")
