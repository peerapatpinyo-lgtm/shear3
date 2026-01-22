import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. SETUP ---
st.set_page_config(page_title="SYS H-Beam: Master Analysis", layout="wide")

# --- 2. DATABASE ---
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 1910},
}

# --- 3. MATH ENGINE ---
def master_calculation(L_m, Fy_ksc, E_gpa, props, method):
    # Units & Constants
    E_ksc = E_gpa * 10197.162
    L_cm = L_m * 100.0
    Aw = (props['D']/10.0) * (props['tw']/10.0)
    
    # 1. Nominal Strengths
    Vn = 0.60 * Fy_ksc * Aw
    Mn = Fy_ksc * props['Zx']
    
    # 2. Design Strengths (Factor Application)
    if method == "ASD":
        factor_v_sym, factor_b_sym = r"\Omega_v", r"\Omega_b"
        val_v, val_b = 1.50, 1.67
        V_cap = Vn / val_v
        M_cap = Mn / val_b
        op_v, op_b = "หาร", "หาร" # For explanation text
    else: # LRFD
        factor_v_sym, factor_b_sym = r"\phi_v", r"\phi_b"
        val_v, val_b = 1.00, 0.90
        V_cap = Vn * val_v
        M_cap = Mn * val_b
        op_v, op_b = "คูณ", "คูณ"

    # 3. Load Capacities (w) at Current Span
    ws = (2 * V_cap / L_cm) * 100
    wm = (8 * M_cap / L_cm**2) * 100
    
    delta_allow = L_cm / 360.0
    # Deflection w: Derived from delta = 5wL^4/384EI
    wd = ((384 * E_ksc * props['Ix'] * delta_allow) / (5 * L_cm**4)) * 100
    
    # 4. Critical Lengths (Transition Points Logic)
    # 4.1 Shear meets Moment: 2V/L = 8M/L^2 -> L = 4M/V
    L_vm_cm = (4 * M_cap) / V_cap
    
    # 4.2 Moment meets Deflection: 8M/L^2 = 384EI(L/360)/5L^4 -> L = 384EI/(14400*M)
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
        "factor_b_sym": factor_b_sym, "val_b": val_b,
        "op_v": op_v, "op_b": op_b
    }

# --- 4. UI ---
st.title("🏗️ SYS H-Beam: Engineering Report (Full Logic)")
st.sidebar.header("Design Parameters")
method = st.sidebar.radio("Method", ["ASD", "LRFD"])
section = st.sidebar.selectbox("Section", list(SYS_H_BEAMS.keys()))
Fy = st.sidebar.number_input("Fy (ksc)", 2400)
E_gpa = st.sidebar.number_input("E (GPa)", 200)
L_input = st.sidebar.slider("Span Length (m)", 1.0, 20.0, 6.0, 0.5)

props = SYS_H_BEAMS[section]
cal = master_calculation(L_input, Fy, E_gpa, props, method)

# --- 5. TABS ---
tab_graph, tab_sheet = st.tabs(["📊 Capacity Envelope", "📝 Detailed Calculation Sheet"])

# === TAB 1: GRAPH ===
with tab_graph:
    # Logic for X-axis range
    L_max = max(15, cal['L_md_m'] * 1.2, L_input * 1.5)
    L_range = np.linspace(0.1, L_max, 400)
    
    ys, ym, yd = [], [], []
    k_def = (384 * cal['E_ksc'] * props['Ix']) / 1800 # Constant part for deflection
    
    for l in L_range:
        l_cm = l * 100
        ys.append(2 * cal['V_cap'] / l_cm * 100)
        ym.append(8 * cal['M_cap'] / l_cm**2 * 100)
        yd.append(k_def / l_cm**3 * 100)
        
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    cur_w = min(cal['ws'], cal['wm'], cal['wd'])
    
    fig = go.Figure()
    
    # Zones
    fig.add_vrect(x0=0, x1=cal['L_vm_m'], fillcolor="rgba(255,0,0,0.1)", line_width=0, annotation_text="SHEAR", annotation_position="top left")
    fig.add_vrect(x0=cal['L_vm_m'], x1=cal['L_md_m'], fillcolor="rgba(255,165,0,0.1)", line_width=0, annotation_text="MOMENT", annotation_position="top center")
    fig.add_vrect(x0=cal['L_md_m'], x1=L_max, fillcolor="rgba(0,128,0,0.1)", line_width=0, annotation_text="DEFLECTION", annotation_position="top right")
    
    # Curves
    fig.add_trace(go.Scatter(x=L_range, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=y_gov, name='Governing Capacity', line=dict(color='black', width=4)))
    fig.add_trace(go.Scatter(x=[L_input], y=[cur_w], mode='markers+text', marker=dict(size=15, color='blue', symbol='x'), 
                             text=[f"{cur_w:,.0f}"], textposition="top right", name='Current Design'))
    
    fig.update_layout(height=600, title=f"Capacity Envelope: {section}", xaxis_title="Span (m)", yaxis_title="Load (kg/m)", yaxis_range=[0, max(cur_w*2.5, 2000)])
    st.plotly_chart(fig, use_container_width=True)

