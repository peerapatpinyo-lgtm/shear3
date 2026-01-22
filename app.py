import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก ---
STEEL_SECTIONS = {
    "H-100x100x6x8":   {"W": 17.2, "A": 21.90, "Ix": 383,   "Zx": 76.5, "D": 100, "tw": 6},
    "H-125x125x6.5x9": {"W": 23.8, "A": 30.31, "Ix": 847,   "Zx": 136,  "D": 125, "tw": 6.5},
    "H-150x150x7x10":  {"W": 31.5, "A": 40.14, "Ix": 1640,  "Zx": 219,  "D": 150, "tw": 7},
    "H-175x175x7.5x11": {"W": 40.2, "A": 51.21, "Ix": 2940,  "Zx": 330,  "D": 175, "tw": 7.5},
    "H-200x200x8x12":  {"W": 49.9, "A": 63.53, "Ix": 4720,  "Zx": 472,  "D": 200, "tw": 8},
    "H-250x250x9x14":  {"W": 72.4, "A": 92.18, "Ix": 10800, "Zx": 867,  "D": 250, "tw": 9},
    "H-300x300x10x15":  {"W": 94.0, "A": 119.8, "Ix": 20400, "Zx": 1360, "D": 300, "tw": 10},
    "H-350x350x12x19":  {"W": 137.0,"A": 173.9, "Ix": 40300, "Zx": 2300, "D": 350, "tw": 12},
    "H-400x400x13x21":  {"W": 172.0,"A": 218.7, "Ix": 66600, "Zx": 3330, "D": 400, "tw": 13},
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
        
        # Calculate in terms of Load (w) first
        w_s = (2 * V_allow_N) / L
        w_m = (8 * M_allow_N) / (L**2)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N

# --- Main App ---
st.set_page_config(page_title="Beam Shear Analysis", layout="wide")
st.title("🏗️ Beam Capacity: Shear vs Load View")

# Sidebar
st.sidebar.header("1. เลือกหน้าตัดและวัสดุ")
section_name = st.sidebar.selectbox("Select H-Beam", list(STEEL_SECTIONS.keys()))
props = STEEL_SECTIONS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val = st.sidebar.number_input("E (GPa)", value=200)

st.sidebar.header("2. ตั้งค่ากราฟ")
# *** จุดสำคัญ: เลือกโหมดแกน Y ***
view_mode = st.sidebar.radio("เลือกมุมมองแกน Y:", ["Uniform Load (kg/m)", "Max Shear Force (kg)"])
L_input = st.sidebar.slider("ความยาวคาน L (m)", min_value=1.0, max_value=20.0, value=6.0, step=0.1)

# --- Calculation Data Prep ---
max_graph_len = max(20.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 200)
w_s, w_m, w_d, V_allow_N = get_capacity_curves(L_range, Fy, E_val, props)
V_allow_kg = V_allow_N / 9.81

# หา w_safe (kg/m)
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# --- Convert Data based on View Mode ---
if view_mode == "Max Shear Force (kg)":
    # แปลงทุกอย่างเป็น Shear Force (V = wL/2)
    y_s = np.full_like(L_range, V_allow_kg) # Shear Limit is constant
    y_m = (w_m * L_range) / 2
    y_d = (w_d * L_range) / 2
    y_safe = (w_total_safe * L_range) / 2
    y_title = "Max Shear Force / Reaction (kg)"
    y_unit = "kg"
else:
    # ใช้ค่า w (kg/m) เดิม
    y_s = w_s
    y_m = w_m
    y_d = w_d
    y_safe = w_total_safe
    y_title = "Total Uniform Load Capacity (kg/m)"
    y_unit = "kg/m"

# --- Plotting ---
st.subheader(f"1. กราฟวิเคราะห์ ({view_mode})")
fig = go.Figure()

# Plot Lines
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

# --- Calculation Section (Dynamic) ---
st.markdown("---")
st.subheader(f"2. แสดงวิธีคำนวณที่ L = {L_input} เมตร ({view_mode})")

# Prepare Constants
g = 9.81
Fy_Pa = Fy * 98066.5
E_Pa = E_val * 1e9
Aw_m2 = (props['D']/1000) * (props['tw']/1000)
Zx_m3 = props['Zx'] * 1e-6
Ix_m4 = props['Ix'] * 1e-8

# Calculate Base Values
V_limit_kg = (0.40 * Fy_Pa * Aw_m2) / g # Shear Capacity (kg)
M_limit_kgm = (0.60 * Fy_Pa * Zx_m3) / g # Moment Capacity (kg-m approx) *for logic only
# Re-calculate specific values at L_input
calc_w_s = (2 * V_allow_N) / L_input / g
calc_w_m = (8 * (0.60 * Fy_Pa * Zx_m3)) / (L_input**2) / g
calc_w_d = (384 * E_Pa * Ix_m4 * (L_input/360.0)) / (5 * L_input**4) / g

# Values for Display
val_she_load = calc_w_s
val_mom_load = calc_w_m
val_def_load = calc_w_d

val_she_force = V_limit_kg
val_mom_force = (calc_w_m * L_input) / 2
val_def_force = (calc_w_d * L_input) / 2

# Determine Control
vals = {'Shear': calc_w_s, 'Moment': calc_w_m, 'Deflection': calc_w_d}
control_case = min(vals, key=vals.get)
safe_load = vals[control_case]
safe_shear = (safe_load * L_input) / 2

c1, c2, c3 = st.columns(3)

if view_mode == "Max Shear Force (kg)":
    # --- Mode: Display as Shear Force (V) ---
    with c1:
        st.markdown("### 🟥 1. Shear Limit")
        st.caption("ขีดจำกัดแรงเฉือนของหน้าตัด (Constant):")
        st.latex(r"V_{allow} = 0.4 F_y A_w")
        st.latex(rf"= 0.4 \times {Fy} \times {props['D']/10} \times {props['tw']/10}")
        st.metric("Limit V_shear", f"{val_she_force:,.0f} kg")
    
    with c2:
        st.markdown("### 🟧 2. Moment Limit")
        st.caption("แรงเฉือนที่ทำให้เกิดโมเมนต์สูงสุด ($V = 4M/L$):")
        st.latex(r"M_{allow} = 0.6 F_y Z_x")
        st.latex(r"V_{moment} = \frac{4 \times M_{allow}}{L}")
        st.metric("Limit V_moment", f"{val_mom_force:,.0f} kg")

    with c3:
        st.markdown("### 🟩 3. Deflection Limit")
        st.caption("แรงเฉือนที่ทำให้แอ่นตัวถึงขีดจำกัด ($L/360$):")
        st.latex(r"\delta = \frac{L}{360}, \quad V = \frac{wL}{2}")
        st.latex(r"V_{deflect} = \frac{384 E I \delta}{10 L^3}")
        st.metric("Limit V_deflect", f"{val_def_force:,.0f} kg")

else:
    # --- Mode: Display as Load (w) ---
    with c1:
        st.markdown("### 🟥 1. Shear Limit")
        st.caption("Load ที่ทำให้เกิดแรงเฉือนสูงสุด:")
        st.latex(r"w_s = \frac{2 V_{allow}}{L}")
        st.metric("Limit w_shear", f"{val_she_load:,.0f} kg/m")
    
    with c2:
        st.markdown("### 🟧 2. Moment Limit")
        st.caption("Load ที่ทำให้เกิดโมเมนต์สูงสุด:")
        st.latex(r"w_m = \frac{8 M_{allow}}{L^2}")
        st.metric("Limit w_moment", f"{val_mom_load:,.0f} kg/m")

    with c3:
        st.markdown("### 🟩 3. Deflection Limit")
        st.caption("Load ที่ทำให้คานแอ่น $L/360$:")
        st.latex(r"w_d = \frac{384 E I (L/360)}{5 L^4}")
        st.metric("Limit w_deflect", f"{val_def_load:,.0f} kg/m")

st.markdown("---")
st.info(f"""
**สรุปผล (Conclusion):**
* ที่ความยาว **{L_input} เมตร** กรณีที่ควบคุมคือ: **{control_case}**
* รับแรงเฉือนที่หัวเสาได้สูงสุด (Max Reaction): **{safe_shear:,.0f} kg**
* รับน้ำหนักบรรทุกแผ่ได้สูงสุด (Safe Load): **{safe_load:,.0f} kg/m** (รวมคาน)
""")
