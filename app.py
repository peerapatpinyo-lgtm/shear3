import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Ultimate Master", layout="wide")

# --- 2. DATABASE (FULL STANDARD SERIES) ---
# Format: "Name": {W:kg/m, D:mm, tw:mm, Ix:cm4, Zx:cm3}
# ข้อมูลครบทุก Series หลัก ตั้งแต่เล็กสุดถึงใหญ่สุด
SYS_H_BEAMS = {
    # Series 100
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5, "Ix": 378, "Zx": 84},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6, "Ix": 383, "Zx": 88},
    # Series 125
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6, "Ix": 847, "Zx": 153},
    "H-125x125x6.5x9":  {"W": 23.8, "D": 125, "tw": 6.5, "Ix": 1360, "Zx": 242},
    # Series 150
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5, "Ix": 1050, "Zx": 160},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7, "Ix": 1640, "Zx": 245},
    # Series 175
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5, "Ix": 2040, "Zx": 265},
    "H-175x175x7.5x11": {"W": 40.2, "D": 175, "tw": 7.5, "Ix": 2940, "Zx": 375},
    # Series 200
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840, "Zx": 213},
    "H-200x150x6x9":    {"W": 30.6, "D": 194, "tw": 6, "Ix": 2690, "Zx": 305},
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8, "Ix": 4720, "Zx": 523},
    # Series 250
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6, "Ix": 4050, "Zx": 365},
    "H-250x175x7x11":   {"W": 44.1, "D": 244, "tw": 7, "Ix": 6120, "Zx": 560},
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9, "Ix": 10800, "Zx": 955},
    "H-250x255x14x14":  {"W": 82.2, "D": 250, "tw": 14, "Ix": 11500, "Zx": 1030},
    # Series 300
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210, "Zx": 545},
    "H-300x200x8x12":   {"W": 56.8, "D": 294, "tw": 8, "Ix": 11300, "Zx": 860},
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10, "Ix": 20400, "Zx": 1500},
    # Series 350
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7, "Ix": 13600, "Zx": 875},
    "H-350x250x9x14":   {"W": 79.7, "D": 340, "tw": 9, "Ix": 21700, "Zx": 1420},
    "H-350x350x12x19":  {"W": 137.0, "D": 350, "tw": 12, "Ix": 40300, "Zx": 2550},
    # Series 400
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8, "Ix": 23700, "Zx": 1340},
    "H-400x300x10x16":  {"W": 107.0, "D": 390, "tw": 10, "Ix": 38700, "Zx": 2180},
    "H-400x400x13x21":  {"W": 172.0, "D": 400, "tw": 13, "Ix": 66600, "Zx": 3750},
    # Series 450-500
    "H-450x200x9x14":   {"W": 76.0, "D": 450, "tw": 9, "Ix": 33500, "Zx": 1690},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10, "Ix": 47800, "Zx": 2150},
    # Series 600-900 (Large)
    "H-588x300x12x20":  {"W": 151.0, "D": 588, "tw": 12, "Ix": 118000, "Zx": 4450},
    "H-600x200x11x17":  {"W": 106.0, "D": 600, "tw": 11, "Ix": 77600, "Zx": 2950},
    "H-700x300x13x24":  {"W": 185.0, "D": 700, "tw": 13, "Ix": 201000, "Zx": 6450},
    "H-800x300x14x26":  {"W": 210.0, "D": 800, "tw": 14, "Ix": 292000, "Zx": 8250},
    "H-900x300x16x28":  {"W": 243.0, "D": 900, "tw": 16, "Ix": 411000, "Zx": 10200},
}

# --- 3. LOGIC & CALCULATION ---
def core_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Setup
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    
    # 3.2 Nominal
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * props['Zx']
    
    # 3.3 Design Factor
    if method == "ASD":
        val_v, val_b = 1.50, 1.67
        V_des = Vn / val_v
        M_des = Mn / val_b
        txt_v, txt_m = r"\frac{V_n}{1.50}", r"\frac{M_n}{1.67}"
    else: # LRFD
        val_v, val_b = 1.00, 0.90
        V_des = Vn * val_v
        M_des = Mn * val_b
        txt_v, txt_m = r"1.00 V_n", r"0.90 M_n"
        
    # 3.4 Equivalent Uniform Loads (kg/m)
    ws = (2 * V_des / L_cm) * 100
    wm = (8 * M_des / L_cm**2) * 100
    
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 3.5 Transition Points (Critical Lengths)
    L_vm_cm = (4 * M_des) / V_des
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_des)
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'],
        "V_des": V_des, "M_des": M_des,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta": delta_allow,
        "L_vm": L_vm_cm/100.0, "L_md": L_md_cm/100.0,
        "txt_v": txt_v, "txt_m": txt_m
    }

# --- 4. UI INTERFACE ---
st.title("🏗️ SYS H-Beam: Complete Engineering Design")

