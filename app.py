import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Engineering Report", layout="wide")

# --- 2. DATABASE (SYS H-BEAM Standard) ---
# หน่วย: D, tw (mm) | W (kg/m) | Ix (cm4) | Zx (cm3)
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

# --- 3. CALCULATION CORE ---
def engineering_calc(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversion
    # 1 GPa = 10,197.1621 kg/cm^2 (Approx)
    E_ksc = E_gpa * 10197.162 
    
    # 3.2 Dimensions (mm -> cm)
    Ix = props['Ix']
    Zx = props['Zx']
    D_cm = props['D'] / 10.0
    tw_cm = props['tw'] / 10.0
    Aw = D_cm * tw_cm # Area Web
    
    # 3.3 Nominal Strength (AISC 360)
    # Shear: Vn = 0.6 * Fy * Aw
    Vn = 0.60 * Fy_ksc * Aw 
    # Moment: Mn = Fy * Zx (Compact Section Assumption)
    Mn = Fy_ksc * Zx        
    
    # 3.4 Allowable/Design Strength
    if method == "ASD":
        # Safety Factors
        omega_v = 1.50
        omega_b = 1.67
        V_cap = Vn / omega_v
        M_cap = Mn / omega_b
    else:
        # Resistance Factors
        phi_v = 1.00
        phi_b = 0.90
        V_cap = phi_v * Vn
        M_cap = phi_b * Mn
        
    # 3.5 Specific Calculation for Current Length
    L_cm = L_m * 100.0
    
    # Uniform Load Formulas
    # Shear Control: w = 2V/L
    w_shear_kgm = ((2 * V_cap) / L_cm) * 100
    
    # Moment Control: w = 8M/L^2
    w_moment_kgm = ((8 * M_cap) / (L_cm**2)) * 100
    
    # Deflection Control: w derived from delta = 5wL^4 / 384EI
    # Limit delta = L/360
    delta_allow = L_cm / 360.0
    # w (kg/cm) = (384 * E * I * delta) / (5 * L^4)
    w_deflect_kgcm = (384 * E_ksc * Ix * delta_allow) / (5 * (L_cm**4))
    w_deflect_kgm = w_deflect_kgcm * 100

    return {
        "Aw": Aw, "Ix": Ix, "Zx": Zx, "E_ksc": E_ksc, 
        "L_cm": L_cm, "delta_allow": delta_allow,
        "Vn": Vn, "Mn": Mn, "V_cap": V_cap, "M_cap": M_cap,
        "ws": w_shear_kgm, "wm": w_moment_kgm, "wd": w_deflect_kgm
    }

# --- 4. UI SETUP ---
st.title("🏗️ SYS H-Beam: รายการคำนวณวิศวกรรม (Detailed Report)")
st.sidebar.header("1. Input Parameters")

method = st.sidebar.radio("Design Method:", ["ASD", "LRFD"])
section = st.sidebar.selectbox("Section Size:", list(SYS_H_BEAMS.keys()))
Fy = st.sidebar.number_input("Yield Strength (Fy) [ksc]:", value=2400)
E_gpa = st.sidebar.number_input("Elastic Modulus (E) [GPa]:", value=200)
L_input = st.sidebar.slider("Span Length (m):", 1.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = engineering_calc(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["📊 1. Analysis Graph", "📝 2. Detailed Calculation", "📚 3. Formulas & Derivation"])

# ===== TAB 1: GRAPH & ANALYSIS =====
with tab1:
    col_g1, col_g2 = st.columns([3, 1])
    
    with col_g1:
        # Create Graph Data
        L_range = np.linspace(0.5, max(15, L_input*1.5), 300)
        y_s, y_m, y_d = [], [], []
        
        # Constant capacities for loop efficiency
        v_c = cal['V_cap']
        m_c = cal['M_cap']
        E_val = cal['E_ksc']
        Ix_val = props['Ix']

        for l in L_range:
            l_cm = l * 100
            y_s.append((2 * v_c / l_cm) * 100)
            y_m.append((8 * m_c / l_cm**2) * 100)
            delta = l_cm / 360
            y_d.append(((384 * E_val * Ix_val * delta) / (5 * l_cm**4)) * 100)
            
        y_gov = np.minimum(np.minimum(y_s, y_m), y_d)
        cur_gov = min(cal['ws'], cal['wm'], cal['wd'])
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear Limit (แรงเฉือน)', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment Limit (โมเมนต์)', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection Limit (ระยะแอ่น)', line=dict(color='green', dash='dot')))
        fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Governing Capacity', line=dict(color='black', width=4)))
        fig.add_trace(go.Scatter(x=[L_input], y=[cur_gov], mode='markers', marker=dict(size=15, color='blue', symbol='x'), name=f'Design @ {L_input}m'))

        # Zone Coloring
        gov_idx = np.argmin([y_s, y_m, y_d], axis=0)
        colors = ['rgba(255,0,0,0.1)', 'rgba(255,165,0,0.1)', 'rgba(0,128,0,0.1)']
        
        start_i = 0
        for i in range(1, len(L_range)):
            if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
                fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], line_width=0)
                start_i = i
                
        fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title="Load (kg/m)", margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.markdown("### 📌 Analysis Result")
        st.metric("Load Capacity", f"{cur_gov:,.0f} kg/m")
        
        # Find Transition Point (Shear -> Moment)
        # 2V/L = 8M/L^2 => L = 4M/V
        L_trans_vm = (4 * m_c) / v_c / 100 # m
        
        st.markdown("---")
        st.markdown("**จุดเปลี่ยนพฤติกรรม (Critical Lengths):**")
        st.info(f"**1. Shear $\\to$ Moment:**\n\n ที่ระยะ $L = {L_trans_vm:.2f}$ m")
        if L_input < L_trans_vm:
            st.error(f"ปัจจุบัน: {L_input} m (Shear Control)")
        else:
            st.warning(f"ปัจจุบัน: {L_input} m (Moment/Deflect Control)")


