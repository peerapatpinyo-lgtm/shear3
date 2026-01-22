import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS Beam Design: Professional", layout="wide")

# --- 2. DATABASE (Standard JIS/SYS H-Beam) ---
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

# --- 3. MATH ENGINE (Pure Metric) ---
def calculate_all(lengths_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversion
    E_ksc = E_gpa * 10197.16 
    Ix = props['Ix']         
    Zx = props['Zx']         
    Aw = (props['D'] / 10.0) * (props['tw'] / 10.0) 
    
    # 3.2 Nominal Strength
    Vn = 0.60 * Fy_ksc * Aw  
    Mn = Fy_ksc * Zx         
    
    # 3.3 Design Factors
    if method == "ASD":
        omega_v, omega_b = 1.50, 1.67
        V_cap = Vn / omega_v
        M_cap = Mn / omega_b
    else:
        phi_v, phi_b = 1.00, 0.90
        V_cap = phi_v * Vn
        M_cap = phi_b * Mn

    # 3.4 Generate Curves
    w_shear, w_moment, w_deflect = [], [], []
    
    for L_m in lengths_m:
        if L_m == 0: 
            w_shear.append(None); w_moment.append(None); w_deflect.append(None)
            continue
        
        L_cm = L_m * 100.0
        
        # Shear Limit (w = 2V/L)
        ws = (2 * V_cap) / L_cm
        w_shear.append(ws * 100) # kg/m
        
        # Moment Limit (w = 8M/L^2)
        wm = (8 * M_cap) / (L_cm**2)
        w_moment.append(wm * 100) # kg/m
        
        # Deflection Limit (w based on L/360)
        delta_lim = L_cm / 360.0
        wd = (384 * E_ksc * Ix * delta_lim) / (5 * (L_cm**4))
        w_deflect.append(wd * 100) # kg/m

    return {
        "w_s": np.array(w_shear), "w_m": np.array(w_moment), "w_d": np.array(w_deflect),
        "Vn": Vn, "Mn": Mn, "V_cap": V_cap, "M_cap": M_cap, "E_ksc": E_ksc, "Aw": Aw
    }

# --- 4. UI SIDEBAR ---
st.title("🏗️ SYS H-Beam: Engineering Analysis")

col_left, col_right = st.columns([1, 3])

with col_left:
    st.header("Design Parameters")
    method = st.radio("Method", ["ASD", "LRFD"])
    section = st.selectbox("Section", list(SYS_H_BEAMS.keys()))
    Fy = st.number_input("Fy (ksc)", value=2400)
    E_gpa = st.number_input("E (GPa)", value=200)
    L_input = st.slider("Span (m)", 1.0, 24.0, 6.0, 0.5)
    
    props = SYS_H_BEAMS[section]
    
    # Run Calc
    L_max = max(15.0, L_input * 1.5)
    L_range = np.linspace(0.5, L_max, 300)
    res = calculate_all(L_range, Fy, E_gpa, props, method)
    
    # Governing
    w_gross = np.minimum(np.minimum(res["w_s"], res["w_m"]), res["w_d"])
    
    # Current Point Data
    idx = (np.abs(L_range - L_input)).argmin()
    cur_gov = w_gross[idx]

# --- 5. TABS ---
with col_right:
    tab1, tab2, tab3 = st.tabs(["📊 Capacity Graph", "📝 Calculation Sheet", "📚 Formulas & References"])

    # ===== TAB 1: GRAPH =====
    with tab1:
        y_title = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load Wu (kg/m)"
        fig = go.Figure()

        # Curves
        fig.add_trace(go.Scatter(x=L_range, y=res["w_s"], name='Shear Limit', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=res["w_m"], name='Moment Limit', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=res["w_d"], name='Deflection Limit', line=dict(color='green', dash='dot')))
        fig.add_trace(go.Scatter(x=L_range, y=w_gross, name='Governing Capacity', line=dict(color='black', width=4)))
        
        # Design Point
        fig.add_trace(go.Scatter(x=[L_input], y=[cur_gov], mode='markers', marker=dict(size=14, color='blue', symbol='x'), name='Current Design'))

        # Background Zones Logic
        gov_idx = np.argmin([res["w_s"], res["w_m"], res["w_d"]], axis=0)
        colors = ['rgba(255,0,0,0.1)', 'rgba(255,165,0,0.1)', 'rgba(0,128,0,0.1)']
        labels = ['Shear Control', 'Moment Control', 'Deflection Control']
        
        start_i = 0
        for i in range(1, len(L_range)):
            if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
                fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], line_width=0,
                              annotation_text=labels[gov_idx[start_i]], annotation_position="top right")
                start_i = i
        
        fig.update_layout(height=550, xaxis_title="Span Length (m)", yaxis_title=y_title, hovermode="x unified", title=f"Capacity Envelope ({method})")
        st.plotly_chart(fig, use_container_width=True)

    # ===== TAB 2: CALCULATION =====
    with tab2:
        st.markdown(f"### 📄 รายการคำนวณละเอียด ({method})")
        st.caption("การคำนวณใช้หน่วย Metric (kg, cm) เพื่อความแม่นยำสูงสุด")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Section", section)
        c2.metric("Span Length", f"{L_input} m")
        c3.metric("Yield Strength", f"{Fy} ksc")
        
        st.divider()
        L_cm = L_input * 100
        
        # 1. SHEAR
        st.markdown("#### 1️⃣ Shear Check (แรงเฉือน)")
        st.latex(rf"V_n = 0.60 F_y A_w = 0.60 \times {Fy} \times {res['Aw']:.2f} = {res['Vn']:,.0f} \text{{ kg}}")
        if method == "ASD":
            st.latex(rf"V_{{allow}} = \frac{{V_n}}{{1.50}} = \frac{{{res['Vn']:,.0f}}}{{1.50}} = \mathbf{{{res['V_cap']:,.0f}}} \text{{ kg}}")
        else:
            st.latex(rf"V_u = 1.00 \times V_n = \mathbf{{{res['V_cap']:,.0f}}} \text{{ kg}}")
            
        st.write("Convert to Load ($w$):")
        st.latex(rf"w_{{shear}} = \frac{{2 V}}{{L}} = \frac{{2 \times {res['V_cap']:,.0f}}}{{{L_cm:.0f}}} \times 100 = \mathbf{{{res['w_s'][idx]:,.0f}}} \text{{ kg/m}}")
        
        st.divider()

        # 2. MOMENT
        st.markdown("#### 2️⃣ Moment Check (โมเมนต์ดัด)")
        st.latex(rf"M_n = F_y Z_x = {Fy} \times {props['Zx']} = {res['Mn']:,.0f} \text{{ kg-cm}}")
        if method == "ASD":
            st.latex(rf"M_{{allow}} = \frac{{M_n}}{{1.67}} = \frac{{{res['Mn']:,.0f}}}{{1.67}} = \mathbf{{{res['M_cap']:,.0f}}} \text{{ kg-cm}}")
        else:
            st.latex(rf"M_u = 0.90 \times M_n = \mathbf{{{res['M_cap']:,.0f}}} \text{{ kg-cm}}")
            
        st.write("Convert to Load ($w$):")
        st.latex(rf"w_{{moment}} = \frac{{8 M}}{{L^2}} = \frac{{8 \times {res['M_cap']:,.0f}}}{{{L_cm:.0f}^2}} \times 100 = \mathbf{{{res['w_m'][idx]:,.0f}}} \text{{ kg/m}}")
        
        st.divider()

        # 3. DEFLECTION
        st.markdown("#### 3️⃣ Deflection Check (ระยะแอ่นตัว)")
        delta = L_cm / 360
        st.latex(rf"\delta_{{allow}} = L/360 = {L_cm:.0f}/360 = {delta:.2f} \text{{ cm}}")
        
        numerator = 384 * res['E_ksc'] * props['Ix'] * delta
        denominator = 5 * (L_cm**4)
        st.latex(rf"w_{{deflect}} = \frac{{384 E I \delta}}{{5 L^4}} = \frac{{384 \times {res['E_ksc']:,.0f} \times {props['Ix']:,} \times {delta:.2f}}}{{5 \times {L_cm:.0f}^4}} \times 100 = \mathbf{{{res['w_d'][idx]:,.0f}}} \text{{ kg/m}}")
        
        st.divider()
        st.success(f"✅ **Governing Load: {cur_gov:,.0f} kg/m**")

    # ===== TAB 3: FORMULAS & REFERENCES =====
    with tab3:
        st.markdown("### 📚 สูตรและที่มา (Theory & References)")
        
        st.info("💡 **Logic ของช่วง Control (แถบสีบนกราฟ):**\n\n"
                "กราฟแสดงความสามารถในการรับน้ำหนัก ($w$) เทียบกับความยาวช่วงคาน ($L$) "
                "โดยจุดที่กราฟเปลี่ยนสี (Intersection Points) เกิดจากการแก้สมการหาจุดตัดระหว่างโหมดความวิบัติ:")
        
        st.markdown("---")
        
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            st.subheader("1. Transition: Shear ➔ Moment")
            st.write("จุดที่พฤติกรรมเปลี่ยนจากแรงเฉือน (Shear) เป็นโมเมนต์ (Moment) เกิดขึ้นเมื่อ:")
            st.latex(r"w_{shear} = w_{moment}")
            st.latex(r"\frac{2 V_{cap}}{L} = \frac{8 M_{cap}}{L^2}")
            st.write("ย้ายข้างสมการหาค่า $L$:")
            st.latex(r"L_{trans(V-M)} = \frac{4 M_{cap}}{V_{cap}}")
            st.caption("ถ้า $L$ น้อยกว่าค่านี้ $\Rightarrow$ Shear Control (กราฟเส้นตรงชันกว่า)")
            st.caption("ถ้า $L$ มากกว่าค่านี้ $\Rightarrow$ Moment Control (กราฟเส้นโค้ง $1/L^2$)")
            
            # Calculate actual value
            L_vm = (4 * res['M_cap']) / res['V_cap'] / 100 # Convert back to m
            st.markdown(f"**📍 สำหรับหน้าตัดนี้ จุดตัดอยู่ที่ $L \\approx {L_vm:.2f}$ m**")

        with col_f2:
            st.subheader("2. Transition: Moment ➔ Deflection")
            st.write("จุดที่พฤติกรรมเปลี่ยนจากโมเมนต์ เป็นระยะแอ่นตัว (Serviceability) ควบคุม:")
            st.latex(r"w_{moment} = w_{deflection}")
            st.latex(r"\frac{8 M_{cap}}{L^2} = \frac{384 E I (L/360)}{5 L^4} = \frac{384 E I}{1800 L^3}")
            st.write("สมการนี้ซับซ้อนกว่า ($L^2$ vs $L^3$) โดยปกติระยะแอ่นตัวจะเริ่ม Control ที่ช่วงคานยาวๆ")
            st.latex(r"L_{trans(M-D)} = \frac{384 E I}{14400 M_{cap}}")
        
        st.markdown("---")
        st.subheader("3. Reference Standards (มาตรฐานอ้างอิง)")
        st.markdown("""
        * **AISC 360-16:** Specification for Structural Steel Buildings.
            * *Chapter F (Flexure):* $M_n = F_y Z_x$ (Yielding state for compact section).
            * *Chapter G (Shear):* $V_n = 0.6 F_y A_w$.
            * *Chapter L (Serviceability):* Deflection limit $L/360$ (Common practice for Live Load).
        * **EIT 1020-59 (วสท.):** มาตรฐานสำหรับอาคารเหล็กรูปพรรณ (ฉบับ ASD/LRFD).
        """)
        
        st.markdown("---")
        st.subheader("4. Load Formulas (สูตรแปลง Load)")
        st.markdown("สำหรับคานช่วงเดียวรับน้ำหนักแผ่สม่ำเสมอ (Simply Supported Beam with Uniform Load):")
        st.latex(r"V_{max} = \frac{wL}{2} \Rightarrow w = \frac{2V}{L}")
        st.latex(r"M_{max} = \frac{wL^2}{8} \Rightarrow w = \frac{8M}{L^2}")
        st.latex(r"\delta_{max} = \frac{5wL^4}{384EI} \Rightarrow w = \frac{384EI\delta}{5L^4}")
