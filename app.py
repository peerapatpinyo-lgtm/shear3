import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS (Siam Yamato Steel / TIS 1227) ---
# Format: Key = Name, Value = {Weight (kg/m), D (mm), tw (mm), Ix (cm4), Zx (cm3)}
SYS_H_BEAMS = {
    # --- Series 100 ---
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 76.5},
    # --- Series 125 ---
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6,   "Ix": 847,    "Zx": 136}, # Standard TIS often matches 125x60
    "H-125x125x6.5x9":  {"W": 23.8, "D": 125, "tw": 6.5, "Ix": 1360,   "Zx": 217}, # Corrected Ix for 125x125
    # --- Series 150 ---
    "H-148x100x6x9":    {"W": 21.1, "D": 148, "tw": 6,   "Ix": 1020,   "Zx": 138},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 219},
    # --- Series 175 ---
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5,   "Ix": 2040,   "Zx": 233},
    "H-175x175x7.5x11": {"W": 40.2, "D": 175, "tw": 7.5, "Ix": 2940,   "Zx": 330},
    # --- Series 200 ---
    "H-194x150x6x9":    {"W": 30.6, "D": 194, "tw": 6,   "Ix": 2690,   "Zx": 277},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8,   "Ix": 4720,   "Zx": 472},
    "H-200x204x12x12":  {"W": 56.2, "D": 200, "tw": 12,  "Ix": 4980,   "Zx": 498}, # Pile section
    # --- Series 250 ---
    "H-244x175x7x11":   {"W": 44.1, "D": 244, "tw": 7,   "Ix": 6120,   "Zx": 502},
    "H-248x124x5x8":    {"W": 25.7, "D": 248, "tw": 5,   "Ix": 3540,   "Zx": 285},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9,   "Ix": 10800,  "Zx": 867},
    "H-250x255x14x14":  {"W": 82.2, "D": 250, "tw": 14,  "Ix": 11500,  "Zx": 919}, # Pile section
    # --- Series 300 ---
    "H-294x200x8x12":   {"W": 56.8, "D": 294, "tw": 8,   "Ix": 11300,  "Zx": 771},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10,  "Ix": 20400,  "Zx": 1360},
    # --- Series 350 ---
    "H-340x250x9x14":   {"W": 79.7, "D": 340, "tw": 9,   "Ix": 21700,  "Zx": 1280},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-350x350x12x19":  {"W": 137.0,"D": 350, "tw": 12,  "Ix": 40300,  "Zx": 2300},
    # --- Series 400 ---
    "H-390x300x10x16":  {"W": 107.0,"D": 390, "tw": 10,  "Ix": 38700,  "Zx": 1980},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
    "H-400x408x21x21":  {"W": 197.0,"D": 400, "tw": 21,  "Ix": 70900,  "Zx": 3540}, # Heavy
    # --- Series 450 ---
    "H-440x300x11x18":  {"W": 124.0,"D": 440, "tw": 11,  "Ix": 56100,  "Zx": 2550},
    "H-450x200x9x14":   {"W": 76.0, "D": 450, "tw": 9,   "Ix": 33500,  "Zx": 1490},
    # --- Series 500 ---
    "H-482x300x11x15":  {"W": 115.0,"D": 482, "tw": 11,  "Ix": 60700,  "Zx": 2520},
    "H-488x300x11x18":  {"W": 128.0,"D": 488, "tw": 11,  "Ix": 71000,  "Zx": 2910},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 1910},
    # --- Series 600 ---
    "H-588x300x12x20":  {"W": 151.0,"D": 588, "tw": 12,  "Ix": 118000, "Zx": 4020},
    "H-594x302x14x23":  {"W": 175.0,"D": 594, "tw": 14,  "Ix": 137000, "Zx": 4620},
    "H-600x200x11x17":  {"W": 106.0,"D": 600, "tw": 11,  "Ix": 77600,  "Zx": 2590},
    # --- Series 700 ---
    "H-700x300x13x24":  {"W": 185.0,"D": 700, "tw": 13,  "Ix": 201000, "Zx": 5760},
    # --- Series 800 ---
    "H-800x300x14x26":  {"W": 210.0,"D": 800, "tw": 14,  "Ix": 292000, "Zx": 7290},
    # --- Series 900 ---
    "H-900x300x16x28":  {"W": 243.0,"D": 900, "tw": 16,  "Ix": 404000, "Zx": 8980},
}

# --- 2. ฟังก์ชันคำนวณกราฟ ---
def get_capacity_curves(lengths, Fy_ksc, E_gpa, props):
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # Base Capacity (SI Units)
    V_allow_N = 0.40 * Fy_pa * Aw 
    M_allow_N = 0.60 * Fy_pa * Zx
    
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Calculate Load (w)
        w_s = (2 * V_allow_N) / L
        w_m = (8 * M_allow_N) / (L**2)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N

# --- Main App ---
st.set_page_config(page_title="SYS Beam Analysis", layout="wide")
st.title("🏗️ SYS H-Beam Capacity Analysis")
st.markdown("วิเคราะห์การรับน้ำหนักเหล็ก **SYS (Siam Yamato Steel)** ตามมาตรฐานมอก.")

