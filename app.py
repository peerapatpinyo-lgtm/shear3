import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS (Siam Yamato Steel) ---
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

# --- 2. ฟังก์ชันคำนวณ (Calculations) ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method="ASD"):
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # --- Strength Parameters (Nominal Strength) ---
    # Shear: Vn = 0.6 * Fy * Aw (simplified for hot rolled)
    Vn = 0.60 * Fy_pa * Aw
    # Moment: Mn = Fy * Zx (Plastic Moment, assume compact)
    Mn = Fy_pa * Zx
    
    # --- Apply Factors based on Method ---
    if method == "ASD":
        # Allowable Stress Design (Using approximate Safety Factors common in EIT/AISC)
        # Shear: Omega_v = 1.50 (Modern) or use 0.4Fy (Old EIT). Let's use 0.4Fy equivalent for consistency with old users
        # V_allow approx 0.4 Fy Aw -> Vn / 1.5
        V_limit = Vn / 1.50 
        # Moment: Omega_b = 1.67
        M_limit = Mn / 1.67 
    else:
        # LRFD (Load & Resistance Factor Design)
        # Phi_v = 1.00 (Shear)
        V_limit = 1.00 * Vn
        # Phi_b = 0.90 (Flexure)
        M_limit = 0.90 * Mn

    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # 1. Shear Limit (Uniform Load)
        w_s = (2 * V_limit) / L
        
        # 2. Moment Limit (Uniform Load)
        w_m = (8 * M_limit) / (L**2)
        
        # 3. Deflection Limit (Service Load Control)
        # Note: Deflection is always checked at Service Load.
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_limit, M_limit

# --- Main App ---
st.set_page_config(page_title="SYS H-Beam: ASD vs LRFD", layout="wide")
st.title("🏗️ SYS H-Beam Design: ASD vs LRFD")

# Sidebar
st.sidebar.header("1. เลือกวิธีออกแบบ (Design Method)")
method = st.sidebar.radio("Method:", ["ASD (Allowable Stress)", "LRFD (Load & Resistance Factor)"])
if method == "ASD":
    st.sidebar.info("📌 **ASD:** แสดงผลเป็น **Service Load** (ยังไม่คูณ Load Factor)\n\nใช้ Safety Factor ($\Omega$)")
else:
    st.sidebar.info("📌 **LRFD:** แสดงผลเป็น **Factored Load** ($w_u$)\n\nใช้ Resistance Factor ($\phi$)")

st.sidebar.markdown("---")
st.sidebar.header("2. ตัวแปรตั้งต้น")
section_name = st.sidebar.selectbox("เลือกหน้าตัด (Section)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa)", value=200)
L_input = st.sidebar.slider("ความยาว L (m)", 1.0, 24.0, 6.0, 0.1)

# Calculation
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, V_lim_N, M_lim_N = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# Net Capacity (Subtract Beam Weight only for Service Load concept mostly, but we do for both to show Net Cap)
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# Y-Axis Title
if method == "ASD":
    y_title = "Allowable Service Load (kg/m)"
    load_type_text = "Service Load ($D+L$)"
else:
    y_title = "Design Factored Load $w_u$ (kg/m)"
    load_type_text = "Factored Load ($1.2D+1.6L$)"

# Tabs
tab1, tab2 = st.tabs(["📊 กราฟเปรียบเทียบ (Chart)", f"📝 รายการคำนวณ ({method})"])

