import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Complete Analysis", layout="wide")

# --- 2. DATABASE ---
# Units: W(kg/m), D(mm), tw(mm), Ix(cm4), Zx(cm3)
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
}

# --- 3. MATH ENGINE ---
def precision_calc(L_m, Fy_ksc, E_gpa, props, method):
    # 3.1 Unit Conversion
    E_ksc = E_gpa * 10197.162  
    L_cm = L_m * 100.0         
    Aw = (props['D']/10.0) * (props['tw']/10.0) # cm2
    
    # 3.2 Nominal Strengths
    Vn = 0.60 * Fy_ksc * Aw 
    Mn = Fy_ksc * props['Zx']
    
    # 3.3 Apply Factors
    if method == "ASD":
        # AISC 360 ASD
        val_v, val_b = 1.50, 1.67
        V_design = Vn / val_v
        M_design = Mn / val_b
        txt_v_eq, txt_m_eq = r"V_n / \Omega_v", r"M_n / \Omega_b"
    else:
        # AISC 360 LRFD
        val_v, val_b = 1.00, 0.90
        V_design = Vn * val_v
        M_design = Mn * val_b
        txt_v_eq, txt_m_eq = r"\phi_v V_n", r"\phi_b M_n"

    # 3.4 Convert to Uniform Load (w)
    ws = (2 * V_design / L_cm) * 100
    wm = (8 * M_design / L_cm**2) * 100
    
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 3.5 Critical Lengths (Transition Points)
    # L_vm: 2V/L = 8M/L^2 -> L = 4M/V
    L_vm_cm = (4 * M_design) / V_design
    
    # L_md: 8M/L^2 = 384EI/(14400*M) approx derived logic
    # Exact derivation: 8M/L^2 = (384EI * (L/360)) / 5L^4
    # 8M = 384EI / (1800 L)
    # L = 384EI / (14400 M)
    L_md_cm = (384 * E_ksc * props['Ix']) / (14400 * M_design)
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], 
        "Vn": Vn, "Mn": Mn, 
        "V_design": V_design, "M_design": M_design,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta_allow": delta_allow,
        "L_vm_m": L_vm_cm / 100.0, "L_md_m": L_md_cm / 100.0,
        "txt_v_eq": txt_v_eq, "txt_m_eq": txt_m_eq
    }

# --- 4. UI ---
st.title("🏗️ SYS Structural Analysis: Full Detail Report")

