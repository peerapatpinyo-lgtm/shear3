import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# ==========================================
# 🔧 3D GEOMETRY ENGINE
# ==========================================

def create_cylinder(p1, p2, r, color):
    """สร้างก้านน็อต"""
    v = p2 - p1; mag = np.linalg.norm(v)
    if mag == 0: return go.Mesh3d()
    v = v / mag
    not_v = np.array([1, 0, 0])
    if np.abs(np.dot(v, not_v)) > 0.9: not_v = np.array([0, 1, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1); n2 = np.cross(v, n1)
    theta = np.linspace(0, 2*np.pi, 16)
    x_c, y_c = r * np.cos(theta), r * np.sin(theta)
    verts = []
    for x, y in zip(x_c, y_c): verts.append(p1 + x*n1 + y*n2)
    for x, y in zip(x_c, y_c): verts.append(p2 + x*n1 + y*n2)
    verts = np.array(verts)
    n = 16; i, j, k = [], [], []
    for idx in range(n):
        nxt = (idx + 1) % n
        i.extend([idx, nxt, idx+n]); j.extend([nxt, nxt+n, nxt+n]); k.extend([idx+n, idx+n, idx])
        i.extend([idx, idx+n, nxt]); j.extend([nxt, idx, nxt]); k.extend([idx+n, idx, idx])
    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], i=i, j=j, k=k, color=color, flatshading=False)

def create_hex(center, normal, r, thick, color):
    """สร้างหัวน็อต (Simplified as cylinder for perf)"""
    return create_cylinder(center, center + normal*thick, r, color)

def make_box(x, y, z, dx, dy, dz, color, opacity=1.0, name="Part"):
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name
    )

def add_dim(fig, p1, p2, text, color="black", shift_z=0):
    mid = (p1 + p2) / 2
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+shift_z, p2[2]+shift_z],
        mode='lines+markers+text', line=dict(color=color, width=3), marker=dict(size=3),
        text=[None, None], showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+shift_z+5], mode='text', text=[f"<b>{text}</b>"],
        textposition="top center", textfont=dict(color=color, size=12), showlegend=False
    ))

