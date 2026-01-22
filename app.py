import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Precision Calc", layout="wide")

# --- 2. DATABASE (SYS H-BEAM) ---
# หน่วยใน Database: D(mm), tw(mm), W(kg/m), Ix(cm4), Zx(cm3)
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

# --- 3. CORE CALCULATION (PURE METRIC: kg, cm) ---
def calculate_capacities(lengths_m, Fy_ksc, E_gpa, props, method):
    # Convert Inputs to Pure cm/kg units
    E_ksc = E_gpa * 10197.16  # 1 GPa = 10197.16 ksc
    Ix = props['Ix']          # cm4
    Zx = props['Zx']          # cm3
    
    # Area Web (Aw) = d * tw (convert mm to cm)
    Aw = (props['D'] / 10.0) * (props['tw'] / 10.0) # cm2
    
    # 1. Nominal Strength (kg and kg-cm)
    Vn = 0.60 * Fy_ksc * Aw    # kg
    Mn = Fy_ksc * Zx           # kg-cm
    
    # 2. Apply Factors
    if method == "ASD":
        V_allow = Vn / 1.50
        M_allow = Mn / 1.67
    else:
        # LRFD
        V_allow = 1.00 * Vn    # Call it 'allow' for variable consistency, but it's Vu
        M_allow = 0.90 * Mn    # Call it 'allow' for variable consistency, but it's Mu

    # 3. Loop Calculation
    w_shear_list, w_moment_list, w_deflect_list = [], [], []
    
    for L_m in lengths_m:
        if L_m == 0: 
            w_shear_list.append(None)
            continue
        
        L_cm = L_m * 100.0  # Convert m to cm
        
        # --- SHEAR ---
        # w (kg/cm) = 2 * V / L
        w_s_kgcm = (2 * V_allow) / L_cm
        w_s_kgm = w_s_kgcm * 100  # Convert to kg/m
        
        # --- MOMENT ---
        # w (kg/cm) = 8 * M / L^2
        w_m_kgcm = (8 * M_allow) / (L_cm**2)
        w_m_kgm = w_m_kgcm * 100  # Convert to kg/m
        
        # --- DEFLECTION ---
        # Delta = L/360
        delta_allow = L_cm / 360.0
        # w (kg/cm) = (384 * E * I * delta) / (5 * L^4)
        w_d_kgcm = (384 * E_ksc * Ix * delta_allow) / (5 * (L_cm**4))
        w_d_kgm = w_d_kgcm * 100 # Convert to kg/m
        
        w_shear_list.append(w_s_kgm)
        w_moment_list.append(w_m_kgm)
        w_deflect_list.append(w_d_kgm)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn, Aw, E_ksc

# --- 4. SIDEBAR ---
st.title("🏗️ SYS H-Beam Design: Precision Calculation")
st.sidebar.header("1. Design Method")
method = st.sidebar.radio("Select Method:", ["ASD", "LRFD"])

st.sidebar.header("2. Parameters")
section_name = st.sidebar.selectbox("Section:", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc):", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa):", value=200)
L_input = st.sidebar.slider("Span Length (m):", 1.0, 24.0, 6.0, 0.5)

# --- 5. PROCESS DATA ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)

# Calculate
w_s, w_m, w_d, Vn_val, Mn_val, Aw_val, E_ksc_val = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# Governing Logic
w_safe_gross = np.minimum(np.minimum(w_s, w_m), w_d)
w_safe_net = np.maximum(w_safe_gross - props['W'], 0)

# Current Values (at chosen Length)
cur_idx = (np.abs(L_range - L_input)).argmin()
res_w_s = w_s[cur_idx]
res_w_m = w_m[cur_idx]
res_w_d = w_d[cur_idx]
gov_val = w_safe_gross[cur_idx]

# --- 6. TABS ---
tab1, tab2 = st.tabs(["📊 Capacity Graph", "📝 Detailed Calculation"])

