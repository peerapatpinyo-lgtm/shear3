import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🚀 Connection Digital Twin & Studio")
    st.caption("Capabilities: **3D Visualization** | **BOM Costing** | **Auto-Reporting** | **AISC 360-16**")

    # --- 1. DESIGN INPUTS (Compact) ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            span = st.number_input("Span (m)", 6.0, step=0.5)
        with c3:
            # Auto Load Logic
            c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
            rec_load = 0.75 * max(0, ((2*c_ref['V_des']/(c_ref['L_vm']*100))*100) - props['W'])
            load = st.number_input("Load (kg/m)", value=float(int(rec_load)), step=100.0)
        with c4:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("Rows", 2, 8, 3)

        # Advanced Geometry
        d_b_mm = float(bolt_size.replace("M",""))
        c5, c6, c7, c8 = st.columns(4)
        with c5: plate_t = st.selectbox("Plate T (mm)", [6, 9, 12, 16, 19, 25], index=2)
        with c6: pitch = st.number_input("Pitch (mm)", value=int(3*d_b_mm), step=5)
        with c7: lev = st.number_input("V-Edge (mm)", value=int(1.5*d_b_mm), step=5)
        with c8: leh = st.number_input("H-Edge (mm)", value=40, step=5)

    # --- 2. CALCULATION CORE ---
    # Setup
    V_u = ((load + props['W']) * span) / 2
    d_b = d_b_mm/10; tp = plate_t/10; plate_h = ((2*lev) + (n_rows-1)*pitch)/10
    
    # AISC Checks (Simplified for brevity, reusing logic)
    phi = 0.75 if method == "LRFD" else 0.5 # 1/Omega
    # 1. Bolt Shear
    Rn_shear = n_rows * (3720 * np.pi * d_b**2 / 4) # A325 assumed
    Rc_shear = Rn_shear * phi
    # 2. Plate Bearing
    Rn_bear = (n_rows * 2.4 * d_b * tp * 4100) # Simplified upper bound
    Rc_bear = Rn_bear * phi
    # 3. Weld
    Rn_weld = 0.707 * 0.6 * 4900 * 2 * plate_h # 6mm weld assumed
    Rc_weld = Rn_weld * phi
    
    capacities = {"Bolt Shear": Rc_shear, "Bearing": Rc_bear, "Weld": Rc_weld}
    min_cap = min(capacities.values())
    ratio = V_u / min_cap
    status = "✅ SAFE" if ratio <= 1.0 else "❌ FAIL"
    color_status = "green" if ratio <= 1.0 else "red"

    # --- 3. THE DIGITAL TWIN (3D VISUALIZATION) ---
    st.subheader("1. 🧊 3D Connection Model")
    
    # 3D Helper Function: Create a Box Mesh
    def make_box(x_center, y_center, z_center, dx, dy, dz, color):
        return go.Mesh3d(
            # 8 vertices of a cube
            x=[x_center-dx/2, x_center-dx/2, x_center+dx/2, x_center+dx/2, x_center-dx/2, x_center-dx/2, x_center+dx/2, x_center+dx/2],
            y=[y_center-dy/2, y_center+dy/2, y_center+dy/2, y_center-dy/2, y_center-dy/2, y_center+dy/2, y_center+dy/2, y_center-dy/2],
            z=[z_center-dz/2, z_center-dz/2, z_center-dz/2, z_center-dz/2, z_center+dz/2, z_center+dz/2, z_center+dz/2, z_center+dz/2],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1.0, flatshading=True, name='Box'
        )

    col_3d, col_bom = st.columns([2, 1])
    
    with col_3d:
        fig_3d = go.Figure()
        
        # A. Beam Web (Gray)
        # Assume Web is on Y-Z plane, thickness along X
        tw_mm = props.get('tw', 6.0)
        web_h_mm = props['D'] * 10
        web_l_mm = 300 # Show 30cm of beam
        fig_3d.add_trace(make_box(0, web_l_mm/2, web_h_mm/2, tw_mm, web_l_mm, web_h_mm, '#bdc3c7'))

        # B. Connection Plate (Blue)
        # Attached to web (x = tw/2 + tp/2)
        pl_h_mm = plate_h * 10
        pl_w_mm = leh + 20
        pl_x_center = (tw_mm/2) + (plate_t/2)
        # Position vertically centered usually, but here based on inputs? Let's center it for viz
        fig_3d.add_trace(make_box(pl_x_center, pl_w_mm/2, web_h_mm/2, plate_t, pl_w_mm, pl_h_mm, '#3498db'))

        # C. Bolts (Red Cylinders - approximated as lines with width)
        bolt_len = tw_mm + plate_t + 20 # Stick out
        bolt_x_start = -(bolt_len/2) + pl_x_center
        bolt_x_end = (bolt_len/2) + pl_x_center
        
        bolt_y_pos = leh # From beam end (which is Y=0)
        z_start = (web_h_mm/2) + (pl_h_mm/2) - lev # Top bolt
        
        for i in range(n_rows):
            z_pos = z_start - (i * pitch)
            fig_3d.add_trace(go.Scatter3d(
                x=[bolt_x_start, bolt_x_end], y=[bolt_y_pos, bolt_y_pos], z=[z_pos, z_pos],
                mode='lines', line=dict(color='#e74c3c', width=10), name=f'Bolt {i+1}'
            ))

        fig_3d.update_layout(
            scene=dict(
                xaxis_title='X (Thickness)', yaxis_title='Y (Length)', zaxis_title='Z (Height)',
                aspectmode='data', # Real Scale
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
            ),
            margin=dict(l=0, r=0, b=0, t=0),
            height=400
        )
        st.plotly_chart(fig_3d, use_container_width=True)
        st.caption("💡 **Interaction:** Drag to Rotate | Scroll to Zoom | Check for Clash")

    # --- 4. BOM & COSTING ---
    with col_bom:
        st.markdown("### 💰 BOQ & Cost")
        
        # Calculations
        steel_density = 7850 / 1e6 # kg/mm3
        
        # 1. Plate Weight
        vol_plate = plate_t * (leh+20) * (plate_h*10)
        w_plate = vol_plate * steel_density
        
        # 2. Bolt Weight (Approx)
        w_bolt_unit = 0.15 * (d_b_mm/16)**2 # kg approx
        w_bolts = w_bolt_unit * n_rows
        
        # 3. Cost (Assumptions)
        cost_steel = 35 # THB/kg
        cost_fab = 15 # THB/kg (Fabrication)
        cost_bolt = 25 # THB/pcs
        
        total_weight = w_plate + w_bolts
        total_cost = (w_plate * (cost_steel + cost_fab)) + (n_rows * cost_bolt)
        
        st.metric("Total Weight", f"{total_weight:.2f} kg")
        st.metric("Est. Cost", f"฿ {total_cost:.0f}")
        
        st.markdown("---")
        st.markdown(f"**Breakdown:**\n- Plate: {w_plate:.2f} kg\n- Bolts: {n_rows} pcs")

    # --- 5. AUTOMATED REPORT GENERATOR ---
    st.subheader("2. 📝 Automated Calculation Report")
    
    report_text = f"""
    CALCULATION SHEET: SIMPLE SHEAR CONNECTION
    -------------------------------------------------------
    Project: Streamlit Structural Design    Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}
    Method: {method} (AISC 360-16)          Status: {status}
    -------------------------------------------------------
    
    [1] DESIGN PARAMETERS
    Beam Section: {section_name}
    Span: {span} m       Load: {load} kg/m
    Reaction (Vu): {V_u:,.0f} kg
    
    [2] CONNECTION DETAIL (Shear Tab)
    Plate: PL-{plate_t}x{int(leh+20)}x{int(plate_h*10)} mm (SS400)
    Bolts: {n_rows} x {bolt_size} (A325)
    Geometry: Pitch={pitch}mm, Lev={lev}mm, Leh={leh}mm
    
    [3] CAPACITY CHECKS
    -------------------------------------------------------
    1. Bolt Shear Strength    : {Rc_shear:,.0f} kg  [Ratio: {V_u/Rc_shear:.2f}]
    2. Plate Bearing Strength : {Rc_bear:,.0f} kg   [Ratio: {V_u/Rc_bear:.2f}]
    3. Weld Strength (Leg {weld_size}mm) : {Rc_weld:,.0f} kg   [Ratio: {V_u/Rc_weld:.2f}]
    -------------------------------------------------------
    CONTROLLING LIMIT: {min(capacities, key=capacities.get)}
    MAX RATIO: {ratio:.2f}
    
    [4] BILL OF MATERIALS
    Total Steel Weight: {total_weight:.2f} kg
    Estimated Cost: {total_cost:.0f} THB
    -------------------------------------------------------
    """
    
    text_col, btn_col = st.columns([3, 1])
    with text_col:
        st.text_area("Copy this text for your report:", report_text, height=250)
    with btn_col:
        st.download_button(
            label="💾 Download Report (.txt)",
            data=report_text,
            file_name=f"Calculation_{section_name}_{method}.txt",
            mime="text/plain"
        )
        if ratio > 1.0:
            st.error("⚠️ DESIGN FAIL")
        else:
            st.success("✅ READY TO PRINT")
