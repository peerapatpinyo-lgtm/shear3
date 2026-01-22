import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="SYS H-Beam: Complete Analysis", layout="wide")

# --- 2. DATABASE (SYS Standard) ---
# Units: D, tw (mm) | W (kg/m) | Ix (cm4) | Zx (cm3)
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
def core_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversions
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    Ix = props['Ix']
    Zx = props['Zx']
    
    # 3.2 Strengths
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * Zx
    
    if method == "ASD":
        V_cap = Vn / 1.50
        M_cap = Mn / 1.67
    else:
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn
        
    # 3.3 Loads at Current Span (w)
    # Shear
    ws = (2 * V_cap / L_cm) * 100
    # Moment
    wm = (8 * M_cap / L_cm**2) * 100
    # Deflection (Limit L/360)
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * Ix * delta_allow) / (5 * L_cm**4)) * 100
    
    # 3.4 Transition Points (The "Control Zone" Logic)
    # Point 1: Shear intersects Moment (2V/L = 8M/L^2) -> L = 4M/V
    L_trans_VM_cm = (4 * M_cap) / V_cap
    
    # Point 2: Moment intersects Deflection (8M/L^2 = 384EI(L/360)/5L^4)
    # Simplify: 8M/L^2 = 384EI / (1800 L^3) -> L = 384EI / (14400 M)
    L_trans_MD_cm = (384 * E_ksc * Ix) / (14400 * M_cap)
    
    return {
        "Aw": Aw, "Ix": Ix, "Zx": Zx, "E_ksc": E_ksc,
        "Vn": Vn, "Mn": Mn, "V_cap": V_cap, "M_cap": M_cap,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "delta_allow": delta_allow,
        "L_VM_m": L_trans_VM_cm / 100.0,
        "L_MD_m": L_trans_MD_cm / 100.0
    }

# --- 4. UI ---
st.title("🏗️ SYS H-Beam: Complete Analysis & Control Zones")
st.sidebar.header("Input Parameters")
method = st.sidebar.radio("Method", ["ASD", "LRFD"])
section = st.sidebar.selectbox("Section", list(SYS_H_BEAMS.keys()))
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_gpa = st.sidebar.number_input("E (GPa)", value=200)
L_input = st.sidebar.slider("Span (m)", 1.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = core_calculation(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab_graph, tab_calc, tab_info = st.tabs(["📊 Graph & Zones", "📝 Detailed Calculation", "📚 Formula Reference"])

# ===== TAB 1: GRAPH =====
with tab_graph:
    # Prepare Data for plotting
    L_max = max(15, cal['L_MD_m'] * 1.2, L_input * 1.5)
    L_range = np.linspace(0.1, L_max, 400)
    
    ys, ym, yd = [], [], []
    v_c, m_c = cal['V_cap'], cal['M_cap']
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 # Combined constant for deflection
    
    for l in L_range:
        l_cm = l * 100
        ys.append(2 * v_c / l_cm * 100)
        ym.append(8 * m_c / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100) # derived from substituting delta=L/360
        
    y_final = np.minimum(np.minimum(ys, ym), yd)
    cur_w = min(cal['ws'], cal['wm'], cal['wd'])
    
    fig = go.Figure()
    
    # 1. Background Zones (Control Areas)
    # Zone 1: Shear (0 to L_VM)
    fig.add_vrect(x0=0, x1=cal['L_VM_m'], fillcolor="rgba(255, 0, 0, 0.1)", line_width=0, 
                  annotation_text="SHEAR CONTROL", annotation_position="top left")
    # Zone 2: Moment (L_VM to L_MD)
    fig.add_vrect(x0=cal['L_VM_m'], x1=cal['L_MD_m'], fillcolor="rgba(255, 165, 0, 0.1)", line_width=0,
                  annotation_text="MOMENT CONTROL", annotation_position="top center")
    # Zone 3: Deflection (L_MD onwards)
    fig.add_vrect(x0=cal['L_MD_m'], x1=L_max, fillcolor="rgba(0, 128, 0, 0.1)", line_width=0,
                  annotation_text="DEFLECTION CONTROL", annotation_position="top right")

    # 2. Curves
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_final, name='Governing Capacity', line=dict(color='black', width=4)))
    
    # 3. User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[cur_w], mode='markers', marker=dict(size=15, color='blue', symbol='x'), name='Your Design'))

    fig.update_layout(height=600, title=f"Capacity Envelope: {section}", xaxis_title="Span Length (m)", yaxis_title="Load (kg/m)", yaxis_range=[0, max(cur_w*2, 2000)])
    st.plotly_chart(fig, use_container_width=True)