# ===== TAB 2: DETAILED CALCULATION =====
with tab2:
    st.markdown(f"### 📄 รายการคำนวณ: **{section}** ({method} Method)")
    st.markdown("---")

    # 1. Properties
    st.markdown("#### 1. ข้อมูลการออกแบบ (Design Data)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Section:** {section}")
        st.write(f"- $D = {props['D']}$ mm, $t_w = {props['tw']}$ mm")
        st.write(f"- $I_x = {props['Ix']:,}$ cm⁴")
        st.write(f"- $Z_x = {props['Zx']:,}$ cm³")
        st.write(f"- $A_w = D \\times t_w = {cal['Aw']:.2f}$ cm²")
    with c2:
        st.write(f"**Materials & Span:**")
        st.write(f"- $F_y = {Fy}$ ksc")
        st.write(f"- $E = {E_gpa}$ GPa $\\approx {cal['E_ksc']:,.0f}$ ksc")
        st.write(f"- Span $L = {L_input}$ m $= {cal['L_cm']:.0f}$ cm")

    st.markdown("---")

    # 2. Shear
    st.markdown("#### 2. ตรวจสอบแรงเฉือน (Shear Capacity)")
    st.markdown("**Step 1: กำลังรับแรงเฉือนระบุ ($V_n$)**")
    st.latex(rf"V_n = 0.60 \times F_y \times A_w")
    st.latex(rf"V_n = 0.60 \times {Fy} \times {cal['Aw']:.2f} = \mathbf{{{cal['Vn']:,.0f}}} \text{{ kg}}")
    
    st.markdown(f"**Step 2: กำลังรับแรงเฉือนที่ยอมให้ ({method})**")
    if method == "ASD":
        st.latex(rf"V_{{allow}} = \frac{{V_n}}{{\Omega}} = \frac{{{cal['Vn']:,.0f}}}{{1.50}} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
    else:
        st.latex(rf"V_u = \phi V_n = 1.00 \times {cal['Vn']:,.0f} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")

    st.markdown("**Step 3: แปลงเป็นน้ำหนักแผ่ ($w$)**")
    st.latex(r"w_{shear} = \frac{2 V}{L} \times 100")
    st.latex(rf"w_{{shear}} = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # 3. Moment
    st.markdown("#### 3. ตรวจสอบโมเมนต์ดัด (Moment Capacity)")
    st.markdown("**Step 1: กำลังรับโมเมนต์ระบุ ($M_n$)**")
    st.latex(rf"M_n = F_y \times Z_x")
    st.latex(rf"M_n = {Fy} \times {props['Zx']} = \mathbf{{{cal['Mn']:,.0f}}} \text{{ kg-cm}}")

    st.markdown(f"**Step 2: กำลังรับโมเมนต์ที่ยอมให้ ({method})**")
    if method == "ASD":
        st.latex(rf"M_{{allow}} = \frac{{M_n}}{{\Omega}} = \frac{{{cal['Mn']:,.0f}}}{{1.67}} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")
    else:
        st.latex(rf"M_u = \phi M_n = 0.90 \times {cal['Mn']:,.0f} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3: แปลงเป็นน้ำหนักแผ่ ($w$)**")
    st.latex(r"w_{moment} = \frac{8 M}{L^2} \times 100")
    st.latex(rf"w_{{moment}} = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # 4. Deflection
    st.markdown("#### 4. ตรวจสอบระยะแอ่นตัว (Deflection Limit)")
    st.markdown("**Step 1: ระยะแอ่นตัวที่ยอมให้ ($\delta_{max}$)**")
    st.latex(rf"\delta_{{allow}} = \frac{{L}}{{360}} = \frac{{{cal['L_cm']:.0f}}}{{360}} = \mathbf{{{cal['delta_allow']:.2f}}} \text{{ cm}}")

    st.markdown("**Step 2: คำนวณน้ำหนักแผ่ย้อนกลับ ($w$)**")
    st.latex(r"w_{deflect} = \frac{384 E I \delta}{5 L^4} \times 100")
    
    # Substitution detail
    st.write("แทนค่า:")
    num = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w = \frac{{{num}}}{{{den}}} \times 100")
    st.latex(rf"w_{{deflect}} = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    st.success(f"✅ **สรุป: รับน้ำหนักได้สูงสุด (Governing) = {cur_gov:,.0f} kg/m**")

# ===== TAB 3: FORMULAS & DERIVATION =====
with tab3:
    st.header("📚 ที่มาของสูตร (Reference & Derivation)")
    
    st.subheader("1. ทำไม $V_n = 0.6 F_y A_w$ ?")
    st.markdown("""
    * **ทฤษฎี:** มาจาก **Von Mises Yield Criterion** ซึ่งระบุว่าวัสดุจะเริ่มคราก (Yield) ด้วยแรงเฉือน เมื่อหน่วยแรงเฉือนมีค่าประมาณ $1/\sqrt{3}$ ของหน่วยแรงดึง
    * **ตัวเลข:** $1/\sqrt{3} \approx 0.577$
    * **มาตรฐาน AISC:** ปัดตัวเลขให้จำง่ายเป็น **0.60**
    * **พื้นที่ ($A_w$):** สำหรับ H-Beam จะคิดพื้นที่รับแรงเฉือนเฉพาะส่วนเอว (Web) คือ $D \times t_w$
    """)
    st.latex(r"\tau_{yield} \approx 0.577 \sigma_{yield} \Rightarrow V_n = 0.60 F_y A_w")

    st.divider()

    st.subheader("2. ทำไมน้ำหนักแผ่ (w) ถึงใช้สูตรต่างกัน?")
    st.markdown("มาจากสูตร **Beam Mechanics (Simply Supported)** พื้นฐาน:")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("**ก. กรณีแรงเฉือน (Shear Control):**")
        st.image("https://calcresource.com/images.beam-reaction.jpg", caption="Shear Diagram (V)", width=200) # Placeholder concept
        st.latex(r"V_{max} = \frac{wL}{2}")
        st.write("ย้ายข้างหา $w$:")
        st.latex(r"w = \frac{2 V_{allow}}{L}")

    with col_f2:
        st.markdown("**ข. กรณีโมเมนต์ (Moment Control):**")
        st.latex(r"M_{max} = \frac{wL^2}{8}")
        st.write("ย้ายข้างหา $w$:")
        st.latex(r"w = \frac{8 M_{allow}}{L^2}")

    st.divider()
    
    st.subheader("3. การหาจุดตัดกราฟ (Transition Point Logic)")
    st.markdown("ทำไมกราฟถึงเปลี่ยนสี? เราหาจุดที่ **ความสามารถรับแรงเฉือน = ความสามารถรับโมเมนต์**")
    
    st.latex(r"w_{shear} = w_{moment}")
    st.latex(r"\frac{2V}{L} = \frac{8M}{L^2}")
    st.write("ตัด $L$ ทั้งสองข้าง และย้ายข้างสมการ:")
    st.latex(r"L = \frac{4M}{V}")
    
    st.info("""
    * **ถ้า $L < 4M/V$:** คานสั้นเกินไป $\to$ แรงเฉือนพังก่อน (Shear Control)
    * **ถ้า $L > 4M/V$:** คานยาวพอ $\to$ โมเมนต์พังก่อน (Moment Control)
    """)
