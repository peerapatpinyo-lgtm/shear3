import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. ฐานข้อมูลหน้าตัดเหล็ก SYS (Siam Yamato Steel) ---
# Format: Key = Name, Value = {W: kg/m, D: mm, tw: mm, Ix: cm4, Zx: cm3}
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

# --- 2. ฟังก์ชันคำนวณกราฟ ---
def get_capacity_curves(lengths, Fy_ksc, E_gpa, props):
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # Base Capacity (SI Units)
    V_allow_N = 0.40 * Fy_pa * Aw 
    M_allow_N = 0.60 * Fy_pa * Zx
    
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Calculate Load (w) in N/m
        w_s = (2 * V_allow_N) / L
        w_m = (8 * M_allow_N) / (L**2)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        # Convert to kg/m
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), V_allow_N

# --- Main App ---
st.set_page_config(page_title="SYS Beam Analysis", layout="wide")
st.title("🏗️ SYS H-Beam Capacity & Calculation Report")

# Sidebar Input
st.sidebar.header("1. เลือกหน้าตัดและวัสดุ")
section_name = st.sidebar.selectbox("เลือกขนาด H-Beam (SYS)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Fy (ksc)", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa)", value=200)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Properties")
st.sidebar.write(f"**Weight:** {props['W']} kg/m")
st.sidebar.write(f"**$A_{{web}} \approx D \\cdot t_w$:** {(props['D']*props['tw'])/100:,.2f} cm²")
st.sidebar.write(f"**$I_x$:** {props['Ix']:,} cm⁴")
st.sidebar.write(f"**$Z_x$:** {props['Zx']:,} cm³")

st.sidebar.markdown("---")
st.sidebar.header("2. ตั้งค่าการคำนวณ")
L_input = st.sidebar.slider("ความยาวคาน L (m)", min_value=1.0, max_value=24.0, value=6.0, step=0.1)
view_mode = st.sidebar.radio("มุมมองกราฟ:", ["Uniform Load (kg/m)", "Max Shear Force (kg)"])

# --- Tabs: แยกส่วนกราฟ และ ส่วนรายการคำนวณ ---
tab1, tab2 = st.tabs(["📊 กราฟวิเคราะห์ (Chart)", "📝 รายการคำนวณละเอียด (Calculation Sheet)"])

# ================= TAB 1: GRAPH =================
with tab1:
    max_graph_len = max(24.0, L_input * 1.5)
    L_range = np.linspace(0.5, max_graph_len, 300)
    w_s, w_m, w_d, V_allow_N = get_capacity_curves(L_range, Fy, E_val_gpa, props)
    V_allow_kg = V_allow_N / 9.81
    
    w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
    w_safe = np.maximum(w_safe, 0)
    w_total_safe = w_safe + props['W']

    # Convert Graph Data
    if view_mode == "Max Shear Force (kg)":
        y_s = np.full_like(L_range, V_allow_kg) 
        y_m = (w_m * L_range) / 2
        y_d = (w_d * L_range) / 2
        y_safe = (w_total_safe * L_range) / 2
        y_title = "Max Shear Force / Reaction (kg)"
    else:
        y_s = w_s
        y_m = w_m
        y_d = w_d
        y_safe = w_total_safe
        y_title = "Total Uniform Load Capacity (kg/m)"

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=y_s, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=y_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=y_d, name='Deflection Limit', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=y_safe, name='Safe Capacity', line=dict(color='black', width=4)))
    
    # Current point marker
    current_idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[y_safe[current_idx]], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))
    
    # Zones
    governing_idx = np.argmin([y_s, y_m, y_d], axis=0)
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

    fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title=y_title, hovermode="x unified")
    fig.update_yaxes(range=[0, y_safe[current_idx]*2.0])
    st.plotly_chart(fig, use_container_width=True)


