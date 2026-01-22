import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก (H-Beam) ---
# Weight (kg/m), Area (cm2), Ix (cm4), Zx (cm3)
STEEL_SECTIONS = {
    "H-100x100x6x8":  {"W": 17.2, "A": 21.90, "Ix": 383,   "Zx": 76.5},
    "H-125x125x6.5x9":{"W": 23.8, "A": 30.31, "Ix": 847,   "Zx": 136},
    "H-150x150x7x10": {"W": 31.5, "A": 40.14, "Ix": 1640,  "Zx": 219},
    "H-175x175x7.5x11":{"W": 40.2, "A": 51.21, "Ix": 2940,  "Zx": 330},
    "H-200x200x8x12": {"W": 49.9, "A": 63.53, "Ix": 4720,  "Zx": 472},
    "H-250x250x9x14": {"W": 72.4, "A": 92.18, "Ix": 10800, "Zx": 867},
    "H-300x300x10x15": {"W": 94.0, "A": 119.8, "Ix": 20400, "Zx": 1360},
    "H-350x350x12x19": {"W": 137.0,"A": 173.9, "Ix": 40300, "Zx": 2300},
    "H-400x400x13x21": {"W": 172.0,"A": 218.7, "Ix": 66600, "Zx": 3330},
}

# --- 2. ฟังก์ชันคำนวณการรับน้ำหนักสูงสุด (Capacity Calculation) ---
def calculate_capacity(L_m, Fy_ksc, E_gpa, props):
    """
    คำนวณ Safe Load (kg/m) จากหน้าตัดและความยาว
    """
    # แปลงหน่วย
    g = 9.81
    E = E_gpa * 1e9        # Pa
    Ix = props['Ix'] * 1e-8 # m4
    Zx = props['Zx'] * 1e-6 # m3
    Weight_beam = props['W'] # kg/m
    
    Fy_pa = Fy_ksc * 98066.5 # ksc -> Pa
    Fb = 0.60 * Fy_pa        # Allowable Bending Stress (ASD)
    
    # 1. Moment Capacity Limitation
    # M_allow = Fb * Zx
    # M_max = (w * L^2) / 8  ->  w = (8 * M_allow) / L^2
    M_allow = Fb * Zx        # Nm
    w_moment_N = (8 * M_allow) / (L_m**2) # N/m
    
    # 2. Deflection Limitation
    # Limit = L / 360
    # delta = (5 * w * L^4) / (384 * E * I)  ->  w = (384 * E * I * delta) / (5 * L^4)
    delta_allow = L_m / 360.0 # m
    w_deflect_N = (384 * E * Ix * delta_allow) / (5 * L_m**4) # N/m
    
    # หาค่าที่น้อยที่สุด (Governing Case)
    w_capacity_N = min(w_moment_N, w_deflect_N)
    
    # แปลงเป็น kg/m
    w_capacity_kg = w_capacity_N / g
    
    # หักน้ำหนักคานออก (Net Safe Load)
    w_net_safe = w_capacity_kg - Weight_beam
    
    # ถ้าค่าติดลบแสดงว่าแค่คานเปล่าก็รับน้ำหนักตัวเองไม่ได้ (หรือแอ่นเกิน)
    if w_net_safe < 0:
        w_net_safe = 0.0

    return {
        "net_load": w_net_safe,         # น้ำหนักบรรทุกปลอดภัย (ไม่รวมคาน)
        "total_load": w_capacity_kg,    # น้ำหนักรวมที่รับได้
        "govern_by": "Moment (การดัด)" if w_moment_N < w_deflect_N else "Deflection (การแอ่น)",
        "w_moment": w_moment_N / g,
        "w_deflect": w_deflect_N / g
    }

# --- 3. ส่วนแสดงผล (Streamlit App) ---
st.set_page_config(page_title="Beam Capacity Check", layout="wide")

