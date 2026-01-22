import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation
from tab1_details import render_tab1  # <--- Import ไฟล์ใหม่เข้ามา

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
final_w = min(c['ws'], c['wm'], c['wd']) # คำนวณค่านี้ไว้ใช้ใน Tab 2 ด้วย

# --- Display Tabs ---
t1, t2 = st.tabs(["📝 รายการคำนวณละเอียด (Detailed Sheet)", "📊 กราฟพฤติกรรม (Graph)"])

# ==========================================
# TAB 1: DETAILED CALCULATION (Refactored)
# ==========================================
with t1:
    # เรียกใช้ฟังก์ชันจากไฟล์ tab1_details.py
    # ส่งค่าที่จำเป็นเข้าไปให้ครบ
    render_tab1(c, props, method, Fy, section)

# ==========================================
# TAB 2: BEHAVIOR GRAPH (ยังอยู่ที่เดิม)
# ==========================================
with t2:
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
    fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="red", weight="bold"))
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="orange", weight="bold"))
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="green", weight="bold"))
    
    # Lines
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=yd, name='Deflection Limit', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=x, y=y_gov, name='Capacity', line=dict(color='black', width=4)))
    
    # User Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='x'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Your Design'))
    
    fig.update_layout(title=f"Capacity Envelope: {section}", height=600, 
                      xaxis_title="Span Length (m)", yaxis_title="Load (kg/m)",
                      yaxis_range=[0, final_w*2.5], hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)
