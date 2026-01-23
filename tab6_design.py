import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# ==========================================
# 🔧 3D GEOMETRY ENGINE (High-Fidelity)
# ==========================================

def create_cylinder(p1, p2, r, color, opacity=1.0):
    """สร้าง Mesh ทรงกระบอก (ก้านน็อต)"""
    v = p2 - p1
    mag = np.linalg.norm(v)
    if mag == 0: return go.Mesh3d()
    v = v / mag
    
    not_v = np.array([1, 0, 0])
    if np.abs(np.dot(v, not_v)) > 0.9: not_v = np.array([0, 1, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    theta = np.linspace(0, 2*np.pi, 20)
    x_circ = r * np.cos(theta)
    y_circ = r * np.sin(theta)
    
    verts = []
    for x, y in zip(x_circ, y_circ): verts.append(p1 + x*n1 + y*n2)
    for x, y in zip(x_circ, y_circ): verts.append(p2 + x*n1 + y*n2)
    verts = np.array(verts)
    
    n = 20
    i, j, k = [], [], []
    for idx in range(n):
        nxt = (idx + 1) % n
        i.extend([idx, nxt, idx+n]); j.extend([nxt, nxt+n, nxt+n]); k.extend([idx+n, idx+n, idx])
        i.extend([idx, idx+n, nxt]); j.extend([nxt, idx, nxt]); k.extend([idx+n, idx, idx]) # Double side

    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], i=i, j=j, k=k, color=color, opacity=opacity, flatshading=False, name='Bolt')

def create_hex(center, normal, r, thick, color):
    """สร้างหัวน็อต 6 เหลี่ยม"""
    p1 = center
    p2 = center + (normal * thick)
    return create_cylinder(p1, p2, r, color, opacity=1.0) # Simplified as cylinder for perf, or could implement hex

def make_box(x, y, z, dx, dy, dz, color, opacity=1.0, name="Part"):
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name,
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2)
    )

def add_dim_line(fig, p1, p2, label, color="black", offset=0):
    """ฟังก์ชันวาดเส้น Dimension ใน 3D"""
    mid = (p1 + p2) / 2
    # Draw Line
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2], p2[2]],
        mode='lines+text', line=dict(color=color, width=3, dash='solid'),
        text=[None, None], showlegend=False
    ))
    # Draw End Ticks (Simple dots for now)
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2], p2[2]],
        mode='markers', marker=dict(size=3, color=color), showlegend=False
    ))
    # Draw Label
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2] + offset],
        mode='text', text=[f"<b>{label}</b>"],
        textposition="top center", textfont=dict(size=12, color=color), showlegend=False
    ))

