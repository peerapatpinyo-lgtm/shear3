import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS (Siam Yamato Steel) ---
# Format: Key = Name, Value = {W: kg/m, D: mm, tw: mm, Ix: cm4, Zx: cm3}
SYS_H_BEAMS = {
    # Series 100
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 76.5},
    # Series 125
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6,   "Ix": 847,    "Zx": 136},
    "H-125x125x6.5x9":  {"W": 23.8, "D": 125, "tw": 6.5, "Ix": 1360,   "Zx": 217},
    # Series 150
    "H-148x100x6x9":    {"W": 21.1, "D": 148, "tw": 6,   "Ix": 1020,   "Zx": 138},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 219},
    # Series 175
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5,   "Ix": 2040,   "Zx": 233},
    "H-175x175x7.5x11": {"W": 40.2, "D": 175, "tw": 7.5, "Ix": 2940,   "Zx": 330},
    # Series 200
    "H-194x150x6x9":    {"W": 30.6, "D": 194, "tw": 6,   "Ix": 2690,   "Zx": 277},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8,   "Ix": 4720,   "Zx": 472},
    # Series 250
    "H-244x175x7x11":   {"W": 44.1, "D": 244, "tw": 7,   "Ix": 6120,   "Zx": 502},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9,   "Ix": 10800,  "Zx": 867},
    # Series 300
    "H-294x200x8x12":   {"W": 56.8, "D": 294, "tw": 8,   "Ix": 11300,  "Zx": 771},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10,  "Ix": 20400,  "Zx": 1360},
    # Series 350
    "H-340x250x9x14":   {"W": 79.7, "D": 340, "tw": 9,   "Ix": 21700,  "Zx": 1280},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-350x350x12x19":  {"W": 137.0,"D": 350, "tw": 12,  "Ix": 40300,  "Zx": 2300},
    # Series 400
    "H-390x300x10x16":  {"W": 107.0,"D": 390, "tw": 10,  "Ix": 38700,  "Zx": 1980},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
    # Series 500+
    "H-488x300x11x18":  {"W": 128.0,"D": 488, "tw": 11,  "Ix": 71000,  "Zx": 2910},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 1910},
    "H-588x300x12x20":  {"W": 151.0,"D": 588, "tw": 12,  "Ix": 118000, "Zx": 4020},
    "H-600x200x11x17":  {"W": 106.0,"D": 600, "tw": 11,  "Ix": 77600,  "Zx": 2590},
    "H-700x300x13x24":  {"W": 185.0,"D": 700, "tw": 13,  "Ix": 201000, "Zx": 5760},
    "H-800x300x14x26":  {"W": 210.0,"D": 800, "tw": 14,  "Ix": 292000, "Zx": 7290},
    "H-900x300x16x28":  {"W": 243.0,"D": 900, "tw": 16,  "Ix": 404000, "Zx": 8980},
}

# --- 2. ฟังก์ชันคำนวณกราฟ (Keep for Graph Tab) ---
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

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N

# --- Main App ---
st.set_page_config(page_title="Detailed Beam Calculation", layout="wide")
st.title("🏗️ Beam Analysis Report & Full Calculation")

# Sidebar
st.sidebar.header("1. ตัวแปรตั้งต้น (Input)")
section_name = st.sidebar.selectbox("เลือกหน้าตัด (Section)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Yield Strength (Fy) [ksc]", value=2400)
E_val_gpa = st.sidebar.number_input("Elastic Modulus (E) [GPa]", value=200)

st.sidebar.markdown("---")
st.sidebar.header("2. เลือกจุดพิจารณา")
L_input = st.sidebar.slider("ความยาวช่วงคาน L (เมตร)", min_value=1.0, max_value=24.0, value=6.0, step=0.1)

# Tab Selection
tab1, tab2 = st.tabs(["📊 กราฟสรุป (Chart)", "📝 รายการคำนวณละเอียด (Detailed Calc)"])

