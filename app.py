import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS ---
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
}

# --- 2. ฟังก์ชันคำนวณ ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method):
    # Constants
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Nominal Strengths (กำลังต้านทานระบุ - เหมือนกันทั้ง 2 วิธี)
    Vn = 0.60 * Fy_pa * Aw  
    Mn = Fy_pa * Zx         
    
    # 2. Apply Factors (จุดต่าง)
    if method == "ASD":
        # ASD: หารด้วย Safety Factor
        V_cap = Vn / 1.50 
        M_cap = Mn / 1.67 
    else:
        # LRFD: คูณด้วย Resistance Factor
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
        
        w_s = (2 * V_cap) / L
        w_m = (8 * M_cap) / (L**2)
        
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn

# --- Main App ---
st.set_page_config(page_title="SYS H-Beam", layout="wide")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Design Configuration")
method = st.sidebar.radio("1. Design Method:", ["ASD", "LRFD"])
section_name = st.sidebar.selectbox("2. Section:", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa)", value=200)
L_input = st.sidebar.slider("Length (m)", 1.0, 24.0, 6.0, 0.5)

# --- CALCULATION ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, Vn_raw, Mn_raw = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# Net Capacity
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# --- TABS ---
st.title(f"🏗️ H-Beam Design: {method} Method")
tab1, tab2 = st.tabs(["📊 Graph", "📝 Calculation Sheet"])

# ================= TAB 1: GRAPH =================
with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name='Safe Load', line=dict(color='black', width=4)))
    
    # Current Point
    idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[w_total_safe[idx]], mode='markers', marker=dict(size=12, color='blue')))
    
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 2: DYNAMIC CALCULATION =================
with tab2:
    # เตรียมตัวแปรสำหรับแสดงผล
    cur_idx = (np.abs(L_range - L_input)).argmin()
    res_w_s = w_s[cur_idx]
    res_w_m = w_m[cur_idx]
    
    Vn_kg = Vn_raw / 9.81
    Mn_kgcm = (Mn_raw / 9.81) * 100
    Aw_cm2 = (props['D'] * props['tw']) / 100
    Zx_cm3 = props['Zx']

    # ---------------------------------------------------------
    # แยกส่วนการแสดงผล ASD และ LRFD ออกจากกัน 100% (ป้องกัน Logic ผิด)
    # ---------------------------------------------------------
    
    if method == "ASD":
        # >>>>>>>>>>>> ส่วนของ ASD <<<<<<<<<<<<<<<
        st.success("📌 **MODE: ASD (Allowable Stress Design)** - ใช้ Safety Factor ($\Omega$)")
        
        st.markdown("### 1. Shear Check (ASD)")
        st.latex(r"V_n = 0.60 F_y A_w") 
        st.write(f"Nominal Strength: {Vn_kg:,.0f} kg")
        
        st.markdown("**👇 สูตร ASD (Safety Factor = 1.50):**")
        st.latex(r"V_{allow} = \frac{V_n}{\Omega_v} = \frac{V_n}{1.50}") # <--- สูตรเปลี่ยนตรงนี้
        st.latex(rf"V_{{allow}} = \frac{{{Vn_kg:,.0f}}}{{1.50}} = {Vn_kg/1.50:,.0f} \text{{ kg}}")
        st.latex(rf"w_{{allow}} = {res_w_s:,.0f} \text{{ kg/m}}")
        
        st.markdown("---")
        
        st.markdown("### 2. Moment Check (ASD)")
        st.latex(r"M_n = F_y Z_x")
        st.write(f"Nominal Strength: {Mn_kgcm:,.0f} kg-cm")
        
        st.markdown("**👇 สูตร ASD (Safety Factor = 1.67):**")
        st.latex(r"M_{allow} = \frac{M_n}{\Omega_b} = \frac{M_n}{1.67}") # <--- สูตรเปลี่ยนตรงนี้
        st.latex(rf"M_{{allow}} = \frac{{{Mn_kgcm:,.0f}}}{{1.67}} = {Mn_kgcm/1.67:,.0f} \text{{ kg-cm}}")
        st.latex(rf"w_{{allow}} = {res_w_m:,.0f} \text{{ kg/m}}")

    else:
        # >>>>>>>>>>>> ส่วนของ LRFD <<<<<<<<<<<<<<<
        st.error("📌 **MODE: LRFD (Load & Resistance Factor Design)** - ใช้ Resistance Factor ($\phi$)")
        
        st.markdown("### 1. Shear Check (LRFD)")
        st.latex(r"V_n = 0.60 F_y A_w")
        st.write(f"Nominal Strength: {Vn_kg:,.0f} kg")
        
        st.markdown("**👇 สูตร LRFD (Resistance Factor = 1.00):**")
        st.latex(r"V_u = \phi_v V_n = 1.00 \cdot V_n") # <--- สูตรเปลี่ยนตรงนี้
        st.latex(rf"V_u = 1.00 \times {Vn_kg:,.0f} = {Vn_kg:,.0f} \text{{ kg}}")
        st.latex(rf"w_u = {res_w_s:,.0f} \text{{ kg/m}}")
        
        st.markdown("---")
        
        st.markdown("### 2. Moment Check (LRFD)")
        st.latex(r"M_n = F_y Z_x")
        st.write(f"Nominal Strength: {Mn_kgcm:,.0f} kg-cm")
        
        st.markdown("**👇 สูตร LRFD (Resistance Factor = 0.90):**")
        st.latex(r"M_u = \phi_b M_n = 0.90 \cdot M_n") # <--- สูตรเปลี่ยนตรงนี้
        st.latex(rf"M_u = 0.90 \times {Mn_kgcm:,.0f} = {0.90*Mn_kgcm:,.0f} \text{{ kg-cm}}")
        st.latex(rf"w_u = {res_w_m:,.0f} \text{{ kg/m}}")

    st.markdown("---")
    st.info(f"**Governing Capacity:** {w_total_safe[cur_idx]:,.0f} kg/m")