# Sidebar
st.sidebar.header("1. เลือกหน้าตัดและวัสดุ")
# Dropdown แบบ Searchable
section_name = st.sidebar.selectbox("เลือกขนาด H-Beam (SYS)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val = st.sidebar.number_input("E (GPa)", value=200)

# แสดง Properties ของเหล็กที่เลือกใน Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📌 Properties")
st.sidebar.write(f"**Weight:** {props['W']} kg/m")
st.sidebar.write(f"**Depth (D):** {props['D']} mm")
st.sidebar.write(f"**Web ($t_w$):** {props['tw']} mm")
st.sidebar.write(f"**$I_x$:** {props['Ix']:,} cm⁴")
st.sidebar.write(f"**$Z_x$:** {props['Zx']:,} cm³")

st.sidebar.markdown("---")
st.sidebar.header("2. ตั้งค่าการแสดงผล")
view_mode = st.sidebar.radio("เลือกมุมมองแกน Y:", ["Uniform Load (kg/m)", "Max Shear Force (kg)"])
L_input = st.sidebar.slider("ความยาวคาน L (m)", min_value=1.0, max_value=24.0, value=6.0, step=0.1)

# --- Calculation ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, V_allow_N = get_capacity_curves(L_range, Fy, E_val, props)
V_allow_kg = V_allow_N / 9.81

w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# --- Convert View Mode ---
if view_mode == "Max Shear Force (kg)":
    y_s = np.full_like(L_range, V_allow_kg) 
    y_m = (w_m * L_range) / 2
    y_d = (w_d * L_range) / 2
    y_safe = (w_total_safe * L_range) / 2
    y_title = "Max Shear Force / Reaction (kg)"
else:
    y_s = w_s
    y_m = w_m
    y_d = w_d
    y_safe = w_total_safe
    y_title = "Total Uniform Load Capacity (kg/m)"

# --- 1. กราฟ ---
st.subheader(f"1. กราฟวิเคราะห์ ({view_mode})")
fig = go.Figure()

fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear Limit', line=dict(color='red', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment Limit', line=dict(color='orange', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection Limit', line=dict(color='green', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_safe, name='Safe Capacity', line=dict(color='black', width=4)))

# Current Point
current_idx = (np.abs(L_range - L_input)).argmin()
current_val = y_safe[current_idx]
fig.add_trace(go.Scatter(x=[L_input], y=[current_val], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))

# Color Zones
governing_idx = np.argmin([y_s, y_m, y_d], axis=0)
colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
labels = ['Shear Control', 'Moment Control', 'Deflection Control']
start_idx = 0
for i in range(1, len(L_range)):
    if governing_idx[i] != governing_idx[i-1] or i == len(L_range)-1:
        x0 = L_range[start_idx]
        x1 = L_range[i]
        zone_type = governing_idx[start_idx]
        fig.add_vrect(x0=x0, x1=x1, fillcolor=colors[zone_type], opacity=1, layer="below", line_width=0, annotation_text=labels[zone_type], annotation_position="inside top")
        start_idx = i

fig.update_layout(height=450, margin=dict(t=30, b=0), xaxis_title="Length (m)", yaxis_title=y_title, hovermode="x unified")
fig.update_yaxes(range=[0, current_val * 2.5])
st.plotly_chart(fig, use_container_width=True)

# --- 2. ตารางสรุปและคำนวณ ---
st.markdown("---")
st.subheader(f"2. สรุปผลการคำนวณที่ L = {L_input} เมตร")

# คำนวณค่าจริงที่จุด L
g = 9.81
Fy_Pa = Fy * 98066.5
E_Pa = E_val * 1e9
Aw_m2 = (props['D']/1000) * (props['tw']/1000)
Zx_m3 = props['Zx'] * 1e-6
Ix_m4 = props['Ix'] * 1e-8

calc_w_s = (2 * (0.40 * Fy_Pa * Aw_m2)) / L_input / g
calc_w_m = (8 * (0.60 * Fy_Pa * Zx_m3)) / (L_input**2) / g
calc_w_d = (384 * E_Pa * Ix_m4 * (L_input/360.0)) / (5 * L_input**4) / g

vals = {'Shear': calc_w_s, 'Moment': calc_w_m, 'Deflection': calc_w_d}
control_case = min(vals, key=vals.get)
safe_load = vals[control_case]
safe_load_net = safe_load - props['W']
if safe_load_net < 0: safe_load_net = 0

safe_shear_force = (safe_load * L_input) / 2

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.info(f"**หน้าตัด: {section_name}**")
    st.write(f"น้ำหนักคาน: {props['W']} kg/m")
    
with c2:
    st.metric("Limit Shear (Load)", f"{calc_w_s:,.0f} kg/m", help="รับน้ำหนักแผ่ได้สูงสุดก่อนขาดด้วยแรงเฉือน")

with c3:
    st.metric("Limit Moment (Load)", f"{calc_w_m:,.0f} kg/m", help="รับน้ำหนักแผ่ได้สูงสุดก่อนพังด้วยโมเมนต์ดัด")

with c4:
    st.metric("Limit Deflection (Load)", f"{calc_w_d:,.0f} kg/m", help="รับน้ำหนักแผ่ได้สูงสุดก่อนแอ่นเกิน L/360")

st.success(f"""
### 🏆 บทสรุป (Governing Case)
* **ตัวควบคุม:** {control_case} Control
* **รับน้ำหนักบรรทุกปลอดภัยสุทธิ (Net Safe Load):** {safe_load_net:,.0f} kg/m (หักน้ำหนักคานแล้ว)
* **แรงปฏิกิริยาสูงสุดที่หัวเสา (Max Reaction):** {safe_shear_force:,.0f} kg
""")

with st.expander("ดูตารางเหล็ก SYS ทั้งหมด (Click to view full table)"):
    df_sys = pd.DataFrame.from_dict(SYS_H_BEAMS, orient='index')
    df_sys.index.name = 'Designation'
    st.dataframe(df_sys)
