# tab1_details.py
import streamlit as st

def render_tab1(c, props, method, Fy, section):
    """
    Function to render Tab 1: Detailed Calculation Sheet
    Uses pre-calculated values from calculator.py to ensure logic consistency.
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
                    f"Deflect Limit : L/{c.get('delta', 360)}")
        with ds_c2:
            st.markdown("**🗂️ Database Constants:**")
            st.code(f"Depth (D) : {props['D']} mm\n"
                    f"Web (tw)  : {props['tw']} mm\n"
                    f"Weight    : {props['W']} kg/m\n"
                    f"Sx (Table): {props['Sx_table']} cm3")
    
    st.markdown("---")

    # === 1. PROPERTIES ===
    st.markdown("#### 1. Geometric Properties")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Depth (D)", f"{props['D']} mm")
    c2.metric("Width (B)", f"{props['B']} mm")
    c3.metric("Flange (tf)", f"{props['tf']} mm")
    c4.metric("Web (tw)", f"{props['tw']} mm")
    
    c1b, c2b, c3b, c4b = st.columns(4)
    c1b.metric("Inertia (Ix)", f"{props['Ix']:,} cm4")
    # SHOW CALCULATED Zx
    c2b.metric("Plastic Mod (Zx)", f"{c['Zx']:.1f} cm3", help="Calculated from formula for I-Shape")
    # SHOW TABLE Sx
    c3b.metric("Elastic Mod (Sx)", f"{c['Sx']:.1f} cm3", help="From Standard Table")
    c4b.metric("Unbraced Length", f"{c['Lb']:.2f} m")
    
    st.markdown("---")

    # === 2. SHEAR ===
    st.subheader("2. Shear Capacity Control")
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        st.markdown("**Nominal Strength ($V_n$)**")
        st.latex(rf"V_n = 0.6 \times F_y \times A_w = \mathbf{{{c['Vn']:,.0f}}} \text{{ kg}}")
    with col_s2:
        st.markdown("**Design Strength ($V_{des}$)**")
        st.latex(rf"V_{{des}} = {c['txt_v_method']} = \mathbf{{{c['V_des']:,.0f}}} \text{{ kg}}")
    
    st.markdown("**Safe Uniform Load (Gross) ($w_s$)**")
    st.latex(rf"w_s = \mathbf{{{c['ws_gross']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 3. MOMENT ===
    st.subheader("3. Moment Capacity Control (LTB)")
    st.write(f"**LTB Zone:** {c['Zone']}")
    
    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        st.markdown("**Nominal Strength ($M_n$)**")
        st.latex(rf"M_n = \min(M_p, M_{{ltb}}) = \mathbf{{{c['Mn']:,.0f}}} \text{{ kg-cm}}")
    with col_m2:
        st.markdown("**Design Strength ($M_{des}$)**")
        st.latex(rf"M_{{des}} = {c['txt_m_method']} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")
        
    st.markdown("**Safe Uniform Load (Gross) ($w_m$)**")
    st.latex(rf"w_m = \mathbf{{{c['wm_gross']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Control")
    st.write(f"Limit: L/{c.get('delta', 360):.0f} = {c['delta']:.2f} cm")
    st.markdown("**Safe Uniform Load (Gross Service) ($w_d$)**")
    st.latex(rf"w_d = \mathbf{{{c['wd_gross']:,.0f}}} \text{{ kg/m}}")
    st.caption("Note: This is an unfactored Service Load.")
    
    st.markdown("---")

    # === 5. CONCLUSION (NET LOADS) ===
    st.subheader("5. Net Safe Superimposed Load")
    
    # Retrieve NET values calculated in calculator.py
    net_s = c['ws_net']
    net_m = c['wm_net']
    net_d = c['wd_net']
    final_load = min(net_s, net_m, net_d)
    
    # Display Logic Summary
    if method == "LRFD":
        st.info(f"**Method: LRFD** | Factored Dead Load Deducted: $1.2 \\times {props['W']} = {c['factored_dead_load']:.1f}$ kg/m")
    else:
        st.info(f"**Method: ASD** | Dead Load Deducted: $1.0 \\times {props['W']} = {c['factored_dead_load']:.1f}$ kg/m")

    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.markdown("**Net Capacities (Superimposed):**")
        st.write(f"- Shear Control: **{net_s:,.0f}** kg/m")
        st.write(f"- Moment Control: **{net_m:,.0f}** kg/m")
        st.write(f"- Deflection Control: **{net_d:,.0f}** kg/m")
        
    with res_col2:
        st.success("✅ **Max Safe Superimposed Load**")
        st.metric("Allowable Load", f"{final_load:,.0f} kg/m")
        
        if final_load == net_s:
            st.caption("Governed by Shear")
        elif final_load == net_m:
            st.caption("Governed by Moment")
        else:
            st.caption("Governed by Deflection")
