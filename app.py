import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Full Calculation", layout="wide")

# --- 2. DATABASE ---
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

# --- 3. MATH ENGINE ---
def calculate_details(L_m, Fy_ksc, E_gpa, props, method):
    # Units
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    
    # Props
    Ix = props['Ix']
    Zx = props['Zx']
    Aw = (props['D']/10.0) * (props['tw']/10.0) # cm2
    
    # 1. Nominal Strength
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * Zx
    
    # 2. Design Strength & Factors
    if method == "ASD":
        factor_v_str, factor_b_str = r"\Omega_v = 1.50", r"\Omega_b = 1.67"
        V_cap = Vn / 1.50
        M_cap = Mn / 1.67
        design_v_str = r"V_{allow} = \frac{V_n}{\Omega_v}"
        design_m_str = r"M_{allow} = \frac{M_n}{\Omega_b}"
    else:
        factor_v_str, factor_b_str = r"\phi_v = 1.00", r"\phi_b = 0.90"
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn
        design_v_str = r"V_u = \phi_v V_n"
        design_m_str = r"M_u = \phi_b M_n"
        
    # 3. Load Conversions (kg/m)
    # Shear: w = 2V/L
    ws = (2 * V_cap / L_cm) * 100
    # Moment: w = 8M/L^2
    wm = (8 * M_cap / L_cm**2) * 100
    # Deflection
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * Ix * delta_allow) / (5 * L_cm**4)) * 100
    
    return {
        "Aw": Aw, "Vn": Vn, "Mn": Mn, "V_cap": V_cap, "M_cap": M_cap,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta_allow": delta_allow,
        "factor_v_str": factor_v_str, "factor_b_str": factor_b_str,
        "design_v_str": design_v_str, "design_m_str": design_m_str
    }

# --- 4. UI ---
st.title("🏗️ SYS H-Beam: รายการคำนวณฉบับสมบูรณ์")

with st.sidebar:
    st.header("Input Data")
    method = st.radio("Method", ["ASD", "LRFD"])
    section = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
    Fy = st.number_input("Fy (ksc)", value=2400)
    E_gpa = st.number_input("E (GPa)", value=200)
    L_input = st.slider("Span (m)", 1.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = calculate_details(L_input, Fy, E_gpa, props, method)
w_gross = min(cal['ws'], cal['wm'], cal['wd'])
w_net = max(w_gross - props['W'], 0)

# --- TABS ---
tab_graph, tab_sheet = st.tabs(["📊 Capacity Graph", "📝 Detailed Calculation Sheet"])

# TAB 1: GRAPH (Brief)
with tab_graph:
    # Generate Curve Data
    L_range = np.linspace(0.5, max(15, L_input*1.5), 200)
    y_s, y_m, y_d = [], [], []
    v_c, m_c = cal['V_cap'], cal['M_cap']
    
    for l in L_range:
        l_cm = l*100
        y_s.append(2*v_c/l_cm*100)
        y_m.append(8*m_c/l_cm**2*100)
        y_d.append((384*cal['E_ksc']*props['Ix']*(l_cm/360))/(5*l_cm**4)*100)
    
    y_gov = np.minimum(np.minimum(y_s, y_m), y_d)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[w_gross], mode='markers', marker=dict(size=15, color='blue', symbol='x'), name='Current'))
    
    st.plotly_chart(fig, use_container_width=True)

