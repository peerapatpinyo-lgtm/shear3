import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS (Siam Yamato Steel) ---
SYS_H_BEAMS = {
    # Series 100
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 76.5},
    # Series 150
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 219},
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
}

# --- 2. ฟังก์ชันคำนวณ (Dynamic Calculation) ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method):
    # Constants
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Nominal Strengths (กำลังต้านทานระบุ)
    Vn = 0.60 * Fy_pa * Aw  # Shear Yielding
    Mn = Fy_pa * Zx         # Plastic Moment (Compact)
    
    # 2. Apply Factors based on Method
    if method == "ASD":
        # ASD: หารด้วย Safety Factor (Omega)
        V_cap = Vn / 1.50 
        M_cap = Mn / 1.67 
    else:
        # LRFD: คูณด้วย Resistance Factor (Phi)
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn

    # 3. Loop for Graphs
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Load Capacity (w)
        w_s = (2 * V_cap) / L
        w_m = (8 * M_cap) / (L**2)
        
        # Deflection (Serviceability uses Service Load, usually un-factored)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn

# --- Main App ---
st.set_page_config(page_title="SYS H-Beam Design", layout="wide")
st.title("🏗️ SYS H-Beam Design: ASD vs LRFD")

# --- SIDEBAR ---
st.sidebar.header("1. เลือกวิธีออกแบบ (Design Method)")
method = st.sidebar.radio("Method:", ["ASD (Allowable Stress)", "LRFD (Load & Resistance Factor)"])

# แสดงข้อมูลประกอบการเลือก
if method == "ASD":
    st.sidebar.success("📌 **ASD Mode**\n\n- ใช้ Safety Factor ($\Omega$)\n- แสดงผล: **Service Load**")
    factor_shear = r"\Omega_v = 1.50"
    factor_moment = r"\Omega_b = 1.67"
else:
    st.sidebar.warning("📌 **LRFD Mode**\n\n- ใช้ Resistance Factor ($\phi$)\n- แสดงผล: **Factored Load ($w_u$)**")
    factor_shear = r"\phi_v = 1.00"
    factor_moment = r"\phi_b = 0.90"

st.sidebar.markdown("---")
st.sidebar.header("2. ตัวแปรตั้งต้น")
section_name = st.sidebar.selectbox("เลือกหน้าตัด (Section)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa)", value=200)
L_input = st.sidebar.slider("ความยาว L (m)", 1.0, 24.0, 6.0, 0.1)

# --- CALCULATION ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, Vn_raw, Mn_raw = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# คำนวณ Net Safe Load
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# --- TABS ---
tab1, tab2 = st.tabs(["📊 กราฟ (Chart)", "📝 รายการคำนวณ (Calculation Sheet)"])