# ==========================================
# 🚀 MAIN RENDER
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ 3D Construction Detail")
    st.caption("Standard: **AISC 360-16** | Focus: **Setback & Clearances**")

    # --- INPUTS ---
    with st.expander("🎛️ Parameters", expanded=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            section_name = st.selectbox("Beam", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
        with c2:
            bolt_size = st.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("Rows", 2, 8, 3)
        with c3:
            d_b_mm = float(bolt_size.replace("M",""))
            # Setback Control
            setback = st.slider("Setback (ช่องว่างระหว่างคาน-เสา)", 0, 25, 12, help="ปกติ 10-12mm เพื่อให้ติดตั้งง่าย")
            
            c3a, c3b = st.columns(2)
            plate_t = c3a.selectbox("Plate T", [6, 9, 12, 16, 19, 25], index=2)
            leh_beam = c3b.number_input("Leh (Beam)", value=40, step=5, help="ระยะจากรูถึงปลายคาน")
            
            # Auto Calc Plate Dimensions
            pitch = int(3*d_b_mm)
            lev = int(1.5*d_b_mm)
            leh_plate_tail = 40 # ระยะจากรูถึงขอบเพลท (ด้านนอก)

    # --- GEOMETRY SETUP (Ref Plane: Y=0 is Beam End) ---
    H = props['D'] * 10
    B = props['B'] * 10
    Tw = props.get('tw', 6.0)
    Tf = props.get('tf', 9.0)
    
    # Plate Dimensions
    pl_h = (2 * lev) + ((n_rows - 1) * pitch)
    # Total Plate Width = Setback (Gap) + Leh_beam (Hole to Beam End) + Leh_plate_tail (Hole to Plate End)
    pl_w_total = setback + leh_beam + leh_plate_tail
    
    # --- 3D VIZ ---
    col_viz, col_data = st.columns([3, 1])
    with col_viz:
        fig = go.Figure()
        
        # 1. GHOST COLUMN (The Support) at Y = -Setback
        # Plane representing the column face
        fig.add_trace(make_box(0, -setback - 10, 0, B*1.5, 20, H*1.2, '#bdc3c7', 0.2, "Column Face"))
        
        # 2. BEAM (Starts at Y=0)
        L_beam = 300
        beam_y_center = L_beam / 2
        # Web
        fig.add_trace(make_box(0, beam_y_center, 0, Tw, L_beam, H - 2*Tf, '#95a5a6', 0.5, "Web"))
        # Flanges
        fig.add_trace(make_box(0, beam_y_center, (H/2)-(Tf/2), B, L_beam, Tf, '#7f8c8d', 0.6, "Top Flange"))
        fig.add_trace(make_box(0, beam_y_center, -(H/2)+(Tf/2), B, L_beam, Tf, '#7f8c8d', 0.6, "Bot Flange"))
        
        # 3. SHEAR PLATE
        # Starts at Column Face (Y = -Setback) -> Ends at (Y = Leh_beam + Leh_plate_tail)
        # Center of Plate in Y
        pl_y_start = -setback
        pl_y_end = leh_beam + leh_plate_tail
        pl_y_center = (pl_y_start + pl_y_end) / 2
        pl_x_center = (Tw/2) + (plate_t/2)
        
        fig.add_trace(make_box(pl_x_center, pl_y_center, 0, plate_t, pl_w_total, pl_h, '#f1c40f', 1.0, "Shear Tab"))
        
        # 4. BOLTS
        # Position: Y = Leh_beam (Distance from beam end)
        bx = pl_x_center - (plate_t/2) + (plate_t/2)
        by = leh_beam # Hole position relative to Beam End (Y=0)
        bx_start = -(Tw + plate_t + 30)/2 + (Tw/2)
        bx_end = bx_start + (Tw + plate_t + 30)
        
        z_top = (pl_h/2) - lev
        for i in range(n_rows):
            bz = z_top - (i*pitch)
            fig.add_trace(create_cylinder(np.array([bx_start, by, bz]), np.array([bx_end, by, bz]), d_b_mm/2, '#c0392b'))
            fig.add_trace(create_hex(np.array([bx_end, by, bz]), np.array([1,0,0]), d_b_mm*0.8, d_b_mm*0.6, '#2c3e50'))
            fig.add_trace(create_hex(np.array([bx_start, by, bz]), np.array([-1,0,0]), d_b_mm*0.8, d_b_mm*0.6, '#2c3e50'))

        # 5. DIMENSIONS (To explain the Gap)
        # Setback Dim
        dim_x = -B/2 - 20
        p_col = np.array([dim_x, -setback, 0])
        p_beam = np.array([dim_x, 0, 0])
        add_dim(fig, p_col, p_beam, f"Gap={setback}", "red")
        
        # Leh Beam
        p_hole = np.array([dim_x, by, 0])
        add_dim(fig, p_beam, p_hole, f"Leh={leh_beam}", "blue")

        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                aspectmode='data', camera=dict(eye=dict(x=2.2, y=0.5, z=0.5))
            ),
            margin=dict(l=0, r=0, t=0, b=0), height=450
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_data:
        st.info("💡 **Construction Tip:**")
        if setback > 0:
            st.markdown(f"""
            **Gap (Setback) = {setback} mm**
            *ถูกต้องครับ!* ต้องเว้นระยะนี้ไว้เพื่อให้เครนยกคานลงติดตั้งได้ (Erection Clearance)
            แผ่นเพลทจะเชื่อมติดกับเสา (สีเทาจาง) และยื่นข้ามช่องว่างมาหาคาน
            """)
        else:
            st.warning("""
            **Gap = 0 mm (Flush)**
            *ระวัง!* ติดตั้งยากมาก
            ถ้าเหล็กตัดมายาวเกินนิดเดียว จะใส่ไม่ลง
            (นิยมใช้เฉพาะงาน End Plate)
            """)
            
        st.markdown("---")
        # Calc logic simplified
        V_u = 5000 
        st.metric("Plate Width", f"{pl_w_total} mm")
        st.metric("Plate Height", f"{pl_h} mm")