# ================= TAB 1: GRAPH (ย่อไว้) =================
with tab1:
    max_graph_len = max(24.0, L_input * 1.5)
    L_range = np.linspace(0.5, max_graph_len, 300)
    w_s, w_m, w_d, V_allow_N = get_capacity_curves(L_range, Fy, E_val_gpa, props)
    w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
    w_safe = np.maximum(w_safe, 0)
    w_total_safe = w_safe + props['W']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection Limit', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name='Safe Capacity', line=dict(color='black', width=3)))
    current_idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[w_total_safe[current_idx]], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))
    
    fig.update_layout(height=450, xaxis_title="Length (m)", yaxis_title="Total Load (kg/m)", hovermode="x unified")
    fig.update_yaxes(range=[0, w_total_safe[current_idx]*2])
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 2: FULL CALCULATION (ตามขอ) =================
with tab2:
    st.markdown(f"## 📝 รายการคำนวณโครงสร้าง (Structural Calculation Report)")
    st.markdown(f"**Section:** {section_name} | **Span Length (L):** {L_input:.2f} m")
    
    # --- 1. เตรียมตัวแปร (Variables & Conversion) ---
    st.markdown("### 1. ข้อมูลการออกแบบ (Design Data)")
    
    # แปลงหน่วยให้ดูง่าย (cm, kg, ksc)
    E_ksc = (E_val_gpa * 1e9) / 98066.5 # แปลง Pa -> ksc
    D_cm = props['D'] / 10
    tw_cm = props['tw'] / 10
    Aw_cm2 = D_cm * tw_cm
    Ix_cm4 = props['Ix']
    Zx_cm3 = props['Zx']
    L_cm = L_input * 100
    
    col_var1, col_var2 = st.columns(2)
    with col_var1:
        st.markdown("**1.1 คุณสมบัติวัสดุ (Material Properties)**")
        st.write(f"- Yield Strength ($F_y$) = **{Fy:,.0f}** ksc")
        st.write(f"- Elastic Modulus ($E$) = {E_val_gpa} GPa $\\approx$ **{E_ksc:,.0f}** ksc")
    
    with col_var2:
        st.markdown("**1.2 คุณสมบัติหน้าตัด (Section Properties)**")
        st.write(f"- Depth ($D$) = {props['D']} mm = **{D_cm:.1f}** cm")
        st.write(f"- Web Thickness ($t_w$) = {props['tw']} mm = **{tw_cm:.2f}** cm")
        st.write(f"- Web Area ($A_w \\approx D \\cdot t_w$) = {D_cm:.1f} $\\times$ {tw_cm:.2f} = **{Aw_cm2:.2f}** cm²")
        st.write(f"- Moment of Inertia ($I_x$) = **{Ix_cm4:,.0f}** cm⁴")
        st.write(f"- Section Modulus ($Z_x$) = **{Zx_cm3:,.0f}** cm³")
        st.write(f"- Beam Weight ($w_{{beam}}$) = **{props['W']}** kg/m")

    st.markdown("---")

    # --- 2. SHEAR CHECK ---
    st.markdown("### 2. ความสามารถรับแรงเฉือน (Shear Capacity)")
    st.markdown("**Step 2.1: คำนวณแรงเฉือนที่ยอมให้ ($V_{allow}$)**")
    
    V_allow_kg = 0.40 * Fy * Aw_cm2
    
    st.latex(r"V_{allow} = 0.40 \times F_y \times A_w")
    st.latex(rf"V_{{allow}} = 0.40 \times {Fy} \times {Aw_cm2:.2f}")
    st.latex(rf"V_{{allow}} = \mathbf{{{V_allow_kg:,.0f}}} \text{{ kg}}")
    
    st.markdown("**Step 2.2: แปลงเป็นน้ำหนักบรรทุกแผ่สม่ำเสมอ ($w_s$)**")
    st.write("จากสูตรแรงเฉือนของคานช่วงเดียว: $V_{max} = \\frac{w L}{2} \\Rightarrow w = \\frac{2 V}{L}$")
    
    w_shear_load = (2 * V_allow_kg) / L_input
    
    st.latex(rf"w_s = \frac{{2 \times V_{{allow}}}}{{L}} = \frac{{2 \times {V_allow_kg:,.0f}}}{{{L_input}}}")
    st.latex(rf"w_s = \mathbf{{{w_shear_load:,.0f}}} \text{{ kg/m}} \quad \text{{(Total Load)}}")
    
    st.markdown("---")

    # --- 3. MOMENT CHECK ---
    st.markdown("### 3. ความสามารถรับโมเมนต์ดัด (Moment Capacity)")
    st.markdown("**Step 3.1: คำนวณโมเมนต์ที่ยอมให้ ($M_{allow}$)**")
    
    M_allow_kgcm = 0.60 * Fy * Zx_cm3
    M_allow_kgm = M_allow_kgcm / 100
    
    st.latex(r"M_{allow} = 0.60 \times F_y \times Z_x")
    st.latex(rf"M_{{allow}} = 0.60 \times {Fy} \times {Zx_cm3:.1f} = {M_allow_kgcm:,.0f} \text{{ kg-cm}}")
    st.latex(rf"M_{{allow}} = {M_allow_kgcm:,.0f} / 100 = \mathbf{{{M_allow_kgm:,.0f}}} \text{{ kg-m}}")
    
    st.markdown("**Step 3.2: แปลงเป็นน้ำหนักบรรทุกแผ่สม่ำเสมอ ($w_m$)**")
    st.write("จากสูตรโมเมนต์ของคานช่วงเดียว: $M_{max} = \\frac{w L^2}{8} \\Rightarrow w = \\frac{8 M}{L^2}$")
    
    w_moment_load = (8 * M_allow_kgm) / (L_input**2)
    
    st.latex(rf"w_m = \frac{{8 \times M_{{allow}}}}{{L^2}} = \frac{{8 \times {M_allow_kgm:,.0f}}}{{{L_input}^2}}")
    st.latex(rf"w_m = \frac{{{8 * M_allow_kgm:,.0f}}}{{{L_input**2:.2f}}} = \mathbf{{{w_moment_load:,.0f}}} \text{{ kg/m}} \quad \text{{(Total Load)}}")

    st.markdown("---")

    # --- 4. DEFLECTION CHECK ---
    st.markdown("### 4. ความสามารถรับการแอ่นตัว (Deflection Capacity)")
    st.markdown("**Step 4.1: คำนวณระยะแอ่นตัวที่ยอมให้ ($\delta_{allow}$)**")
    
    delta_allow_cm = L_cm / 360
    st.latex(rf"\delta_{{allow}} = \frac{{L}}{{360}} = \frac{{{L_cm:.0f} \text{{ cm}}}}{{360}} = \mathbf{{{delta_allow_cm:.2f}}} \text{{ cm}}")
    
    st.markdown("**Step 4.2: คำนวณน้ำหนักบรรทุกจากสูตรระยะแอ่น ($w_d$)**")
    st.write("จากสูตรระยะแอ่น: $\\delta = \\frac{5 w L^4}{384 E I} \\Rightarrow w = \\frac{384 E I \\delta}{5 L^4}$")
    st.warning("⚠️ หมายเหตุ: การคำนวณส่วนนี้จะใช้หน่วย kg และ cm เพื่อความถูกต้อง แล้วค่อยแปลงเป็น kg/m ตอนจบ")
    
    # Calc parts for display clarity
    numerator = 384 * E_ksc * Ix_cm4 * delta_allow_cm
    denominator = 5 * (L_cm**4)
    w_d_kg_cm = numerator / denominator
    w_deflect_load = w_d_kg_cm * 100 # convert to m
    
    st.latex(rf"w_d (\text{{kg/cm}}) = \frac{{384 \times ({E_ksc:,.0f}) \times {Ix_cm4:,.0f} \times {delta_allow_cm:.2f}}}{{5 \times ({L_cm:.0f})^4}}")
    
    # Show intermediate result of numerator/denominator if needed, but result is cleaner
    st.latex(rf"w_d = {w_d_kg_cm:.2f} \text{{ kg/cm}}")
    st.latex(rf"w_d = {w_d_kg_cm:.2f} \times 100 = \mathbf{{{w_deflect_load:,.0f}}} \text{{ kg/m}} \quad \text{{(Total Load)}}")
    
    st.markdown("---")
    
    # --- 5. CONCLUSION ---
    st.markdown("### 5. สรุปผลการพิจารณา (Conclusion)")
    
    vals = {'1. แรงเฉือน (Shear)': w_shear_load, '2. โมเมนต์ (Moment)': w_moment_load, '3. การแอ่นตัว (Deflection)': w_deflect_load}
    min_case = min(vals, key=vals.get)
    total_safe_load = vals[min_case]
    net_safe_load = total_safe_load - props['W']
    if net_safe_load < 0: net_safe_load = 0
    
    st.write("เปรียบเทียบน้ำหนักบรรทุกปลอดภัยรวม (Total Safe Load):")
    for k, v in vals.items():
        st.write(f"- {k}: {v:,.0f} kg/m")
        
    st.info(f"👉 **ตัวควบคุม (Governing Case) คือ: {min_case}** ที่ค่าน้อยที่สุด = **{total_safe_load:,.0f} kg/m**")
    
    st.markdown("#### ✅ คำนวณน้ำหนักบรรทุกปลอดภัยสุทธิ (Net Safe Load)")
    st.latex(r"w_{net} = w_{total} - w_{beam}")
    st.latex(rf"w_{{net}} = {total_safe_load:,.0f} - {props['W']} = \mathbf{{{net_safe_load:,.0f}}} \text{{ kg/m}}")
    
    st.success(f"สรุป: คาน {section_name} ที่ความยาว {L_input} เมตร รับน้ำหนักจรปลอดภัยได้ไม่เกิน **{net_safe_load:,.0f} kg/m**")
