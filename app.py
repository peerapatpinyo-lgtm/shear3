import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก (เพิ่ม D และ tw เพื่อคำนวณ Shear) ---
# D: Depth (mm), tw: Web Thickness (mm)
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

def get_capacity_curves(lengths, Fy_ksc, E_gpa, props):
    """
    สร้างข้อมูลกราฟ Curve ของ Capacity ทั้ง 3 ด้าน
    Return เป็น Dictionary ของ Array
    """
    g = 9.81
    # แปลงหน่วย
    E = E_gpa * 1e9         # Pa
    Ix = props['Ix'] * 1e-8 # m4
    Zx = props['Zx'] * 1e-6 # m3
    Aw = (props['D']/1000) * (props['tw']/1000) # m2 (Approximation: D * tw)
    
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Shear Limit (Constant Force)
    # V_allow = 0.40 * Fy * Aw (ASD)
    V_allow_N = 0.40 * Fy_pa * Aw 
    
    # 2. Moment Limit (Constant Moment)
    # M_allow = 0.60 * Fy * Zx
    M_allow_N = 0.60 * Fy_pa * Zx
    
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    # คำนวณค่า w (Load Capacity kg/m) ที่แต่ละความยาว
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
            
        # Case 1: Shear Control (V_max = wL/2 <= V_allow)
        # w = 2 * V_allow / L
        w_s = (2 * V_allow_N) / L
        
        # Case 2: Moment Control (M_max = wL^2/8 <= M_allow)
        # w = 8 * M_allow / L^2
        w_m = (8 * M_allow_N) / (L**2)
        
        # Case 3: Deflection Control (d_max = 5wL^4/384EI <= L/360)
        # w = (384 * E * I * (L/360)) / (5 * L^4)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   # Convert N/m -> kg/m
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N/g

# --- Main App ---
st.set_page_config(page_title="Beam Limits Analysis", layout="wide")
st.title("📊 Beam Limit State Analysis")
st.markdown("วิเคราะห์จุดวิกฤตของคาน: **Shear vs Moment vs Deflection**")

# Sidebar
st.sidebar.header("Parameters")
section_name = st.sidebar.selectbox("Select H-Beam", list(STEEL_SECTIONS.keys()))
props = STEEL_SECTIONS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val = st.sidebar.number_input("E (GPa)", value=200)
max_len = st.sidebar.slider("Max Span to plot (m)", 5, 30, 15)

# ตัวเลือกแกน Y
y_axis_type = st.sidebar.radio("แกน Y แสดงค่า:", ["Load Capacity (kg/m)", "End Shear Force (kg)"])

# คำนวณ
L_range = np.linspace(0.5, max_len, 200)
w_s, w_m, w_d, V_allow_kg = get_capacity_curves(L_range, Fy, E_val, props)

# หา Safe Load (ค่าต่ำสุดของ 3 เส้น)
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W'] # หักน้ำหนักคาน
w_safe = np.maximum(w_safe, 0) # ห้ามติดลบ

# แปลงข้อมูลตามแกน Y ที่เลือก
if y_axis_type == "End Shear Force (kg)":
    # ถ้าเลือกดู Shear: ต้องแปลง Load (w) กลับเป็น Reaction (V = wL/2)
    # แต่ Shear Limit คือค่าคงที่ V_allow
    y_s = np.full_like(L_range, V_allow_kg) # เส้น Shear Limit จะเป็นเส้นตรงแนวนอน
    y_m = (w_m * 9.81 * L_range**2 / 8) * 4 / L_range / 9.81 # Convert Moment Limit back to equivalent Shear V = 4M/L
    y_d = (w_d * L_range / 2) # Convert Deflect Limit back to Shear
    y_safe = (w_safe + props['W']) * L_range / 2 # Total shear from safe load
    y_title = "Max Shear Force / Reaction (kg)"
else:
    # ดูเป็น Load kg/m
    y_s = w_s
    y_m = w_m
    y_d = w_d
    y_safe = w_safe + props['W'] # Show Total Capacity for comparison
    y_title = "Total Uniform Load Capacity (kg/m)"

# --- Plotting ---
fig = go.Figure()

# 1. Plot เส้น Limit ทั้ง 3 (เส้นประจางๆ)
fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear Limit', line=dict(color='red', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment Limit', line=dict(color='orange', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection Limit', line=dict(color='green', dash='dash', width=1)))

# 2. Plot เส้น Safe Capacity (เส้นทึบหนา)
fig.add_trace(go.Scatter(x=L_range, y=y_safe, name='Safe Capacity (Governing)', 
                         line=dict(color='black', width=4), mode='lines'))

# --- 3. Logic การแบ่ง Zone สี (Control Zones) ---
# เราจะหาจุดที่ Condition เปลี่ยน
# เปรียบเทียบค่า y_s, y_m, y_d ว่าตัวไหนต่ำสุดในแต่ละช่วง L
governing_idx = np.argmin([y_s, y_m, y_d], axis=0) # 0=Shear, 1=Moment, 2=Deflection

# สร้าง Shapes สี่เหลี่ยมระบายสีพื้นหลัง
# สี: Shear=แดงอ่อน, Moment=ส้มอ่อน, Deflection=เขียวอ่อน
colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
labels = ['Shear Control', 'Moment Control', 'Deflection Control']

# วนลูปหาช่วงการเปลี่ยนถ่าย (Transition Points)
start_idx = 0
for i in range(1, len(L_range)):
    if governing_idx[i] != governing_idx[i-1] or i == len(L_range)-1:
        # จบช่วงหนึ่งแล้ว -> วาดสี่เหลี่ยม
        x0 = L_range[start_idx]
        x1 = L_range[i]
        zone_type = governing_idx[start_idx]
        
        # แก้ไขจุดที่ Error: เปลี่ยน annotation_position เป็น "inside top"
        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor=colors[zone_type], opacity=1,
            layer="below", line_width=0,
            annotation_text=labels[zone_type], 
            annotation_position="inside top" 
        )
        start_idx = i

# Layout ตกแต่ง
fig.update_layout(
    title=f"Beam Capacity Chart ({section_name})",
    xaxis_title="Beam Span Length (m)",
    yaxis_title=y_title,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    yaxis=dict(rangemode="tozero") # ให้แกน Y เริ่มที่ 0 เสมอ
)

# Limit แกน Y ไม่ให้สูงเกินไป
max_y_view = np.max(y_safe) * 1.5
if y_axis_type == "End Shear Force (kg)":
     max_y_view = V_allow_kg * 1.5
fig.update_yaxes(range=[0, max_y_view])

st.plotly_chart(fig, use_container_width=True)

# คำอธิบายเพิ่มเติม
st.info("""
**คำอธิบายกราฟ (Zones):**
* 🟥 **Red Zone (Shear Control):** ช่วงคานสั้นมาก แรงเฉือนจะถึงขีดจำกัดก่อนที่คานจะหักหรือแอ่น
* 🟧 **Orange Zone (Moment Control):** ช่วงคานยาวปานกลาง คานจะพังจากการดัด (Bending)
* 🟩 **Green Zone (Deflection Control):** ช่วงคานยาว คานจะแอ่นตัวเกินมาตรฐาน (L/360) ก่อนที่จะพัง
""")
