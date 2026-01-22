import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. SETTINGS & DATA ---
st.set_page_config(page_title="SYS Beam Design: Detailed Calc", layout="wide")

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

# --- 2. CALCULATION ENGINE ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method):
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # Nominal Strength
    Vn = 0.60 * Fy_pa * Aw  
    Mn = Fy_pa * Zx         
    
    # Factors
    if method == "ASD":
        V_cap = Vn / 1.50 
        M_cap = Mn / 1.67 
    else:
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn

    # Loop
    w_shear_list, w_moment_list, w_deflect_list = [], [], []
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Load Capacity (kg/m)
        w_s = (2 * V_cap) / L / g
        w_m = (8 * M_cap) / (L**2) / g
        
        # Deflection Limit (L/360)
        delta_lim = L / 360.0
        w_d = ((384 * E * Ix * delta_lim) / (5 * L**4)) / g
        
        w_shear_list.append(w_s)   
        w_moment_list.append(w_m)
        w_deflect_list.append(w_d)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn

# --- 3. UI SIDEBAR ---
st.title("🏗️ SYS H-Beam Design: Fully Detailed Calculation")
st.sidebar.header("1. Design Method")
method = st.sidebar.radio("Select Method:", ["ASD", "LRFD"])

st.sidebar.header("2. Parameters")
section_name = st.sidebar.selectbox("Section:", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc):", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa):", value=200)
L_input = st.sidebar.slider("Span Length (m):", 1.0, 24.0, 6.0, 0.5)

# --- 4. DATA PROCESS ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, Vn_raw, Mn_raw = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# Governing Logic
w_safe_gross = np.minimum(np.minimum(w_s, w_m), w_d)
w_safe_net = np.maximum(w_safe_gross - props['W'], 0)

# Current Values
cur_idx = (np.abs(L_range - L_input)).argmin()
res_w_s = w_s[cur_idx]
res_w_m = w_m[cur_idx]
res_w_d = w_d[cur_idx]
gov_val = w_safe_gross[cur_idx]

# Display Units
Vn_kg = Vn_raw / 9.81
Mn_kgcm = (Mn_raw / 9.81) * 100
Aw_cm2 = (props['D'] * props['tw']) / 100
Zx_cm3 = props['Zx']
Ix_cm4 = props['Ix']
E_ksc = E_val_gpa * 10197.16 # Convert GPa to ksc approx

# --- 5. TABS ---
tab1, tab2 = st.tabs(["📊 Capacity Graph", "📝 Detailed Calculation"])

# ===== TAB 1: GRAPH =====
with tab1:
    y_title = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load (Wu) (kg/m)"
    fig = go.Figure()
    
    # Plots
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_safe_gross, name='Governing Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[gov_val], mode='markers', marker=dict(size=14, color='blue'), name='Current Design'))

    # Zone Coloring
    gov_idx = np.argmin([w_s, w_m, w_d], axis=0)
    colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
    labels = ['Shear Control', 'Moment Control', 'Deflection Control']
    start_i = 0
    for i in range(1, len(L_range)):
        if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
            fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], opacity=1, line_width=0, annotation_text=labels[gov_idx[start_i]], annotation_position="top left")
            start_i = i
            
    fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title=y_title, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: DETAILED CALCULATION =====