st.title("🏗️ Beam Load Capacity Calculator")
st.markdown("คำนวณหา **น้ำหนักบรรทุกปลอดภัย (Safe Load)** ที่คานรับได้ จากขนาดหน้าตัดและความยาว")

# --- Sidebar Inputs ---
st.sidebar.header("ตั้งค่าคุณสมบัติ")
section_name = st.sidebar.selectbox("เลือกขนาด H-Beam", list(STEEL_SECTIONS.keys()))
props = STEEL_SECTIONS[section_name]

L = st.sidebar.slider("ความยาวคาน (m)", min_value=1.0, max_value=20.0, value=6.0, step=0.5)
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val = st.sidebar.number_input("E (GPa)", value=200)

# --- Calculation ---
res = calculate_capacity(L, Fy, E_val, props)

# --- Main Display ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("ผลการคำนวณ (Results)")
    st.info(f"หน้าตัด: **{section_name}**\n\nความยาว: **{L} เมตร**")
    
    st.metric(
        label="รับน้ำหนักบรรทุกปลอดภัย (Safe Load)",
        value=f"{res['net_load']:,.0f} kg/m",
        delta="น้ำหนักที่วางเพิ่มได้จริง"
    )
    
    st.write("---")
    st.write("**รายละเอียด:**")
    st.write(f"🔹 รับได้สูงสุดตามโมเมนต์: `{res['w_moment']:,.0f} kg/m`")
    st.write(f"🔹 รับได้สูงสุดตามระยะแอ่น: `{res['w_deflect']:,.0f} kg/m`")
    st.write(f"🔸 หักน้ำหนักคาน: `-{props['W']} kg/m`")
    
    if res['govern_by'] == "Moment (การดัด)":
        st.warning(f"⚠️ ควบคุมโดย: **{res['govern_by']}**")
    else:
        st.success(f"⚠️ ควบคุมโดย: **{res['govern_by']}** (คานจะแอ่นเกินก่อนที่จะพัง)")

with col2:
    st.subheader(f"กราฟความสามารถในการรับน้ำหนัก (Span vs Load)")
    
    # สร้างกราฟ Curve ความสัมพันธ์ระหว่าง ความยาว vs รับน้ำหนักได้เท่าไหร่
    lengths = np.linspace(2, 20, 50) # คำนวณช่วงความยาว 2-20 เมตร
    loads_moment = []
    loads_deflect = []
    
    for l_x in lengths:
        c = calculate_capacity(l_x, Fy, E_val, props)
        loads_moment.append(c['w_moment'])
        loads_deflect.append(c['w_deflect'])
    
    fig = go.Figure()
    
    # เส้น Limit Moment
    fig.add_trace(go.Scatter(x=lengths, y=loads_moment, mode='lines', name='Limit by Moment', line=dict(color='orange', dash='dash')))
    
    # เส้น Limit Deflection
    fig.add_trace(go.Scatter(x=lengths, y=loads_deflect, mode='lines', name='Limit by Deflection', line=dict(color='green', dash='dash')))
    
    # พื้นที่ Safe Zone (เติมสีใต้กราฟที่ต่ำกว่า)
    safe_loads = [min(m, d) for m, d in zip(loads_moment, loads_deflect)]
    fig.add_trace(go.Scatter(x=lengths, y=safe_loads, mode='lines', name='Safe Capacity', 
                             fill='tozeroy', line=dict(color='blue', width=3)))

    # จุดปัจจุบันที่เลือก
    fig.add_trace(go.Scatter(x=[L], y=[res['total_load']], mode='markers+text', 
                             marker=dict(size=12, color='red'),
                             text=[f"{res['total_load']:.0f} kg/m"], textposition="top right",
                             name='Current Selection'))

    fig.update_layout(
        xaxis_title="ความยาวคาน (m)",
        yaxis_title="น้ำหนักบรรทุกรวม (kg/m)",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("หมายเหตุ: กราฟแสดงน้ำหนักบรรทุกรวม (Total Load) ที่รับได้ (รวมน้ำหนักคานเอง)")
