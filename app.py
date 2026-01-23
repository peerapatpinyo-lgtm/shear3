import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation
from tab1_details import render_tab1
from tab3_capacity import render_tab3
from tab4_summary import render_tab4 

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Professional Design Tool")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.header("2. Single Section Analysis")
    # เรียงลำดับหน้าตัดตามขนาด
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size to Analyze", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Process (Single Section) ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method)
final_w = min(c['ws'], c['wm'], c['wd'])

# --- Display Tabs ---
t1, t2, t3, t4 = st.tabs([
    "📝 รายการคำนวณ (Detail)", 
    "📊 กราฟพฤติกรรม (Graph)", 
    "📋 ตารางรับน้ำหนัก (Table)",
    "📚 เปรียบเทียบทุกหน้าตัด (Master Catalog)"
])

# === TAB 1: Detail Report ===
with t1:
    render_tab1(c, props, method, Fy, section)

# === TAB 2: Interactive Graph (UPDATED UI/UX) ===
with t2:
    st.subheader(f"📈 Capacity Envelope Analysis: {section}")
    st.caption("กราฟแสดงขีดความสามารถในการรับน้ำหนักเทียบกับความยาวช่วงคาน (พื้นที่สีเทาคือโซนที่ปลอดภัย)")

    # 1. เตรียมข้อมูลสำหรับ Plot
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    # คำนวณเส้น Limit ต่างๆ
    ys = (2 * c['V_des'] / (x*100)) * 100
    ym = (8 * c['M_des'] / (x*100)**2) * 100
    k_def = (384 * c['E_ksc'] * props['Ix']) / 1800
    yd = (k_def / (x*100)**3) * 100
    
    # เส้น Capacity จริง (ค่าต่ำสุดของทั้ง 3 เส้น)
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    
    fig = go.Figure()

    # 2. เพิ่มพื้นที่เงา (Safe Zone Fill) - พื้นที่ใต้กราฟที่ปลอดภัย
    fig.add_trace(go.Scatter(
        x=x, y=y_gov,
        fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', # สีเทาจางๆ
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=False,
        name='Safe Zone'
    ))

    # 3. เส้น Limit แต่ละประเภท (เส้นประ)
    line_styles = dict(width=2, dash='dash')
    
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='#d9534f', **line_styles),
                             hovertemplate="Shear Limit: %{y:,.0f} kg/m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='#f0ad4e', **line_styles),
                             hovertemplate="Moment Limit: %{y:,.0f} kg/m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=yd, name='Deflection Limit', line=dict(color='#5cb85c', **line_styles),
                             hovertemplate="Deflection Limit: %{y:,.0f} kg/m<extra></extra>"))

    # 4. เส้นขอบความสามารถสูงสุด (Governing Capacity - เส้นทึบดำ)
    fig.add_trace(go.Scatter(
        x=x, y=y_gov, 
        name='Governing Capacity', 
        line=dict(color='black', width=4),
        hovertemplate="<b>Governing Capacity</b><br>Span: %{x:.2f} m<br>Load: %{y:,.0f} kg/m<extra></extra>"
    ))

    # 5. จุดที่ User เลือก (Your Design)
    fig.add_trace(go.Scatter(
        x=[L_input], y=[final_w],
        mode='markers+text',
        marker=dict(size=14, color='#0275d8', symbol='diamond', line=dict(width=2, color='white')),
        text=[f"Current: {final_w:,.0f}"],
        textposition="top right",
        name='Your Design'
    ))

    # 6. ตกแต่ง Layout และ Background Zones
    y_lim = max(y_gov) * 1.5
    
    # เพิ่มแถบสี Background แยกโซนพฤติกรรม (Shear/Moment/Deflection Zones)
    # Zone 1: Shear
    fig.add_vrect(x0=0, x1=c['L_vm'], 
                  fillcolor="#d9534f", opacity=0.05, layer="below", line_width=0,
                  annotation_text="SHEAR", annotation_position="top left", annotation_font_color="#d9534f")
    
    # Zone 2: Moment
    fig.add_vrect(x0=c['L_vm'], x1=c['L_md'], 
                  fillcolor="#f0ad4e", opacity=0.05, layer="below", line_width=0,
                  annotation_text="MOMENT", annotation_position="top center", annotation_font_color="#f0ad4e")
    
    # Zone 3: Deflection
    fig.add_vrect(x0=c['L_md'], x1=L_max, 
                  fillcolor="#5cb85c", opacity=0.05, layer="below", line_width=0,
                  annotation_text="DEFLECTION", annotation_position="top right", annotation_font_color="#5cb85c")

    fig.update_layout(
        title=dict(text=f"Structural Capacity Envelope: {section}", font=dict(size=20)),
        height=600,
        hovermode="x unified",
        xaxis_title="Span Length (m)",
        yaxis_title="Load Capacity (kg/m)",
        yaxis_range=[0, y_lim],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# === TAB 3: Table ===
with t3:
    render_tab3(props, method, Fy, E_gpa, section)

# === TAB 4: Master Catalog ===
with t4:
    render_tab4(method, Fy, E_gpa)
