import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Modules
from tab1_details import render_tab1
from tab3_capacity import render_tab3
from tab4_summary import render_tab4
from tab5_saved import render_tab5    # Timeline Analysis
from tab6_design import render_tab6   # [NEW] Design Check

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Professional Design Tool")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.write("---")
    st.write("**Deflection Limit:**")
    def_option = st.selectbox("Select Limit", 
                              ["L/360 (General/Floor)", "L/240 (Roof)", "L/180 (Industrial)"], 
                              index=0)
    def_val = int(def_option.split('/')[1].split()[0])
    
    st.header("2. Single Section Analysis")
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size to Analyze", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Process ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method, def_val)
final_w = min(c['ws'], c['wm'], c['wd'])

# --- Display Tabs ---
# [UPDATE] เพิ่ม Tab 6
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📝 Detail Report", 
    "📊 Behavior Graph", 
    "📋 Capacity Table",
    "📚 Master Catalog",
    "📊 Timeline Analysis", # เปลี่ยนชื่อให้ตรงกับเนื้อหา (กราฟแท่ง Timeline)
    "🛠️ Design Check"        # [NEW] Tab 6
])

with t1:
    render_tab1(c, props, method, Fy, section)

with t2:
    # --- Graph Logic for Tab 2 ---
    st.subheader(f"📈 Capacity Envelope Analysis: {section}")
    st.caption(f"Load Capacity Envelope (Deflection Limit: **L/{def_val}**)")

    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    ys = (2 * c['V_des'] / (x*100)) * 100 
    ym = (8 * c['M_des'] / (x*100)**2) * 100 
    
    k_def = (384 * c['E_ksc'] * props['Ix']) / (5 * def_val)
    yd = (k_def / (x*100)**3) * 100
    
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    y_lim = max(y_gov) * 1.5 
    
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x, y=y_gov,
        fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', 
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=False,
        name='Safe Zone'
    ))

    line_styles = dict(width=2, dash='dash')
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', 
                             line=dict(color='#d9534f', **line_styles),
                             hovertemplate="Shear Limit: %{y:,.0f} kg/m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', 
                             line=dict(color='#f0ad4e', **line_styles),
                             hovertemplate="Moment Limit: %{y:,.0f} kg/m<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=yd, name=f'Deflection (L/{def_val})', 
                             line=dict(color='#5cb85c', **line_styles),
                             hovertemplate="Deflection Limit: %{y:,.0f} kg/m<extra></extra>"))

    fig.add_trace(go.Scatter(
        x=x, y=y_gov, 
        name='Governing Capacity', 
        line=dict(color='black', width=4),
        hovertemplate="<b>Governing Capacity</b><br>Span: %{x:.2f} m<br>Load: %{y:,.0f} kg/m<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=[L_input], y=[final_w],
        mode='markers+text',
        marker=dict(size=14, color='#0275d8', symbol='diamond', line=dict(width=2, color='white')),
        text=[f"Current: {final_w:,.0f}"],
        textposition="top right",
        name='Your Design'
    ))

    # Add Zone Annotations
    fig.add_vrect(x0=0, x1=c['L_vm'], fillcolor="#d9534f", opacity=0.05, layer="below", line_width=0)
    if c['L_vm'] > 0:
        fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="#d9534f", weight="bold"))
    
    fig.add_vrect(x0=c['L_vm'], x1=c['L_md'], fillcolor="#f0ad4e", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="#f0ad4e", weight="bold"))
    
    fig.add_vrect(x0=c['L_md'], x1=L_max, fillcolor="#5cb85c", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="#5cb85c", weight="bold"))

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

with t3:
    render_tab3(props, method, Fy, E_gpa, section, def_val)

with t4:
    render_tab4(method, Fy, E_gpa, def_val)

with t5:
    render_tab5(method, Fy, E_gpa, def_val)

# [NEW] Render Tab 6
with t6:
    render_tab6(method, Fy, E_gpa, def_val)
