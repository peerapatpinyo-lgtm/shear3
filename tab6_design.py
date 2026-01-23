import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("### 🏗️ Professional Connection Studio")
    st.caption(f"Code Reference: **AISC 360-16 ({method})** | Scope: Shear Tab Connection (Single Column)")

    # --- 1. GLOBAL INPUTS ---
    with st.expander("🔹 Beam & Load Configuration", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            section_name = st.selectbox("Select Beam Section:", list(SYS_H_BEAMS.keys()))
        
        props = SYS_H_BEAMS[section_name]
        w_sw = props['W']

        # Auto Calculate Reference Capacity
        c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
        L_vm = c_ref['L_vm']
        w_gross = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 if L_vm > 0 else 0
        w_net = max(0, w_gross - w_sw)
        
        with col2:
            st.info(f"Design Capacity suggestion (75%): **{0.75*w_net:,.0f} kg/m**")
            
        c_i1, c_i2 = st.columns(2)
        span = c_i1.slider("Span Length (m):", 1.0, 15.0, 6.0)
        load = c_i2.number_input("External Load (kg/m):", value=float(int(0.75*w_net)), step=100.0)

        # Force Calculation
        w_total = load + w_sw
        V_u = (w_total * span) / 2          # Reaction (Shear Demand)
        M_u = (w_total * span**2) / 8 * 100
        
        # Quick Beam Check
        c_chk = core_calculation(span, Fy, E_gpa, props, method, def_limit)
        beam_ratio = V_u / c_chk['V_des']
        if beam_ratio > 1.0:
            st.warning(f"⚠️ Beam Shear Ratio: {beam_ratio:.2f}")

    # ==============================================================================
    # 🔩 CONNECTION DESIGN PARAMETERS
    # ==============================================================================
    st.subheader("2. 🔩 Connection Detailing")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.markdown("**Bolt Config (Single Col)**")
        bolt_grade = st.selectbox("Bolt Grade", ["A325N", "A307"], index=0)
        bolt_size = st.selectbox("Bolt Size", ["M12", "M16", "M20", "M22", "M24"], index=2)
        n_rows = st.number_input("Rows (No. of Bolts)", 2, 8, 3)
    
    with col_c2:
        st.markdown("**Plate Geometry**")
        plate_t_mm = st.selectbox("Plate Thickness (mm)", [6, 9, 12, 16, 19, 25], index=1)
        # Material Properties
        Fy_plate = 2500 # ksc (SS400)
        Fu_plate = 4100 # ksc (SS400)
        E70XX = 4900 # ksc (Weld Electrode Strength)
        
    # Auto-Geometry Logic
    d_b_mm = float(bolt_size.replace("M",""))
    std_pitch = int(3 * d_b_mm)
    std_edge = int(1.5 * d_b_mm) # Vertical edge (Lev)
    std_leh = int(1.5 * d_b_mm)  # Horizontal edge (Leh) to beam end
    
    with col_c3:
        st.markdown("**Dimensions (mm)**")
        pitch = st.number_input("Pitch (s)", value=std_pitch, step=5, help="Vertical spacing")
        lev = st.number_input("Vertical Edge (Lev)", value=std_edge, step=5, help="Edge to top/bottom of plate")
        leh = st.number_input("Horiz. Edge (Leh)", value=35, step=5, help="Center of hole to Plate Weld Line")
        weld_size = st.selectbox("Weld Size (mm)", [4, 5, 6, 8, 10, 12], index=1)

    # --- CONSTANTS & CONVERSIONS ---
    d_b = d_b_mm / 10
    h_hole = (d_b_mm + 2) / 10 # Standard hole
    s = pitch / 10
    Lev = lev / 10
    Leh = leh / 10
    tp = plate_t_mm / 10
    tw = props.get('tw', props.get('t1', 0.6)) / 10
    
    # Plate Dimensions
    plate_h = (2 * Lev) + ((n_rows - 1) * s)
    plate_w = Leh + 1.5 # Assume 1.5cm clearance from beam end
    
    # --- CALCULATION ENGINE (AISC 360-16) ---
    
    # Factor Setup
    if method == "ASD":
        Om = 2.00; Om_y = 1.50; Om_w = 2.00
        def get_Rn(Rn, type="normal"): 
            if type=="yield": return Rn/Om_y
            return Rn/Om
    else: # LRFD
        Ph = 0.75; Ph_y = 1.00; Ph_w = 0.75
        def get_Rn(Rn, type="normal"):
            if type=="yield": return Ph_y*Rn
            return Ph*Rn

    results = {}

    # 1. Bolt Shear (J3.6)
    Ab = (np.pi * d_b**2) / 4
    Fnv = 3720 if "A325" in bolt_grade else 1880
    Rn_shear = n_rows * Fnv * Ab
    results["Bolt Shear"] = get_Rn(Rn_shear)

    # 2. Bearing & Tearout (J3.10) - Detailed
    # Check Plate Only (Usually Critical for Shear Tab)
    # Edge Bolt
    Lc_edge = Lev - (h_hole/2)
    Rn_edge = min(1.2 * Lc_edge * tp * Fu_plate, 2.4 * d_b * tp * Fu_plate)
    # Inner Bolts
    if n_rows > 1:
        Lc_inner = s - h_hole
        Rn_inner = min(1.2 * Lc_inner * tp * Fu_plate, 2.4 * d_b * tp * Fu_plate) * (n_rows - 1)
    else: Rn_inner = 0
    results["Bearing (Plate)"] = get_Rn(Rn_edge + Rn_inner)

    # 3. Plate Shear Yielding (J4.2)
    Agv = plate_h * tp
    Rn_yield = 0.6 * Fy_plate * Agv
    results["Plate Yielding"] = get_Rn(Rn_yield, "yield")

    # 4. Plate Shear Rupture (J4.2)
    Anv = (plate_h - (n_rows * h_hole)) * tp
    Rn_rup = 0.6 * Fu_plate * Anv
    results["Plate Rupture"] = get_Rn(Rn_rup)

    # 5. Block Shear (J4.3) - The "Pro" Check
    # Failure Path: Vertical Shear line along bolts + Horizontal Tension line to edge
    A_gv = (Lev + (n_rows - 1) * s) * tp  # Gross Shear Area
    A_nv = A_gv - ((n_rows - 0.5) * h_hole * tp) # Net Shear Area
    A_nt = (Leh - (h_hole/2)) * tp # Net Tension Area
    
    Ubs = 1.0 # Uniform tension stress
    # Formula: Rn = min( 0.6FuAnv + UbsFuAnt , 0.6FyAgv + UbsFuAnt )
    R1 = (0.6 * Fu_plate * A_nv) + (Ubs * Fu_plate * A_nt)
    R2 = (0.6 * Fy_plate * Agv) + (Ubs * Fu_plate * A_nt) # Note: Code usually implies shear yield check separately
    # AISC 360-16 Eq J4-5:
    Rn_block = min(R1, (0.6 * Fy_plate * A_gv) + (Ubs * Fu_plate * A_nt))
    results["Block Shear"] = get_Rn(Rn_block)

    # 6. Weld Strength (J2.4)
    # Double Fillet Weld (Both sides of plate to support)
    w_size_cm = weld_size / 10
    Fw = 0.60 * E70XX
    # Effective throat = 0.707 * w
    Rn_weld_per_cm = 0.707 * w_size_cm * Fw * 2 # x2 for double side
    # Length of weld = Plate Height (L)
    Rn_weld_total = Rn_weld_per_cm * plate_h
    results["Weld Strength"] = get_Rn(Rn_weld_total)

    # --- DISPLAY RESULTS ---
    st.markdown("---")
    
    # Layout: Left = Drawing, Right = Checks
    c_res1, c_res2 = st.columns([1.2, 1])
    
    with c_res1:
        st.markdown("#### 📐 Connection Drawing")
        # Generate Plot using Matplotlib
        fig, ax = plt.subplots(figsize=(4, 6))
        
        # 1. Draw Plate (Rectangle)
        # Origin (0,0) at bottom-left of plate attached to support
        rect = patches.Rectangle((0, 0), Leh*10 + 20, plate_h*10, linewidth=2, edgecolor='#333', facecolor='#eee')
        ax.add_patch(rect)
        
        # 2. Draw Weld Line (at x=0)
        ax.plot([0, 0], [0, plate_h*10], color='red', linewidth=4, linestyle='--', label='Weld')
        
        # 3. Draw Bolts
        # First bolt position: x = Leh, y = Lev
        bolt_x = Leh * 10
        for i in range(n_rows):
            bolt_y = (Lev * 10) + (i * s * 10)
            circle = patches.Circle((bolt_x, bolt_y), radius=(d_b_mm/2), color='#0055aa')
            ax.add_patch(circle)
            # Add crosshair
            ax.plot([bolt_x-2, bolt_x+2], [bolt_y, bolt_y], 'w-', lw=1)
            ax.plot([bolt_x, bolt_x], [bolt_y-2, bolt_y+2], 'w-', lw=1)
            
        # 4. Dimensions Annotation
        # Pitch
        if n_rows > 1:
            ax.annotate(f"Pitch {pitch}mm", xy=(bolt_x+10, (Lev*10) + (s*10)/2), color='blue', fontsize=8)
        # Edge
        ax.annotate(f"Leh {leh}mm", xy=(bolt_x/2, -5), color='green', fontsize=8, ha='center')
        ax.annotate(f"Lev {lev}mm", xy=(bolt_x+15, Lev*10), color='green', fontsize=8)

        # Settings
        ax.set_xlim(-10, Leh*10 + 50)
        ax.set_ylim(-20, plate_h*10 + 20)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f"Shear Tab: PL-{plate_t_mm}mm x {int(plate_h*10)}mm", fontsize=10)
        st.pyplot(fig)

    with c_res2:
        st.markdown(f"#### 📊 Demand: **{V_u:,.0f} kg**")
        
        # Determine Status
        df_res = pd.DataFrame({
            "Check Item": list(results.keys()),
            "Capacity (kg)": list(results.values())
        })
        df_res['Ratio'] = V_u / df_res['Capacity (kg)']
        df_res['Status'] = df_res['Ratio'].apply(lambda x: "✅" if x <= 1.0 else "❌")
        
        # Display as a clean table
        st.dataframe(
            df_res.style.format({"Capacity (kg)": "{:,.0f}", "Ratio": "{:.2f}"})
            .applymap(lambda v: 'color: red; font-weight: bold;' if isinstance(v, float) and v > 1.0 else None, subset=['Ratio']),
            use_container_width=True,
            hide_index=True
        )
        
        # Critical Message
        max_ratio = df_res['Ratio'].max()
        if max_ratio <= 1.0:
            st.success(f"**ALL PASSED** (Max Ratio: {max_ratio:.2f})")
        else:
            fail_item = df_res.loc[df_res['Ratio'].idxmax(), 'Check Item']
            st.error(f"**FAILED** at '{fail_item}' (Ratio: {max_ratio:.2f})")
            
            # Smart Recommendations
            if "Weld" in fail_item: st.info("💡 Solution: Increase weld size or plate height.")
            if "Block Shear" in fail_item: st.info("💡 Solution: Increase spacing (pitch) or horizontal edge distance (Leh).")
            if "Bearing" in fail_item: st.info("💡 Solution: Increase Plate Thickness or Edge Distance.")

    # --- EXPANDER: THE "ENGINEER'S NOTE" (BLOCK SHEAR EXPLAINED) ---
    with st.expander("📘 Engineering Calculation Note (Block Shear & Weld)"):
        st.markdown("### 1. Block Shear Rupture (AISC J4.3)")
        st.write("การวิบัติแบบฉีกขาดเป็นรูปตัว L หรือ U (Tension + Shear failure path)")
        st.latex(r"R_n = \min(0.6F_u A_{nv} + U_{bs}F_u A_{nt}, \quad 0.6F_y A_{gv} + U_{bs}F_u A_{nt})")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Shear Plane (Vertical):**")
            st.write(f"- Gross Area ($A_{{gv}}$): {A_gv:.2f} cm²")
            st.write(f"- Net Area ($A_{{nv}}$): {A_nv:.2f} cm²")
        with c2:
            st.markdown(f"**Tension Plane (Horizontal):**")
            st.write(f"- Net Area ($A_{{nt}}$): {A_nt:.2f} cm²")
            st.write(f"- $U_{{bs}}$: 1.0")
            
        st.markdown(f"**Result:** $R_n$ (Block Shear) = {Rn_block:,.0f} kg")
        st.markdown("---")
        
        st.markdown("### 2. Weld Design (AISC J2.4)")
        st.latex(r"R_n = 0.707 w F_w L_{weld}")
        st.write(f"- Weld Size ($w$): {weld_size} mm (E70XX)")
        st.write(f"- Total Length ($L$): {plate_h*10:.0f} mm (Double Sided)")
        st.write(f"- **Capacity:** {Rn_weld_total:,.0f} kg")
