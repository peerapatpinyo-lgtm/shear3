import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIG & DATA ---
st.set_page_config(page_title="SYS Beam Design Pro", layout="wide")

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
}

# --- 2. CALCULATION ENGINE ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method):
    # Constants
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Nominal (Unfactored)
    Vn = 0.60 * Fy_pa * Aw  
    Mn = Fy_pa * Zx         
    
    # 2. Apply Factors
    if method == "ASD":
        V_cap = Vn / 1.50  # Omega v
        M_cap = Mn / 1.67  # Omega b
    else:
        V_cap = 1.00 * Vn  # Phi v
        M_cap = 0.90 * Mn  # Phi b

    # 3. Generate Curves
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Load Capacity (kg/m)
        w_s = (2 * V_cap) / L / g
        w_m = (8 * M_cap) / (L**2) / g
        
        # Deflection Limit (L/360) -> Back calculate Load
        delta_lim = L / 360.0
        w_d = ((384 * E * Ix * delta_lim) / (5 * L**4)) / g
        
        w_shear_list.append(w_s)   
        w_moment_list.append(w_m)
        w_deflect_list.append(w_d)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn

# --- 3. UI SIDEBAR ---
st.title("🏗️ SYS H-Beam Design: ASD vs LRFD")

st.sidebar.header("1. Design Method")
method = st.sidebar.radio("Select Method:", ["ASD", "LRFD"], help="ASD ใช้ Safety Factor (Ω) | LRFD ใช้ Resistance Factor (ϕ)")

st.sidebar.header("2. Section & Material")
section_name = st.sidebar.selectbox("Section:", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc):", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa):", value=200)

st.sidebar.header("3. Geometry")
L_input = st.sidebar.slider("Span Length (m):", 1.0, 24.0, 6.0, 0.5)

# --- 4. PROCESSING ---
# Generate Graph Data
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, Vn_raw, Mn_raw = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# Safe Load Logic
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# Current Point Data
cur_idx = (np.abs(L_range - L_input)).argmin()
res_w_s = w_s[cur_idx]
res_w_m = w_m[cur_idx]
res_w_d = w_d[cur_idx]
gov_cap = w_total_safe[cur_idx]

# Unit Conversion for Display
Vn_kg = Vn_raw / 9.81
Mn_kgcm = (Mn_raw / 9.81) * 100
Aw_cm2 = (props['D'] * props['tw']) / 100
Zx_cm3 = props['Zx']
Ix_cm4 = props['Ix']

# --- 5. TABS ---
tab1, tab2 = st.tabs(["📊 Capacity Chart", "📝 Calculation Sheet (Detailed)"])