# ================= TAB 1: GRAPH =================
with tab1:
    y_label = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load $w_u$ (kg/m)"
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name=f'Shear ({method})', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name=f'Moment ({method})', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection (L/360)', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name=f'Capacity', line=dict(color='black', width=4)))
    
    # Current Point
    idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[w_total_safe[idx]], mode='markers', marker=dict(size=12, color='blue')))
    
    # Zones coloring
    gov_idx = np.argmin([w_s, w_m, w_d], axis=0)
    colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
    labels = ['Shear', 'Moment', 'Deflection']
    start_i = 0
    for i in range(1, len(L_range)):
        if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
            fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], opacity=1, line_width=0, annotation_text=labels[gov_idx[start_i]], annotation_position="top left")
            start_i = i

    fig.update_layout(height=450, xaxis_title="Length (m)", yaxis_title=y_label, hovermode="x unified", title=f"Capacity Curve ({method})")
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 2: DYNAMIC CALCULATION =================
with tab2:
    st.header(f"📝 รายการคำนวณ ({method} Method)")
    st.markdown(f"**Section:** {section_name} | **Span:** {L_input} m")
    
    # ดึงค่าที่จุด L ปัจจุบัน
    cur_idx = (np.abs(L_range - L_input)).argmin()
    res_w_s = w_s[cur_idx]
    res_w_m = w_m[cur_idx]
    res_w_d = w_d[cur_idx]
    
    # ตัวแปรเบื้องต้น
    Aw_cm2 = (props['D'] * props['tw']) / 100
    Zx_cm3 = props['Zx']
    Vn_kg = Vn_raw / 9.81
    Mn_kgcm = (Mn_raw / 9.81) * 100

    # --- 1. SHEAR CHECK ---
    st.markdown("### 1. แรงเฉือน (Shear Check)")
    st.latex(r"V_n = 0.60 F_y A_w \quad (\text{Nominal Strength})")
    st.latex(rf"V_n = 0.60 \times {Fy} \times {Aw_cm2:.2f} = \mathbf{{{Vn_kg:,.0f}}} \text{{ kg}}")
    
    # >>>>> จุดเปลี่ยนสมการตาม ASD/LRFD <<<<<
    if method == "ASD":
        st.markdown("**👉 เลือก ASD:** หารด้วย Safety Factor ($\Omega_v = 1.50$)")
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"V_{allow} = \frac{V_n}{\Omega_v}")
        with col2:
            st.latex(rf"V_{{allow}} = \frac{{{Vn_kg:,.0f}}}{{1.50}} = \mathbf{{{Vn_kg/1.5:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{allow}} = \frac{{2 V_{{allow}}}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
    else: # LRFD
        st.markdown("**👉 เลือก LRFD:** คูณด้วย Resistance Factor ($\phi_v = 1.00$)")
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"\phi V_n = 1.00 \times V_n")
        with col2:
            st.latex(rf"\phi V_n = 1.00 \times {Vn_kg:,.0f} = \mathbf{{{Vn_kg:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{u}} = \frac{{2 (\phi V_n)}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- 2. MOMENT CHECK ---
    st.markdown("### 2. โมเมนต์ดัด (Moment Check)")
    st.latex(r"M_n = F_y Z_x \quad (\text{Nominal Strength})")
    st.latex(rf"M_n = {Fy} \times {Zx_cm3} = {Mn_kgcm:,.0f} \text{{ kg-cm}}")

    # >>>>> จุดเปลี่ยนสมการตาม ASD/LRFD <<<<<
    if method == "ASD":
        st.markdown("**👉 เลือก ASD:** หารด้วย Safety Factor ($\Omega_b = 1.67$)")
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"M_{allow} = \frac{M_n}{\Omega_b}")
        with col2:
            st.latex(rf"M_{{allow}} = \frac{{{Mn_kgcm:,.0f}}}{{1.67}} = {Mn_kgcm/1.67:,.0f} \text{{ kg-cm}}")
        st.latex(rf"w_{{allow}} = \frac{{8 M_{{allow}}}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")
        
    else: # LRFD
        st.markdown("**👉 เลือก LRFD:** คูณด้วย Resistance Factor ($\phi_b = 0.90$)")
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"\phi M_n = 0.90 \times M_n")
        with col2:
            st.latex(rf"\phi M_n = 0.90 \times {Mn_kgcm:,.0f} = {0.90*Mn_kgcm:,.0f} \text{{ kg-cm}}")
        st.latex(rf"w_{{u}} = \frac{{8 (\phi M_n)}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # --- 3. SUMMARY ---
    st.markdown("### 3. สรุปผล (Summary)")
    vals = {"Shear": res_w_s, "Moment": res_w_m, "Deflection": res_w_d}
    min_key = min(vals, key=vals.get)
    
    st.info(f"🚩 **Governing Case:** {min_key} Control")
    if method == "ASD":
        st.success(f"✅ **Safe Service Load:** {vals[min_key]:,.0f} kg/m")
        st.caption("ค่านี้นำไปเทียบกับ $D+L$ ได้เลย")
    else:
        st.success(f"✅ **Design Capacity ($w_u$):** {vals[min_key]:,.0f} kg/m")
        st.caption("ค่านี้นำไปเทียบกับ $1.2D+1.6L$")
