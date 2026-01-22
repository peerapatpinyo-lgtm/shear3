import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS Beam Calculation: Detailed", layout="wide")

# --- 2. DATABASE (SYS H-BEAM Standard) ---
# D, tw (mm) | W (kg/m) | Ix (cm4) | Zx (cm3)
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 76.5},
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6,   "Ix": 847,    "Zx": 136},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 219},
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5,   "Ix": 2040,   "Zx": 233},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8,   "Ix": 4720,   "Zx": 472},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9,   "Ix": 10800,  "Zx": 867},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10,  "Ix": 20400,  "Zx": 1360},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 1910},
    "H-600x200x11x17":  {"W": 106.0,"D": 600, "tw": 11,  "Ix": 77600,  "Zx": 2590},
}

# --- 3. MATH ENGINE (Pure Metric: kg, cm) ---
def perform_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversions (เก็บทศนิยมละเอียดเพื่อความแม่นยำ)
    L_cm = L_m * 100.0
    E_ksc = E_gpa * 10197.162 # 1 GPa = 10197.162 ksc
    Ix = props['Ix']
    Zx = props['Zx']
    Aw = (props['D'] / 10.0) * (props['tw'] / 10.0) # mm -> cm
    
    # 3.2 Nominal Strength
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * Zx
    
    # 3.3 Design Strength
    if method == "ASD":
        V_cap = Vn / 1.50
        M_cap = Mn / 1.67
    else:
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn
        
    # 3.4 Uniform Load Calculation (kg/m)
    # Shear: w = 2V/L
    w_s_kgcm = (2 * V_cap) / L_cm
    w_s = w_s_kgcm * 100
    
    # Moment: w = 8M/L^2
    w_m_kgcm = (8 * M_cap) / (L_cm**2)
    w_m = w_m_kgcm * 100
    
    # Deflection: w = (384 E I delta) / (5 L^4)
    delta_allow = L_cm / 360.0
    w_d_kgcm = (384 * E_ksc * Ix * delta_allow) / (5 * (L_cm**4))
    w_d = w_d_kgcm * 100
    
    return {
        "Aw": Aw, "Ix": Ix, "Zx": Zx, "E_ksc": E_ksc, "L_cm": L_cm,
        "Vn": Vn, "Mn": Mn, "V_cap": V_cap, "M_cap": M_cap,
        "w_s": w_s, "w_m": w_m, "w_d": w_d,
        "delta_allow": delta_allow
    }

# --- 4. UI LAYOUT ---
st.title("🏗️ SYS H-Beam Design: Step-by-Step Calculation")