with tab2:
    st.markdown(f"### 📄 รายการคำนวณละเอียด ({method})")
    
    # 1. Properties
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info(f"**Section: {section_name}**\n\nSpan $L = {L_input}$ m\n\n$F_y = {Fy}$ ksc")
    with col2:
        df_prop = pd.DataFrame({
            "Property": ["Depth (D)", "Web (tw)", "Area (Aw)", "Inertia (Ix)", "Modulus (Zx)"],
            "Value": [f"{props['D']} mm", f"{props['tw']} mm", f"{Aw_cm2:.2f} cm²", f"{Ix_cm4:,.0f} cm⁴", f"{Zx_cm3:,.0f} cm³"]
        })
        st.dataframe(df_prop, hide_index=True, use_container_width=True)
    st.markdown("---")

    # 2. CALCULATION LOGIC (WITH SUBSTITUTION)
    if method == "ASD":
        # ================= ASD =================
        st.success("📌 **MODE: ASD** (Safety Factor $\Omega$)")

        # --- SHEAR ---
        st.markdown("#### 1️⃣ Shear Check")
        st.latex(rf"V_n = 0.60 \times F_y \times A_w = 0.60 \times {Fy} \times {Aw_cm2:.2f} = {Vn_kg:,.0f} \text{{ kg}}")
        
        st.write("หาค่าแรงเฉือนที่ยอมให้ ($V_{allow}$):")
        # แสดงการแทนค่าหาร
        st.latex(rf"V_{{allow}} = \frac{{V_n}}{{1.50}} = \frac{{{Vn_kg:,.0f}}}{{1.50}} = \mathbf{{{Vn_kg/1.50:,.0f}}} \text{{ kg}}")
        
        st.write("แปลงเป็นน้ำหนักแผ่ ($w$):")
        # แสดงการแทนค่าสูตร w
        st.latex(rf"w_{{shear}} = \frac{{2 \times V_{{allow}}}}{{L}} = \frac{{2 \times {Vn_kg/1.50:,.0f}}}{{{L_input}}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")

        # --- MOMENT ---
        st.markdown("#### 2️⃣ Moment Check")
        st.latex(rf"M_n = F_y \times Z_x = {Fy} \times {Zx_cm3} = {Mn_kgcm:,.0f} \text{{ kg-cm}}")
        
        st.write("หาค่าโมเมนต์ที่ยอมให้ ($M_{allow}$):")
        # แสดงการแทนค่าหาร
        st.latex(rf"M_{{allow}} = \frac{{M_n}}{{1.67}} = \frac{{{Mn_kgcm:,.0f}}}{{1.67}} = \mathbf{{{Mn_kgcm/1.67:,.0f}}} \text{{ kg-cm}}")
        
        st.write("แปลงเป็นน้ำหนักแผ่ ($w$):")
        # แสดงการแทนค่าสูตร w (แปลงหน่วย M จาก kg-cm เป็น kg-m โดยหาร 100 ในสูตรเพื่อโชว์)
        M_allow_val = Mn_kgcm/1.67
        st.latex(rf"w_{{moment}} = \frac{{8 \times M_{{allow}}}}{{L^2}} = \frac{{8 \times ({M_allow_val:,.0f}/100)}}{{{L_input}^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    else:
        # ================= LRFD =================
        st.error("📌 **MODE: LRFD** (Resistance Factor $\phi$)")

        # --- SHEAR ---
        st.markdown("#### 1️⃣ Shear Check")
        st.latex(rf"V_n = 0.60 \times {Fy} \times {Aw_cm2:.2f} = {Vn_kg:,.0f} \text{{ kg}}")
        
        st.write("หาค่ากำลังรับแรงเฉือนออกแบบ ($V_u$):")
        # แสดงการแทนค่าคูณ
        st.latex(rf"V_u = 1.00 \times V_n = 1.00 \times {Vn_kg:,.0f} = \mathbf{{{Vn_kg:,.0f}}} \text{{ kg}}")
        
        st.write("แปลงเป็นน้ำหนักแผ่ ($w_u$):")
        st.latex(rf"w_{{u,shear}} = \frac{{2 \times V_u}}{{L}} = \frac{{2 \times {Vn_kg:,.0f}}}{{{L_input}}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")

        # --- MOMENT ---
        st.markdown("#### 2️⃣ Moment Check")
        st.latex(rf"M_n = {Fy} \times {Zx_cm3} = {Mn_kgcm:,.0f} \text{{ kg-cm}}")
        
        st.write("หาค่ากำลังรับโมเมนต์ออกแบบ ($M_u$):")
        # แสดงการแทนค่าคูณ
        M_u_val = 0.90 * Mn_kgcm
        st.latex(rf"M_u = 0.90 \times M_n = 0.90 \times {Mn_kgcm:,.0f} = \mathbf{{{M_u_val:,.0f}}} \text{{ kg-cm}}")
        
        st.write("แปลงเป็นน้ำหนักแผ่ ($w_u$):")
        st.latex(rf"w_{{u,moment}} = \frac{{8 \times M_u}}{{L^2}} = \frac{{8 \times ({M_u_val:,.0f}/100)}}{{{L_input}^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # 3. DEFLECTION (COMMON)
    st.markdown("#### 3️⃣ Deflection Check (Serviceability)")
    st.write(f"ตรวจสอบระยะแอ่นตัวที่ยอมให้ $L/360$ (ใช้ $E \\approx {E_ksc:,.0f}$ ksc)")
    
    # แสดงการแทนค่า L/360
    delta_allow = (L_input * 100) / 360
    st.latex(rf"\delta_{{allow}} = \frac{{{L_input} \times 100}}{{360}} = \mathbf{{{delta_allow:.2f}}} \text{{ cm}}")
    
    st.write("คำนวณน้ำหนักแผ่สูงสุดที่ยอมให้ (ย้ายข้างสมการ $\delta$):")
    # แสดงสูตรย้ายข้าง
    st.latex(r"w_{deflect} = \frac{384 E I \delta_{allow}}{5 L^4}")
    
    # แสดงการแทนค่าตัวเลข (ตัดทอนให้ดูง่ายขึ้นเล็กน้อยเพื่อไม่ให้บรรทัดยาวทะลุจอ)
    # แปลง L เป็น cm ในสูตรนี้
    L_cm = L_input * 100
    st.latex(rf"w = \frac{{384 \times {E_ksc:,.0f} \times {Ix_cm4:,.0f} \times {delta_allow:.2f}}}{{5 \times {L_cm:.0f}^4}} \times 100 (\text{{unit conv}})")
    st.latex(rf"w_{{deflect}} = \mathbf{{{res_w_d:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    st.success(f"✅ **Governing Capacity (ค่าน้อยที่สุด): {gov_val:,.0f} kg/m**")
    st.caption(f"Net Safe Load (Subtract Beam Weight {props['W']} kg/m) = {w_safe_net[cur_idx]:,.0f} kg/m")
