import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam: Precision Analysis", layout="wide")

# --- 2. DATABASE (AISC Standard Properties) ---
# Units: W(kg/m), D(mm), tw(mm), Ix(cm4), Zx(cm3 - Plastic Modulus)
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
    # 1 GPa approx 10197.16 ksc
    E_ksc = E_gpa * 10197.162  
    L_cm = L_m * 100.0         
    
    # Area of Web (Aw = d * tw) for Shear
    Aw = (props['D']/10.0) * (props['tw']/10.0) # cm2
    
    # 3.2 Nominal Strengths (Nominal Capacity)
    # Shear: Vn = 0.6 * Fy * Aw (Yielding)
    Vn = 0.60 * Fy_ksc * Aw 
    # Moment: Mn = Fy * Zx (Plastic Moment for Compact Section)
    Mn = Fy_ksc * props['Zx']
    
    # 3.3 Apply Factors (ASD vs LRFD)
    if method == "ASD":
        # AISC 360 ASD: Divide by Omega
        omega_v = 1.50  # Safety Factor for Shear
        omega_b = 1.67  # Safety Factor for Bending
        
        V_design = Vn / omega_v
        M_design = Mn / omega_b
        
        # Latex strings for display
        txt_v_eq = r"V_{allow} = \frac{V_n}{\Omega_v}"
        txt_v_sub = rf"\frac{{{Vn:,.0f}}}{{1.50}}"
        
        txt_m_eq = r"M_{allow} = \frac{M_n}{\Omega_b}"
        txt_m_sub = rf"\frac{{{Mn:,.0f}}}{{1.67}}"
        
    else:
        # AISC 360 LRFD: Multiply by Phi
        phi_v = 1.00    # Resistance Factor for Shear
        phi_b = 0.90    # Resistance Factor for Bending
        
        V_design = Vn * phi_v
        M_design = Mn * phi_b
        
        # Latex strings for display
        txt_v_eq = r"V_u = \phi_v V_n"
        txt_v_sub = rf"1.00 \times {Vn:,.0f}"
        
        txt_m_eq = r"M_u = \phi_b M_n"
        txt_m_sub = rf"0.90 \times {Mn:,.0f}"

    # 3.4 Convert to Uniform Load (w)
    # Shear Control: V = wL/2 -> w = 2V/L
    ws = (2 * V_design / L_cm) * 100  # *100 to convert kg/cm -> kg/m
    
    # Moment Control: M = wL^2/8 -> w = 8M/L^2
    wm = (8 * M_design / L_cm**2) * 100
    
    # Deflection Control: delta = 5wL^4/384EI -> w = 384EI(delta)/5L^4
    delta_allow = L_cm / 360.0
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 3.5 Critical Lengths (Transition Points)
    L_vm = (4 * M_design) / V_design # cm
    L_md = (384 * E_ksc * props['Ix']) / (14400 * M_design) # cm
    
    return {
        "Aw": Aw, "Ix": props['Ix'], "Zx": props['Zx'], 
        "Vn": Vn, "Mn": Mn, 
        "V_design": V_design, "M_design": M_design,
        "ws": ws, "wm": wm, "wd": wd,
        "L_cm": L_cm, "E_ksc": E_ksc, "delta_allow": delta_allow,
        "L_vm_m": L_vm / 100.0, "L_md_m": L_md / 100.0,
        "txt_v_eq": txt_v_eq, "txt_v_sub": txt_v_sub,
        "txt_m_eq": txt_m_eq, "txt_m_sub": txt_m_sub
    }

# --- 4. UI ---
st.title("🏗️ SYS Structural Analysis: ASD vs LRFD")