# ===== TAB 1: GRAPH =====
with tab1:
    y_label = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load (kg/m)"
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_safe_gross, name='Governing Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[gov_val], mode='markers', marker=dict(size=14, color='blue', symbol='x'), name='Current Design'))

    # Zone Coloring
    gov_idx = np.argmin([w_s, w_m, w_d], axis=0)
    colors = ['rgba(255, 0, 0, 0.1)', 'rgba(255, 165, 0, 0.1)', 'rgba(0, 128, 0, 0.1)']
    labels = ['Shear Control', 'Moment Control', 'Deflection Control']
    start_i = 0
    for i in range(1, len(L_range)):
        if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
            fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], line_width=0, 
                          annotation_text=labels[gov_idx[start_i]], annotation_position="top left")
            start_i = i

    fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title=y_label, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: DETAILED CALCULATION (CORRECTED MATH) =====
with tab2:
    st.markdown(f"### 📄 รายการคำนวณ: **{method}** (ระบบ Metric kg-cm)")
    
    # Properties Section
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info(f"**Section: {section_name}**\n\nSpan $L = {L_input}$ m ($={L_input*100:.0f}$ cm)\n\n$F_y = {Fy}$ ksc")
    with col2:
        df_prop = pd.DataFrame({
            "Property": ["Depth (D)", "Web (tw)", "Area Web (Aw)", "Inertia (Ix)", "Modulus (Zx)", "Elastic Modulus (E)"],
            "Value": [f"{props['D']} mm", f"{props['tw']} mm", f"{Aw_val:.2f} cm²", f"{props['Ix']:,.0f} cm⁴", f"{props['Zx']:,.0f} cm³", f"{E_ksc_val:,.0f} ksc"]
        })
        st.dataframe(df_prop, hide_index=True, use_container_width=True)
    st.markdown("---")

    # ตัวแปรสำหรับแสดงผล
    L_cm = L_input * 100
    
    if method == "ASD":
        # ==================== ASD ====================
        st.success("📌 **MODE: ASD** (Safety Factor $\Omega$)")

        # --- 1. SHEAR ---
        st.markdown("#### 1️⃣ Shear Check")
        st.write("**Step 1: Nominal Strength ($V_n$)**")
        st.latex(rf"V_n = 0.60 \cdot F_y \cdot A_w = 0.60 \times {Fy} \times {Aw_val:.2f} = \mathbf{{{Vn_val:,.0f}}} \text{{ kg}}")
        
        st.write("**Step 2: Allowable Strength ($V_{allow}$)**")
        V_allow = Vn_val / 1.50
        st.latex(rf"V_{{allow}} = \frac{{V_n}}{{1.50}} = \frac{{{Vn_val:,.0f}}}{{1.50}} = \mathbf{{{V_allow:,.0f}}} \text{{ kg}}")
        
        st.write("**Step 3: Uniform Load ($w$)**")
        st.latex(rf"w = \frac{{2 V_{{allow}}}}{{L}} = \frac{{2 \times {V_allow:,.0f}}}{{{L_cm:.0f} \text{{ cm}}}} = {2*V_allow/L_cm:,.2f} \text{{ kg/cm}}")
        st.latex(rf"w_{{shear}} = {2*V_allow/L_cm:,.2f} \times 100 = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")

        # --- 2. MOMENT ---
        st.markdown("#### 2️⃣ Moment Check")
        st.write("**Step 1: Nominal Strength ($M_n$)**")
        st.latex(rf"M_n = F_y \cdot Z_x = {Fy} \times {props['Zx']} = \mathbf{{{Mn_val:,.0f}}} \text{{ kg-cm}}")
        
        st.write("**Step 2: Allowable Strength ($M_{allow}$)**")
        M_allow = Mn_val / 1.67
        st.latex(rf"M_{{allow}} = \frac{{M_n}}{{1.67}} = \frac{{{Mn_val:,.0f}}}{{1.67}} = \mathbf{{{M_allow:,.0f}}} \text{{ kg-cm}}")
        
        st.write("**Step 3: Uniform Load ($w$)**")
        st.latex(rf"w = \frac{{8 M_{{allow}}}}{{L^2}} = \frac{{8 \times {M_allow:,.0f}}}{{{L_cm:.0f}^2}} = {8*M_allow/(L_cm**2):,.2f} \text{{ kg/cm}}")
        st.latex(rf"w_{{moment}} = {8*M_allow/(L_cm**2):,.2f} \times 100 = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    else:
        # ==================== LRFD ====================
        st.error("📌 **MODE: LRFD** (Resistance Factor $\phi$)")

        # --- 1. SHEAR ---
        st.markdown("#### 1️⃣ Shear Check")
        st.write("**Step 1: Nominal Strength ($V_n$)**")
        st.latex(rf"V_n = 0.60 \cdot F_y \cdot A_w = 0.60 \times {Fy} \times {Aw_val:.2f} = \mathbf{{{Vn_val:,.0f}}} \text{{ kg}}")
        
        st.write("**Step 2: Design Strength ($V_u$)**")
        V_u = 1.00 * Vn_val
        st.latex(rf"V_u = 1.00 \times V_n = 1.00 \times {Vn_val:,.0f} = \mathbf{{{V_u:,.0f}}} \text{{ kg}}")
        
        st.write("**Step 3: Uniform Load ($w_u$)**")
        st.latex(rf"w_u = \frac{{2 V_u}}{{L}} = \frac{{2 \times {V_u:,.0f}}}{{{L_cm:.0f}}} \times 100 = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")

        # --- 2. MOMENT ---
        st.markdown("#### 2️⃣ Moment Check")
        st.write("**Step 1: Nominal Strength ($M_n$)**")
        st.latex(rf"M_n = F_y \cdot Z_x = {Fy} \times {props['Zx']} = \mathbf{{{Mn_val:,.0f}}} \text{{ kg-cm}}")
        
        st.write("**Step 2: Design Strength ($M_u$)**")
        M_u = 0.90 * Mn_val
        st.latex(rf"M_u = 0.90 \times M_n = 0.90 \times {Mn_val:,.0f} = \mathbf{{{M_u:,.0f}}} \text{{ kg-cm}}")
        
        st.write("**Step 3: Uniform Load ($w_u$)**")
        st.latex(rf"w_u = \frac{{8 M_u}}{{L^2}} = \frac{{8 \times {M_u:,.0f}}}{{{L_cm:.0f}^2}} \times 100 = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # --- 3. DEFLECTION (COMMON) ---
    st.markdown("#### 3️⃣ Deflection Check")
    st.write(f"ตรวจสอบที่ระยะ $L = {L_cm:.0f}$ cm")
    
    delta_allow = L_cm / 360.0
    st.latex(rf"\delta_{{allow}} = L/360 = {L_cm:.0f}/360 = \mathbf{{{delta_allow:.2f}}} \text{{ cm}}")
    
    st.write("**คำนวณน้ำหนักที่ทำให้เกิดระยะแอ่นตัวสูงสุด:**")
    st.latex(r"w = \frac{384 E I \delta}{5 L^4}")
    
    # Calculate for display
    numerator = 384 * E_ksc_val * props['Ix'] * delta_allow
    denominator = 5 * (L_cm**4)
    w_kgcm = numerator / denominator
    
    st.latex(rf"w = \frac{{384 \times {E_ksc_val:,.0f} \times {props['Ix']:,.0f} \times {delta_allow:.2f}}}{{5 \times {L_cm:.0f}^4}} = {w_kgcm:.4f} \text{{ kg/cm}}")
    st.latex(rf"w_{{deflect}} = {w_kgcm:.4f} \times 100 = \mathbf{{{res_w_d:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    st.success(f"✅ **Governing Capacity (Gross): {gov_val:,.0f} kg/m**")
    st.caption(f"Net Safe Load = {gov_val:,.0f} - {props['W']} (Beam Weight) = {max(gov_val - props['W'], 0):,.0f} kg/m")
