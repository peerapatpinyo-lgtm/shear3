import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS

# ==========================================
# 📐 GEOMETRY UTILS
# ==========================================

def make_cuboid(center, size, color, name, opacity=1.0):
    x, y, z = center
    dx, dy, dz = size
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.2)
    )

def add_dim_line(fig, p1, p2, text, color="black", offset_z=0):
    mid = (p1 + p2) / 2
    # Line
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+offset_z, p2[2]+offset_z],
        mode='lines+markers', line=dict(color=color, width=4),
        marker=dict(size=4, color=color, symbol='circle'), showlegend=False
    ))
    # Text
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+offset_z+15],
        mode='text', text=[f"<b>{text}</b>"],
        textposition="middle center", textfont=dict(color=color, size=14, family="Arial Black"), showlegend=False
    ))

# ==========================================
# 🏗️ MAIN RENDER
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ 3D Shop Drawing (Pro)")
    
    # --- 1. INPUTS ---
    with st.expander("🎛️ Design Parameters", expanded=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            section_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
            # Unit Check
            d_factor = 10 if props['D'] < 100 else 1
            H_real = props['D'] * d_factor
            B_real = props['B'] * d_factor
            Tw_real = props.get('t1', 6.0)
            Tf_real = props.get('t2', 9.0)
            st.caption(f"Dim: {H_real:.0f}x{B_real:.0f} mm")

        with c2:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("Rows", 2, 8, 3)

        with c3:
            d_b_mm = float(bolt_size.replace("M",""))
            setback = st.slider("Setback (Gap)", 0, 25, 12)
            plate_t = st.selectbox("Plate T", [6, 9, 12, 16, 20], index=2)
            
            pitch = int(3 * d_b_mm)
            lev = int(1.5 * d_b_mm)
            leh_beam = 40 

    # --- 2. GEOMETRY PREP ---
    L_beam_show = 400 
    pl_h = (2 * lev) + ((n_rows - 1) * pitch)
    pl_w_total = setback + leh_beam + 40 
    
    # --- 3. DRAWING ---
    fig = go.Figure()

    # --- A. REFERENCE PLANE (GHOST COLUMN) - EXTENDED! ---
    col_face_y = -setback
    # ปรับขนาดตรงนี้: กว้าง 2.5 เท่า / สูง 3.0 เท่า ของคาน
    col_width = B_real * 2.5
    col_height = H_real * 3.0
    
    fig.add_trace(make_cuboid(
        center=[0, col_face_y - 10, 0], 
        size=[col_width, 20, col_height], # <--- ใหญ่ขึ้นสะใจ
        color='#bdc3c7', name="Column Face", opacity=0.3
    ))

    # --- B. BEAM (True Scale) ---
    beam_center_y = L_beam_show / 2
    web_h = H_real - (2 * Tf_real)
    # Web
    fig.add_trace(make_cuboid([0, beam_center_y, 0], [Tw_real, L_beam_show, web_h], '#7f8c8d', "Web"))
    # Flanges
    z_flange = (web_h/2) + (Tf_real/2)
    fig.add_trace(make_cuboid([0, beam_center_y, z_flange], [B_real, L_beam_show, Tf_real], '#7f8c8d', "Top Flange"))
    fig.add_trace(make_cuboid([0, beam_center_y, -z_flange], [B_real, L_beam_show, Tf_real], '#7f8c8d', "Bot Flange"))

    # --- C. PLATE ---
    pl_x = (Tw_real/2) + (plate_t/2)
    pl_y_center = -setback + (pl_w_total / 2)
    fig.add_trace(make_cuboid([pl_x, pl_y_center, 0], [plate_t, pl_w_total, pl_h], '#f1c40f', "Shear Plate"))

    # --- D. BOLTS ---
    bolt_len = Tw_real + plate_t + 30
    bx = pl_x - (plate_t/2) + (plate_t/2)
    by = leh_beam 
    z_start = (pl_h/2) - lev
    
    for i in range(n_rows):
        bz = z_start - (i * pitch)
        fig.add_trace(go.Scatter3d(
            x=[bx - bolt_len/2, bx + bolt_len/2], y=[by, by], z=[bz, bz],
            mode='lines', line=dict(color='#c0392b', width=d_b_mm), name='Bolt'
        ))
        fig.add_trace(go.Scatter3d(
            x=[bx + bolt_len/2], y=[by], z=[bz],
            mode='markers', marker=dict(size=d_b_mm*0.8, color='black', symbol='diamond'), showlegend=False
        ))

    # --- E. REFERENCE LINES (All included) ---
    dim_x = -B_real/2 - 60 # ขยับเส้นบอกระยะออกไปอีกนิด เพราะเสาใหญ่ขึ้น
    
    # 1. GAP [RED]
    add_dim_line(fig, np.array([dim_x, -setback, 0]), np.array([dim_x, 0, 0]), f"Gap={setback}", "red")

    # 2. LEH [BLUE]
    add_dim_line(fig, np.array([dim_x, 0, 0]), np.array([dim_x, by, 0]), f"Leh={leh_beam}", "blue")

    # 3. PITCH [GREEN]
    if n_rows > 1:
        dim_x_p = B_real/2 + 60
        add_dim_line(fig, 
            np.array([dim_x_p, by, z_start]), 
            np.array([dim_x_p, by, z_start - pitch]), 
            f"Pitch={pitch}", "green")
        
        # 4. PLATE HEIGHT [BLACK]
        add_dim_line(fig,
            np.array([dim_x_p, pl_y_center, pl_h/2]),
            np.array([dim_x_p, pl_y_center, -pl_h/2]),
            f"H={pl_h:.0f}", "black")

    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=2.2, y=0.8, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0), height=500
    )
    st.plotly_chart(fig, use_container_width=True)
