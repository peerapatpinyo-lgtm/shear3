import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# --- HELPER: GEOMETRY ENGINE ---
def create_cylinder_mesh(p1, p2, r, color, sides=16):
    """สร้าง Mesh ทรงกระบอกสมจริง (เชื่อมระหว่างจุด p1 และ p2)"""
    v = p2 - p1
    h = np.linalg.norm(v)
    if h == 0: return go.Mesh3d()
    v = v / h # Unit vector
    
    # สร้าง Basis vectors
    not_v = np.array([1, 0, 0])
    if np.abs(np.dot(v, not_v)) > 0.9: not_v = np.array([0, 1, 0])
    n1 = np.cross(v, not_v)
    n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    # Generate points
    theta = np.linspace(0, 2*np.pi, sides+1)[:-1]
    x_circle = r * np.cos(theta)
    y_circle = r * np.sin(theta)
    
    # Vertices
    vertices = []
    # Bottom circle
    for x, y in zip(x_circle, y_circle):
        pos = p1 + x*n1 + y*n2
        vertices.append(pos)
    # Top circle
    for x, y in zip(x_circle, y_circle):
        pos = p2 + x*n1 + y*n2
        vertices.append(pos)
    
    vertices = np.array(vertices)
    
    # Triangles (Indices)
    i_list, j_list, k_list = [], [], []
    n = sides
    for idx in range(n):
        next_idx = (idx + 1) % n
        # Side 1
        i_list.extend([idx, next_idx, idx + n])
        j_list.extend([next_idx, next_idx + n, next_idx + n])
        k_list.extend([idx + n, idx + n, idx])
        
        # End caps (simple fan)
        # (ละไว้เพื่อ performance เน้นผิวข้าง)

    return go.Mesh3d(
        x=vertices[:,0], y=vertices[:,1], z=vertices[:,2],
        i=i_list, j=j_list, k=k_list,
        color=color, opacity=1.0, flatshading=False, name='Bolt'
    )

def create_hex_head(center, direction, r, thickness, color):
    """สร้างหัวน็อต 6 เหลี่ยม"""
    p1 = center
    p2 = center + (direction * thickness)
    return create_cylinder_mesh(p1, p2, r, color, sides=6)

def make_box_pro(x, y, z, dx, dy, dz, color, name, opacity=1.0):
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name,
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.5, roughness=0.1) # Metallic feel
    )

