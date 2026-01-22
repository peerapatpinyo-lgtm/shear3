import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก (ตัวอย่าง H-Beam มาตรฐาน) ---
# หน่วย: Area (cm2), I (cm4), Z (cm3)
STEEL_SECTIONS = {
    "H-100x100x6x8": {"A": 21.9, "Ix": 383, "Zx": 76.5, "Iy": 134, "Zy": 26.7, "Weight": 17.2},
    "H-150x150x7x10": {"A": 40.14, "Ix": 1640, "Zx": 219, "Iy": 563, "Zy": 75.1, "Weight": 31.5},
    "H-200x200x8x12": {"A": 63.53, "Ix": 4720, "Zx": 472, "Iy": 1600, "Zy": 160, "Weight": 49.9},
    "H-250x250x9x14": {"A": 92.18, "Ix": 10800, "Zx": 867, "Iy": 3650, "Zy": 292, "Weight": 72.4},
    "H-300x300x10x15": {"A": 119.8, "Ix": 20400, "Zx": 1360, "Iy": 6750, "Zy": 450, "Weight": 94.0},
    "Custom": {"A": 0, "Ix": 0, "Zx": 0} # ให้กรอกเอง
}

# --- 2. ฟังก์ชันคำนวณ (Analysis Engine) ---
def calculate_beam(L, E, I, w_udl, P_load, a_dist):
    """
    คำนวณ Shear, Moment, Deflection สำหรับ Simply Supported Beam
    L: ความยาวคาน (m)
    E: Young's Modulus (Pa)
    I: Moment of Inertia (m^4)
    w_udl: Distributed Load (N/m)
    P_load: Point Load (N)
    a_dist: ระยะ Point load จากซ้าย (m)
    """
    x = np.linspace(0, L, 500)  # แบ่งคานเป็น 500 ส่วน
    
    # --- กรณี UDL (Uniform Distributed Load) ---
    # Reaction
    R1_w = w_udl * L / 2
    R2_w = w_udl * L / 2
    
    # Shear (V)
    V_w = R1_w - w_udl * x
    
    # Moment (M)
    M_w = (w_udl * x / 2) * (L - x)
    
    # Deflection (d) -> สูตร: (-w x / 24EI) * (L^3 - 2Lx^2 + x^3)
    d_w = -(w_udl * x) / (24 * E * I) * (L**3 - 2*L*x**2 + x**3)

    # --- กรณี Point Load ---
    # Reaction
    b_dist = L - a_dist
    R1_p = P_load * b_dist / L
    R2_p = P_load * a_dist / L
    
    # คำนวณ V, M, d โดยใช้เงื่อนไขของ x (Macauley Method หรือแยกช่วง)
    V_p = np.where(x < a_dist, R1_p, R1_p - P_load)
    
    M_p = np.where(x < a_dist, R1_p * x, R1_p * x - P_load * (x - a_dist))
    
    # Deflection สูตรแยกช่วง
    # ช่วง x < a
    d_p1 = -(P_load * b_dist * x) / (6 * L * E * I) * (L**2 - b_dist**2 - x**2)
    # ช่วง x > a
    d_p2 = -(P_load * b_dist * x) / (6 * L * E * I) * (L**2 - b_dist**2 - x**2) + (P_load * (x - a_dist)**3) / (6 * E * I)
    
    d_p = np.where(x < a_dist, d_p1, d_p2)

    # --- Superposition (รวมผล) ---
    V_total = V_w + V_p
    M_total = M_w + M_p
    d_total = d_w + d_p
    
    return x, V_total, M_total, d_total

# --- 3. ส่วนแสดงผล (Streamlit App) ---
st.set_page_config(page_title="Steel Beam Design", layout="wide")

st.title("🏗️ Steel Beam Calculator (Simple Beam)")
st.markdown("คำนวณ Shear, Moment, Deflection และตรวจสอบ Ratio ของคานเหล็ก")

# --- Sidebar Inputs ---
st.sidebar.header("1. คุณสมบัติวัสดุและหน้าตัด")

# เลือกหน้าตัด
section_name = st.sidebar.selectbox("เลือกขนาด H-Beam", list(STEEL_SECTIONS.keys()))
props = STEEL_SECTIONS[section_name]

if section_name == "Custom":
    Ix_cm4 = st.sidebar.number_input("Moment of Inertia, Ix (cm4)", value=1000.0)
    Zx_cm3 = st.sidebar.number_input("Section Modulus, Zx (cm3)", value=100.0)
else:
    Ix_cm4 = props["Ix"]
    Zx_cm3 = props["Zx"]
    st.sidebar.info(f"Ix: {Ix_cm4} cm4 | Zx: {Zx_cm3} cm3")

# ค่าวัสดุ
Fy = st.sidebar.number_input("Yield Strength, Fy (MPa/ksc)", value=2400.0, help="เช่น SS400 = 2400 ksc (approx 235 MPa)")
E_val = st.sidebar.number_input("Young's Modulus, E (GPa)", value=200.0) # เหล็ก ~200 GPa
Allowable_Stress_Ratio = 0.60 # ASD method (0.6Fy)
Fb = Fy * Allowable_Stress_Ratio # Allowable Bending Stress