# ===== TAB 2: CALCULATION SHEET (THE CORE REQUEST) =====
with tab_calc:
    st.markdown(f"### 📄 รายการคำนวณ: {section} ({method})")
    
    # --- Part 1: Initial Data ---
    st.markdown("#### 1. ข้อมูลและคุณสมบัติ (Properties)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"- $L = {L_input}$ m")
        st.write(f"- $F_y = {Fy}$ ksc")
        st.write(f"- $E = {cal['E_ksc']:,.0f}$ ksc")
    with c2:
        st.write(f"- $A_w = {cal['Aw']:.2f}$ cm²")
        st.write(f"- $Z_x = {props['Zx']}$ cm³")
        st.write(f"- $I_x = {props['Ix']:,}$ cm⁴")
    st.markdown("---")

    # --- Part 2: Load Calculations ---
    st.markdown("#### 2. คำนวณความสามารถรับน้ำหนัก (Load Capacity)")
    
    # 2.1 Shear
    st.markdown("**2.1 กรณีแรงเฉือน (Shear Control)**")
    st.latex(rf"V_{{cap}} = \frac{{0.6 F_y A_w}}{{\Omega/\phi}} \rightarrow \text{{(ขึ้นอยู่กับ ASD/LRFD)}}")
    st.latex(rf"V_{{cap}} = {cal['V_cap']:,.0f} \text{{ kg}}")
    
    st.write("สูตรหา Load ($w_s$):")
    st.latex(r"w_s = \frac{2 V_{cap}}{L}")
    st.write("แทนค่า:")
    st.latex(rf"w_s = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")

    # 2.2 Moment
    st.markdown("**2.2 กรณีโมเมนต์ (Moment Control)**")
    st.latex(rf"M_{{cap}} = \frac{{F_y Z_x}}{{\Omega/\phi}}")
    st.latex(rf"M_{{cap}} = {cal['M_cap']:,.0f} \text{{ kg-cm}}")
    
    st.write("สูตรหา Load ($w_m$):")
    st.latex(r"w_m = \frac{8 M_{cap}}{L^2}")
    st.write("แทนค่า:")
    st.latex(rf"w_m = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")

    # 2.3 Deflection
    st.markdown("**2.3 กรณีระยะแอ่นตัว (Deflection Control)**")
    st.write("พิกัดการแอ่นตัว ($\delta = L/360$):")
    st.latex(rf"\delta = {cal['L_cm']:.0f} / 360 = {cal['delta_allow']:.2f} \text{{ cm}}")
    
    st.write("สูตรหา Load ($w_d$):")
    st.latex(r"w_d = \frac{384 E I \delta}{5 L^4}")
    st.write("แทนค่า:")
    num_str = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den_str = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w_d = \frac{{{num_str}}}{{{den_str}}} \times 100 = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- Part 3: CONTROL ZONE ANALYSIS (NEW & CRITICAL) ---
    st.markdown("#### 3. วิเคราะห์ช่วง Control (Transition Points Analysis)")
    st.info("ส่วนนี้คำนวณหาจุดตัดกราฟ เพื่อดูว่าที่ความยาวปัจจุบัน พฤติกรรมใดเป็นตัวควบคุม (Governing)")

    # 3.1 Point 1 (Shear vs Moment)
    st.subheader("🅰️ จุดเปลี่ยน Shear $\\to$ Moment ($L_{v-m}$)")
    st.write("เกิดเมื่อความสามารถรับแรงเฉือน เท่ากับ ความสามารถรับโมเมนต์")
    st.latex(r"w_s = w_m \Rightarrow \frac{2V}{L} = \frac{8M}{L^2}")
    st.write("ย้ายข้างหาค่า $L$:")
    st.latex(r"L_{v-m} = \frac{4 M_{cap}}{V_{cap}}")
    st.write("แทนค่า:")
    st.latex(rf"L_{{v-m}} = \frac{{4 \times {cal['M_cap']:,.0f}}}{{{cal['V_cap']:,.0f}}} = {cal['L_VM_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_VM_m']:.2f}}} \text{{ m}}")

    # 3.2 Point 2 (Moment vs Deflection)
    st.subheader("🅱️ จุดเปลี่ยน Moment $\\to$ Deflection ($L_{m-d}$)")
    st.write("เกิดเมื่อความสามารถรับโมเมนต์ เท่ากับ ขีดจำกัดระยะแอ่นตัว")
    st.latex(r"w_m = w_d \Rightarrow \frac{8M}{L^2} = \frac{384EI}{1800 L^3}")
    st.write("ย้ายข้างหาค่า $L$:")
    st.latex(r"L_{m-d} = \frac{384 E I}{14400 M_{cap}}")
    st.write("แทนค่า:")
    num_md = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,}"
    den_md = f"14400 \\times {cal['M_cap']:,.0f}"
    st.latex(rf"L_{{m-d}} = \frac{{{num_md}}}{{{den_md}}} = {cal['L_MD_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_MD_m']:.2f}}} \text{{ m}}")

    # 3.3 Conclusion Logic
    st.markdown("#### 4. สรุปผลการตรวจสอบ (Final Logic)")
    st.write(f"ความยาวคานปัจจุบันของคุณคือ **$L = {L_input}$ m**")
    
    if L_input <= cal['L_VM_m']:
        st.error(f"📍 ผลลัพธ์: $L < {cal['L_VM_m']:.2f}$ m ดังนั้น **Shear Control** (แรงเฉือนเป็นตัวคุม)")
        gov_load = cal['ws']
    elif L_input <= cal['L_MD_m']:
        st.warning(f"📍 ผลลัพธ์: ${cal['L_VM_m']:.2f} < L < {cal['L_MD_m']:.2f}$ m ดังนั้น **Moment Control** (โมเมนต์เป็นตัวคุม)")
        gov_load = cal['wm']
    else:
        st.success(f"📍 ผลลัพธ์: $L > {cal['L_MD_m']:.2f}$ m ดังนั้น **Deflection Control** (ระยะแอ่นเป็นตัวคุม)")
        gov_load = cal['wd']
        
    st.markdown(f"**Gross Safe Load ($w_{{gross}}$):** {gov_load:,.0f} kg/m")
    st.markdown(f"**Net Safe Load ($w_{{net}} = w_{{gross}} - W_{{beam}}$):**")
    st.latex(rf"{gov_load:,.0f} - {props['W']} = \mathbf{{{max(gov_load - props['W'], 0):,.0f}}} \text{{ kg/m}}")

# ===== TAB 3: INFO =====
with tab_info:
    st.markdown("### 📚 รวมสูตรที่ใช้ในโปรแกรม")
    st.markdown("""
    **1. Strength Calculations (AISC/EIT):**
    * $V_n = 0.6 F_y A_w$
    * $M_n = F_y Z_x$
    
    **2. Uniform Load Conversion (Simply Supported):**
    * $V_{max} = wL/2 \rightarrow w = 2V/L$
    * $M_{max} = wL^2/8 \rightarrow w = 8M/L^2$
    * $\delta_{max} = 5wL^4/384EI \rightarrow w = 384EI\delta/5L^4$
    
    **3. Intersection Logic (Critical Lengths):**
    * **Shear-Moment:** หา $L$ ที่ทำให้ $w_{shear} = w_{moment}$
    * **Moment-Deflection:** หา $L$ ที่ทำให้ $w_{moment} = w_{deflect}$ (โดยแทน $\delta=L/360$)
    """)
