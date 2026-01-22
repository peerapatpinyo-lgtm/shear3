import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Master Analysis (Verified)", layout="wide")

# --- 2. DATABASE (Standard SYS H-Beam Properties) ---
# Units: W(kg/m), D(mm), tw(mm), Ix(cm4), Zx(cm3 - Plastic Modulus)
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

# --- 3. MATH ENGINE (Verified Logic) ---
def master_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversions
    E_ksc = E_gpa * 10197.162  # GPa -> ksc
    L_cm = L_m * 100.0         # m -> cm
    Aw = (props['D']/10.0) * (props['tw']/10.0) # cm2
    
    # 3.2 Nominal Strengths (AISC 360)
    # Shear: Vn = 0.6 Fy Aw
    Vn = 0.60 * Fy_ksc * Aw 
    # Moment: Mn = Fy Zx (Assuming Compact & Fully Braced)
    Mn = Fy_ksc * props['Zx']
    
    # 3.3 Design Strengths (Factor Application)
    if method == "ASD":
        factor_v_sym, factor_b_sym = r"\Omega_v", r"\Omega_b"
        val_v, val_b = 1.50, 1.67
        V_cap = Vn / val_v
        M_cap = Mn / val_b
    else: # LRFD
        factor_v_sym, factor_b_sym = r"\phi_v", r"\phi_b"
        val_v, val_b = 1.00, 0.90
        V_cap = Vn * val_v
        M_cap = Mn * val_b

    # 3.4 Load Capacities (w) at Current Span
    # w_shear = 2V/L
    ws = (2 * V_cap / L_cm) * 100
    # w_moment = 8M/L^2
    wm = (8 * M_cap / L_cm**2) * 100
    
    # w_deflection (limit L/360) derived from delta = 5wL^4/384EI
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 3.5 Critical Transition Points (Mathematical Intersection)
    # L where Shear Control ends and Moment Control begins:
    # 2V/L = 8M/L^2  -> L = 4M/V
    L_vm_cm = (4 * M_cap) / V_cap
    
    # L where Moment Control ends and Deflection Control begins:
    # 8M/L^2 = 384EI/(1800 L^3) -> L = 384EI / (14400 M)
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_cap)
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], "E_ksc": E_ksc,
        "Vn": Vn, "Mn": Mn, 
        "V_cap": V_cap, "M_cap": M_cap,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "delta_allow": delta_allow,
        "L_vm_m": L_vm_cm / 100.0,
        "L_md_m": L_md_cm / 100.0,
        "factor_v_sym": factor_v_sym, "val_v": val_v,
        "factor_b_sym": factor_b_sym, "val_b": val_b
    }

# --- 4. UI SETUP ---
st.title("🏗️ SYS H-Beam: Verified Engineering Analysis")
st.sidebar.header("Input Parameters")
method = st.sidebar.radio("Design Method", ["ASD", "LRFD"])
section = st.sidebar.selectbox("Section Size", list(SYS_H_BEAMS.keys()))
Fy = st.sidebar.number_input("Yield Strength, Fy (ksc)", value=2400)
E_gpa = st.sidebar.number_input("Elastic Modulus, E (GPa)", value=200)
L_input = st.sidebar.slider("Span Length (m)", 1.0, 24.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = master_calculation(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab_graph, tab_sheet = st.tabs(["📊 Capacity Envelope (Graph)", "📝 Calculation Sheet (Detailed)"])

# === TAB 1: GRAPH & VISUALIZATION ===
with tab_graph:
    # Prepare Plot Data
    L_max = max(15, cal['L_md_m'] * 1.2, L_input * 1.5)
    L_range = np.linspace(0.1, L_max, 400)
    
    ys, ym, yd = [], [], []
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 # Pre-calc constant
    
    for l in L_range:
        l_cm = l * 100
        # Check divide by zero safety (l starts at 0.1)
        ys.append(2 * cal['V_cap'] / l_cm * 100)
        ym.append(8 * cal['M_cap'] / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100)
        
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    cur_w = min(cal['ws'], cal['wm'], cal['wd'])
    
    fig = go.Figure()
    
    # --- FIXED: Use 'inside top' for annotation_position to avoid ValueError ---
    # Zone 1: Shear
    fig.add_vrect(x0=0, x1=cal['L_vm_m'], fillcolor="rgba(255,0,0,0.1)", line_width=0, 
                  annotation_text="SHEAR CONTROL", annotation_position="inside top")
    
    # Zone 2: Moment
    fig.add_vrect(x0=cal['L_vm_m'], x1=cal['L_md_m'], fillcolor="rgba(255,165,0,0.1)", line_width=0, 
                  annotation_text="MOMENT CONTROL", annotation_position="inside top")
    
    # Zone 3: Deflection
    fig.add_vrect(x0=cal['L_md_m'], x1=L_max, fillcolor="rgba(0,128,0,0.1)", line_width=0, 
                  annotation_text="DEFLECTION CONTROL", annotation_position="inside top")
    
    # Lines
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Governing Capacity', line=dict(color='black', width=4)))
    
    # User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[cur_w], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='x'), 
                             text=[f"{cur_w:,.0f}"], textposition="top right", 
                             name='Your Design'))
    
    fig.update_layout(height=600, title=f"Capacity Envelope: {section}", 
                      xaxis_title="Span Length (m)", yaxis_title="Safe Load (kg/m)", 
                      yaxis_range=[0, max(cur_w*2.5, 2000)])
    st.plotly_chart(fig, use_container_width=True)