st.sidebar.header("2. รูปร่างและน้ำหนักบรรทุก")
L = st.sidebar.number_input("ความยาวคาน, L (m)", value=6.0, step=0.5)

st.sidebar.subheader("Loadings")
w_load_kg = st.sidebar.number_input("Distributed Load (kg/m)", value=500.0)
p_load_kg = st.sidebar.number_input("Point Load (kg)", value=1000.0)
a_pos = st.sidebar.slider("ตำแหน่ง Point Load (m)", 0.0, L, L/2)

# --- การแปลงหน่วย (Unit Conversion) เพื่อคำนวณ ---
# เราจะคำนวณในหน่วย SI Base (N, m, Pa) เพื่อความแม่นยำ แล้วแปลงกลับตอนแสดงผล
g = 9.81
w_newton = w_load_kg * g     # kg/m -> N/m
p_newton = p_load_kg * g     # kg -> N
E_pascal = E_val * 1e9       # GPa -> Pa
I_m4 = Ix_cm4 * 1e-8         # cm4 -> m4
Z_m3 = Zx_cm3 * 1e-6         # cm3 -> m3
Fy_pascal = Fy * 98066.5     # ksc -> Pa (สมมติ input เป็น ksc ตามความนิยมไทย, ถ้าเป็น MPa ให้แก้ตัวคูณ)
# หมายเหตุ: ถ้า user กรอก Fy เป็น ksc (kg/cm2) -> 1 ksc ≈ 98066.5 Pa

# --- Run Calculation ---
x, V, M, d = calculate_beam(L, E_pascal, I_m4, w_newton, p_newton, a_pos)

# หาค่าสูงสุด (Absolute Max)
max_V = np.max(np.abs(V))
max_M = np.max(np.abs(M))
max_d = np.max(np.abs(d))

# --- Design Check (Ratio) ---
# 1. Moment Capacity (Allowable Moment)
# M_all = Fb * Zx
M_allowable = (Fb * 98066.5) * Z_m3 # แปลง Fb(ksc) -> Pa แล้วคูณ Z(m3) -> Nm
moment_ratio = max_M / M_allowable

# 2. Deflection Limit (L/360)
d_limit = L / 360 # meters
deflection_ratio = max_d / d_limit

# --- Display Results ---
col1, col2, col3 = st.columns(3)

# แปลงหน่วยกลับเพื่อแสดงผลให้ดูง่าย (kg, m, cm)
# Moment: Nm -> kg.m
m_display = max_M / g 
# Shear: N -> kg
v_display = max_V / g
# Deflection: m -> mm
d_display = max_d * 1000
d_limit_display = d_limit * 1000

with col1:
    st.metric("Max Moment", f"{m_display:,.2f} kg·m")
    status = "✅ PASS" if moment_ratio <= 1.0 else "❌ FAIL"
    st.write(f"**Moment Ratio:** {moment_ratio:.2f} ({status})")
    st.progress(min(moment_ratio, 1.0))

with col2:
    st.metric("Max Shear", f"{v_display:,.2f} kg")
    # Shear check มักจะผ่านง่ายในคานยาว ขอละไว้หรือเพิ่มโค้ดเช็ค 0.4Fy ได้
    st.write("*(Shear typically passes for long beams)*")

with col3:
    st.metric("Max Deflection", f"{d_display:,.2f} mm")
    status_d = "✅ PASS" if deflection_ratio <= 1.0 else "❌ FAIL"
    st.write(f"**Limit (L/360):** {d_limit_display:.2f} mm")
    st.write(f"**Deflection Ratio:** {deflection_ratio:.2f} ({status_d})")

st.markdown("---")

# --- Plotting Diagrams ---
fig = make_subplots(rows=3, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.1,
                    subplot_titles=("Shear Force Diagram (kg)", "Bending Moment Diagram (kg·m)", "Deflection (mm)"))

# SFD
fig.add_trace(go.Scatter(x=x, y=V/g, fill='tozeroy', line=dict(color='red'), name='Shear (kg)'), row=1, col=1)

# BMD
fig.add_trace(go.Scatter(x=x, y=M/g, fill='tozeroy', line=dict(color='blue'), name='Moment (kg·m)'), row=2, col=1)

# Deflection (กลับด้านแกน Y เพื่อให้ดูเหมือนคานแอ่นลง)
fig.add_trace(go.Scatter(x=x, y=d*1000, line=dict(color='green', width=3), name='Deflection (mm)'), row=3, col=1)
fig.update_yaxes(autorange="reversed", row=3, col=1) # กลับหัวกราฟแอ่นตัว

fig.update_layout(height=800, showlegend=False, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.info("หมายเหตุ: การคำนวณนี้สำหรับ Simple Beam (คานช่วงเดียวปลายหมุน) และใช้หน่วย Elastic Design (ASD) เบื้องต้น")