# TAB 2: DETAILED CALCULATION
with tab_sheet:
    st.markdown(f"### 📄 รายการคำนวณโครงสร้างคานเหล็ก: {section}")
    st.markdown("---")
    
    # 1. Properties
    st.markdown("#### 1. ข้อมูลการออกแบบและคุณสมบัติหน้าตัด")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"- **หน้าตัด:** {section}")
        st.write(f"- **ความยาวคาน ($L$):** {L_input} m = {cal['L_cm']:.0f} cm")
        st.write(f"- **กำลังจุดคราก ($F_y$):** {Fy} ksc")
        st.write(f"- **น้ำหนักคาน ($W_{{beam}}$):** {props['W']} kg/m")
    with c2:
        st.write(f"- **พื้นที่รับแรงเฉือน ($A_w$):** {cal['Aw']:.2f} cm²")
        st.write(f"- **โมดูลัสหน้าตัด ($Z_x$):** {props['Zx']:,} cm³")
        st.write(f"- **โมเมนต์อินเนอร์เชีย ($I_x$):** {props['Ix']:,} cm⁴")
        st.write(f"- **โมดูลัสยืดหยุ่น ($E$):** {cal['E_ksc']:,.0f} ksc")
    
    st.markdown("---")
    
    # 2. Shear
    st.markdown("#### 2. คำนวณความสามารถรับแรงเฉือน (Shear Check)")
    st.write("2.1 หาแรงเฉือนระบุ ($V_n$) และค่าที่ยอมให้:")
    st.latex(rf"V_n = 0.60 F_y A_w = 0.60 \times {Fy} \times {cal['Aw']:.2f} = {cal['Vn']:,.0f} \text{{ kg}}")
    st.latex(rf"{cal['design_v_str']} \Rightarrow \text{{ใช้ }} {cal['factor_v_str']}")
    st.latex(rf"V_{{design}} = {cal['V_cap']:,.0f} \text{{ kg}}")
    
    st.write("2.2 แปลงเป็นน้ำหนักแผ่ประลัยบนคาน ($w_{shear}$):")
    st.info("สำหรับคานช่วงเดียว (Simple Beam) แรงเฉือนสูงสุดคือ $V_{max} = wL/2$ ดังนั้น $w = 2V/L$")
    st.latex(rf"w_{{shear}} = \frac{{2 \times V_{{design}}}}{{L}} = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100")
    st.latex(rf"w_{{shear}} = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}} \quad \text{--- (1)}")
    
    st.markdown("---")
    
    # 3. Moment
    st.markdown("#### 3. คำนวณความสามารถรับโมเมนต์ดัด (Moment Check)")
    st.write("3.1 หาโมเมนต์ระบุ ($M_n$) และค่าที่ยอมให้:")
    st.latex(rf"M_n = F_y Z_x = {Fy} \times {props['Zx']} = {cal['Mn']:,.0f} \text{{ kg-cm}}")
    st.latex(rf"{cal['design_m_str']} \Rightarrow \text{{ใช้ }} {cal['factor_b_str']}")
    st.latex(rf"M_{{design}} = {cal['M_cap']:,.0f} \text{{ kg-cm}}")
    
    st.write("3.2 แปลงเป็นน้ำหนักแผ่ประลัยบนคาน ($w_{moment}$):")
    st.info("สำหรับคานช่วงเดียว โมเมนต์สูงสุดคือ $M_{max} = wL^2/8$ ดังนั้น $w = 8M/L^2$")
    st.latex(rf"w_{{moment}} = \frac{{8 \times M_{{design}}}}{{L^2}} = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100")
    st.latex(rf"w_{{moment}} = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}} \quad \text{--- (2)}")
    
    st.markdown("---")
    
    # 4. Deflection
    st.markdown("#### 4. ตรวจสอบการแอ่นตัว (Deflection Check)")
    st.write("4.1 ระยะแอ่นตัวที่ยอมให้ ($\delta_{max}$):")
    st.latex(rf"\delta_{{allow}} = L/360 = {cal['L_cm']:.0f}/360 = {cal['delta_allow']:.2f} \text{{ cm}}")
    
    st.write("4.2 หาน้ำหนักแผ่ที่ทำให้เกิดการแอ่นตัวพิกัด ($w_{deflect}$):")
    st.info("สูตรระยะแอ่นตัว: $\delta = 5wL^4 / 384EI \Rightarrow$ ย้ายข้างหา $w$")
    
    num = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w_{{deflect}} = \frac{{384 E I \delta}}{{5 L^4}} = \frac{{{num}}}{{{den}}} \times 100")
    st.latex(rf"w_{{deflect}} = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}} \quad \text{--- (3)}")
    
    st.markdown("---")
    
    # 5. Summary & Logic (THE FINAL STEP)
    st.markdown("#### 5. สรุปผลการคำนวณ (Conclusion)")
    st.write("**ขั้นตอนสุดท้าย: เปรียบเทียบค่าทั้ง 3 กรณีเพื่อหาจุดวิกฤต**")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("1. Shear Limit", f"{cal['ws']:,.0f} kg/m")
    col_res2.metric("2. Moment Limit", f"{cal['wm']:,.0f} kg/m")
    col_res3.metric("3. Deflection Limit", f"{cal['wd']:,.0f} kg/m")
    
    st.write("เลือกค่าน้อยที่สุดเป็น **Total Capacity (Gross Load)**:")
    st.latex(rf"w_{{gross}} = \min({cal['ws']:,.0f}, {cal['wm']:,.0f}, {cal['wd']:,.0f}) = \mathbf{{{w_gross:,.0f}}} \text{{ kg/m}}")
    
    st.write(f"**หักน้ำหนักตัวเองของคานออก ($W_{{beam}} = {props['W']}$ kg/m):**")
    st.latex(rf"w_{{net}} = w_{{gross}} - W_{{beam}} = {w_gross:,.0f} - {props['W']}")
    
    # Final Result Box
    st.success(f"✅ **น้ำหนักบรรทุกปลอดภัยสุทธิ (Safe Superimposed Load) = {w_net:,.0f} kg/m**")
    if method == "ASD":
        st.caption("ค่านี้คือ Safe Load (DL+LL) ที่ใช้งานได้จริง")
    else:
        st.caption("ค่านี้คือ Factored Load ($w_u$) ที่คานรับได้เพิ่มเติมนอกเหนือจากน้ำหนักตัวเอง")
