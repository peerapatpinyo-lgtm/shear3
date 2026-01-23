import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🚀 Connection Digital Twin & Studio")
    st.caption("Capabilities: **3D Visualization** | **BOM Costing** | **Auto-Reporting** | **AISC 360-16**")

    # --- 1. DESIGN INPUTS ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        # Row 1: Beam & Load
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            span = st.number_input("Span (m)", 6.0, step=0.5)
        with c3:
            # Auto Load Logic
            c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
            L_vm = c_ref['L_vm']
            w_max = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 if L_vm > 0 else 0
            rec_load = 0.75 * max(0, w_max - props['W'])
            load = st.number_input("Load (kg/m)", value=float(int(rec_load)), step=100.0)
        with c4:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)

        # Row 2: Detail Geometry
        d_b_mm = float(bolt_size.replace("M",""))
        c5, c6, c7, c8, c9 = st.columns(5) # Increased columns to fit Weld Size
        with c5: n_rows = st.number_input("Rows", 2, 8, 3)
        with c6: plate_t = st.selectbox("Plate T (mm)", [6, 9, 12, 16, 19, 25], index=2)
        with c7: weld_size = st.selectbox("Weld (mm)", [4, 6, 8, 10], index=1) # [FIXED] Added Variable
        with c8: pitch = st.number_input("Pitch (mm)", value=int(3*d_b_mm), step=5)
        with c9: lev = st.number_input("V-Edge (mm)", value=int(1.5*d_b_mm), step=5)
        
        # Extra parameter (Hidden or optional, default to standard)
        leh = 40 # Horizontal edge default

    # --- 2. CALCULATION CORE ---
    # Setup
    V_u = ((load + props['W']) * span) / 2
    d_b = d_b_mm/10
    tp = plate_t/10
    plate_h = ((2*lev) + (n_rows-1)*pitch)/10
    
    # Factors
    phi = 0.75 if method == "LRFD" else 0.5 # 1/Omega (ASD=2.0 -> 0.5)
    
    # 1. Bolt Shear (A325 approx)
    Rn_shear = n_rows * (3720 * np.pi * d_b**2 / 4)
    Rc_shear = Rn_shear * phi
    
    # 2. Plate Bearing (Simplified)
    Rn_bear = (n_rows * 2.4 * d_b * tp * 4100) 
    Rc_bear = Rn_bear * phi
    
    # 3. Weld (E70XX) [FIXED CALCULATION]
    # Rn = 0.707 * w * 0.6F_exx * L
    Rn_weld = 0.707 * (weld_size/10) * (0.6 * 4900) * (2 * plate_h) # 2 sides
    Rc_weld = Rn_weld * phi
    
    capacities = {"Bolt Shear": Rc_shear, "Bearing": Rc_bear, "Weld": Rc_weld}
    min_cap = min(capacities.values())
    ratio = V_u / min_cap
    status = "✅ SAFE" if ratio <= 1.0 else "❌ FAIL"

    # --- 3. THE DIGITAL TWIN (3D VISUALIZATION) ---
    st.subheader("1. 🧊 3D Connection Model")
    
    def make_box(x_center, y_center, z_center, dx, dy, dz, color):
        return go.Mesh3d(
            x=[x_center-dx/2, x_center-dx/2, x_center+dx/2, x_center+dx/2, x_center-dx/2, x_center-dx/2, x_center+dx/2, x_center+dx/2],
            y=[y_center-dy/2, y_center+dy/2, y_center+dy/2, y_center-dy/2, y_center-dy/2, y_center+dy/2, y_center+dy/2, y_center-dy/2],
            z=[z_center-dz/2, z_center-dz/2, z_center-dz/2, z_center-dz/2, z_center+dz/2, z_center+dz/2, z_center+dz/2, z_center+dz/2],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1.0, flatshading=True, name='Part'
        )

    col_3d, col_bom = st.columns([2, 1])
    
    with col_3d:
        fig_3d = go.Figure()
        
        # Beam Web
        tw_mm = props.get('tw', 6.0)
        web_h_mm = props['D'] * 10
        web_l_mm = 300 
        fig_3d.add_trace(make_box(0, web_l_mm/2, web_h_mm/2, tw_mm, web_l_mm, web_h_mm, '#bdc3c7'))

        # Plate
        pl_h_mm = plate_h * 10
        pl_w_mm = leh + 20
        pl_x_center = (tw_mm/2) + (plate_t/2)
        fig_3d.add_trace(make_box(pl_x_center, pl_w_mm/2, web_h_mm/2, plate_t, pl_w_mm, pl_h_mm, '#3498db'))

        # Bolts
        bolt_len = tw_mm + plate_t + 25
        bolt_x_center = (tw_mm/2) + (plate_t/2) - (plate_t/2) # Centered on interface roughly
        bolt_y_pos = leh
        z_start = (web_h_mm/2) + (pl_h_mm/2) - lev
        
        for i in range(n_rows):
            z_pos = z_start - (i * pitch)
            fig_3d.add_trace(go.Scatter3d(
                x=[-bolt_len/2 + pl_x_center, bolt_len/2 + pl_x_center], 
                y=[bolt_y_pos, bolt_y_pos], 
                z=[z_pos, z_pos],
                mode='lines', line=dict(color='#c0392b', width=8)
            ))

        fig_3d.update_layout(
            scene=dict(aspectmode='data', camera=dict(eye=dict(x=1.6, y=1.6, z=1.2))),
            margin=dict(l=0, r=0, b=0, t=0), height=350
        )
        st.plotly_chart(fig_3d, use_container_width=True)

    # --- 4. BOM & REPORT ---
    with col_bom:
        st.markdown("### 💰 Cost Est.")
        vol_plate = plate_t * (leh+20) * pl_h_mm
        w_plate = vol_plate * 7850 / 1e6
        total_cost = (w_plate * 50) + (n_rows * 25) # Approx rates
        
        st.metric("Weight", f"{w_plate:.2f} kg")
        st.metric("Cost", f"฿ {total_cost:.0f}")
        
        if ratio > 1.0: st.error(f"FAIL (Ratio {ratio:.2f})")
        else: st.success(f"PASS (Ratio {ratio:.2f})")

    # --- 5. REPORT GENERATOR ---
    st.markdown("---")
    report_text = f"""
    CALCULATION SHEET: {section_name}
    -------------------------------------------
    Design Load (Vu) : {V_u:,.0f} kg
    Connection       : {n_rows} x {bolt_size} (Grade A325)
    Plate            : {plate_t} mm x {int(pl_h_mm)} mm (SS400)
    Weld Size        : {weld_size} mm (E70XX)
    -------------------------------------------
    [CHECK RESULTS] ({method})
    1. Bolt Shear    : {Rc_shear:,.0f} kg (Ratio {V_u/Rc_shear:.2f})
    2. Plate Bearing : {Rc_bear:,.0f} kg (Ratio {V_u/Rc_bear:.2f})
    3. Weld Strength : {Rc_weld:,.0f} kg (Ratio {V_u/Rc_weld:.2f})
    -------------------------------------------
    STATUS: {status}
    """
    
    st.download_button("💾 Download Report", report_text, "calc_report.txt")