# --- TAB 1: CHART ---
with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name=f'Shear Strength ({method})', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name=f'Moment Strength ({method})', line=dict(color='orange', dash='dash')))
    
    # Deflection Note for LRFD
    def_name = 'Deflection Limit (L/360)'
    if method == "LRFD":
        def_name += " [Check at Service Load]"
    
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name=def_name, line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name=f'Design Capacity ({method})', line=dict(color='black', width=4)))
    
    # Current Point
    current_idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[w_total_safe[current_idx]], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))

    # Highlights
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

    fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title=y_title, hovermode="x unified", title=f"Capacity Curve ({method})")
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: CALCULATION SHEET ---
with tab2:
    st.markdown(f"## 📝 รายการคำนวณ ({method} Method)")
    st.markdown(f"**Section:** {section_name} | **Span:** {L_input} m")
    
    # Constants
    E_ksc = (E_val_gpa * 1e9) / 98066.5 
    Aw_cm2 = (props['D'] * props['tw']) / 100
    Zx_cm3 = props['Zx']
    
    # Retrieve calculated values at specific L
    idx = (np.abs(L_range - L_input)).argmin()
    res_w_s = w_s[idx]
    res_w_m = w_m[idx]
    res_w_d = w_d[idx]

    # --- 1. Shear Calculation ---
    st.markdown("### 1. แรงเฉือน (Shear Check)")
    st.write(f"Nominal Shear Strength ($V_n$) = $0.6 F_y A_w$")
    if method == "ASD":
        st.latex(r"\Omega_v = 1.50 \quad (\text{Safety Factor})")
        st.latex(rf"V_{{allow}} = \frac{{V_n}}{{\Omega_v}} = \frac{{0.6 \times {Fy} \times {Aw_cm2:.2f}}}{{1.50}} = \mathbf{{{V_lim_N/9.81:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{shear}} = \frac{{2 V_{{allow}}}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
    else:
        st.latex(r"\phi_v = 1.00 \quad (\text{Resistance Factor})")
        st.latex(rf"V_u = \phi_v V_n = 1.00 \times (0.6 \times {Fy} \times {Aw_cm2:.2f}) = \mathbf{{{V_lim_N/9.81:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{u,shear}} = \frac{{2 V_u}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- 2. Moment Calculation ---
    st.markdown("### 2. โมเมนต์ดัด (Moment Check)")
    st.write(f"Nominal Moment Strength ($M_n$) = $F_y Z_x$ (Plastic Moment)")
    if method == "ASD":
        st.latex(r"\Omega_b = 1.67 \quad (\text{Safety Factor})")
        st.latex(rf"M_{{allow}} = \frac{{M_n}}{{\Omega_b}} = \frac{{{Fy} \times {Zx_cm3}}}{{1.67}} = \mathbf{{{(M_lim_N/9.81)/100:,.0f}}} \text{{ kg-m}}")
        st.latex(rf"w_{{moment}} = \frac{{8 M_{{allow}}}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")
    else:
        st.latex(r"\phi_b = 0.90 \quad (\text{Resistance Factor})")
        st.latex(rf"M_u = \phi_b M_n = 0.90 \times ({Fy} \times {Zx_cm3}) = \mathbf{{{(M_lim_N/9.81)/100:,.0f}}} \text{{ kg-m}}")
        st.latex(rf"w_{{u,moment}} = \frac{{8 M_u}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- 3. Deflection Calculation ---
    st.markdown("### 3. การแอ่นตัว (Deflection Check)")
    st.warning("⚠️ การตรวจสอบการแอ่นตัวใช้ **Service Load** เสมอ (ไม่ว่าออกแบบด้วย ASD หรือ LRFD)")
    st.latex(rf"\delta_{{allow}} = L/360")
    st.latex(rf"w_{{deflect}} = \mathbf{{{res_w_d:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- 4. Conclusion ---
    st.markdown("### 4. สรุปผล (Conclusion)")
    vals = {'Shear': res_w_s, 'Moment': res_w_m, 'Deflection': res_w_d}
    gov = min(vals, key=vals.get)
    capacity = vals[gov]
    
    st.info(f"👉 **Governing Case:** {gov} Control")
    if method == "ASD":
        st.success(f"✅ **Safe Service Load (Total): {capacity:,.0f} kg/m**")
        st.write(f"(หักน้ำหนักคาน {props['W']} kg/m เหลือรับน้ำหนักจรสุทธิ: **{max(capacity-props['W'],0):,.0f}** kg/m)")
    else:
        st.success(f"✅ **Design Factored Load ($w_u$ Total): {capacity:,.0f} kg/m**")
        st.caption("**Note:** สำหรับ LRFD นี่คือน้ำหนักบรรทุกประลัย ($1.2D + 1.6L$) ที่รับได้สูงสุด")
