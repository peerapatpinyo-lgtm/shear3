import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# ==========================================
# 📐 GEOMETRY UTILS (PRECISE)
# ==========================================

def make_cuboid(center, size, color, name):
    """
    สร้างกล่องสี่เหลี่ยม (Cuboid) แบบกำหนดจุดศูนย์กลางและขนาด (กว้าง, ยาว, สูง)
    center: [x, y, z]
    size: [dx, dy, dz]
    """
    x, y, z = center
    dx, dy, dz = size
    
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=1.0, flatshading=True, name=name,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.1) # Matte Steel Look
    )

def create_bolt_hex(x, y, z_start, z_end, d, color):
    """วาดน็อตแบบง่าย (เส้นหนา) เพื่อลดภาระเครื่องแต่ดูรู้เรื่อง"""
    return go.Scatter3d(
        x=[x, x], y=[y, y], z=[z_start, z_end],
        mode='lines', line=dict(color=color, width=d*0.8), # Width scale approx
        name='Bolt'
    )

# ==========================================
# 🏗️ MAIN RENDER
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    st.markdown("## 🏗️ 3D Structural Detail (True Scale)")
    
    # --- 1. CONFIG ---
    with st.expander("🎛️ Design & Geometry", expanded=True):
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            section_name = st.selectbox("เลือกหน้าตัด (H-Beam)", list(SYS_H_BEAMS.keys()))
            props = SYS_H_BEAMS[section_name]
            
            # 🔍 DEBUG DATA: แสดงค่าที่จะเอาไปวาดจริง
            # แปลงหน่วย: สมมติ Database เก็บ cm ต้องคูณ 10 เป็น mm
            # (ตรวจสอบ Database ของคุณ: ถ้าค่า D < 100 สันนิษฐานว่าเป็น cm)
            d_factor = 10 if props['D'] < 100 else 1
            
            H_real = props['D'] * d_factor
            B_real = props['B'] * d_factor
            Tw_real = props.get('t1', 6.0) # Web thick
            Tf_real = props.get('t2', 9.0) # Flange thick
            
            st.caption(f"📏 Dimensions: H{H_real:.0f} x B{B_real:.0f} x t{Tw_real} x t{Tf_real} mm")

        with c2:
            bolt_size = st.selectbox("ขนาดน็อต", ["M16", "M20", "M22", "M24"], index=1)
            n_rows = st.number_input("จำนวนแถว", 2, 8, 3)

        with c3:
            d_b_mm = float(bolt_size.replace("M",""))
            # Auto Layout
            pitch = int(3 * d_b_mm)
            lev = int(1.5 * d_b_mm)
            leh = 40
            
            plate_t = st.selectbox("ความหนาเพลท (mm)", [6, 9, 12, 16, 20, 25], index=2)
            
    # --- 2. CALCULATE GEOMETRY (Unit: mm) ---
    L_beam_show = H_real * 1.5 # ความยาวคานที่โชว์ (อิงตามความลึกคานให้ดูสมส่วน)
    
    # Plate Dimensions
    pl_h = (2 * lev) + ((n_rows - 1) * pitch)
    pl_w = leh + 20 
    
    # --- 3. DRAWING ENGINE ---
    fig = go.Figure()

    # --- PART 1: THE BEAM (H-SHAPE) ---
    # สีเหล็ก (Industrial Grey)
    c_steel = '#7f8c8d'
    
    # 1.1 Web (เอวกลาง)
    # สูง = H - 2*Tf
    web_h = H_real - (2 * Tf_real)
    fig.add_trace(make_cuboid(
        center=[0, 0, 0], 
        size=[Tw_real, L_beam_show, web_h], 
        color=c_steel, name="Web"
    ))
    
    # 1.2 Top Flange (ปีกบน)
    # ตำแหน่ง Z = (Web/2) + (Tf/2)
    z_top = (web_h/2) + (Tf_real/2)
    fig.add_trace(make_cuboid(
        center=[0, 0, z_top],
        size=[B_real, L_beam_show, Tf_real],
        color=c_steel, name="Top Flange"
    ))
    
    # 1.3 Bottom Flange (ปีกล่าง)
    z_bot = -z_top
    fig.add_trace(make_cuboid(
        center=[0, 0, z_bot],
        size=[B_real, L_beam_show, Tf_real],
        color=c_steel, name="Bot Flange"
    ))

    # --- PART 2: THE PLATE (SHEAR TAB) ---
    c_plate = '#f1c40f' # Yellow Safety
    # ติดที่ผิว Web: X offset = (Tw/2) + (Tp/2)
    pl_x = (Tw_real/2) + (plate_t/2)
    # ตำแหน่ง Y: ให้เพลทอยู่ตรงปลายคาน (End offset)
    pl_y = (L_beam_show/2) - (pl_w/2) + 10 # ยื่นออกมานิดนึง
    
    fig.add_trace(make_cuboid(
        center=[pl_x, pl_y, 0],
        size=[plate_t, pl_w, pl_h],
        color=c_plate, name="Shear Plate"
    ))

    # --- PART 3: BOLTS ---
    c_bolt = '#c0392b' # Red High Strength
    bolt_len = Tw_real + plate_t + 25
    
    # Bolt Center Calculation
    b_y = pl_y + (pl_w/2) - leh # Hole position relative to plate
    b_x = 0 + (plate_t/2) # Middle of grip
    
    z_start = (pl_h/2) - lev
    
    for i in range(n_rows):
        bz = z_start - (i * pitch)
        # ใช้ Scatter3d Line ความหนาเยอะๆ แทน Cylinder เพื่อ Performance และความชัด
        fig.add_trace(go.Scatter3d(
            x=[b_x - bolt_len/2, b_x + bolt_len/2],
            y=[b_y, b_y],
            z=[bz, bz],
            mode='lines',
            line=dict(color=c_bolt, width=d_b_mm), # Width roughly mimics diameter
            name='Bolt'
        ))
        # หัวน็อต (Marker)
        fig.add_trace(go.Scatter3d(
            x=[b_x + bolt_len/2], y=[b_y], z=[bz],
            mode='markers', marker=dict(size=d_b_mm*0.8, color='black', symbol='diamond'),
            showlegend=False
        ))

    # --- PART 4: DIMENSION LINES (Reference) ---
    # เส้นบอกความสูงคาน (Depth)
    dim_x = -B_real/2 - 20
    fig.add_trace(go.Scatter3d(
        x=[dim_x, dim_x], y=[0, 0], z=[-H_real/2, H_real/2],
        mode='lines+text', line=dict(color='black', dash='dash'),
        text=[f"H={H_real:.0f}", ""], textposition="middle left"
    ))
    
    # เส้นบอกความกว้างปีก (Width)
    dim_y = -L_beam_show/2 - 20
    fig.add_trace(go.Scatter3d(
        x=[-B_real/2, B_real/2], y=[dim_y, dim_y], z=[H_real/2, H_real/2],
        mode='lines+text', line=dict(color='blue', dash='dash'),
        text=[f"B={B_real:.0f}", ""], textposition="top center"
    ))

    # --- CRITICAL FIX: FORCING 1:1 ASPECT RATIO ---
    max_dim = max(H_real, B_real, L_beam_show)
    
    fig.update_layout(
        scene=dict(
            # บังคับสเกลแกน X, Y, Z ให้เท่ากัน (1 unit = 1 mm จริง)
            aspectmode='data', 
            xaxis=dict(visible=False), 
            yaxis=dict(visible=False), 
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.5, y=0.5, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Info Box
    st.info(f"""
    **🔍 Checking Scale:**
    - คานสูง (D): {H_real} mm
    - ปีกกว้าง (B): {B_real} mm
    - เอวหนา (tw): {Tw_real} mm
    - ปีกหนา (tf): {Tf_real} mm
    
    *รูป 3D นี้ใช้สัดส่วน 1:1 (True Scale) ไม่มีการยืดหดแกน*
    """)
