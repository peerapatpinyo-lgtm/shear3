import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: ASD vs LRFD", layout="wide")

# --- 2. DATABASE ---
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
}

# --- 3. CALCULATION ENGINE ---
def calculate_all(L_m, Fy_ksc, E_gpa, props, method):
    # Units
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    
    # Section Properties
    Aw = (props['D']/10.0) * (props['tw']/10.0) # cm2
    Zx = props['Zx'] # cm3
    Ix = props['Ix'] # cm4
    
    # 1. Nominal Strength (กำลังระบุ - เท่ากันทั้ง 2 วิธี)
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * Zx
    
    # 2. Design Strength (แยกวิธี)
    if method == "ASD":
        # Allowable Strength Design
        omega_v = 1.50
        omega_b = 1.67
        V_cap = Vn / omega_v
        M_cap = Mn / omega_b
        txt_v = r"\Omega_v = 1.50"
        txt_m = r"\Omega_b = 1.67"
    else:
        # LRFD
        phi_v = 1.00
        phi_b = 0.90
        V_cap = phi_v * Vn
        M_cap = phi_b * Mn
        txt_v = r"\phi_v = 1.00"
        txt_m = r"\phi_b = 0.90"

    # 3. Load Conversion (w)
    ws = (2 * V_cap / L_cm) * 100      # Shear Control
    wm = (8 * M_cap / L_cm**2) * 100   # Moment Control
    
    # 4. Deflection
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * Ix * delta_allow) / (5 * L_cm**4)) * 100
    
    # 5. Governing Logic
    w_gross = min(ws, wm, wd)
    
    return {
        "Aw": Aw, "Vn": Vn, "Mn": Mn, 
        "V_cap": V_cap, "M_cap": M_cap,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta_allow": delta_allow,
        "txt_v": txt_v, "txt_m": txt_m
    }

# --- 4. UI SETUP ---
st.title("🏗️ ASD vs LRFD: เจาะลึกสูตรและการแทนค่า")

with st.sidebar:
    st.header("1. เลือกวิธีออกแบบ")
    method = st.radio("Design Method", ["ASD", "LRFD"], index=0, help="ASD ใช้ตัวหาร (Safety Factor) | LRFD ใช้ตัวคูณ (Resistance Factor)")
    
    st.header("2. ข้อมูลหน้าตัด")
    section = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
    Fy = st.number_input("Fy (ksc)", value=2400)
    L_input = st.slider("ความยาวคาน (m)", 2.0, 20.0, 6.0, 0.5)
    E_gpa = 200 # Fixed for simplicity

props = SYS_H_BEAMS[section]
cal = calculate_all(L_input, Fy, E_gpa, props, method)

# --- 5. MAIN CONTENT ---
tab1, tab2 = st.tabs(["📝 รายการคำนวณ (เน้นสูตร)", "📊 กราฟเปรียบเทียบ"])