with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.header("2. Section & Span")
    section = st.selectbox("Section Name", list(SYS_H_BEAMS.keys()))
    L_input = st.slider("Span Length (L) [m]", 2.0, 15.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = precision_calc(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab_sheet, tab_graph = st.tabs(["📝 Calculation Sheet (รายการคำนวณ)", "📊 Behavior Graph (กราฟพฤติกรรม)"])

with tab_sheet:
    st.markdown(f"### รายการคำนวณ: {section} (Method: {method})")
    st.markdown("---")
    
    # === PART 1: SHEAR ===
    st.subheader("1. Shear Capacity (แรงเฉือน)")
    col1, col2 = st.columns([1.5, 2])
    
    with col1:
        st.info("Step 1: Nominal Shear Strength ($V_n$)")
        st.latex(r"V_n = 0.60 F_y A_w")
        st.latex(rf"V_n = 0.60 \times {Fy} \times {cal['Aw']:.2f} = \mathbf{{{cal['Vn']:,.0f}}} \text{{ kg}}")
        
    with col2:
        st.success(f"Step 2: Design Shear Strength ({method})")
        st.latex(cal['txt_v_eq'])
        st.latex(rf"= {cal['txt_v_sub']} = \mathbf{{{cal['V_design']:,.0f}}} \text{{ kg}}")

    st.markdown("**Step 3: Convert to Uniform Load ($w_s$)**")
    st.latex(r"w_s = \frac{2 V_{design}}{L} \times 100 \quad \text{(Unit Conversion)}")
    st.latex(rf"w_s = \frac{{2 \times {cal['V_design']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # === PART 2: MOMENT ===
    st.subheader("2. Moment Capacity (โมเมนต์ดัด)")
    col3, col4 = st.columns([1.5, 2])
    
    with col3:
        st.info("Step 1: Nominal Moment Strength ($M_n$)")
        st.latex(r"M_n = F_y Z_x")
        st.latex(rf"M_n = {Fy} \times {cal['Zx']} = \mathbf{{{cal['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col4:
        st.success(f"Step 2: Design Moment Strength ({method})")
        st.latex(cal['txt_m_eq'])
        st.latex(rf"= {cal['txt_m_sub']} = \mathbf{{{cal['M_design']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3: Convert to Uniform Load ($w_m$)**")
    st.latex(r"w_m = \frac{8 M_{design}}{L^2} \times 100")
    st.latex(rf"w_m = \frac{{8 \times {cal['M_design']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # === PART 3: DEFLECTION ===
    st.subheader("3. Deflection Limit (ระยะแอ่นตัว)")
    st.write("Target: $\delta_{max} \leq L/360$")
    st.latex(rf"\delta_{{allow}} = \frac{{{cal['L_cm']:.0f}}}{{360}} = {cal['delta_allow']:.2f} \text{{ cm}}")
    
    st.write("Reverse calculate load ($w_d$):")
    st.latex(r"w_d = \frac{384 E I \delta_{allow}}{5 L^4} \times 100")
    
    # Format large numbers for cleaner display
    E_sci = f"{cal['E_ksc']:.2e}".replace("+", "")
    st.latex(rf"w_d = \frac{{384 \times ({cal['E_ksc']:,.0f}) \times {cal['Ix']:,} \times {cal['delta_allow']:.2f}}}{{5 \times {cal['L_cm']:.0f}^4}} \times 100 = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # === SUMMARY ===
    final_w = min(cal['ws'], cal['wm'], cal['wd'])
    net_w = final_w - props['W']
    
    st.markdown("### 4. Conclusion (สรุปผล)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Shear Limit", f"{cal['ws']:,.0f} kg/m")
    c2.metric("Moment Limit", f"{cal['wm']:,.0f} kg/m")
    c3.metric("Deflection Limit", f"{cal['wd']:,.0f} kg/m")
    
    st.success(f"✅ **Safe Net Load (น้ำหนักบรรทุกปลอดภัยสุทธิ): {net_w:,.0f} kg/m**")

with tab_graph:
    # Prepare Data
    L_max = max(12, cal['L_md_m'] * 1.2, L_input * 1.5)
    L_range = np.linspace(0.5, L_max, 200)
    
    ys = []
    ym = []
    yd = []
    
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 # Constant for deflection
    
    for l in L_range:
        l_cm = l * 100
        ys.append(2 * cal['V_design'] / l_cm * 100)
        ym.append(8 * cal['M_design'] / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100)
        
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    
    fig = go.Figure()
    
    # Plot Lines
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit (ws)', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit (wm)', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit (wd)', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Design Capacity', line=dict(color='black', width=4)))
    
    # Plot User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text',
                             marker=dict(size=15, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right",
                             name='Your Design'))

    # Add Regions (Using add_shape/add_annotation for safety)
    # Zone 1: Shear
    fig.add_shape(type="rect", x0=0, x1=cal['L_vm_m'], y0=0, y1=max(y_gov)*1.5, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_annotation(x=cal['L_vm_m']/2, y=max(y_gov), text="SHEAR", showarrow=False, font=dict(color="red"))
    
    # Zone 2: Moment
    fig.add_shape(type="rect", x0=cal['L_vm_m'], x1=cal['L_md_m'], y0=0, y1=max(y_gov)*1.5, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_annotation(x=(cal['L_vm_m']+cal['L_md_m'])/2, y=max(y_gov), text="MOMENT", showarrow=False, font=dict(color="orange"))
    
    # Zone 3: Deflection
    fig.add_shape(type="rect", x0=cal['L_md_m'], x1=L_max, y0=0, y1=max(y_gov)*1.5, fillcolor="green", opacity=0.1, line_width=0)
    fig.add_annotation(x=(cal['L_md_m']+L_max)/2, y=max(y_gov), text="DEFLECTION", showarrow=False, font=dict(color="green"))

    fig.update_layout(
        title=f"Capacity Curve: {section} ({method})",
        xaxis_title="Span Length (m)",
        yaxis_title="Safe Uniform Load (kg/m)",
        yaxis_range=[0, final_w * 2.5],
        height=600,
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
