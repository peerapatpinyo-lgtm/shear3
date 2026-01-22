# main.py
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS  # เรียกใช้ข้อมูลจากไฟล์ database.py
from calculator import core_calculation # เรียกใช้สูตรจากไฟล์ calculator.py

# --- Configuration ---
st.set_page_config(page_title="SYS H-Beam: Ultimate Master", layout="wide")
st.title("🏗️ SYS H-Beam: Complete Engineering Design")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("1. Parameters")
    method = st.radio("Design Method", ["ASD", "LRFD"])
    Fy = st.number_input("Yield Strength (ksc)", value=2400, step=100)
    E_gpa = st.number_input("Elastic Modulus (GPa)", value=200)
    
    st.header("2. Section & Span")
    # เรียงลำดับหน้าตัดเพื่อให้หาง่าย
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Calculation Trigger ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method)

# --- Tabs ---
t1, t2 = st.tabs(["📝 รายการคำนวณ (Calculation)", "📊 กราฟพฤติกรรม (Graph)"])

# ==========================================
# TAB 1: CALCULATION SHEET
# ==========================================
with t1:
    st.markdown(f"### 📄 Detailed Report: {section}")
    st.markdown("---")
    
    # 1. Properties Display
    c1, c2, c3 = st.columns(3)
    c1.metric("Area Web ($A_w$)", f"{c['Aw']:.2f} cm²")
    c2.metric("Plastic Modulus ($Z_x$)", f"{props['Zx']:,} cm³")
    c3.metric("Inertia ($I_x$)", f"{props['Ix']:,} cm⁴")
    
    st.markdown("---")
    
    # 2. Strength Calculation
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
    
    # 3. Transition Points (The Missing Part)
    st.subheader("📍 จุดเปลี่ยนพฤติกรรม (Transition Lengths)")
    st.write("ระยะ Span ที่ทำให้จุดวิกฤตเปลี่ยนรูปแบบ (Critical Mode Switching):")
    
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
    
    # 4. Summary
    final_w = min(c['ws'], c['wm'], c['wd'])
    net_w = max(0, final_w - props['W'])
    st.success(f"✅ **Safe Net Load (น้ำหนักบรรทุกปลอดภัยสุทธิ) = {net_w:,.0f} kg/m**")

# ==========================================
# TAB 2: BEHAVIOR GRAPH
# ==========================================
with t2:
    # 1. Prepare Data for Plotting
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    # Calculate curves
    ys = (2 * c['V_des'] / (x*100)) * 100          # Shear curve
    ym = (8 * c['M_des'] / (x*100)**2) * 100       # Moment curve
    k_def = (384 * c['E_ksc'] * props['Ix']) / 1800
    yd = (k_def / (x*100)**3) * 100                # Deflection curve
    y_gov = np.minimum(np.minimum(ys, ym), yd)     # Governing curve
    
    fig = go.Figure()
    
    # 2. Draw Background Zones (Shear/Moment/Deflection Areas)
    y_lim = max(y_gov) * 1.4
    # Red Zone (Shear)
    fig.add_shape(type="rect", x0=0, x1=c['L_vm'], y0=0, y1=y_lim, fillcolor="red", opacity=0.1, line_width=0)
    # Orange Zone (Moment)
    fig.add_shape(type="rect", x0=c['L_vm'], x1=c['L_md'], y0=0, y1=y_lim, fillcolor="orange", opacity=0.1, line_width=0)
    # Green Zone (Deflection)
    fig.add_shape(type="rect", x0=c['L_md'], x1=L_max, y0=0, y1=y_lim, fillcolor="green", opacity=0.1, line_width=0)
    
    # 3. Add Zone Labels
    fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="red", weight="bold"))
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="orange", weight="bold"))
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="green", weight="bold"))
    
    # 4. Draw Limit Lines
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    
    # 5. Draw Governing Capacity Line (Thick Black Line)
    fig.add_trace(go.Scatter(x=x, y=y_gov, name='Capacity', line=dict(color='black', width=4)))
    
    # 6. Plot User's Current Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Your Design'))
    
    # 7. Layout Settings
    fig.update_layout(title=f"Capacity Envelope: {section}", height=600, 
                      xaxis_title="Span Length (m)", yaxis_title="Load (kg/m)",
                      yaxis_range=[0, final_w*2.5], hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)
