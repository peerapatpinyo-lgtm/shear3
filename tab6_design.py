import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ Connection Design Studio (Tekla-Lite)")
    st.caption("Standard: **AISC 360-16** | Features: **True-Shape 3D**, **Clash Detection**, **Mathcad-Style Calc**")

    # --- 1. GLOBAL PARAMETERS ---
    with st.expander("🎛️ Design Configuration", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2: # Auto Load Logic
            c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
            rec_load = 0.75 * max(0, ((2*c_ref['V_des']/(c_ref['L_vm']*100))*100) - props['W'])
            load = st.number_input("Design Load (kg/m)", value=float(int(rec_load)), step=100.0)
            span = 6.0 # Fixed span for simpler UI
        with c3:
            bolt_size = st.selectbox("Bolt Size", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = "A325"
        with c4:
            n_rows = st.number_input("Bolt Rows", 2, 8, 3)

        # Detailed Geometry
        d_b_mm = float(bolt_size.replace("M",""))
        st.markdown("**Plate & Layout (mm)**")
        g1, g2, g3, g4, g5 = st.columns(5)
        with g1: plate_t = st.selectbox("Plate T", [6, 9, 12, 16, 19, 25], index=2)
        with g2: weld_size = st.selectbox("Weld Leg", [4, 6, 8, 10], index=1)
        with g3: pitch = st.number_input("Pitch (s)", value=int(3*d_b_mm), step=5)
        with g4: lev = st.number_input("V-Edge (Lev)", value=int(1.5*d_b_mm), step=5)
        with g5: leh = st.number_input("H-Edge (Leh)", value=40, step=5)

    # --- 2. CALCULATIONS (BACKEND) ---
    # Forces
    V_u = ((load + props['W']) * span) / 2
    
    # Geometry Conversions
    d_b = d_b_mm/10; tp = plate_t/10; 
    plate_h_mm = (2*lev) + (n_rows-1)*pitch
    plate_h = plate_h_mm / 10
    
    # AISC Capacities
    phi = 0.75 if method == "LRFD" else 0.5
    
    # 1. Bolt Shear
    Ab = np.pi * d_b**2 / 4
    Fnv = 3720 # A325
    Rn_shear = n_rows * Fnv * Ab
    Rc_shear = Rn_shear * phi
    
    # 2. Bearing (Simplified conservative)
    Rn_bear = n_rows * 2.4 * d_b * tp * 4100
    Rc_bear = Rn_bear * phi
    
    # 3. Weld
    Rn_weld = 0.707 * (weld_size/10) * (0.6 * 4900) * (2 * plate_h)
    Rc_weld = Rn_weld * phi
    
    # Check
    limit_state = min(Rc_shear, Rc_bear, Rc_weld)
    util_ratio = V_u / limit_state
    
    # --- 3. 3D VISUALIZATION ENGINE ---
    st.subheader("1. 🧊 True-Shape 3D Model")
    
    col_viz, col_clash = st.columns([3, 1])
    
    with col_viz:
        # Helper to draw a box
        def make_prism(x, y, z, dx, dy, dz, color, name):
            return go.Mesh3d(
                x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
                y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
                z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
                j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
                k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color=color, opacity=1.0, flatshading=True, name=name
            )

        fig = go.Figure()
        
        # --- A. BEAM GEOMETRY (Constructing the 'I' Shape) ---
        H = props['D'] * 10
        B = props['B'] * 10
        Tw = props.get('tw', 6.0)
        Tf = props.get('tf', 9.0)
        L_beam = 400 # Length to show
        
        # Color Palette (Tekla Style)
        c_steel = '#95a5a6' # Concrete/Steel Gray
        c_plate = '#f1c40f' # Yellow Plate (Highlight)
        c_bolt = '#e74c3c'  # Red Bolts
        c_weld = '#e67e22'  # Orange Weld
        
        # 1. Web
        web_h = H - (2 * Tf)
        fig.add_trace(make_prism(0, 0, 0, Tw, L_beam, web_h, c_steel, "Beam Web"))
        
        # 2. Top Flange
        fig.add_trace(make_prism(0, 0, (web_h/2)+(Tf/2), B, L_beam, Tf, c_steel, "Top Flange"))
        
        # 3. Bottom Flange
        fig.add_trace(make_prism(0, 0, -(web_h/2)-(Tf/2), B, L_beam, Tf, c_steel, "Bot Flange"))
        
        # --- B. CONNECTION PLATE ---
        # Position: Attached to Web surface (x = Tw/2 + Tp/2)
        # Vertical: Centered to beam (simplified) or specific? Let's center it.
        pl_x = (Tw/2) + (plate_t/2)
        pl_y = -(L_beam/2) + (leh) + 20 # Offset from beam end
        # Plate dimensions
        fig.add_trace(make_prism(pl_x, pl_y, 0, plate_t, leh+20, plate_h_mm, c_plate, "Shear Plate"))
        
        # --- C. WELD (Triangular Prisms approximated as thin boxes) ---
        weld_x = (Tw/2) + (weld_size/2) 
        weld_y = pl_y - ((leh+20)/2) # At the back of plate
        # fig.add_trace(make_prism(weld_x, weld_y, 0, weld_size, weld_size, plate_h_mm, c_weld, "Weld"))
        
        # --- D. BOLTS ---
        bolt_len = Tw + plate_t + 25
        bolt_x = 0 + (plate_t/2) # Centered on interface
        bolt_y = pl_y + (leh/2) - (10) # Roughly at hole position
        
        # Start Z for bolts
        z_start = (plate_h_mm/2) - lev
        
        for i in range(n_rows):
            bz = z_start - (i*pitch)
            # Bolt Shank
            fig.add_trace(go.Scatter3d(
                x=[-bolt_len/2, bolt_len/2], y=[bolt_y, bolt_y], z=[bz, bz],
                mode='lines', line=dict(color=c_bolt, width=12), name='Bolt'
            ))
            # Bolt Head (Hex approx)
            fig.add_trace(go.Scatter3d(
                x=[bolt_len/2], y=[bolt_y], z=[bz],
                mode='markers', marker=dict(size=10, color='black', symbol='diamond'), showlegend=False
            ))

        # Camera & Layout
        fig.update_layout(
            scene=dict(
                aspectmode='data',
                xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                camera=dict(eye=dict(x=2.0, y=0.5, z=0.5))
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_clash:
        st.markdown("##### ⚠️ Geometry Checks")
        
        # k-Distance Check (Fillet Clash)
        # H-Beams have a fillet radius (r) between web and flange.
        # k = Tf + r. We must ensure Plate Height < (H - 2k)
        
        # Estimate k (approx Tf + 10mm for small beams, +15 for large)
        k_approx = props.get('tf', 10) + 12 
        clear_web = (props['D']*10) - (2*k_approx)
        
        st.metric("Web Clear Height", f"{clear_web:.0f} mm", help="พื้นที่เรียบของเอวคาน (ไม่ชนส่วนโค้ง)")
        st.metric("Plate Height", f"{plate_h_mm:.0f} mm")
        
        if plate_h_mm > clear_web:
            st.error("🚨 **CLASH DETECTED!**")
            st.caption("แผ่นเพลทสูงเกินไป ชนส่วนโค้ง (Fillet) ของคาน")
        else:
            st.success("✅ Geometry OK")
            st.caption("เพลทติดตั้งได้ ไม่ชน Fillet")
            
        st.markdown("---")
        # Entering Clearance
        clr = pitch - d_b_mm
        st.metric("Wrench Clearance", f"{clr:.1f} mm")
        if clr < d_b_mm: st.warning("⚠️ ขันน็อตยาก")

    # --- 4. MATHCAD-STYLE REPORT ---
    st.subheader("2. 📝 Calculation Note (Transparent Math)")
    st.markdown("แสดงรายการคำนวณแบบละเอียด พร้อมแทนค่าตัวเลขจริง")

    with st.container():
        # HTML/Latex Formatting
        st.markdown("---")
        
        # Header
        c_r1, c_r2 = st.columns([3, 1])
        c_r1.markdown(f"**PROJECT:** Connection Design Check for {section_name}")
        c_r2.markdown(f"**RATIO:** `{util_ratio:.2f}`")
        
        # 1. SHEAR CHECK
        st.markdown("#### 1. Bolt Shear Strength (AISC J3.6)")
        st.latex(r"R_n = F_{nv} A_b N_{rows}")
        st.markdown(f"Substitute values:")
        st.latex(f"R_n = {Fnv} \\cdot ({d_b:.2f}^2 \\pi / 4) \\cdot {n_rows}")
        st.latex(f"R_n = {Rn_shear:,.0f} \\text{ kg}")
        st.latex(f"\\phi R_n = {phi} \\cdot {Rn_shear:,.0f} = \\mathbf{{{Rc_shear:,.0f}}} \\text{ kg}")
        
        if V_u > Rc_shear: st.error(f"❌ FAIL: Demand {V_u:,.0f} > Capacity {Rc_shear:,.0f}")
        else: st.success(f"✅ PASS: Demand {V_u:,.0f} <= Capacity {Rc_shear:,.0f}")
        
        st.markdown("---")
        
        # 2. BEARING CHECK
        st.markdown("#### 2. Plate Bearing Strength (AISC J3.10)")
        st.latex(r"R_n = 2.4 d t F_u N_{rows}")
        st.markdown(f"Substitute values ($F_u=4100$ ksc):")
        st.latex(f"R_n = 2.4 \\cdot {d_b} \\cdot {tp} \\cdot 4100 \\cdot {n_rows}")
        st.latex(f"R_n = {Rn_bear:,.0f} \\text{ kg}")
        st.latex(f"\\phi R_n = {phi} \\cdot {Rn_bear:,.0f} = \\mathbf{{{Rc_bear:,.0f}}} \\text{ kg}")

        if V_u > Rc_bear: st.error(f"❌ FAIL: Demand {V_u:,.0f} > Capacity {Rc_bear:,.0f}")
        else: st.success(f"✅ PASS: Demand {V_u:,.0f} <= Capacity {Rc_bear:,.0f}")

        st.markdown("---")

        # 3. WELD CHECK
        st.markdown("#### 3. Weld Strength (AISC J2.4)")
        st.latex(r"R_n = 0.707 w (0.6 F_{EXX}) L_{weld}")
        st.markdown(f"Substitute values (E70XX = 4900 ksc, 2 sides):")
        st.latex(f"R_n = 0.707 \\cdot {weld_size/10} \\cdot (0.6 \\cdot 4900) \\cdot (2 \\cdot {plate_h:.2f})")
        st.latex(f"R_n = {Rn_weld:,.0f} \\text{ kg}")
        st.latex(f"\\phi R_n = {phi} \\cdot {Rn_weld:,.0f} = \\mathbf{{{Rc_weld:,.0f}}} \\text{ kg}")
