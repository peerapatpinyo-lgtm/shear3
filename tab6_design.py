import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🛠️ Detailed Connection Design")
    st.caption(f"Standard: **AISC 360-16 ({method})** | Complete Checks: Bolt Shear, Bearing (Lc Method), Plate Yielding & Rupture")

    # --- 1. Selection Section ---
    col1, col2 = st.columns([1, 2])
    with col1:
        section_name = st.selectbox("Select Section:", list(SYS_H_BEAMS.keys()), index=0)
    
    props = SYS_H_BEAMS[section_name]
    w_sw = props['W']

    # --- 2. Calculate Load ---
    c_ref = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
    L_vm = c_ref['L_vm']
    w_gross_cap = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 if L_vm > 0 else 0
    w_net_cap = max(0, w_gross_cap - w_sw)
    w_75 = 0.75 * w_net_cap
    
    with col2:
        st.info(f"**Design Load (75%): {w_75:,.0f} kg/m** (Max Ext: {w_net_cap:,.0f})")

    st.markdown("---")

    # --- 3. Beam Analysis (Quick Check) ---
    st.subheader("1. 🏗️ Beam Check")
    col_i1, col_i2 = st.columns(2)
    with col_i1: span = st.slider("Span (m):", 1.0, 15.0, 6.0)
    with col_i2: load = st.number_input("Ext. Load (kg/m):", value=float(int(w_75)), step=100.0)
    
    w_total = load + w_sw
    V_u = (w_total * span) / 2
    M_u = (w_total * span**2) / 8 * 100
    
    c_check = core_calculation(span, Fy, E_gpa, props, method, def_limit)
    ratio_v = V_u / c_check['V_des']
    
    if ratio_v > 1.0: st.error(f"❌ Beam Shear Fail (Ratio: {ratio_v:.2f})")
    else: st.success(f"✅ Beam Shear OK (Ratio: {ratio_v:.2f}) - Reaction: **{V_u:,.0f} kg**")

    st.markdown("---")

    # ==============================================================================
    # 🔩 SECTION 2: ADVANCED CONNECTION DESIGN
    # ==============================================================================
    st.subheader("2. 🔩 Connection Detail (Shear Tab)")
    
    # --- A. CONFIGURATION ---
    c1, c2, c3 = st.columns(3)
    with c1:
        bolt_grade = st.selectbox("Bolt Grade", ["A325N", "A307"], index=0)
        bolt_size = st.selectbox("Bolt Size", ["M12", "M16", "M20", "M22", "M24"], index=2)
    with c2:
        n_rows = st.number_input("Rows of Bolts", 2, 10, 3)
        plate_t_mm = st.selectbox("Plate Thick (mm)", [6, 9, 12, 16, 19, 25], index=1)
    with c3:
        # Auto-suggest geometry based on bolt size (Standard Practice ~3db)
        d_b_mm = float(bolt_size.replace("M",""))
        pitch = st.number_input("Pitch (s) [mm]", value=int(3*d_b_mm), step=5, help="Distance center-to-center")
        edge_dist = st.number_input("Edge Dist (Le) [mm]", value=int(1.5*d_b_mm), step=5, help="Distance center-to-edge")

    # --- B. CONSTANTS & MATERIAL ---
    # Material Strength (approx)
    Fu_beam = 4000 if Fy < 3000 else 5200 # ksc
    Fy_plate = 2500 # SS400
    Fu_plate = 4000 # SS400
    
    # Geometry Conversions
    d_b = d_b_mm / 10 # cm
    h_hole = (d_b_mm + 2) / 10 # cm (Standard hole size = db + 2mm)
    s = pitch / 10 # cm
    le = edge_dist / 10 # cm
    tp = plate_t_mm / 10 # cm
    tw = props.get('tw', props.get('t1', 0.6)) / 10 # cm
    
    # Plate Height (Calculated)
    plate_h = (2 * le) + ((n_rows - 1) * s)
    
    # Safety Factors
    if method == "ASD":
        Om = 2.00; Om_y = 1.50 # Shear Yield Omega is 1.50
        Phi = 1.00; Phi_y = 1.00
        def get_design(Rn, omega): return Rn / omega
    else: # LRFD
        Phi = 0.75; Phi_y = 1.00 # Shear Yield Phi is 1.00
        Om = 1.00; Om_y = 1.00
        def get_design(Rn, phi): return phi * Rn

    # --- C. CHECK 1: BOLT SHEAR (J3.6) ---
    Ab = (np.pi * d_b**2) / 4
    Fnv = 3720 if "A325" in bolt_grade else 1880
    Rn_shear_total = (Fnv * Ab) * n_rows
    if method == "ASD": Rc_shear = Rn_shear_total / 2.0
    else: Rc_shear = 0.75 * Rn_shear_total

    # --- D. CHECK 2: BEARING & TEAROUT (J3.10) - THE DETAILED METHOD ---
    # We must check both Web and Plate.
    # Lc = Clear distance, in the direction of the force.
    
    def calc_bearing_capacity(t, Fu):
        # 1. Edge Bolt (1 bolt): Lc = Le - (hole/2)
        Lc_edge = le - (h_hole / 2)
        Rn_edge = min(1.2 * Lc_edge * t * Fu, 2.4 * d_b * t * Fu)
        
        # 2. Inner Bolts (n-1 bolts): Lc = s - hole
        if n_rows > 1:
            Lc_inner = s - h_hole
            Rn_inner_1unit = min(1.2 * Lc_inner * t * Fu, 2.4 * d_b * t * Fu)
            Rn_inner_total = Rn_inner_1unit * (n_rows - 1)
        else:
            Rn_inner_total = 0
            
        return Rn_edge + Rn_inner_total

    Rn_bear_web_total = calc_bearing_capacity(tw, Fu_beam)
    Rn_bear_plate_total = calc_bearing_capacity(tp, Fu_plate)
    
    if method == "ASD":
        Rc_bear_web = Rn_bear_web_total / 2.0
        Rc_bear_plate = Rn_bear_plate_total / 2.0
    else:
        Rc_bear_web = 0.75 * Rn_bear_web_total
        Rc_bear_plate = 0.75 * Rn_bear_plate_total

    # --- E. CHECK 3: PLATE CHECKS (J4) ---
    # 3.1 Shear Yielding (J4.2): Rn = 0.6 * Fy * Ag
    Ag = plate_h * tp
    Rn_yield = 0.6 * Fy_plate * Ag
    if method == "ASD": Rc_yield = Rn_yield / 1.50 # Note: Omega = 1.50 for Yielding
    else: Rc_yield = 1.00 * Rn_yield

    # 3.2 Shear Rupture (J4.2): Rn = 0.6 * Fu * Anv
    Anv = (plate_h - (n_rows * h_hole)) * tp # Net Area Shear
    Rn_rupture = 0.6 * Fu_plate * Anv
    if method == "ASD": Rc_rupture = Rn_rupture / 2.00
    else: Rc_rupture = 0.75 * Rn_rupture

    # --- F. SUMMARY ---
    capacities = {
        "1. Bolt Shear": Rc_shear,
        "2. Bearing (Web)": Rc_bear_web,
        "3. Bearing (Plate)": Rc_bear_plate,
        "4. Plate Yielding": Rc_yield,
        "5. Plate Rupture": Rc_rupture
    }
    
    min_cap_val = min(capacities.values())
    controlling_mode = min(capacities, key=capacities.get)
    total_ratio = V_u / min_cap_val

    # --- G. DISPLAY ---
    st.markdown(f"#### 📊 Analysis Result: {'✅ PASS' if total_ratio <= 1.0 else '❌ FAIL'}")
    
    # Summary Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Demand (Vu)", f"{V_u:,.0f} kg")
    m2.metric("Capacity (Rn/Ω)", f"{min_cap_val:,.0f} kg")
    m3.metric("Ratio", f"{total_ratio:.2f}", delta_color="inverse")
    
    st.error(f"**Controlling Limit:** {controlling_mode}")

    # Detailed Table
    st.markdown("---")
    st.markdown("**Detailed Checks Breakdown:**")
    
    df_res = pd.DataFrame({
        "Check Item": list(capacities.keys()),
        "Capacity (kg)": [f"{v:,.0f}" for v in capacities.values()],
        "Ratio": [f"{V_u/v:.2f}" for v in capacities.values()],
        "Status": ["✅" if V_u/v <= 1 else "❌" for v in capacities.values()]
    })
    st.dataframe(df_res, use_container_width=True)

    # --- EXPANDER: TEXTBOOK CALCULATION ---
    with st.expander("📝 View Professional Calculation Note (Step-by-Step)"):
        st.markdown(f"### Design Calculation Sheet ({method})")
        
        st.markdown("**1. Geometry & Parameters**")
        st.write(f"- Bolts: {n_rows} x {bolt_size} ({bolt_grade}) | Hole $\phi$: {h_hole*10:.1f} mm")
        st.write(f"- Spacing: Pitch $s={pitch}$ mm, Edge $L_e={edge_dist}$ mm")
        st.write(f"- Plate: $t={plate_t_mm}$ mm, $H={plate_h*10:.0f}$ mm ($A_g={Ag:.2f} cm^2$)")
        
        st.markdown("---")
        st.markdown("**2. Bearing Strength Check (Tear-out Method - AISC Eq J3-6a)**")
        st.latex(r"R_n = 1.2 L_c t F_u \leq 2.4 d t F_u")
        st.markdown("**Consideration for Connection Plate:**")
        
        # Calculate Lc for display
        Lc_edge_show = le - (h_hole/2)
        Lc_inner_show = s - h_hole
        st.markdown(f"- **Edge Bolt ($L_c$):** {le*10} - {h_hole*10/2:.1f} = {Lc_edge_show*10:.1f} mm")
        if n_rows > 1:
            st.markdown(f"- **Inner Bolt ($L_c$):** {pitch} - {h_hole*10:.1f} = {Lc_inner_show*10:.1f} mm")
        
        st.markdown(f"Nominal Strength ($R_n$) per set = **{Rn_bear_plate_total:,.0f} kg**")
        
        st.markdown("---")
        st.markdown("**3. Plate Shear Capacity (AISC J4.2)**")
        
        st.markdown("**(a) Shear Yielding (Gross Area):**")
        st.latex(r"R_n = 0.60 F_y A_g")
        st.caption(f"Rn = 0.6 * {Fy_plate} * {Ag:.2f} = {Rn_yield:,.0f} kg")
        
        st.markdown("**(b) Shear Rupture (Net Area):**")
        st.latex(r"R_n = 0.60 F_u A_{nv}")
        st.caption(f"Anv = ({plate_h*10:.0f} - {n_rows}*{h_hole*10:.1f}) * {tp*10:.1f} / 100 = {Anv:.2f} cm²")
        st.caption(f"Rn = 0.6 * {Fu_plate} * {Anv:.2f} = {Rn_rupture:,.0f} kg")

        st.info("Note: Block Shear Rupture is not included in this simplified tool but should be checked if tension exists.")
