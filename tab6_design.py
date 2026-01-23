import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    # --- HEADER ---
    st.markdown("### 🏗️ Ultimate Connection Studio")
    st.caption(f"Standard: **AISC 360-16 ({method})** | Type: **Single Plate Shear Connection (Shear Tab)**")
    
    # --- 1. GLOBAL LOAD & BEAM SELECTION ---
    with st.expander("🔹 1. Beam & Load Analysis (วิเคราะห์แรงจากคาน)", expanded=True):
        col_b1, col_b2, col_b3 = st.columns([1.5, 1, 1])
        with col_b1:
            section_name = st.selectbox("Select Beam Section:", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
            w_sw = props['W']
        
        # Auto-calc Reference
        c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
        L_vm = c_ref['L_vm']
        w_max_cap = (2 * c_ref['V_des'] / (L_vm * 100)) * 100 if L_vm > 0 else 0
        w_design_rec = 0.75 * max(0, w_max_cap - w_sw)

        with col_b2:
            span = st.number_input("Span Length (m)", value=6.0, step=0.5)
        with col_b3:
            load = st.number_input("Superimposed Load (kg/m)", value=float(int(w_design_rec)), step=100.0)
            
        # Analysis
        w_total = load + w_sw
        V_u = (w_total * span) / 2
        
        # Beam Capacity Check
        c_chk = core_calculation(span, Fy, E_gpa, props, method, def_limit)
        beam_ratio = V_u / c_chk['V_des']
        
        # Status Bar for Beam
        st.markdown("---")
        c_res1, c_res2, c_res3 = st.columns(3)
        c_res1.metric("Reaction Force (Vu)", f"{V_u:,.0f} kg", help="แรงเฉือนที่จุดต่อต้องรับ")
        c_res2.metric("Beam Shear Cap.", f"{c_chk['V_des']:,.0f} kg", delta_color="inverse", 
                      delta="PASS" if beam_ratio <= 1 else "FAIL")
        c_res3.metric("Utilization", f"{beam_ratio*100:.1f} %")

    # ==============================================================================
    # 🔩 2. CONNECTION DESIGN STUDIO
    # ==============================================================================
    st.subheader("2. 🔩 Connection Detailing")
    
    col_ui, col_viz = st.columns([1, 1.8])
    
    # --- LEFT COLUMN: INPUTS ---
    with col_ui:
        st.info("🛠️ **Configuration**")
        
        # A. Bolt Settings
        st.markdown("**Bolt Spec**")
        bolt_grade = st.selectbox("Grade", ["A325N", "A307"], index=0)
        bolt_size = st.selectbox("Size", ["M12", "M16", "M20", "M22", "M24", "M30"], index=2)
        n_rows = st.slider("Rows", 2, 8, 3)
        
        # B. Plate Settings
        st.markdown("**Plate Spec (SS400)**")
        plate_t_mm = st.selectbox("Thickness (mm)", [6, 9, 12, 16, 19, 25], index=1)
        weld_size = st.selectbox("Weld Leg (mm)", [4, 5, 6, 8, 10, 12], index=1)
        
        # C. Geometry (Smart Defaults)
        st.markdown("**Geometry (mm)**")
        d_b_mm = float(bolt_size.replace("M",""))
        
        # Validate Inputs
        min_pitch = int(2.66 * d_b_mm)
        rec_pitch = int(3 * d_b_mm)
        pitch = st.number_input("Pitch (s)", value=rec_pitch, min_value=min_pitch, step=5, help="ระยะห่างระหว่างน็อต")
        
        min_le = int(d_b_mm + 5) # Rough approx for table J3.4
        lev = st.number_input("V-Edge (Lev)", value=int(1.5*d_b_mm), min_value=min_le, step=5, help="ระยะขอบแนวตั้ง")
        leh = st.number_input("H-Edge (Leh)", value=40, min_value=30, step=5, help="ระยะจากรูเจาะถึงแนวเชื่อม")

    # --- CALCULATION ENGINE ---
    # Conversions
    d_b = d_b_mm / 10; h_hole = (d_b_mm + 2)/10
    tp = plate_t_mm / 10; tw = props.get('tw', props.get('t1', 0.6)) / 10
    Fy_pl = 2500; Fu_pl = 4100; E70 = 4900
    
    # Dimensions
    plate_h_mm = (2 * lev) + ((n_rows - 1) * pitch)
    plate_h = plate_h_mm / 10
    plate_w_mm = leh + 15 # Gap 15mm
    
    # Safety Factors (ASD/LRFD)
    if method == "ASD":
        Om = 2.00; Om_y = 1.50
        def get_design(Rn, type="normal"): return Rn/Om_y if type=="yield" else Rn/Om
    else:
        Ph = 0.75; Ph_y = 1.00
        def get_design(Rn, type="normal"): return Ph_y*Rn if type=="yield" else Ph*Rn

    # 1. Bolt Shear
    Ab = (np.pi * d_b**2)/4
    Fnv = 3720 if "A325" in bolt_grade else 1880
    Rc_shear = get_design(n_rows * Fnv * Ab)
    
    # 2. Bearing (Tearout)
    Lc_edge = (lev/10) - (h_hole/2)
    Lc_inner = (pitch/10) - h_hole
    Rn_bear_edge = min(1.2*Lc_edge*tp*Fu_pl, 2.4*d_b*tp*Fu_pl)
    Rn_bear_inner = min(1.2*Lc_inner*tp*Fu_pl, 2.4*d_b*tp*Fu_pl) * (n_rows-1)
    Rc_bearing = get_design(Rn_bear_edge + Rn_bear_inner)
    
    # 3. Plate Checks
    Agv = plate_h * tp
    Anv = (plate_h - (n_rows * h_hole)) * tp
    Rc_yield = get_design(0.6 * Fy_pl * Agv, "yield")
    Rc_rupture = get_design(0.6 * Fu_pl * Anv)
    
    # 4. Block Shear
    Ant = ((leh/10) - (h_hole/2)) * tp
    # Assume L-shape tearout pattern (Standard Shear Tab)
    # Tension area is horizontal to edge
    R_block_1 = (0.6*Fu_pl*Anv) + (1.0*Fu_pl*Ant)
    R_block_2 = (0.6*Fy_pl*Agv) + (1.0*Fu_pl*Ant)
    Rc_block = get_design(min(R_block_1, R_block_2))
    
    # 5. Weld (Double Fillet)
    Rn_weld = 0.707 * (weld_size/10) * (0.6*E70) * 2 * plate_h
    Rc_weld = get_design(Rn_weld)
    
    # --- SUMMARY ---
    checks = {
        "Bolt Shear": Rc_shear, "Bearing": Rc_bearing, 
        "Plate Yield": Rc_yield, "Plate Rupture": Rc_rupture,
        "Block Shear": Rc_block, "Weld Strength": Rc_weld
    }
    max_util = 0
    ctrl_mode = ""
    
    # --- RIGHT COLUMN: VISUALIZATION & DASHBOARD ---
    with col_viz:
        # --- TAB INTERFACE ---
        tab_draw, tab_detail = st.tabs(["📐 CAD Drawing", "📋 Engineering Report"])
        
        with tab_draw:
            # 1. Create Plotly Figure
            fig = go.Figure()

            # Colors
            steel_color = '#E5E7EB' # Light Gray
            plate_color = '#93C5FD' # Light Blue
            bolt_color = '#1E3A8A'  # Dark Blue
            
            # Draw Beam Web (Background)
            fig.add_shape(type="rect",
                x0=-50, y0=-20, x1=plate_w_mm+50, y1=plate_h_mm+50,
                fillcolor="#f0f2f6", line=dict(color="white"), layer="below"
            )
            
            # Draw Connection Plate
            # Origin (0,0) is at the weld line bottom
            fig.add_shape(type="rect",
                x0=0, y0=0, x1=leh+15, y1=plate_h_mm,
                fillcolor=plate_color, line=dict(color="black", width=2),
                opacity=0.8
            )
            
            # Draw Weld (Zigzag Approx)
            weld_y = np.linspace(0, plate_h_mm, 20)
            weld_x = np.sin(weld_y * 0.5) * 2
            fig.add_trace(go.Scatter(x=weld_x, y=weld_y, mode='lines', 
                                     line=dict(color='red', width=3), name='Fillet Weld'))

            # Draw Bolts
            bolt_x_coords = []
            bolt_y_coords = []
            
            bx = leh # X pos of bolt line
            for i in range(n_rows):
                by = lev + (i * pitch)
                bolt_x_coords.append(bx)
                bolt_y_coords.append(by)
                
                # Bolt Circle
                fig.add_shape(type="circle",
                    x0=bx-(d_b_mm/2), y0=by-(d_b_mm/2),
                    x1=bx+(d_b_mm/2), y1=by+(d_b_mm/2),
                    fillcolor=bolt_color, line_color="black"
                )
                
                # Crosshair
                fig.add_trace(go.Scatter(
                    x=[bx-3, bx+3, None, bx, bx], 
                    y=[by, by, None, by-3, by+3],
                    mode='lines', line=dict(color='white', width=1), showlegend=False
                ))

            # Add Dimensions (Annotations)
            # Pitch
            if n_rows > 1:
                fig.add_annotation(x=bx+10, y=lev + pitch/2, text=f"s={pitch}", showarrow=False, font=dict(color="blue", size=10))
            
            # Plate Size
            fig.add_annotation(x=leh/2, y=plate_h_mm+10, text=f"PL-{plate_t_mm}x{int(plate_w_mm)}x{int(plate_h_mm)}", showarrow=False, font=dict(size=12, color="black"))

            # Layout Settings
            fig.update_layout(
                title=dict(text="Real-scale Connection Detail", font=dict(size=14)),
                xaxis=dict(range=[-20, leh+40], showgrid=False, zeroline=False, visible=False),
                yaxis=dict(range=[-20, plate_h_mm+30], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
                height=450,
                margin=dict(l=10, r=10, t=40, b=10),
                plot_bgcolor="white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- FABRICATION CHECKS ---
            st.markdown("##### 👷 Fabrication Checks")
            fc1, fc2, fc3 = st.columns(3)
            
            # Check 1: Wrench Clearance (Approx 2d)
            clearance = pitch - d_b_mm
            req_clearance = 2.0 * d_b_mm # Approximate for impact wrench
            if pitch >= 3*d_b_mm: fc1.success("✅ Pitch OK")
            else: fc1.warning(f"⚠️ Tight Pitch ({pitch}mm)")
            
            # Check 2: Edge Distance
            if lev >= d_b_mm * 1.5: fc2.success("✅ V-Edge OK")
            else: fc2.error("❌ Edge Risk")
            
            # Check 3: Weld vs Web
            if weld_size <= tw*10: fc3.success("✅ Weld OK")
            else: fc3.warning(f"⚠️ Large Weld ({weld_size}mm > Tw)")

        # --- TAB: REPORT ---
        with tab_detail:
            # Result Table Construction
            res_data = []
            for k, cap in checks.items():
                ratio = V_u / cap
                status = "✅ PASS" if ratio <= 1.0 else "❌ FAIL"
                res_data.append([k, f"{cap:,.0f}", f"{ratio:.2f}", status])
                if ratio > max_util:
                    max_util = ratio
                    ctrl_mode = k
            
            df_res = pd.DataFrame(res_data, columns=["Check", "Capacity (kg)", "Ratio", "Status"])
            
            # GAUGE CHART (Overall Status)
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = max_util * 100,
                title = {'text': f"Max Utilization ({ctrl_mode})"},
                gauge = {
                    'axis': {'range': [0, 150]},
                    'bar': {'color': "red" if max_util > 1 else "green"},
                    'steps': [
                        {'range': [0, 80], 'color': "#dcfce7"},
                        {'range': [80, 100], 'color': "#fef9c3"},
                        {'range': [100, 150], 'color': "#fee2e2"}],
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Data Table
            st.dataframe(df_res.style.applymap(
                lambda v: 'color: red; font-weight: bold;' if "FAIL" in str(v) or (isinstance(v,float) and v>1) else None
            ), use_container_width=True)
            
            if max_util > 1.0:
                st.error(f"❌ **DESIGN FAILED** controlled by **{ctrl_mode}**")
                st.markdown("**Suggestions:**")
                if "Shear" in ctrl_mode: st.write("- Increase Bolt Diameter or Grade")
                if "Bearing" in ctrl_mode: st.write("- Increase Plate Thickness")
                if "Block" in ctrl_mode: st.write("- Increase Pitch or Edge Distance (Leh)")
                if "Weld" in ctrl_mode: st.write("- Increase Weld Size or Plate Height")
            else:
                st.success("✅ **DESIGN PASSED** - Safe to Construct")