# ===== TAB 1: CHART =====
with tab1:
    y_title = "Allowable Service Load (kg/m)" if method == "ASD" else "Factored Load (Wu) (kg/m)"
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection (L/360)', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name='Safe Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[gov_cap], mode='markers', marker=dict(size=12, color='blue'), name='Current Span'))
    
    fig.update_layout(height=500, xaxis_title="Span Length (m)", yaxis_title=y_title, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: CALCULATION SHEET =====
with tab2:
    # Header
    st.markdown(f"### 📄 รายการคำนวณโครงสร้างเหล็ก ({method} Method)")
    st.markdown("---")
    
    # [NEW] 1. Section Properties Display (สิ่งที่เคยตกหล่นไป)
    col_prop1, col_prop2 = st.columns([1, 2])
    with col_prop1:
        st.info(f"**Section: {section_name}**")
        st.write(f"Span ($L$): {L_input} m")
        st.write(f"Yield Strength ($F_y$): {Fy} ksc")
    with col_prop2:
        # Create a clean dataframe for properties
        prop_data = {
            "Property": ["Weight", "Depth (D)", "Web Thickness (tw)", "Area (Aw)", "Inertia (Ix)", "Modulus (Zx)"],
            "Value": [f"{props['W']} kg/m", f"{props['D']} mm", f"{props['tw']} mm", f"{Aw_cm2:.2f} cm²", f"{Ix_cm4:,.0f} cm⁴", f"{Zx_cm3:,.0f} cm³"]
        }
        st.dataframe(pd.DataFrame(prop_data), hide_index=True, use_container_width=True)

    st.markdown("---")

    # 2. Logic แยก ASD / LRFD (แก้ไขเรื่องสมการไม่ขึ้น)
    if method == "ASD":
        # >>> ASD CALCULATION <<<
        st.markdown("#### 1️⃣ Shear Capacity Check (ASD)")
        st.write("ตรวจสอบกำลังรับแรงเฉือน (ใช้ Safety Factor $\Omega_v = 1.50$)")
        
        # Step 1: Nominal
        st.latex(rf"V_n = 0.60 F_y A_w = 0.60 \times {Fy} \times {Aw_cm2:.2f} = {Vn_kg:,.0f} \text{{ kg}}")
        
        # Step 2: Allowable (SHOW THE DIVISION CLEARLY)
        st.markdown("**👇 Allowable Shear Strength:**")
        st.latex(r"V_{allow} = \frac{V_n}{\Omega_v} = \frac{V_n}{1.50}") # แสดงตัวแปรคู่ตัวเลข
        st.latex(rf"V_{{allow}} = \frac{{{Vn_kg:,.0f}}}{{1.50}} = \mathbf{{{Vn_kg/1.50:,.0f}}} \text{{ kg}}")
        
        # Step 3: Load
        st.latex(rf"w_{{shear}} = \frac{{2 V_{{allow}}}}{{L}} = \frac{{2 \times {Vn_kg/1.50:,.0f}}}{{{L_input}}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("#### 2️⃣ Moment Capacity Check (ASD)")
        st.write("ตรวจสอบกำลังรับโมเมนต์ดัด (ใช้ Safety Factor $\Omega_b = 1.67$)")
        
        # Step 1: Nominal
        st.latex(rf"M_n = F_y Z_x = {Fy} \times {Zx_cm3} = {Mn_kgcm:,.0f} \text{{ kg-cm}}")
        
        # Step 2: Allowable (SHOW THE DIVISION CLEARLY)
        st.markdown("**👇 Allowable Moment Strength:**")
        st.latex(r"M_{allow} = \frac{M_n}{\Omega_b} = \frac{M_n}{1.67}") # แสดงตัวแปรคู่ตัวเลข
        st.latex(rf"M_{{allow}} = \frac{{{Mn_kgcm:,.0f}}}{{1.67}} = \mathbf{{{Mn_kgcm/1.67:,.0f}}} \text{{ kg-cm}}")
        
        # Step 3: Load
        st.latex(rf"w_{{moment}} = \frac{{8 M_{{allow}}}}{{L^2}} = \frac{{8 \times {Mn_kgcm/1.67/100:,.0f}}}{{{L_input}^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    else:
        # >>> LRFD CALCULATION <<<
        st.markdown("#### 1️⃣ Shear Capacity Check (LRFD)")
        st.write("ตรวจสอบกำลังรับแรงเฉือน (ใช้ Resistance Factor $\phi_v = 1.00$)")
        
        st.latex(rf"V_n = 0.60 F_y A_w = {Vn_kg:,.0f} \text{{ kg}}")
        st.markdown("**👇 Design Shear Strength:**")
        st.latex(r"V_u = \phi_v V_n = 1.00 \cdot V_n") # แสดงการคูณ
        st.latex(rf"V_u = 1.00 \times {Vn_kg:,.0f} = \mathbf{{{Vn_kg:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{u,shear}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("#### 2️⃣ Moment Capacity Check (LRFD)")
        st.write("ตรวจสอบกำลังรับโมเมนต์ดัด (ใช้ Resistance Factor $\phi_b = 0.90$)")
        
        st.latex(rf"M_n = F_y Z_x = {Mn_kgcm:,.0f} \text{{ kg-cm}}")
        st.markdown("**👇 Design Moment Strength:**")
        st.latex(r"M_u = \phi_b M_n = 0.90 \cdot M_n") # แสดงการคูณ
        st.latex(rf"M_u = 0.90 \times {Mn_kgcm:,.0f} = \mathbf{{{0.90*Mn_kgcm:,.0f}}} \text{{ kg-cm}}")
        st.latex(rf"w_{{u,moment}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # 3. Deflection Check (สิ่งที่เคยตกหล่นไป: แสดงที่มาของ delta limit)
    st.markdown("#### 3️⃣ Deflection Check (Serviceability)")
    st.write("การตรวจสอบระยะแอ่นตัว (ใช้ Service Load เสมอ)")
    
    delta_allow = (L_input * 100) / 360
    st.latex(rf"\delta_{{allow}} = \frac{{L}}{{360}} = \frac{{{L_input*100:.0f} \text{{ cm}}}}{{360}} = \mathbf{{{delta_allow:.2f}}} \text{{ cm}}")
    st.latex(rf"w_{{deflect}} = \frac{{384 E I \delta_{{allow}}}}{{5 L^4}} = \mathbf{{{res_w_d:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # 4. Final Summary
    st.success(f"✅ **Governing Capacity (ค่าน้อยที่สุด): {gov_cap:,.0f} kg/m**")
    net_safe = max(gov_cap - props['W'], 0)
    st.caption(f"หักน้ำหนักคาน ({props['W']} kg/m) เหลือรับน้ำหนักบรรทุกจรจริง = {net_safe:,.0f} kg/m")