# --- MAIN RENDER FUNCTION ---
def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ Ultimate Connection Studio (Pro-CAD)")
    st.caption("Mode: **High-Fidelity 3D** | **Parametric Bolts** | **Interactive Report**")

    # --- 1. INPUTS ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            # Auto Load Logic
            c_ref = core_calculation(6.0, Fy, E_gpa, props, method, def_limit)
            rec_load = 0.75 * max(0, ((2*c_ref['V_des']/(c_ref['L_vm']*100))*100) - props['W'])
            load = st.number_input("Load (kg/m)", value=float(int(rec_load)), step=100.0)
            span = 6.0
        with c3:
            bolt_size = st.selectbox("Bolt Size", ["M16", "M20", "M22", "M24", "M27", "M30"], index=1)
        with c4:
            n_rows = st.number_input("Rows", 2, 10, 3)

        d_b_mm = float(bolt_size.replace("M",""))
        
        st.markdown("**Detailing (mm)**")
        g1, g2, g3, g4, g5 = st.columns(5)
        with g1: plate_t = st.selectbox("Plate T", [6, 9, 12, 16, 19, 25], index=2)
        with g2: weld_size = st.selectbox("Weld Leg", [4, 6, 8, 10, 12], index=1)
        with g3: pitch = st.number_input("Pitch", value=int(3*d_b_mm), step=5)
        with g4: lev = st.number_input("V-Edge", value=int(1.5*d_b_mm), step=5)
        with g5: leh = st.number_input("H-Edge", value=45, step=5)

    # --- 2. CALCULATION ---
    V_u = ((load + props['W']) * span) / 2
    d_b = d_b_mm/10; tp = plate_t/10; plate_h = ((2*lev) + (n_rows-1)*pitch)/10
    phi = 0.75 if method == "LRFD" else 0.5
    
    # 1. Shear
    Rn_shear = n_rows * (3720 * np.pi * d_b**2 / 4)
    Rc_shear = Rn_shear * phi
    # 2. Bearing
    Rn_bear = n_rows * 2.4 * d_b * tp * 4100
    Rc_bear = Rn_bear * phi
    # 3. Weld
    Rn_weld = 0.707 * (weld_size/10) * (0.6 * 4900) * (2 * plate_h)
    Rc_weld = Rn_weld * phi
    
    limit_state = min(Rc_shear, Rc_bear, Rc_weld)
    util_ratio = V_u / limit_state if limit_state > 0 else 999.0

    # --- 3. PRO-CAD VISUALIZATION ---
    st.subheader("1. 🧊 High-Fidelity Model")
    col_viz, col_info = st.columns([3, 1])
    
    with col_viz:
        fig = go.Figure()
        
        # Dimensions for drawing
        H = props['D'] * 10
        B = props['B'] * 10
        Tw = props.get('tw', 6.0)
        Tf = props.get('tf', 9.0)
        L_beam = 350
        
        # Materials (Colors)
        c_beam = '#bdc3c7'   # Silver
        c_plate = '#3498db'  # Structural Blue
        c_bolt = '#2c3e50'   # Dark Steel
        c_head = '#7f8c8d'   # Hex Head Color
        
        # A. Beam (Ghost Mode: Opacity 0.8 to see through)
        web_h = H - (2 * Tf)
        fig.add_trace(make_box_pro(0, 0, 0, Tw, L_beam, web_h, c_beam, "Web", 0.7)) # Transparent Web
        fig.add_trace(make_box_pro(0, 0, (web_h/2)+(Tf/2), B, L_beam, Tf, c_beam, "Top Flange", 0.8))
        fig.add_trace(make_box_pro(0, 0, -(web_h/2)-(Tf/2), B, L_beam, Tf, c_beam, "Bot Flange", 0.8))
        
        # B. Shear Plate
        pl_x = (Tw/2) + (plate_t/2)
        pl_y = -(L_beam/2) + leh + 20 
        pl_h_mm = (2*lev) + ((n_rows-1)*pitch)
        fig.add_trace(make_box_pro(pl_x, pl_y, 0, plate_t, leh+20, pl_h_mm, c_plate, "Plate", 1.0))
        
        # C. REALISTIC BOLTS (Cylinders + Hex Heads)
        bolt_len = Tw + plate_t + 20
        shank_r = d_b_mm / 2
        head_r = d_b_mm * 0.8 # Approx hex radius
        head_thick = d_b_mm * 0.6
        
        # Bolt Y Position
        bolt_y = pl_y + (leh/2) - 10
        # Bolt X Range
        bx_start = -(bolt_len/2) + (plate_t/2) 
        bx_end = (bolt_len/2) + (plate_t/2)
        
        z_start = (pl_h_mm/2) - lev
        
        for i in range(n_rows):
            bz = z_start - (i*pitch)
            
            # 1. Shank (Cylinder)
            p1 = np.array([bx_start, bolt_y, bz])
            p2 = np.array([bx_end, bolt_y, bz])
            fig.add_trace(create_cylinder_mesh(p1, p2, shank_r, c_bolt))
            
            # 2. Head (Hexagon) - Front
            dir_vec = np.array([1, 0, 0])
            fig.add_trace(create_hex_head(p2, dir_vec, head_r, head_thick, c_head))
            
            # 3. Nut (Hexagon) - Back
            fig.add_trace(create_hex_head(p1, -dir_vec, head_r, head_thick, c_head))

        # Scene Setup
        fig.update_layout(
            scene=dict(
                aspectmode='data',
                xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                bgcolor='white',
                camera=dict(eye=dict(x=1.5, y=0.8, z=0.8), up=dict(x=0, y=0, z=1)),
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.markdown(f"### Status: {'✅ PASS' if util_ratio <=1 else '❌ FAIL'}")
        
        # Gauge Chart
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = util_ratio*100,
            title = {'text': "Load Ratio (%)"},
            gauge = {'axis': {'range': [0, 120]}, 
                     'bar': {'color': "green" if util_ratio<=1 else "red"},
                     'steps': [{'range': [0, 80], 'color': "#ecf0f1"}]}
        ))
        fig_g.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=0))
        st.plotly_chart(fig_g, use_container_width=True)
        
        # Cost
        weight = (plate_t * (leh+20) * pl_h_mm * 7.85 / 1000000) + (n_rows * 0.2)
        cost = weight * 45 # 45 THB/kg combined
        st.metric("Est. Weight", f"{weight:.2f} kg")
        st.metric("Est. Cost", f"฿ {cost:.0f}")

    # --- 4. REPORT (Fixed LaTeX) ---
    st.subheader("2. 📝 Engineering Report")
    with st.expander("Show Calculation Details", expanded=True):
        st.markdown("---")
        c_r1, c_r2 = st.columns([3, 1])
        c_r1.markdown(f"**Section:** {section_name} | **Load:** {V_u:,.0f} kg")
        
        st.markdown("#### Checks:")
        
        # Helper for safe latex
        def latex_check(name, Rn, Rc, Vu):
            status = "OK" if Vu <= Rc else "FAIL"
            color = "green" if status == "OK" else "red"
            st.markdown(f"**{name}:**")
            st.latex(f"\\phi R_n = {phi} \\cdot {Rn:,.0f} = \\mathbf{{{Rc:,.0f}}} \\text{{ kg}}")
            st.markdown(f"Result: :{color}[{status}] (Ratio: {Vu/Rc:.2f})")
        
        latex_check("Bolt Shear", Rn_shear, Rc_shear, V_u)
        latex_check("Plate Bearing", Rn_bear, Rc_bear, V_u)
        latex_check("Weld Strength", Rn_weld, Rc_weld, V_u)