# Sidebar Inputs
with st.sidebar:
    st.header("Design Parameters")
    method = st.radio("Design Method", ["ASD", "LRFD"])
    section = st.selectbox("Section Size", list(SYS_H_BEAMS.keys()))
    Fy = st.number_input("Fy (ksc)", value=2400)
    E_gpa = st.number_input("E (GPa)", value=200)
    L_input = st.slider("Span Length (m)", 1.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
res = perform_calculation(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Graph & Zone", "📝 Detailed Calculation", "📚 Theory & References"])

# ===== TAB 1: GRAPH =====
with tab1:
    # Generate Data Points
    L_range = np.linspace(0.5, max(15, L_input*1.5), 200)
    ws_list, wm_list, wd_list = [], [], []
    
    # Pre-calculate constants for speed
    if method == "ASD":
        v_c, m_c = res['Vn']/1.5, res['Mn']/1.67
    else:
        v_c, m_c = 1.0*res['Vn'], 0.9*res['Mn']
        
    for l_val in L_range:
        l_cm = l_val * 100
        ws_list.append((2 * v_c / l_cm) * 100)
        wm_list.append((8 * m_c / l_cm**2) * 100)
        delta = l_cm / 360
        wd_list.append(((384 * res['E_ksc'] * res['Ix'] * delta) / (5 * l_cm**4)) * 100)

    w_safe = np.minimum(np.minimum(ws_list, wm_list), wd_list)
    cur_gov = min(res['w_s'], res['w_m'], res['w_d'])

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=ws_list, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=wm_list, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=wd_list, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_safe, name='Governing Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[cur_gov], mode='markers', marker=dict(size=15, color='blue', symbol='x'), name='Current Design'))

    # Logic to find exact transition points for coloring
    # Shear vs Moment: 2V/L = 8M/L^2 -> L = 4M/V
    L_trans1 = (4 * m_c) / v_c / 100 # m
    
    # Moment vs Deflection (Approximate intersection logic for visualization)
    # Use array argmin to find switch points
    gov_idx = np.argmin([ws_list, wm_list, wd_list], axis=0)
    
    # Draw Background Zones
    colors = ['rgba(255,0,0,0.1)', 'rgba(255,165,0,0.1)', 'rgba(0,128,0,0.1)']
    labels = ['Shear Zone', 'Moment Zone', 'Deflection Zone']
    
    start_i = 0
    for i in range(1, len(L_range)):
        if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
            fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], line_width=0, 
                          annotation_text=labels[gov_idx[start_i]], annotation_position="top right")
            start_i = i

    y_label = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load (kg/m)"
    fig.update_layout(height=550, xaxis_title="Length (m)", yaxis_title=y_label, title=f"Capacity Graph: {section}")
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: DETAILED CALCULATION (CORE REQUEST) =====
with tab2:
    st.markdown(f"### 📄 รายการคำนวณ: {section} ({method})")
    
    # 1. PROPERTIES
    st.markdown("#### 1. คุณสมบัติหน้าตัด (Section Properties)")
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.write(f"- **Depth ($D$):** {props['D']} mm")
        st.write(f"- **Web ($t_w$):** {props['tw']} mm")
        st.write(f"- **Span ($L$):** {L_input} m = {res['L_cm']:.0f} cm")
    with col_p2:
        st.write(f"- **Area Web ($A_w$):** $D \\times t_w = {props['D']/10} \\times {props['tw']/10} = {res['Aw']:.2f}$ cm²")
        st.write(f"- **Section Modulus ($Z_x$):** {res['Zx']} cm³")
        st.write(f"- **Moment of Inertia ($I_x$):** {res['Ix']:,} cm⁴")
        st.write(f"- **Elastic Modulus ($E$):** {res['E_ksc']:,.0f} ksc")
    
    st.divider()

    # 2. SHEAR CHECK
    st.markdown("#### 2. ตรวจสอบแรงเฉือน (Shear Capacity)")
    st.markdown("**สูตร:** $V_n = 0.60 \cdot F_y \cdot A_w$")
    st.latex(rf"V_n = 0.60 \times {Fy} \times {res['Aw']:.2f} = \mathbf{{{res['Vn']:,.0f}}} \text{{ kg}}")
    
    if method == "ASD":
        st.markdown("**ASD:** ใช้ Safety Factor $\Omega = 1.50$")
        st.latex(rf"V_{{allow}} = \frac{{V_n}}{{1.50}} = \frac{{{res['Vn']:,.0f}}}{{1.50}} = \mathbf{{{res['V_cap']:,.0f}}} \text{{ kg}}")
    else:
        st.markdown("**LRFD:** ใช้ Resistance Factor $\phi = 1.00$")
        st.latex(rf"V_u = 1.00 \times V_n = 1.00 \times {res['Vn']:,.0f} = \mathbf{{{res['V_cap']:,.0f}}} \text{{ kg}}")
        
    st.markdown("แปลงเป็นน้ำหนักแผ่ปลอดภัย ($w$):")
    st.latex(r"w_{shear} = \frac{2 \cdot V}{L}")
    st.latex(rf"w_{{shear}} = \frac{{2 \times {res['V_cap']:,.0f}}}{{{res['L_cm']:.0f}}} \times 100 (\text{{to m}}) = \mathbf{{{res['w_s']:,.0f}}} \text{{ kg/m}}")
    
    st.divider()

    # 3. MOMENT CHECK
    st.markdown("#### 3. ตรวจสอบโมเมนต์ดัด (Moment Capacity)")
    st.markdown("**สูตร:** $M_n = F_y \cdot Z_x$")
    st.latex(rf"M_n = {Fy} \times {res['Zx']} = \mathbf{{{res['Mn']:,.0f}}} \text{{ kg-cm}}")
    
    if method == "ASD":
        st.markdown("**ASD:** ใช้ Safety Factor $\Omega = 1.67$")
        st.latex(rf"M_{{allow}} = \frac{{M_n}}{{1.67}} = \frac{{{res['Mn']:,.0f}}}{{1.67}} = \mathbf{{{res['M_cap']:,.0f}}} \text{{ kg-cm}}")
    else:
        st.markdown("**LRFD:** ใช้ Resistance Factor $\phi = 0.90$")
        st.latex(rf"M_u = 0.90 \times M_n = 0.90 \times {res['Mn']:,.0f} = \mathbf{{{res['M_cap']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("แปลงเป็นน้ำหนักแผ่ปลอดภัย ($w$):")
    st.latex(r"w_{moment} = \frac{8 \cdot M}{L^2}")
    st.latex(rf"w_{{moment}} = \frac{{8 \times {res['M_cap']:,.0f}}}{{{res['L_cm']:.0f}^2}} \times 100 (\text{{to m}}) = \mathbf{{{res['w_m']:,.0f}}} \text{{ kg/m}}")
    
    st.divider()

    # 4. DEFLECTION CHECK
    st.markdown("#### 4. ตรวจสอบระยะแอ่นตัว (Deflection Limit)")
    st.markdown(f"**เกณฑ์ยอมรับ:** $\delta_{{max}} = L/360$")
    st.latex(rf"\delta_{{allow}} = \frac{{{res['L_cm']:.0f}}}{{360}} = \mathbf{{{res['delta_allow']:.2f}}} \text{{ cm}}")
    
    st.markdown("หาน้ำหนักแผ่ที่ทำให้แอ่นตัวเท่ากับพิกัด ($w$):")
    st.latex(r"w_{deflect} = \frac{384 \cdot E \cdot I \cdot \delta_{allow}}{5 \cdot L^4}")
    
    # แสดงการแทนค่าแบบละเอียด
    num_str = f"384 \\times {res['E_ksc']:,.0f} \\times {res['Ix']:,} \\times {res['delta_allow']:.2f}"
    den_str = f"5 \\times {res['L_cm']:.0f}^4"
    st.latex(rf"w = \frac{{{num_str}}}{{{den_str}}}")
    
    val_kgcm = (384 * res['E_ksc'] * res['Ix'] * res['delta_allow']) / (5 * res['L_cm']**4)
    st.latex(rf"w_{{deflect}} = {val_kgcm:.4f} \text{{ kg/cm}} \times 100 = \mathbf{{{res['w_d']:,.0f}}} \text{{ kg/m}}")
    
    st.divider()
    
    # 5. CONCLUSION
    st.success(f"✅ **ความสามารถในการรับน้ำหนัก (Governing Capacity): {min(res['w_s'], res['w_m'], res['w_d']):,.0f} kg/m**")
    st.warning(f"**Net Safe Load (หักน้ำหนักคาน {props['W']} kg/m):** {max(min(res['w_s'], res['w_m'], res['w_d']) - props['W'], 0):,.0f} kg/m")

# ===== TAB 3: THEORY =====
with tab3:
    st.markdown("### 📚 ทฤษฎีและที่มาของกราฟ (Theory)")
    
    st.info("กราฟนี้สร้างขึ้นโดยการหาค่าน้อยที่สุด (Envelope) จาก 3 สมการหลัก ดังนี้:")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        st.subheader("1. Shear Control")
        st.write("จะเกิดขี้นในช่วง **คานสั้น**")
        st.latex(r"w = \frac{2 V_{cap}}{L}")
        st.write("กราฟเป็นเส้นโค้ง Hyperbola ($1/L$) แต่ชันมาก")
        
    with col_t2:
        st.subheader("2. Moment Control")
        st.write("จะเกิดขึ้นในช่วง **คานยาวปานกลาง**")
        st.latex(r"w = \frac{8 M_{cap}}{L^2}")
        st.write("กราฟเป็นเส้นโค้ง Parabola ($1/L^2$) ความชันลดลงเร็วกว่า Shear")

    with col_t3:
        st.subheader("3. Deflection Control")
        st.write("จะเกิดขึ้นในช่วง **คานยาวมาก**")
        st.latex(r"w \propto \frac{1}{L^3}")
        st.write("เนื่องจาก $\delta = L/360$ (เป็นฟังก์ชันของ L) เมื่อแทนในสูตรหลัก $1/L^4$ จะเหลือ $1/L^3$")

    st.markdown("---")
    st.subheader("📍 จุดเปลี่ยนโหมด (Transition Points)")
    
    st.write("**1. จุดตัด Shear ↔ Moment:**")
    st.write("หาได้จากการจับสมการเท่ากัน $2V/L = 8M/L^2$")
    st.latex(r"L_{transition} = \frac{4 M_{cap}}{V_{cap}}")
    l_trans_val = (4 * res['M_cap']) / res['V_cap'] / 100
    st.write(f"สำหรับหน้าตัดนี้ จุดตัดอยู่ที่ $L = {l_trans_val:.2f}$ m (ถ้าน้อยกว่านี้ Shear คุม)")

    st.write("**2. จุดตัด Moment ↔ Deflection:**")
    st.write("ขึ้นอยู่กับค่า $E$ และ $I$ เทียบกับ $F_y$ ยิ่งคานยาว Deflection จะยิ่งมีผลมาก")
