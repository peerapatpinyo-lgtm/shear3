import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Detailed Calculation Report")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.header("2. Section & Span")
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Process ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method)

# --- Display ---
t1, t2 = st.tabs(["📝 รายการคำนวณละเอียด (Detailed Sheet)", "📊 กราฟพฤติกรรม (Graph)"])

with t1:
    st.markdown(f"### 📄 Engineering Report: {section} ({method})")
    st.markdown("---")

    # === 1. PROPERTIES ===
    st.markdown("#### 1. Geometric Properties (คุณสมบัติหน้าตัด)")
    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Depth (D):** {props['D']} mm")
    c2.write(f"**Web (tw):** {props['tw']} mm")
    c3.write(f"**Area Web ($A_w$):** {c['Aw']:.2f} cm²")
    c4.write(f"**Plastic Modulus ($Z_x$):** {props['Zx']:,} cm³")
    st.markdown("---")

    # === 2. SHEAR ===
    st.subheader("2. Shear Capacity (กำลังรับแรงเฉือน)")
    col_s1, col_s2 = st.columns([1, 1])
    
    with col_s1:
        st.markdown("**Step 2.1: Nominal Shear Strength ($V_n$)**")
        st.latex(r"V_n = 0.60 \times F_y \times A_w")
        st.latex(rf"V_n = 0.60 \times {Fy} \times {c['Aw']:.2f}")
        st.latex(rf"\therefore V_n = \mathbf{{{c['Vn']:,.0f}}} \text{{ kg}}")
        
    with col_s2:
        st.markdown("**Step 2.2: Design Shear Strength ($V_{design}$)**")
        st.latex(c['txt_v_method'])
        if method == "ASD":
             st.latex(rf"V_{{design}} = \frac{{{c['Vn']:,.0f}}}{{{c['omega_v']:.2f}}}")
        else:
             st.latex(rf"V_{{design}} = {c['phi_v']:.2f} \times {c['Vn']:,.0f}")
        st.latex(rf"\therefore V_{{design}} = \mathbf{{{c['V_des']:,.0f}}} \text{{ kg}}")
    
    st.markdown("**Step 2.3: Equivalent Uniform Load ($w_s$)**")
    st.write("แปลงเป็นน้ำหนักแผ่ปลอดภัย (Uniform Load) จากสูตร $V = wL/2$")
    st.latex(rf"w_s = \frac{{2 V_{{design}}}}{{L}} \times 100 (\text{{unit conv.}})")
    st.latex(rf"w_s = \frac{{2 \times {c['V_des']:,.0f}}}{{{c['L_cm']:.0f}}} \times 100 = \mathbf{{{c['ws']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 3. MOMENT ===
    st.subheader("3. Moment Capacity (กำลังรับโมเมนต์ดัด)")
    col_m1, col_m2 = st.columns([1, 1])
    
    with col_m1:
        st.markdown("**Step 3.1: Nominal Moment Strength ($M_n$)**")
        st.latex(r"M_n = F_y \times Z_x")
        st.latex(rf"M_n = {Fy} \times {props['Zx']}")
        st.latex(rf"\therefore M_n = \mathbf{{{c['Mn']:,.0f}}} \text{{ kg-cm}}")
        
    with col_m2:
        st.markdown("**Step 3.2: Design Moment Strength ($M_{design}$)**")
        st.latex(c['txt_m_method'])
        if method == "ASD":
             st.latex(rf"M_{{design}} = \frac{{{c['Mn']:,.0f}}}{{{c['omega_b']:.2f}}}")
        else:
             st.latex(rf"M_{{design}} = {c['phi_b']:.2f} \times {c['Mn']:,.0f}")
        st.latex(rf"\therefore M_{{design}} = \mathbf{{{c['M_des']:,.0f}}} \text{{ kg-cm}}")

    st.markdown("**Step 3.3: Equivalent Uniform Load ($w_m$)**")
    st.write("แปลงเป็นน้ำหนักแผ่ปลอดภัย จากสูตร $M = wL^2/8$")
    st.latex(rf"w_m = \frac{{8 M_{{design}}}}{{L^2}} \times 100")
    st.latex(rf"w_m = \frac{{8 \times {c['M_des']:,.0f}}}{{{c['L_cm']:.0f}^2}} \times 100 = \mathbf{{{c['wm']:,.0f}}} \text{{ kg/m}}")
    st.markdown("---")

    # === 4. DEFLECTION ===
    st.subheader("4. Deflection Limit (ระยะแอ่นตัว)")
    st.write(f"ระยะแอ่นตัวที่ยอมให้ ($L/360$):")
    st.latex(rf"\delta_{{allow}} = \frac{{{c['L_cm']:.0f}}}{{360}} = {c['delta']:.2f} \text{{ cm}}")
    
    st.markdown("**Step 4.1: Convert to Uniform Load ($w_d$)**")
    st.write("คำนวณน้ำหนักแผ่ที่ทำให้เกิดระยะแอ่นเท่ากับค่าที่ยอมให้ จากสูตร $\delta = \\frac{5wL^4}{384EI}$")
    st.latex(r"w_d = \frac{384 E I \delta_{allow}}{5 L^4} \times 100")
    st.latex(rf"w_d = \frac{{384 \times {c['E_ksc']:,.0f} \times {props['Ix']:,} \times {c['delta']:.2f}}}{{5 \times {c['L_cm']:.0f}^4}} \times 100")
    st.latex(rf"\therefore w_d = \mathbf{{{c['wd']:,.0f}}} \text{{ kg/m}}")
    
    st.markdown("---")

    # === 5. CONCLUSION ===
    st.subheader("5. Summary (สรุปผลการคำนวณ)")
    
    final_w = min(c['ws'], c['wm'], c['wd'])
    net_w = max(0, final_w - props['W'])
    
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        if c['ws'] == final_w: ctrl = "Shear Control"
        elif c['wm'] == final_w: ctrl = "Moment Control"
        else: ctrl = "Deflection Control"
        
        st.info(f"**Governing Case:** {ctrl}")
        st.write(f"- Shear Capacity: {c['ws']:,.0f} kg/m")
        st.write(f"- Moment Capacity: {c['wm']:,.0f} kg/m")
        st.write(f"- Deflection Limit: {c['wd']:,.0f} kg/m")
    
    with res_col2:
        st.success(f"✅ **Safe Net Load (รับน้ำหนักปลอดภัยสุทธิ):**")
        st.metric(label="Net Load (Exclude beam weight)", value=f"{net_w:,.0f} kg/m")
        st.caption(f"*หักน้ำหนักคาน {props['W']} kg/m ออกแล้ว")

with t2:
    # (โค้ดกราฟใช้ Logic เดิมได้ แต่ขอใส่ให้ครบเพื่อความสมบูรณ์)
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    ys = (2 * c['V_des'] / (x*100)) * 100
    ym = (8 * c['M_des'] / (x*100)**2) * 100
    k_def = (384 * c['E_ksc'] * props['Ix']) / 1800
    yd = (k_def / (x*100)**3) * 100
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    
    fig = go.Figure()
    y_lim = max(y_gov) * 1.4
    
    # Zones
    fig.add_shape(type="rect", x0=0, x1=c['L_vm'], y0=0, y1=y_lim, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=c['L_vm'], x1=c['L_md'], y0=0, y1=y_lim, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_shape(type="rect", x0=c['L_md'], x1=L_max, y0=0, y1=y_lim, fillcolor="green", opacity=0.1, line_width=0)
    
    # Text
    fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="red"))
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="orange"))
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="green"))
    
    # Lines
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=x, y=y_gov, name='Capacity', line=dict(color='black', width=4)))
    
    # Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Your Design'))
    
    fig.update_layout(title=f"Capacity Envelope: {section}", height=600, 
                      xaxis_title="Span Length (m)", yaxis_title="Load (kg/m)",
                      yaxis_range=[0, final_w*2.5])
    
    st.plotly_chart(fig, use_container_width=True)
