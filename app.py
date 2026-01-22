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

# --- 2. ฟังก์ชันคำนวณกราฟ (สำหรับ plot) ---
def get_capacity_curves(lengths, Fy_ksc, E_gpa, props):
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    V_allow_N = 0.40 * Fy_pa * Aw 
    M_allow_N = 0.60 * Fy_pa * Zx
    
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        w_s = (2 * V_allow_N) / L
        w_m = (8 * M_allow_N) / (L**2)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N/g

# --- Main App ---
st.set_page_config(page_title="Detailed Beam Analysis", layout="wide")
st.title("🏗️ Beam Capacity: Calculation & Analysis")

# Sidebar
st.sidebar.header("1. เลือกหน้าตัดและวัสดุ")
section_name = st.sidebar.selectbox("Select H-Beam", list(STEEL_SECTIONS.keys()))
props = STEEL_SECTIONS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val = st.sidebar.number_input("E (GPa)", value=200)

st.sidebar.header("2. เลือกความยาวเพื่อดูวิธีทำ")
# Slider นี้ใช้ทั้งปรับกราฟและแสดงวิธีทำ
L_input = st.sidebar.slider("ความยาวคาน L (m)", min_value=1.0, max_value=20.0, value=6.0, step=0.1)
max_graph_len = max(20.0, L_input * 1.5)

# --- ส่วนที่ 1: กราฟ (เหมือนเดิมแต่ตัดทอนให้กระชับ) ---
st.subheader("1. กราฟวิเคราะห์พฤติกรรม (Span vs Capacity)")
L_range = np.linspace(0.5, max_graph_len, 200)
w_s, w_m, w_d, V_allow_kg = get_capacity_curves(L_range, Fy, E_val, props)
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)

y_safe = w_safe + props['W'] # Plot total load for clarity

fig = go.Figure()
fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection Limit', line=dict(color='green', dash='dash', width=1)))
fig.add_trace(go.Scatter(x=L_range, y=y_safe, name='Total Safe Capacity', line=dict(color='black', width=4)))

# เพิ่มจุด L ปัจจุบัน
current_idx = (np.abs(L_range - L_input)).argmin()
current_val = y_safe[current_idx]
fig.add_trace(go.Scatter(x=[L_input], y=[current_val], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))

# แบ่ง Zone สี
governing_idx = np.argmin([w_s, w_m, w_d], axis=0)
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

fig.update_layout(height=400, margin=dict(t=30, b=0), xaxis_title="Length (m)", yaxis_title="Total Load Capacity (kg/m)", hovermode="x unified")
fig.update_yaxes(range=[0, current_val * 2.5]) # Zoom ให้เห็นค่าปัจจุบันชัดๆ
st.plotly_chart(fig, use_container_width=True)

# --- ส่วนที่ 2: แสดงวิธีทำละเอียด (Calculations) ---
st.markdown("---")
st.subheader(f"2. แสดงวิธีคำนวณที่ระยะ L = {L_input} เมตร")

# เตรียมตัวแปร (Variables Preparation)
g = 9.81
Fy_Pa = Fy * 98066.5
E_Pa = E_val * 1e9
Aw_m2 = (props['D']/1000) * (props['tw']/1000)
Zx_m3 = props['Zx'] * 1e-6
Ix_m4 = props['Ix'] * 1e-8

# คำนวณค่า Limit (SI Unit)
# 1. Shear
V_allow_SI = 0.40 * Fy_Pa * Aw_m2
w_shear_SI = (2 * V_allow_SI) / L_input
w_shear_kg = w_shear_SI / g

# 2. Moment
M_allow_SI = 0.60 * Fy_Pa * Zx_m3
w_moment_SI = (8 * M_allow_SI) / (L_input**2)
w_moment_kg = w_moment_SI / g

# 3. Deflection
delta_allow_SI = L_input / 360.0
w_deflect_SI = (384 * E_Pa * Ix_m4 * delta_allow_SI) / (5 * L_input**4)
w_deflect_kg = w_deflect_SI / g

# หาตัว Control
vals = {'Shear': w_shear_kg, 'Moment': w_moment_kg, 'Deflection': w_deflect_kg}
control_case = min(vals, key=vals.get)
safe_load_total = vals[control_case]
safe_load_net = safe_load_total - props['W']
if safe_load_net < 0: safe_load_net = 0