# ==========================================
# 🚀 MAIN APP RENDERER
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ 3D Shop Drawing & Design")
    st.caption("Mode: **Real-Scale 1:1** | **Auto-Dimensioning** | **Fabrication Check**")

    # --- 1. PARAMETERS ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            section_name = st.selectbox("Beam Size", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("Rows", 2, 8, 3)
        with c3:
            # Smart Default Geometry
            d_b_mm = float(bolt_size.replace("M",""))
            plate_t = st.selectbox("Plate T (mm)", [6, 9, 12, 16, 19, 25], index=2)
            
            c3a, c3b, c3c = st.columns(3)
            pitch = c3a.number_input("Pitch", value=int(3*d_b_mm), step=5)
            lev = c3b.number_input("V-Edge", value=int(1.5*d_b_mm), step=5)
            leh = c3c.number_input("H-Edge", value=40, step=5)

            weld_size = 6 # Default weld

    # --- 2. PREPARE GEOMETRY (Unit: mm) ---
    # Convert DB properties (assuming DB stores D, B in cm, t in mm)
    H_beam = props['D'] * 10
    B_beam = props['B'] * 10
    Tw = props.get('tw', props.get('t1', 6.0))
    Tf = props.get('tf', props.get('t2', 9.0))
    
    # Plate Calc
    plate_h = (2 * lev) + ((n_rows - 1) * pitch)
    plate_w = leh + 20 # Clearance from beam end
    
    # --- 3. 3D VISUALIZATION ---
    st.subheader("1. 🧊 3D Model with Dimensions")
    
    col_viz, col_info = st.columns([3, 1])
    
    with col_viz:
        fig = go.Figure()
        
        # --- A. DRAW BEAM (Ghost View) ---
        L_show = 400 # Length to display
        # Web
        fig.add_trace(make_box(0, 0, 0, Tw, L_show, H_beam - 2*Tf, '#95a5a6', 0.3, "Web"))
        # Top Flange
        fig.add_trace(make_box(0, 0, (H_beam/2)-(Tf/2), B_beam, L_show, Tf, '#7f8c8d', 0.4, "Top Flange"))
        # Bot Flange
        fig.add_trace(make_box(0, 0, -(H_beam/2)+(Tf/2), B_beam, L_show, Tf, '#7f8c8d', 0.4, "Bot Flange"))

        # --- B. DRAW PLATE (Solid) ---
        # Position: Attached to Web face (x = Tw/2 + Tp/2)
        pl_x = (Tw/2) + (plate_t/2)
        pl_y = -(L_show/2) + plate_w # Offset from cut end
        fig.add_trace(make_box(pl_x, pl_y, 0, plate_t, plate_w, plate_h, '#f1c40f', 1.0, "Shear Plate"))

        # --- C. DRAW BOLTS ---
        bolt_len = Tw + plate_t + 30
        bx = pl_x - (plate_t/2) + (plate_t/2) # Centered? actually goes through both
        bx_start = -(bolt_len/2) + (Tw/2) # Through web
        bx_end = bx_start + bolt_len
        
        by = pl_y - (plate_w/2) + leh # Hole position from back of plate
        
        z_top_bolt = (plate_h/2) - lev
        
        for i in range(n_rows):
            bz = z_top_bolt - (i * pitch)
            # Bolt Shank
            fig.add_trace(create_cylinder(np.array([bx_start, by, bz]), np.array([bx_end, by, bz]), d_b_mm/2, '#e74c3c'))
            # Heads (Hex)
            fig.add_trace(create_hex(np.array([bx_end, by, bz]), np.array([1,0,0]), d_b_mm*0.8, d_b_mm*0.6, '#2c3e50'))
            fig.add_trace(create_hex(np.array([bx_start, by, bz]), np.array([-1,0,0]), d_b_mm*0.8, d_b_mm*0.6, '#2c3e50'))

        # --- D. **DIMENSION LINES (The Magic)** ---
        # 1. Plate Height Dimension (Side)
        dim_x = pl_x + 50 # Pull out to side
        dim_y = pl_y
        p_top = np.array([dim_x, dim_y, plate_h/2])
        p_bot = np.array([dim_x, dim_y, -plate_h/2])
        add_dim_line(fig, p_top, p_bot, f"PL H={plate_h:.0f}", "blue")

        # 2. Pitch Dimensions
        if n_rows > 1:
            dim_x_p = pl_x + 50
            dim_y_p = by
            # Draw from first to second bolt
            p_b1 = np.array([dim_x_p, dim_y_p, z_top_bolt])
            p_b2 = np.array([dim_x_p, dim_y_p, z_top_bolt - pitch])
            add_dim_line(fig, p_b1, p_b2, f"Pitch={pitch}", "red")

        # 3. Beam Depth (Overall)
        dim_x_d = -B_beam/2 - 20
        p_d_top = np.array([dim_x_d, 0, H_beam/2])
        p_d_bot = np.array([dim_x_d, 0, -H_beam/2])
        add_dim_line(fig, p_d_top, p_d_bot, f"D={H_beam:.0f}", "black")

        # 4. Horizontal Edge (Leh)
        # From Plate back (weld line) to Bolt
        p_back = np.array([pl_x, pl_y - plate_w/2, plate_h/2 + 20])
        p_hole = np.array([pl_x, by, plate_h/2 + 20])
        add_dim_line(fig, p_back, p_hole, f"Leh={leh}", "green")

        # Setup Camera
        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                aspectmode='data', # 1:1 Scale
                camera=dict(eye=dict(x=2.0, y=1.0, z=0.5))
            ),
            margin=dict(l=0, r=0, t=0, b=0), height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_info:
        st.markdown("### 📋 Specs")
        st.info(f"""
        **Beam:** {section_name}
        - Depth: {H_beam} mm
        - Flange: {B_beam} mm
        
        **Plate:**
        - Size: {plate_w} x {plate_h} mm
        - Thick: {plate_t} mm
        
        **Bolts:**
        - {n_rows} x {bolt_size}
        - Pitch: {pitch} mm
        """)
        
        # Check Geometry
        clr = pitch - d_b_mm
        st.metric("Wrench Clearance", f"{clr:.1f} mm")
        if clr < d_b_mm: st.warning("⚠️ Tight spacing")
        else: st.success("✅ Spacing OK")

    # --- 4. CALCULATION REPORT (Backend) ---
    # (Simplified for display)
    V_u = 10000 # Dummy for Viz focus
    phi = 0.75
    Rn_shear = n_rows * (0.6 * 8250 * np.pi * (d_b_mm/10/2)**2) # Approx
    
    st.markdown("---")
    st.markdown("### 📝 Design Verification")
    st.write(f"Model generated based on actual dimensions of **{section_name}** and user inputs.")