# === TAB 2: DETAILED CALCULATION ===
with tab_sheet:
    st.markdown(f"### 📄 รายการคำนวณวิศวกรรม: {section} ({method})")
    
    # 1. Properties
    st.markdown("#### 1. ข้อมูลและคุณสมบัติ (Design Data)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"- $L = {L_input}$ m")
        st.write(f"- $F_y = {Fy}$ ksc")
        st.write(f"- วิธีออกแบบ: **{method}**")
    with c2:
        st.write(f"- $A_w = {cal['Aw']:.2f}$ cm²")
        st.write(f"- $Z_x = {props['Zx']}$ cm³")
        st.write(f"- $I_x = {props['Ix']:,}$ cm⁴")
    st.markdown("---")
    
    # 2. Capacity Calculation (Dynamic ASD/LRFD)
    st.markdown("#### 2. การคำนวณกำลังรับน้ำหนัก (Load Capacity)")
    
    # 2.1 Shear
    st.subheader("2.1 แรงเฉือน (Shear)")
    st.write(f"หา $V_n$ และปรับแก้ด้วย {cal['factor_v_sym']} ({cal['val_v']}):")
    st.latex(rf"V_n = 0.60 F_y A_w = 0.60 \times {Fy} \times {cal['Aw']:.2f} = {cal['Vn']:,.0f} \text{{ kg}}")
    if method == "ASD":
        st.latex(rf"V_{{design}} = \frac{{V_n}}{{\Omega_v}} = \frac{{{cal['Vn']:,.0f}}}{{{cal['val_v']}}} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
    else:
        st.latex(rf"V_{{design}} = \phi_v V_n = {cal['val_v']} \times {cal['Vn']:,.0f} = \mathbf{{{cal['V_cap']:,.0f}}} \text{{ kg}}")
    
    st.write("แปลงเป็นน้ำหนักแผ่ ($w_s = 2V/L$):")
    st.latex(rf"w_s = \frac{{2 \times {cal['V_cap']:,.0f}}}{{{cal['L_cm']:.0f}}} \times 100 = \mathbf{{{cal['ws']:,.0f}}} \text{{ kg/m}}")
    
    # 2.2 Moment
    st.subheader("2.2 โมเมนต์ (Moment)")
    st.write(f"หา $M_n$ และปรับแก้ด้วย {cal['factor_b_sym']} ({cal['val_b']}):")
    st.latex(rf"M_n = F_y Z_x = {Fy} \times {props['Zx']} = {cal['Mn']:,.0f} \text{{ kg-cm}}")
    if method == "ASD":
        st.latex(rf"M_{{design}} = \frac{{M_n}}{{\Omega_b}} = \frac{{{cal['Mn']:,.0f}}}{{{cal['val_b']}}} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")
    else:
        st.latex(rf"M_{{design}} = \phi_b M_n = {cal['val_b']} \times {cal['Mn']:,.0f} = \mathbf{{{cal['M_cap']:,.0f}}} \text{{ kg-cm}}")

    st.write("แปลงเป็นน้ำหนักแผ่ ($w_m = 8M/L^2$):")
    st.latex(rf"w_m = \frac{{8 \times {cal['M_cap']:,.0f}}}{{{cal['L_cm']:.0f}^2}} \times 100 = \mathbf{{{cal['wm']:,.0f}}} \text{{ kg/m}}")
    
    # 2.3 Deflection
    st.subheader("2.3 ระยะแอ่นตัว (Deflection)")
    st.write("ตรวจสอบที่พิกัด $\delta_{allow} = L/360$:")
    st.latex(rf"\delta = {cal['L_cm']:.0f} / 360 = {cal['delta_allow']:.2f} \text{{ cm}}")
    st.write("หาน้ำหนักแผ่จากสูตร $\delta = 5wL^4/384EI$:")
    num_d = f"384 \\times {cal['E_ksc']:,.0f} \\times {props['Ix']:,} \\times {cal['delta_allow']:.2f}"
    den_d = f"5 \\times {cal['L_cm']:.0f}^4"
    st.latex(rf"w_d = \frac{{{num_d}}}{{{den_d}}} \times 100 = \mathbf{{{cal['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")
    
    # 3. TRANSITION ANALYSIS (The Requested Logic)
    st.markdown("#### 3. วิเคราะห์จุดเปลี่ยนพฤติกรรม (Control Zone Analysis)")
    st.info("ส่วนนี้แสดงการคำนวณจุดตัดของกราฟ เพื่อยืนยันว่าช่วงความยาวใดถูกควบคุมโดยแรงชนิดไหน")
    
    st.write("**3.1 จุดตัด Shear $\\leftrightarrow$ Moment ($L_{v-m}$):**")
    st.write("หา $L$ ที่ทำให้ $w_s = w_m$:")
    st.latex(rf"L_{{v-m}} = \frac{{4 M_{{design}}}}{{V_{{design}}}} = \frac{{4 \times {cal['M_cap']:,.0f}}}{{{cal['V_cap']:,.0f}}} = {cal['L_vm_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_vm_m']:.2f}}} \text{{ m}}")
    
    st.write("**3.2 จุดตัด Moment $\\leftrightarrow$ Deflection ($L_{m-d}$):**")
    st.write("หา $L$ ที่ทำให้ $w_m = w_d$:")
    num_md = f"384 E I"
    den_md = f"14400 M_{{design}}"
    st.latex(rf"L_{{m-d}} = \frac{{{num_md}}}{{{den_md}}} = \frac{{384 \times {cal['E_ksc']:,.0f} \times {props['Ix']:,}}}{{14400 \times {cal['M_cap']:,.0f}}} = {cal['L_md_m']*100:.1f} \text{{ cm}} = \mathbf{{{cal['L_md_m']:.2f}}} \text{{ m}}")
    
    st.markdown("---")
    
    # 4. FINAL CONCLUSION
    st.markdown("#### 4. สรุปผลการคำนวณ (Conclusion)")
    
    # Determine Control Case
    if L_input <= cal['L_vm_m']:
        status = "Shear Control"
        color = "red"
        reason = f"เนื่องจาก $L ({L_input}) < L_{{v-m}} ({cal['L_vm_m']:.2f})$"
    elif L_input <= cal['L_md_m']:
        status = "Moment Control"
        color = "orange"
        reason = f"เนื่องจาก $L_{{v-m}} < L ({L_input}) < L_{{m-d}} ({cal['L_md_m']:.2f})$"
    else:
        status = "Deflection Control"
        color = "green"
        reason = f"เนื่องจาก $L ({L_input}) > L_{{m-d}} ({cal['L_md_m']:.2f})$"
        
    st.markdown(f"**สถานะ:** :{color}[**{status}**] ({reason})")
    
    w_gross = min(cal['ws'], cal['wm'], cal['wd'])
    w_net = max(w_gross - props['W'], 0)
    
    col_final1, col_final2 = st.columns(2)
    col_final1.metric("Gross Safe Load", f"{w_gross:,.0f} kg/m")
    col_final2.metric("Net Safe Load (หักน้ำหนักคาน)", f"{w_net:,.0f} kg/m", delta_color="normal")
    
    st.success(f"✅ คานนี้รับน้ำหนักบรรทุกปลอดภัยสุทธิได้ **{w_net:,.0f} kg/m**")