# --- แสดงผล (Display Layout) ---
c1, c2, c3 = st.columns(3)

# Function ช่วย format ตัวเลข
def fmt(val): return f"{val:,.2f}"
def sci(val): return f"{val:.2e}" # Scientific notation

with c1:
    st.markdown("### 🟥 1. Check Shear")
    st.caption("แรงเฉือนที่ยอมให้ ($0.4F_y A_w$):")
    st.latex(rf"V_{{all}} = 0.4 \times {Fy_Pa:.0f} \times {Aw_m2:.6f} = {V_allow_SI/1000:,.1f} \text{{ kN}}")
    st.caption(f"หาน้ำหนักแผ่ $w$ จาก $V_{{max}} = wL/2$:")
    st.latex(rf"w_s = \frac{{2 \times V_{{all}}}}{{L}} = \frac{{2 \times {V_allow_SI:.0f}}}{{{L_input}}}")
    st.metric("Shear Capacity", f"{w_shear_kg:,.0f} kg/m")

with c2:
    st.markdown("### 🟧 2. Check Moment")
    st.caption("โมเมนต์ที่ยอมให้ ($0.6F_y Z_x$):")
    st.latex(rf"M_{{all}} = 0.6 \times {Fy_Pa:.0f} \times {Zx_m3:.6f} = {M_allow_SI/1000:,.1f} \text{{ kNm}}")
    st.caption(f"หาน้ำหนักแผ่ $w$ จาก $M_{{max}} = wL^2/8$:")
    st.latex(rf"w_m = \frac{{8 \times M_{{all}}}}{{L^2}} = \frac{{8 \times {M_allow_SI:.0f}}}{{{L_input}^2}}")
    st.metric("Moment Capacity", f"{w_moment_kg:,.0f} kg/m")

with c3:
    st.markdown("### 🟩 3. Check Deflection")
    st.caption("ระยะแอ่นที่ยอมให้ ($L/360$):")
    st.latex(rf"\delta_{{all}} = \frac{{{L_input}}}{{360}} = {delta_allow_SI*1000:.2f} \text{{ mm}}")
    st.caption(f"หาน้ำหนักแผ่ $w$ จาก $\delta = 5wL^4/384EI$:")
    st.latex(rf"w_d = \frac{{384 E I \delta_{{all}}}}{{5 L^4}} = \frac{{384 \cdot {E_Pa:.1e} \cdot {Ix_m4:.1e} \cdot {delta_allow_SI:.4f}}}{{5 \cdot {L_input}^4}}")
    st.metric("Deflection Capacity", f"{w_deflect_kg:,.0f} kg/m")

st.markdown("---")

# --- ส่วนสรุป (Conclusion) ---
final_col1, final_col2 = st.columns([2, 1])

with final_col1:
    st.subheader(f"🎯 บทสรุปที่ L = {L_input} เมตร")
    st.markdown(f"""
    จากการเปรียบเทียบทั้ง 3 กรณี พบว่าค่าน้อยที่สุดคือ:
    ### **{control_case} Control**
    
    1. **Total Safe Load** (รวมน้ำหนักคาน) = **{safe_load_total:,.0f} kg/m**
    2. **Beam Weight** (น้ำหนักคาน) = **{props['W']} kg/m**
    3. **Net Safe Load** (น้ำหนักบรรทุกปลอดภัยสุทธิ) = {safe_load_total:,.0f} - {props['W']}
    """)
    
    st.success(f"✅ สรุป: รับน้ำหนักภายนอกได้สูงสุด = {safe_load_net:,.0f} kg/m")

with final_col2:
    # Visual Indicator
    if control_case == "Shear":
        st.error("⚠️ Shear Control (วิกฤตที่แรงเฉือน)")
    elif control_case == "Moment":
        st.warning("⚠️ Moment Control (วิกฤตที่การดัด)")
    else:
        st.success("⚠️ Deflection Control (วิกฤตที่การแอ่นตัว)")
        
    st.write("หมายเหตุ:")
    st.write("- การคำนวณใช้หน่วย SI (Pa, N, m) เพื่อความแม่นยำ")
    st.write("- แสดงผลลัพธ์สุดท้ายเป็น kg/m ($g=9.81$)")
