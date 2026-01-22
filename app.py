import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Ultimate Design", layout="wide")

# --- 2. DATABASE (FULL SYS/TIS STANDARD) ---
# Properties: W(kg/m), D(mm), tw(mm), Ix(cm4), Zx(cm3 - Plastic Modulus)
# Note: Zx is used for Compact Section strength (Mn = Fy*Zx). 
# If Zx is not available in old tables, Zx approx 1.10-1.15 * Sx. 
# Values below are based on standard catalogs.

SYS_H_BEAMS = {
    # --- Series 100 ---
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 84.0},  # Sx=75.6
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 88.0},  # Sx=76.5
    
    # --- Series 125 ---
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6,   "Ix": 847,    "Zx": 153},   # Sx=136
    "H-125x125x6.5x9":  {"W": 23.8, "D": 125, "tw": 6.5, "Ix": 1360,   "Zx": 242},   # Sx=218
    
    # --- Series 150 ---
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 160},   # Sx=140
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 245},   # Sx=219
    "H-148x100x6x9 (Wide)":{"W": 21.1, "D": 148, "tw": 6,   "Ix": 1020,   "Zx": 155}, # Sx=138
    
    # --- Series 175 ---
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5,   "Ix": 2040,   "Zx": 265},   # Sx=233
    "H-175x175x7.5x11": {"W": 40.2, "D": 175, "tw": 7.5, "Ix": 2940,   "Zx": 375},   # Sx=335
    
    # --- Series 200 ---
    "H-194x150x6x9":    {"W": 30.6, "D": 194, "tw": 6,   "Ix": 2690,   "Zx": 305},   # Sx=277
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 213},   # Sx=184
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8,   "Ix": 4720,   "Zx": 523},   # Sx=472
    
    # --- Series 250 ---
    "H-244x175x7x11":   {"W": 44.1, "D": 244, "tw": 7,   "Ix": 6120,   "Zx": 560},   # Sx=502
    "H-248x124x5x8":    {"W": 25.7, "D": 248, "tw": 5,   "Ix": 3540,   "Zx": 320},   # Sx=285
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 365},   # Sx=324
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9,   "Ix": 10800,  "Zx": 955},   # Sx=867
    "H-250x255x14x14":  {"W": 82.2, "D": 250, "tw": 14,  "Ix": 11500,  "Zx": 1030},  # Sx=919

    # --- Series 300 ---
    "H-294x200x8x12":   {"W": 56.8, "D": 294, "tw": 8,   "Ix": 11300,  "Zx": 860},   # Sx=771
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 545},   # Sx=481
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10,  "Ix": 20400,  "Zx": 1500},  # Sx=1360
    
    # --- Series 350 ---
    "H-340x250x9x14":   {"W": 79.7, "D": 340, "tw": 9,   "Ix": 21700,  "Zx": 1420},  # Sx=1280
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 875},   # Sx=775
    "H-350x350x12x19":  {"W": 137.0,"D": 350, "tw": 12,  "Ix": 40300,  "Zx": 2550},  # Sx=2300

    # --- Series 400 ---
    "H-390x300x10x16":  {"W": 107.0,"D": 390, "tw": 10,  "Ix": 38700,  "Zx": 2180},  # Sx=1980
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1340},  # Sx=1190
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3750},  # Sx=3330
    
    # --- Series 450 - 900 (Large Sections) ---
    "H-440x300x11x18":  {"W": 124.0,"D": 440, "tw": 11,  "Ix": 56100,  "Zx": 2800},  # Sx=2550
    "H-450x200x9x14":   {"W": 76.0, "D": 450, "tw": 9,   "Ix": 33500,  "Zx": 1690},  # Sx=1490
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 2150},  # Sx=1910
    "H-588x300x12x20":  {"W": 151.0,"D": 588, "tw": 12,  "Ix": 118000, "Zx": 4450},  # Sx=4020
    "H-600x200x11x17":  {"W": 106.0,"D": 600, "tw": 11,  "Ix": 77600,  "Zx": 2950},  # Sx=2590
    "H-700x300x13x24":  {"W": 185.0,"D": 700, "tw": 13,  "Ix": 201000, "Zx": 6450},  # Sx=5760
    "H-800x300x14x26":  {"W": 210.0,"D": 800, "tw": 14,  "Ix": 292000, "Zx": 8250},  # Sx=7290
    "H-900x300x16x28":  {"W": 243.0,"D": 900, "tw": 16,  "Ix": 411000, "Zx": 10200}, # Sx=9140
}

# --- 3. MATH ENGINE ---
def precision_calc(L_m, Fy_ksc, E_gpa, props, method):
    # Units
    E_ksc = E_gpa * 10197.162  
    L_cm = L_m * 100.0         
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    
    # Capacities
    Vn = 0.60 * Fy_ksc * Aw 
    Mn = Fy_ksc * props['Zx']
    
    if method == "ASD":
        # AISC ASD
        val_v, val_b = 1.50, 1.67
        V_design = Vn / val_v
        M_design = Mn / val_b
        txt_v_eq, txt_m_eq = r"V_n / 1.50", r"M_n / 1.67"
    else:
        # AISC LRFD
        val_v, val_b = 1.00, 0.90
        V_design = Vn * val_v
        M_design = Mn * val_b
        txt_v_eq, txt_m_eq = r"1.00 \cdot V_n", r"0.90 \cdot M_n"

    # Equivalent Loads
    ws = (2 * V_design / L_cm) * 100
    wm = (8 * M_design / L_cm**2) * 100
    
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # Transitions
    L_vm_cm = (4 * M_design) / V_design
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_design)
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], 
        "V_design": V_design, "M_design": M_design,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta_allow": delta_allow,
        "L_vm_m": L_vm_cm / 100.0, "L_md_m": L_md_cm / 100.0,
        "txt_v_eq": txt_v_eq, "txt_m_eq": txt_m_eq
    }

