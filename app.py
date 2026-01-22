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
st.set_page_config(page_title="SYS H-Beam Analysis", layout="wide")
st.title("🏗️ SYS H-Beam Capacity Analysis & Calculation")

# Sidebar
st.sidebar.header("1. ตัวแปรตั้งต้น (Input)")
section_name = st.sidebar.selectbox("เลือกหน้าตัด (Section)", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]
Fy = st.sidebar.number_input("Yield Strength (Fy) [ksc]", value=2400)
E_val_gpa = st.sidebar.number_input("Elastic Modulus (E) [GPa]", value=200)

st.sidebar.markdown("---")
st.sidebar.header("2. ตั้งค่าการแสดงผล")
L_input = st.sidebar.slider("ความยาวช่วงคาน L (เมตร)", min_value=1.0, max_value=24.0, value=6.0, step=0.1)
view_mode = st.sidebar.radio("มุมมองกราฟ (Y-Axis):", ["Uniform Load (kg/m)", "Max Shear Force (kg)"])

# Tabs
tab1, tab2 = st.tabs(["📊 กราฟวิเคราะห์ (Chart)", "📝 รายการคำนวณ (Calculation Sheet)"])

# ================= TAB 1: GRAPH (Full Feature) =================
with tab1:
    max_graph_len = max(24.0, L_input * 1.5)
    L_range = np.linspace(0.5, max_graph_len, 300)
    w_s, w_m, w_d, V_allow_N = get_capacity_curves(L_range, Fy, E_val_gpa, props)
    V_allow_kg = V_allow_N / 9.81
    
    # Base Safe Load (kg/m)
    w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
    w_safe = np.maximum(w_safe, 0)
    w_total_safe = w_safe + props['W']

    # --- Convert Graph Data based on View Mode ---
    if view_mode == "Max Shear Force (kg)":
        # Convert w (kg/m) to Shear Force V (kg) -> V = wL/2
        y_s = np.full_like(L_range, V_allow_kg) # Shear Limit is constant force
        y_m = (w_m * L_range) / 2
        y_d = (w_d * L_range) / 2
        y_safe = (w_total_safe * L_range) / 2
        y_title = "Max Shear Force / Reaction (kg)"
    else:
        # Keep as Load w (kg/m)
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
    
    # Current Point
    current_idx = (np.abs(L_range - L_input)).argmin()
    fig.add_trace(go.Scatter(x=[L_input], y=[y_safe[current_idx]], mode='markers', marker=dict(size=12, color='blue'), name='Current L'))
    
    # Color Zones (Highlights)
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
    fig.update_yaxes(range=[0, y_safe[current_idx]*2.5]) # Zoom to relevant range
    st.plotly_chart(fig, use_container_width=True)


# ================= TAB 2: FULL CALCULATION (ละเอียด) =================
with tab2:
    st.markdown(f"## 📝 รายการคำนวณโครงสร้าง (Structural Calculation)")
    st.markdown(f"**Project:** Beam Check | **Section:** {section_name} | **Span:** {L_input:.2f} m")
    
    # 1. Variables
    st.markdown("### 1. ข้อมูลการออกแบบ (Design Data)")
    E_ksc = (E_val_gpa * 1e9) / 98066.5 
    D_cm = props['D'] / 10
    tw_cm = props['tw'] / 10
    Aw_cm2 = D_cm * tw_cm
    Ix_cm4 = props['Ix']
    Zx_cm3 = props['Zx']
    L_cm = L_input * 100
    
    col_var1, col_var2 = st.columns(2)
    with col_var1:
        st.write(f"- $F_y$ = **{Fy:,.0f}** ksc")
        st.write(f"- $E$ = {E_val_gpa} GPa $\\approx$ **{E_ksc:,.0f}** ksc")
    with col_var2:
        st.write(f"- $D$ = **{D_cm:.1f}** cm, $t_w$ = **{tw_cm:.2f}** cm")
        st.write(f"- $A_w$ = **{Aw_cm2:.2f}** cm²")
        st.write(f"- $I_x$ = **{Ix_cm4:,.0f}** cm⁴, $Z_x$ = **{Zx_cm3:,.0f}** cm³")
        st.write(f"- Weight = **{props['W']}** kg/m")

    st.markdown("---")

    # 2. SHEAR CHECK
    st.markdown("### 2. แรงเฉือน (Shear Capacity)")
    V_allow_kg = 0.40 * Fy * Aw_cm2
    w_shear_load = (2 * V_allow_kg) / L_input
    
    st.latex(rf"V_{{allow}} = 0.40 \times {Fy} \times {Aw_cm2:.2f} = \mathbf{{{V_allow_kg:,.0f}}} \text{{ kg}}")
    st.latex(rf"w_s = \frac{{2 \times V_{{allow}}}}{{L}} = \frac{{2 \times {V_allow_kg:,.0f}}}{{{L_input}}} = \mathbf{{{w_shear_load:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # 3. MOMENT CHECK
    st.markdown("### 3. โมเมนต์ดัด (Moment Capacity)")
    M_allow_kgcm = 0.60 * Fy * Zx_cm3
    M_allow_kgm = M_allow_kgcm / 100
    w_moment_load = (8 * M_allow_kgm) / (L_input**2)
    
    st.latex(rf"M_{{allow}} = 0.60 \times {Fy} \times {Zx_cm3:.1f} = {M_allow_kgcm:,.0f} \text{{ kg-cm}} = {M_allow_kgm:,.0f} \text{{ kg-m}}")
    st.latex(rf"w_m = \frac{{8 \times M_{{allow}}}}{{L^2}} = \frac{{8 \times {M_allow_kgm:,.0f}}}{{{L_input}^2}} = \mathbf{{{w_moment_load:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")

    # 4. DEFLECTION CHECK
    st.markdown("### 4. การแอ่นตัว (Deflection Capacity)")
    delta_allow_cm = L_cm / 360
    w_d_kg_cm = (384 * E_ksc * Ix_cm4 * delta_allow_cm) / (5 * (L_cm**4))
    w_deflect_load = w_d_kg_cm * 100 
    
    st.latex(rf"\delta_{{allow}} = L/360 = {delta_allow_cm:.2f} \text{{ cm}}")
    st.latex(rf"w_d = \frac{{384 E I \delta}}{{5 L^4}} = \frac{{384 \cdot {E_ksc:.0f} \cdot {Ix_cm4} \cdot {delta_allow_cm:.2f}}}{{5 \cdot {L_cm:.0f}^4}}")
    st.latex(rf"= {w_d_kg_cm:.2f} \text{{ kg/cm}} \Rightarrow \mathbf{{{w_deflect_load:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # 5. CONCLUSION
    st.markdown("### 5. สรุปผล (Conclusion)")
    vals = {'Shear': w_shear_load, 'Moment': w_moment_load, 'Deflection': w_deflect_load}
    min_case = min(vals, key=vals.get)
    total_safe = vals[min_case]
    net_safe = max(total_safe - props['W'], 0)
    
    st.info(f"👉 **Governing Case:** {min_case} Control (Limit = {total_safe:,.0f} kg/m)")
    st.success(f"✅ **Safe Net Load (รับน้ำหนักบรรทุกปลอดภัยสุทธิ): {net_safe:,.0f} kg/m**")