with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.header("2. Section & Span")
    section = st.selectbox("Section Name", list(SYS_H_BEAMS.keys()))
    L_input = st.slider("Span Length (L) [m]", 2.0, 20.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = precision_calc(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab_sheet, tab_graph = st.tabs(["📝 Calculation Sheet (รายการคำนวณ)", "📊 Behavior Graph (กราฟพฤติกรรม)"])

with tab_sheet:
    st.markdown(f"### รายการคำนวณวิศวกรรม: {section} ({method})")
    
    # === PART 1: PROPERTIES ===
    st.markdown("#### 1. Properties (คุณสมบัติ)")
    c1, c2, c3 = st.columns(3)
    c1.write(f"$A_w = {cal['Aw']:.2f}$ cm²")
    c2.write(f"$Z_x = {props['Zx']}$ cm³")
    c3.write(f"$I_x = {props['Ix']:,}$ cm⁴")
    st.markdown("---")
    
    # === PART 2: CAPACITY ===
    st.markdown("#### 2. Capacity Calculations (การคำนวณกำลัง)")
    
    # Shear
    st.write("**2.1 Shear Capacity ($V_{design}$)**")
    st.latex(rf"V_{{design}} = {cal['txt_v_eq']} = \mathbf{{{cal['V_design']:,.0f}}} \text{{ kg}}")
    
    # Moment
    st.write("**2.2 Moment Capacity ($M_{design}$)**")
    st.latex(rf"M_{{design}} = {cal['txt_m_eq']} = \mathbf{{{cal['M_design']:,.0f}}} \text{{ kg-cm}}")
    
    # Deflection Limit
    st.write("**2.3 Deflection Limit ($\delta_{allow}$)**")
    st.latex(rf"\delta_{{allow}} = L/360 = {cal['L_cm']:.0f}/360 = \mathbf{{{cal['delta_allow']:.2f}}} \text{{ cm}}")
    
    st.markdown("---")

    # === PART 3: UNIFORM LOAD ===
    st.markdown("#### 3. Equivalent Uniform Load (น้ำหนักบรรทุกแผ่)")
    st.latex(rf"w_s = \frac{{2 V_{{design}}}}{{L}} = \frac{{2 \times {cal['V_design']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")
    st.latex(rf"w_m = \frac{{8 M_{{design}}}}{{L^2}} = \frac{{8 \times {cal['M_design']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")
    st.latex(rf"w_d = \frac{{384 E I \delta}}{{5 L^4}} = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # === PART 4: TRANSITION LENGTHS (THE MISSING PART) ===
    st.markdown("#### 4. Critical Transition Lengths (จุดเปลี่ยนพฤติกรรม)")
    st.info("ส่วนนี้แสดงการคำนวณหาระยะความยาวคาน ($L$) ที่ทำให้โหมดการวิบัติเปลี่ยนรูปแบบ")

    # 4.1 Shear -> Moment
    st.markdown("**4.1 จุดเปลี่ยน Shear $\\to$ Moment ($L_{v-m}$)**")
    st.write("เกิดที่จุดซึ่ง $w_s = w_m$ (Shear Load = Moment Load):")
    st.latex(r"L_{v-m} = \frac{4 M_{design}}{V_{design}}")
    st.write("แทนค่า:")
    st.latex(rf"L_{{v-m}} = \frac{{4 \times {cal['M_design']:,.0f}}}{{{cal['V_design']:,.0f}}} = {cal['L_vm_m']*100:,.1f} \text{{ cm}}")
    st.success(f"📌 ดังนั้น $L_{{v-m}} = $ **{cal['L_vm_m']:.2f} m**")
    
    # 4.2 Moment -> Deflection
    st.markdown("**4.2 จุดเปลี่ยน Moment $\\to$ Deflection ($L_{m-d}$)**")
    st.write("เกิดที่จุดซึ่ง $w_m = w_d$:")
    st.latex(r"L_{m-d} = \frac{384 E I}{14400 M_{design}}")
    st.write("แทนค่า:")
    st.latex(rf"L_{{m-d}} = \frac{{384 \times {cal['E_ksc']:,.0f} \times {cal['Ix']:,}}}{{14400 \times {cal['M_design']:,.0f}}} = {cal['L_md_m']*100:,.1f} \text{{ cm}}")
    st.success(f"📌 ดังนั้น $L_{{m-d}} = $ **{cal['L_md_m']:.2f} m**")

    st.markdown("---")
    
    # === PART 5: CONCLUSION ===
    st.markdown("#### 5. Conclusion (สรุปผล)")
    
    if L_input <= cal['L_vm_m']:
        ctrl_case = "Shear Control"
        ctrl_reason = f"L ({L_input} m) < L_{{v-m}} ({cal['L_vm_m']:.2f} m)"
        ctrl_color = "red"
    elif L_input <= cal['L_md_m']:
        ctrl_case = "Moment Control"
        ctrl_reason = f"L_{{v-m}} < L ({L_input} m) < L_{{m-d}}"
        ctrl_color = "orange"
    else:
        ctrl_case = "Deflection Control"
        ctrl_reason = f"L ({L_input} m) > L_{{m-d}} ({cal['L_md_m']:.2f} m)"
        ctrl_color = "green"
        
    st.markdown(f"**Governing Case:** :{ctrl_color}[**{ctrl_case}**]")
    st.caption(f"*Reason: {ctrl_reason}*")
    
    final_w = min(cal['ws'], cal['wm'], cal['wd'])
    net_w = final_w - props['W']
    
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Gross Capacity", f"{final_w:,.0f} kg/m")
    col_res2.metric("Net Safe Load", f"{net_w:,.0f} kg/m")

with tab_graph:
    # Prepare Data
    L_max = max(12, cal['L_md_m'] * 1.2, L_input * 1.5)
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
    
    # Regions
    fig.add_shape(type="rect", x0=0, x1=cal['L_vm_m'], y0=0, y1=max(y_gov)*1.5, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=cal['L_vm_m'], x1=cal['L_md_m'], y0=0, y1=max(y_gov)*1.5, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=cal['L_md_m'], x1=L_max, y0=0, y1=max(y_gov)*1.5, fillcolor="green", opacity=0.1, line_width=0)
    
    # Text Labels for Regions (Fixed Position)
    fig.add_annotation(x=cal['L_vm_m']/2, y=max(y_gov)*1.1, text=f"SHEAR<br>(< {cal['L_vm_m']:.2f}m)", showarrow=False, font=dict(color="red", size=10))
    fig.add_annotation(x=(cal['L_vm_m']+cal['L_md_m'])/2, y=max(y_gov)*1.1, text=f"MOMENT", showarrow=False, font=dict(color="orange", size=10))
    fig.add_annotation(x=(cal['L_md_m']+L_max)/2, y=max(y_gov)*1.1, text=f"DEFLECTION<br>(> {cal['L_md_m']:.2f}m)", showarrow=False, font=dict(color="green", size=10))

    # Lines
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Design Capacity', line=dict(color='black', width=4)))
    
    # User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text',
                             marker=dict(size=15, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right",
                             name='Your Design'))

    fig.update_layout(
        title=f"Capacity Curve: {section}",
        xaxis_title="Span Length (m)",
        yaxis_title="Safe Uniform Load (kg/m)",
        yaxis_range=[0, final_w * 2.5],
        height=600,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