# --- 4. UI ---
st.title("🏗️ SYS H-Beam: Professional Design Tool")

with st.sidebar:
    st.header("1. Parameters")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (ksc)", value=2400, step=100)
    E_gpa = st.number_input("E (GPa)", value=200)
    
    st.header("2. Section Selection")
    # Sort keys for easier finding
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select H-Beam Size", sorted_sections, index=10) # Default to H-200
    
    L_input = st.slider("Span Length (m)", 2.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = precision_calc(L_input, Fy, E_gpa, props, method)

# --- 5. REPORT & GRAPH ---
tab_sheet, tab_graph = st.tabs(["📝 Calculation Sheet", "📊 Capacity Graph"])

with tab_sheet:
    st.markdown(f"### Engineering Report: {section}")
    st.markdown("---")
    
    # Properties
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Weight", f"{props['W']} kg/m")
    c2.metric("Aw (Shear Area)", f"{cal['Aw']:.2f} cm²")
    c3.metric("Zx (Plastic)", f"{props['Zx']:,} cm³")
    c4.metric("Ix (Inertia)", f"{props['Ix']:,} cm⁴")
    
    st.markdown("---")
    
    # Detailed Steps
    col_L, col_R = st.columns(2)
    
    with col_L:
        st.subheader("🔹 Shear (แรงเฉือน)")
        st.latex(rf"V_{{design}} = {cal['txt_v_eq']} = \mathbf{{{cal['V_design']:,.0f}}} \text{{ kg}}")
        st.write("Equivalent Load ($w_s$):")
        st.latex(rf"w_s = \frac{{2 V}}{{L}} = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")

    with col_R:
        st.subheader("🔹 Moment (โมเมนต์)")
        st.latex(rf"M_{{design}} = {cal['txt_m_eq']} = \mathbf{{{cal['M_design']:,.0f}}} \text{{ kg-cm}}")
        st.write("Equivalent Load ($w_m$):")
        st.latex(rf"w_m = \frac{{8 M}}{{L^2}} = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")
    
    st.subheader("🔹 Deflection (ระยะแอ่น)")
    st.write(f"Allowable $\delta = L/360 = {cal['delta_allow']:.2f}$ cm")
    st.latex(rf"w_d = \frac{{384 E I \delta}}{{5 L^4}} = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # Critical Lengths
    st.subheader("📍 Critical Transition Lengths")
    st.write("จุดเปลี่ยนพฤติกรรมการรับน้ำหนัก (Transition Points):")
    cols1, cols2 = st.columns(2)
    cols1.info(f"**Shear ➝ Moment ($L_{{v-m}}$):**\n\n $L = {cal['L_vm_m']:.2f}$ m")
    cols2.info(f"**Moment ➝ Deflection ($L_{{m-d}}$):**\n\n $L = {cal['L_md_m']:.2f}$ m")

    # Conclusion
    final_w = min(cal['ws'], cal['wm'], cal['wd'])
    net_w = max(0, final_w - props['W'])
    
    st.success(f"✅ **Max Safe Load (Net): {net_w:,.0f} kg/m**")

with tab_graph:
    # Graphing Logic
    L_max = max(15, cal['L_md_m'] * 1.2, L_input * 1.5)
    L_range = np.linspace(0.5, L_max, 300)
    
    ys, ym, yd = [], [], []
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 
    
    for l in L_range:
        l_cm = l * 100
        ys.append(2 * cal['V_design'] / l_cm * 100)
        ym.append(8 * cal['M_design'] / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100)
        
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    
    fig = go.Figure()
    
    # Zones
    y_top = max(y_gov) * 1.3
    fig.add_shape(type="rect", x0=0, x1=cal['L_vm_m'], y0=0, y1=y_top, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=cal['L_vm_m'], x1=cal['L_md_m'], y0=0, y1=y_top, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=cal['L_md_m'], x1=L_max, y0=0, y1=y_top, fillcolor="green", opacity=0.1, line_width=0)
    
    # Labels
    fig.add_annotation(x=cal['L_vm_m']/2, y=y_top*0.9, text="SHEAR", showarrow=False, font=dict(color="red"))
    fig.add_annotation(x=(cal['L_vm_m']+cal['L_md_m'])/2, y=y_top*0.9, text="MOMENT", showarrow=False, font=dict(color="orange"))
    fig.add_annotation(x=(cal['L_md_m']+L_max)/2, y=y_top*0.9, text="DEFLECTION", showarrow=False, font=dict(color="green"))

    # Curves
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Capacity', line=dict(color='black', width=3)))
    
    # Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', marker=dict(size=12, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Your Design'))

    fig.update_layout(title=f"Capacity Envelope: {section}", xaxis_title="Span (m)", yaxis_title="Load (kg/m)", 
                      yaxis_range=[0, final_w * 2.5], height=600)
    st.plotly_chart(fig, use_container_width=True)