with tab1:
    st.markdown(f"### รายการคำนวณหน้าตัด: {section} (วิธี {method})")
    st.info(f"**Key Concept ของ {method}:** " + 
            ("ใช้วิธี **หาร** ด้วย Safety Factor ($\Omega$)" if method == "ASD" else "ใช้วิธี **คูณ** ด้วย Resistance Factor ($\phi$)"))
    
    st.markdown("---")
    
    # ==== 1. SHEAR ====
    st.header("1. แรงเฉือน (Shear Calculation)")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("**Step 1.1: หาแรงเฉือนระบุ ($V_n$)**")
        st.caption("กำลังของวัสดุเพียวๆ ก่อนคูณ factor")
        st.latex(r"V_n = 0.6 F_y A_w")
        st.latex(rf"V_n = 0.6 \times {Fy} \times {cal['Aw']:.2f} = \mathbf{{{cal['Vn']:,.0f}}} \text{{ kg}}")
        
    with col2:
        st.markdown(f"**Step 1.2: ปรับแก้ด้วย Factor ({method})**")
        if method == "ASD":
            st.write("สูตร ASD (หารด้วย $\Omega_v$):")
            st.latex(r"V_{allow} = \frac{V_n}{\Omega_v}")
            st.write("แทนค่า:")
            st.latex(rf"V_{{allow}} = \frac{{{cal['Vn']:,.0f}}}{{1.50}} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
        else:
            st.write("สูตร LRFD (คูณด้วย $\phi_v$):")
            st.latex(r"V_u = \phi_v V_n")
            st.write("แทนค่า:")
            st.latex(rf"V_u = 1.00 \times {cal['Vn']:,.0f} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")

    st.markdown("**Step 1.3: แปลงเป็นน้ำหนักแผ่ ($w_{shear}$)**")
    st.latex(rf"w_s = \frac{{2 V_{{cap}}}}{{L}} = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # ==== 2. MOMENT ====
    st.header("2. โมเมนต์ดัด (Moment Calculation)")
    
    col3, col4 = st.columns([1, 2])
    with col3:
        st.markdown("**Step 2.1: หาโมเมนต์ระบุ ($M_n$)**")
        st.caption("กำลังต้านทานการดัดของหน้าตัด")
        st.latex(r"M_n = F_y Z_x")
        st.latex(rf"M_n = {Fy} \times {props['Zx']} = \mathbf{{{cal['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col4:
        st.markdown(f"**Step 2.2: ปรับแก้ด้วย Factor ({method})**")
        if method == "ASD":
            st.write("สูตร ASD (หารด้วย $\Omega_b$):")
            st.latex(r"M_{allow} = \frac{M_n}{\Omega_b}")
            st.write("แทนค่า:")
            st.latex(rf"M_{{allow}} = \frac{{{cal['Mn']:,.0f}}}{{1.67}} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")
        else:
            st.write("สูตร LRFD (คูณด้วย $\phi_b$):")
            st.latex(r"M_u = \phi_b M_n")
            st.write("แทนค่า:")
            st.latex(rf"M_u = 0.90 \times {cal['Mn']:,.0f} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 2.3: แปลงเป็นน้ำหนักแผ่ ($w_{moment}$)**")
    st.latex(rf"w_m = \frac{{8 M_{{cap}}}}{{L^2}} = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # ==== 3. DEFLECTION ====
    st.header("3. ระยะแอ่น (Deflection Check)")
    st.info("⚠️ หมายเหตุ: การตรวจสอบระยะแอ่นตัว (Serviceability) ใช้สูตรเดียวกัน ไม่ขึ้นกับ ASD/LRFD")
    st.write("ระยะแอ่นที่ยอมให้ ($\delta_{max} = L/360$):")
    st.latex(rf"\delta = {cal['L_cm']:.0f} / 360 = {cal['delta_allow']:.2f} \text{{ cm}}")
    st.write("หาน้ำหนักแผ่ ($w_{deflect}$):")
    
    # LateX formatting for big fraction
    num_str = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den_str = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w_d = \frac{{{num_str}}}{{{den_str}}} \times 100 = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")

    st.success(f"📌 **สรุป Capacity ที่คานรับได้ (Governing Load): {min(cal['ws'], cal['wm'], cal['wd']):,.0f} kg/m**")

with tab2:
    # Graph Plotting
    L_range = np.linspace(1, 15, 100)
    ys = []
    ym = []
    yd = []
    
    # Pre-calculate constants for loop speed
    vc = cal['V_cap']
    mc = cal['M_cap']
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 # 360*5
    
    for l in L_range:
        l_cm = l * 100
        ys.append(2 * vc / l_cm * 100)
        ym.append(8 * mc / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100)

    y_gov = np.minimum(np.minimum(ys, ym), yd)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Design Capacity', line=dict(color='black', width=4)))
    
    # User Point
    current_cap = min(cal['ws'], cal['wm'], cal['wd'])
    fig.add_trace(go.Scatter(x=[L_input], y=[current_cap], mode='markers+text', 
                             marker=dict(size=12, color='blue'),
                             text=[f"{current_cap:,.0f}"], textposition="top center",
                             name='Selected Span'))

    fig.update_layout(title=f"Capacity Curve ({method}): {section}", xaxis_title="Span (m)", yaxis_title="Load (kg/m)", height=500)
    st.plotly_chart(fig, use_container_width=True)