# ================= TAB 2: CALCULATION SHEET =================
with tab2:
    st.markdown("## 📝 รายการคำนวณ (Calculation Sheet)")
    st.markdown(f"**Project:** Beam Capacity Check | **Section:** {section_name} | **Span:** {L_input} m")
    st.markdown("---")
    
    # --- Constants for Calc Display ---
    g = 9.81
    # Unit Conversions for Display Consistency
    Aw_cm2 = (props['D'] * props['tw']) / 100
    Zx_cm3 = props['Zx']
    Ix_cm4 = props['Ix']
    L_cm = L_input * 100
    L_m = L_input
    E_ksc = (E_val_gpa * 1e9) / 98066.5 # Approx convert GPa to ksc
    
    # 1. SHEAR CALCULATION
    st.markdown("### 1. ตรวจสอบแรงเฉือน (Shear Check)")
    st.markdown("สมมติฐาน: พื้นที่รับแรงเฉือน $A_w \approx D \times t_w$ (สำหรับเหล็กรูปพรรณรีดร้อน)")
    
    # Calculate values
    V_allow_kg = 0.40 * Fy * Aw_cm2
    w_shear_allow = (2 * V_allow_kg) / L_m
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**สูตร (Formula):**")
        st.latex(r"V_{allow} = 0.40 \cdot F_y \cdot A_w")
        st.latex(r"w_{shear} = \frac{2 \cdot V_{allow}}{L}")
    with col2:
        st.markdown("**แทนค่า (Substitution):**")
        st.latex(rf"V_{{allow}} = 0.40 \times {Fy} \times {Aw_cm2:.2f} = \mathbf{{{V_allow_kg:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{shear}} = \frac{{2 \times {V_allow_kg:,.0f}}}{{{L_m}}} = \mathbf{{{w_shear_allow:,.0f}}} \text{{ kg/m}}")
    
    st.info(f"👉 **Shear Capacity ($w_s$) = {w_shear_allow:,.0f} kg/m**")
    st.markdown("---")

    # 2. MOMENT CALCULATION
    st.markdown("### 2. ตรวจสอบโมเมนต์ดัด (Moment Check)")
    st.markdown("สมมติฐาน: หน้าตัด Compact และมีการค้ำยันเพียงพอ ($F_b = 0.60 F_y$)")
    
    # Calculate values
    M_allow_kgcm = 0.60 * Fy * Zx_cm3
    M_allow_kgm = M_allow_kgcm / 100
    w_moment_allow = (8 * M_allow_kgm) / (L_m**2)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**สูตร (Formula):**")
        st.latex(r"M_{allow} = 0.60 \cdot F_y \cdot Z_x")
        st.latex(r"w_{moment} = \frac{8 \cdot M_{allow}}{L^2}")
    with col2:
        st.markdown("**แทนค่า (Substitution):**")
        st.latex(rf"M_{{allow}} = 0.60 \times {Fy} \times {Zx_cm3} = {M_allow_kgcm:,.0f} \text{{ kg-cm}}")
        st.latex(rf"M_{{allow}} (\text{{kg-m}}) = {M_allow_kgm:,.0f} \text{{ kg-m}}")
        st.latex(rf"w_{{moment}} = \frac{{8 \times {M_allow_kgm:,.0f}}}{{{L_m}^2}} = \mathbf{{{w_moment_allow:,.0f}}} \text{{ kg/m}}")

    st.info(f"👉 **Moment Capacity ($w_m$) = {w_moment_allow:,.0f} kg/m**")
    st.markdown("---")

    # 3. DEFLECTION CALCULATION
    st.markdown("### 3. ตรวจสอบการแอ่นตัว (Deflection Check)")
    st.markdown("เกณฑ์ที่ยอมให้: $\delta_{allow} = L/360$")
    
    # Calculate values
    delta_allow_cm = L_cm / 360
    # Formula: w = (384 E I delta) / (5 L^4) -> need careful units. 
    # Use kg, cm units for calc then convert to m
    # w (kg/cm) = ...
    w_deflect_kg_cm = (384 * E_ksc * Ix_cm4 * delta_allow_cm) / (5 * (L_cm**4))
    w_deflect_kg_m = w_deflect_kg_cm * 100 # convert load per cm to load per m
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**สูตร (Formula):**")
        st.latex(r"\delta_{allow} = \frac{L}{360}")
        st.latex(r"w_{deflect} = \frac{384 \cdot E \cdot I \cdot \delta_{allow}}{5 \cdot L^4}")
    with col2:
        st.markdown("**แทนค่า (Substitution - Units: kg, cm):**")
        st.latex(rf"\delta_{{allow}} = \frac{{{L_cm:.0f}}}{{360}} = {delta_allow_cm:.2f} \text{{ cm}}")
        # Show E in scientific notation for brevity
        st.latex(rf"w_{{d}} = \frac{{384 \cdot ({E_ksc:.2e}) \cdot {Ix_cm4} \cdot {delta_allow_cm:.2f}}}{{5 \cdot {L_cm:.0f}^4}}")
        st.latex(rf"= {w_deflect_kg_cm:.2f} \text{{ kg/cm}} \Rightarrow \mathbf{{{w_deflect_kg_m:,.0f}}} \text{{ kg/m}}")

    st.info(f"👉 **Deflection Capacity ($w_d$) = {w_deflect_kg_m:,.0f} kg/m**")
    st.markdown("---")

    # 4. SUMMARY
    st.markdown("### 4. สรุปผลการคำนวณ (Conclusion)")
    
    vals = {'Shear ($w_s$)': w_shear_allow, 'Moment ($w_m$)': w_moment_allow, 'Deflection ($w_d$)': w_deflect_kg_m}
    control_case = min(vals, key=vals.get)
    safe_load_total = vals[control_case]
    safe_load_net = safe_load_total - props['W']
    if safe_load_net < 0: safe_load_net = 0
    
    st.write("เปรียบเทียบค่าความสามารถในการรับน้ำหนัก (Total Load):")
    st.write(f"1. Shear: {w_shear_allow:,.0f} kg/m")
    st.write(f"2. Moment: {w_moment_allow:,.0f} kg/m")
    st.write(f"3. Deflection: {w_deflect_kg_m:,.0f} kg/m")
    
    st.success(f"""
    **✅ Governing Case (ค่าน้อยที่สุด): {control_case}**
    
    * **Total Safe Load:** {safe_load_total:,.0f} kg/m
    * **หักน้ำหนักคาน:** -{props['W']} kg/m
    * **Net Safe Load (น้ำหนักบรรทุกปลอดภัย): {safe_load_net:,.0f} kg/m**
    """)