with st.sidebar:
    st.header("1. Parameters")
    method = st.radio("Design Method", ["ASD", "LRFD"])
    Fy = st.number_input("Yield Strength (ksc)", value=2400)
    E_gpa = st.number_input("Elastic Modulus (GPa)", value=200)
    
    st.header("2. Section & Span")
    # Sort Sections by Size (D)
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method)

# --- 5. VISUALIZATION ---
t1, t2 = st.tabs(["📝 รายการคำนวณ (Calculation)", "📊 กราฟพฤติกรรม (Graph)"])

with t1:
    st.markdown(f"### 📄 Detailed Report: {section}")
    st.markdown("---")
    
    # Properties
    c1, c2, c3 = st.columns(3)
    c1.metric("Area Web ($A_w$)", f"{c['Aw']:.2f} cm²")
    c2.metric("Plastic Modulus ($Z_x$)", f"{props['Zx']:,} cm³")
    c3.metric("Inertia ($I_x$)", f"{props['Ix']:,} cm⁴")
    
    st.markdown("---")
    
    # Calculation Steps
    colA, colB = st.columns(2)
    with colA:
        st.info("**1. แรงเฉือน (Shear Control)**")
        st.latex(rf"V_{{design}} = {c['txt_v']} = \mathbf{{{c['V_des']:,.0f}}} \text{{ kg}}")
        st.write("Safe Load ($w_s$):")
        st.latex(rf"w_s = \frac{{2 V}}{{L}} = \mathbf{{{c['ws']:,.0f}}} \text{{ kg/m}}")
        
    with colB:
        st.success("**2. โมเมนต์ (Moment Control)**")
        st.latex(rf"M_{{design}} = {c['txt_m']} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")
        st.write("Safe Load ($w_m$):")
        st.latex(rf"w_m = \frac{{8 M}}{{L^2}} = \mathbf{{{c['wm']:,.0f}}} \text{{ kg/m}}")
    
    st.warning(f"**3. ระยะแอ่นตัว (Deflection Control)** $\delta = L/360 = {c['delta']:.2f}$ cm")
    st.latex(rf"w_d = \frac{{384 E I \delta}}{{5 L^4}} = \mathbf{{{c['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # Transition Points Calculation
    st.subheader("📍 จุดเปลี่ยนพฤติกรรม (Transition Lengths)")
    st.write("แสดงที่มาของการคำนวณระยะ Span ที่ทำให้โหมดการวิบัติเปลี่ยนไป:")
    
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown("**1. จุดเปลี่ยน Shear $\\to$ Moment ($L_{v-m}$)**")
        st.latex(r"L_{v-m} = \frac{4 M_{design}}{V_{design}}")
        st.latex(rf"= \frac{{4 \times {c['M_des']:,.0f}}}{{{c['V_des']:,.0f}}} = \mathbf{{{c['L_vm']:.2f}}} \text{{ m}}")
        
    with t_col2:
        st.markdown("**2. จุดเปลี่ยน Moment $\\to$ Deflection ($L_{m-d}$)**")
        st.latex(r"L_{m-d} = \frac{384 E I}{14400 M_{design}}")
        st.latex(rf"= \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,}}}{{14400 \times {c['M_des']:,.0f}}} = \mathbf{{{c['L_md']:.2f}}} \text{{ m}}")

    st.markdown("---")
    
    # Conclusion
    final_w = min(c['ws'], c['wm'], c['wd'])
    net_w = max(0, final_w - props['W'])
    st.success(f"✅ **Safe Net Load (น้ำหนักบรรทุกปลอดภัยสุทธิ) = {net_w:,.0f} kg/m**")

with t2:
    # Graph Generation
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    # Arrays
    ys = (2 * c['V_des'] / (x*100)) * 100
    ym = (8 * c['M_des'] / (x*100)**2) * 100
    k_def = (384 * c['E_ksc'] * props['Ix']) / 1800
    yd = (k_def / (x*100)**3) * 100
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    
    fig = go.Figure()
    
    # Background Zones
    y_lim = max(y_gov) * 1.4
    fig.add_shape(type="rect", x0=0, x1=c['L_vm'], y0=0, y1=y_lim, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=c['L_vm'], x1=c['L_md'], y0=0, y1=y_lim, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=c['L_md'], x1=L_max, y0=0, y1=y_lim, fillcolor="green", opacity=0.1, line_width=0)
    
    # Text Annotations
    fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="red"))
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="orange"))
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="green"))
    
    # Curves
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=x, y=y_gov, name='Capacity', line=dict(color='black', width=3)))
    
    # User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Your Design'))
    
    fig.update_layout(title=f"Capacity Envelope: {section}", height=600, 
                      xaxis_title="Span Length (m)", yaxis_title="Load (kg/m)",
                      yaxis_range=[0, final_w*2.5])
    
    st.plotly_chart(fig, use_container_width=True)