# === TAB 2: ENGINEERING CALCULATION ===
with tab_sheet:
    st.markdown(f"### 📄 รายการคำนวณวิศวกรรม: {section} ({method})")
    
    # 1. Properties
    st.markdown("#### 1. ข้อมูลและคุณสมบัติ (Design Data)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"- Span ($L$) = **{L_input}** m")
        st.write(f"- Yield Strength ($F_y$) = **{Fy}** ksc")
        st.write(f"- Design Method: **{method}**")
    with c2:
        st.write(f"- Area ($A_w \approx d \cdot t_w$) = **{cal['Aw']:.2f}** cm²")
        st.write(f"- Plastic Modulus ($Z_x$) = **{props['Zx']}** cm³")
        st.write(f"- Moment of Inertia ($I_x$) = **{props['Ix']:,}** cm⁴")
    st.markdown("---")
    
    # 2. Calculations
    st.markdown("#### 2. การคำนวณกำลังรับน้ำหนัก (Load Capacity)")
    
    # 2.1 Shear
    st.subheader("2.1 แรงเฉือน (Shear Capacity)")
    st.write(f"Nominal Strength ($V_n = 0.6 F_y A_w$):")
    st.latex(rf"V_n = 0.60 \times {Fy} \times {cal['Aw']:.2f} = {cal['Vn']:,.0f} \text{{ kg}}")
    
    st.write(f"Design Strength ($V_{{cap}}$) using {cal['factor_v_sym']} = {cal['val_v']}:")
    if method == "ASD":
        st.latex(rf"V_{{cap}} = \frac{{{cal['Vn']:,.0f}}}{{{cal['val_v']}}} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
    else:
        st.latex(rf"V_{{cap}} = {cal['val_v']} \times {cal['Vn']:,.0f} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
    
    st.write("Safe Uniform Load ($w_s = 2V/L$):")
    st.latex(rf"w_s = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")
    
    # 2.2 Moment
    st.subheader("2.2 โมเมนต์ (Moment Capacity)")
    st.write(f"Nominal Strength ($M_n = F_y Z_x$) *Assuming Fully Braced*:")
    st.latex(rf"M_n = {Fy} \times {props['Zx']} = {cal['Mn']:,.0f} \text{{ kg-cm}}")
    
    st.write(f"Design Strength ($M_{{cap}}$) using {cal['factor_b_sym']} = {cal['val_b']}:")
    if method == "ASD":
        st.latex(rf"M_{{cap}} = \frac{{{cal['Mn']:,.0f}}}{{{cal['val_b']}}} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")
    else:
        st.latex(rf"M_{{cap}} = {cal['val_b']} \times {cal['Mn']:,.0f} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")

    st.write("Safe Uniform Load ($w_m = 8M/L^2$):")
    st.latex(rf"w_m = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")
    
    # 2.3 Deflection
    st.subheader("2.3 ระยะแอ่นตัว (Deflection Limit)")
    st.write("Allowable Deflection ($\delta_{allow} = L/360$):")
    st.latex(rf"\delta = {cal['L_cm']:.0f} / 360 = {cal['delta_allow']:.2f} \text{{ cm}}")
    
    st.write("Safe Uniform Load ($w_d$ derived from $\delta = 5wL^4/384EI$):")
    num_d = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den_d = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w_d = \frac{{{num_d}}}{{{den_d}}} \times 100 = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # 3. Transition Analysis
    st.markdown("#### 3. วิเคราะห์จุดเปลี่ยนพฤติกรรม (Control Zones)")
    st.info("คำนวณหาความยาว ($L$) ที่ทำให้โหมดการวิบัติเปลี่ยนรูปแบบ")
    
    st.write("**3.1 จุดเปลี่ยน Shear $\\to$ Moment ($L_{v-m}$):**")
    st.latex(rf"L_{{v-m}} = \frac{{4 M_{{cap}}}}{{V_{{cap}}}} = \frac{{4 \times {cal['M_cap']:,.0f}}}{{{cal['V_cap']:,.0f}}} = {cal['L_vm_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_vm_m']:.2f}}} \text{{ m}}")
    
    st.write("**3.2 จุดเปลี่ยน Moment $\\to$ Deflection ($L_{m-d}$):**")
    st.latex(rf"L_{{m-d}} = \frac{{384 E I}}{{14400 M_{{cap}}}} = \frac{{384 \times {cal['E_ksc']:,.0f} \times {props['Ix']:,}}}{{14400 \times {cal['M_cap']:,.0f}}} = {cal['L_md_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_md_m']:.2f}}} \text{{ m}}")
    
    st.markdown("---")
    
    # 4. Final Conclusion
    st.markdown("#### 4. สรุปผล (Conclusion)")
    
    w_gross = min(cal['ws'], cal['wm'], cal['wd'])
    w_net = max(w_gross - props['W'], 0)
    
    # Logic Check
    if L_input <= cal['L_vm_m']:
        status, color = "SHEAR CONTROL", "red"
    elif L_input <= cal['L_md_m']:
        status, color = "MOMENT CONTROL", "orange"
    else:
        status, color = "DEFLECTION CONTROL", "green"

    st.markdown(f"**Governing Case:** :{color}[**{status}**]")
    
    col_final1, col_final2 = st.columns(2)
    col_final1.metric("Gross Safe Load", f"{w_gross:,.0f} kg/m")
    col_final2.metric("Net Safe Load (Subtract Self-weight)", f"{w_net:,.0f} kg/m")
    
    st.success(f"✅ คานรับน้ำหนักบรรทุกปลอดภัยสุทธิ (Net Safe Load) = **{w_net:,.0f} kg/m**")
