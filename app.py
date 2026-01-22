import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก ---
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
    """ สร้างข้อมูลกราฟ Curve ของ Capacity ทั้ง 3 ด้าน """
    g = 9.81
    # แปลงหน่วย
    E = E_gpa * 1e9         # Pa
    Ix = props['Ix'] * 1e-8 # m4
    Zx = props['Zx'] * 1e-6 # m3
    Aw = (props['D']/1000) * (props['tw']/1000) # m2
    
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Shear Limit
    V_allow_N = 0.40 * Fy_pa * Aw 
    
    # 2. Moment Limit
    M_allow_N = 0.60 * Fy_pa * Zx
    
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
            
        # Case 1: Shear
        w_s = (2 * V_allow_N) / L
        
        # Case 2: Moment
        w_m = (8 * M_allow_N) / (L**2)
        
        # Case 3: Deflection
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
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

# หา Safe Load
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)

# แปลงข้อมูลตามแกน Y
if y_axis_type == "End Shear Force (kg)":
    y_s = np.full_like(L_range, V_allow_kg)
    y_m = (w_m * 9.81 * L_range**2 / 8) * 4 / L_range / 9.81
    y_d = (w_d * L_range / 2)
    y_safe = (w_safe + props['W']) * L_range / 2
    y_title = "Max Shear Force / Reaction (kg)"
else:
    y_s = w_s
    y_m = w_m
    y_d = w_d
    y_safe = w_safe + props['W']
    y_title = "Total Uniform Load Capacity (kg/m)"

# --- Plotting ---
fig = go.Figure()

# Plot เส้น Limit
fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear Limit', line=dict(color='red', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment Limit', line=dict(color='orange', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection Limit', line=dict(color='green', dash='dash', width=1)))

# Plot เส้น Safe Capacity
fig.add_trace(go.Scatter(x=L_range, y=y_safe, name='Safe Capacity (Governing)', 
                         line=dict(color='black', width=4), mode='lines'))

# Logic การแบ่ง Zone สี
governing_idx = np.argmin([y_s, y_m, y_d], axis=0)
colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
labels = ['Shear Control', 'Moment Control', 'Deflection Control']

start_idx = 0
for i in range(1, len(L_range)):
    if governing_idx[i] != governing_idx[i-1] or i == len(L_range)-1:
        x0 = L_range[start_idx]
        x1 = L_range[i]
        zone_type = governing_idx[start_idx]
        
        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor=colors[zone_type], opacity=1,
            layer="below", line_width=0,
            annotation_text=labels[zone_type], 
            annotation_position="inside top" 
        )
        start_idx = i

fig.update_layout(
    title=f"Beam Capacity Chart ({section_name})",
    xaxis_title="Beam Span Length (m)",
    yaxis_title=y_title,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    yaxis=dict(rangemode="tozero")
)

max_y_view = np.max(y_safe) * 1.5
if y_axis_type == "End Shear Force (kg)":
     max_y_view = V_allow_kg * 1.5
fig.update_yaxes(range=[0, max_y_view])

st.plotly_chart(fig, use_container_width=True)

# --- ส่วนอธิบายสูตร (Documentation) ---
st.markdown("---")
st.subheader("📚 ที่มาการคำนวณและสูตร (Methodology)")

with st.expander("ดูรายละเอียดสูตรการคำนวณ (Click to expand)", expanded=False):
    st.markdown("""
    การคำนวณใช้วิธี **Allowable Stress Design (ASD)** สำหรับคานช่วงเดียว (Simple Beam) ที่รับน้ำหนักบรรทุกแผ่สม่ำเสมอ ($w$) โดยพิจารณา 3 เงื่อนไขหลัก:
    """)

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 1. แรงเฉือน (Shear Control)")
        st.markdown("ตรวจสอบแรงเฉือนสูงสุดที่หัวคาน ($V_{max}$) ไม่ให้เกินความสามารถรับแรงเฉือน ($V_{allow}$)")
        st.latex(r"V_{max} = \frac{w L}{2} \leq V_{allow}")
        st.latex(r"V_{allow} = 0.40 F_y A_w")
        st.info("💡 **สีแดงในกราฟ:** มักเกิดกับคานช่วงสั้น")

    with col2:
        st.markdown("#### 2. โมเมนต์ดัด (Moment Control)")
        st.markdown("ตรวจสอบโมเมนต์สูงสุดที่กลางคาน ($M_{max}$) ไม่ให้เกินโมเมนต์ที่ยอมให้ ($M_{allow}$)")
        st.latex(r"M_{max} = \frac{w L^2}{8} \leq M_{allow}")
        st.latex(r"M_{allow} = 0.60 F_y Z_x")
        st.info("💡 **สีส้มในกราฟ:** มักเกิดกับคานช่วงความยาวปานกลาง")

    st.markdown("#### 3. ระยะแอ่นตัว (Deflection Control)")
    st.markdown("ตรวจสอบระยะแอ่นตัวสูงสุด ($\delta_{max}$) ไม่ให้เกินมาตรฐาน ($L/360$)")
    st.latex(r"\delta_{max} = \frac{5 w L^4}{384 E I} \leq \frac{L}{360}")
    st.info("💡 **สีเขียวในกราฟ:** มักเกิดกับคานช่วงยาว (Long Span)")
    
    st.markdown("---")
    st.markdown("#### 🏁 สรุปการหา Safe Load ($w_{safe}$)")
    st.latex(r"w_{safe} = \min(w_{shear}, w_{moment}, w_{deflection}) - w_{beam}")
    st.caption("*หมายเหตุ: การคำนวณนี้เป็นการประมาณเบื้องต้น สมมติว่าหน้าตัด Compact และมีการค้ำยันด้านข้างเพียงพอ*")
