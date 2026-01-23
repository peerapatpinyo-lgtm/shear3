import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Modules
# Ensure these filenames match your local directory (e.g., tab4_details.py or tab4_summary.py)
from tab1_details import render_tab1
from tab3_capacity import render_tab3
from tab4_summary import render_tab4  # Using tab4_summary as per previous instructions

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Professional Design Tool")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    # [NEW] Deflection Limit Selection
    st.write("---")
    st.write("**Deflection Limit:**")
    def_option = st.selectbox("Select Limit", 
                              ["L/360 (General/Floor)", "L/240 (Roof)", "L/180 (Industrial)"], 
                              index=0)
    # Extract numerical value (360, 240, 180)
    def_val = int(def_option.split('/')[1].split()[0])
    
    st.header("2. Single Section Analysis")
    # Sort sections by size (Height)
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size to Analyze", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Process (Single Section) ---
props = SYS_H_BEAMS[section]

# [CRITICAL] Pass def_val to calculation to get correct L_md based on the limit
c = core_calculation(L_input, Fy, E_gpa, props, method, def_val)
final_w = min(c['ws'], c['wm'], c['wd'])

# --- Display Tabs ---
t1, t2, t3, t4 = st.tabs([
    "📝 Detailed Report", 
    "📊 Behavior Graph", 
    "📋 Capacity Table",
    "📚 Master Catalog"
])

# === TAB 1: Detail Report ===
with t1:
    render_tab1(c, props, method, Fy, section)

# === TAB 2: Interactive Graph ===
with t2:
    st.subheader(f"📈 Capacity Envelope Analysis: {section}")
    st.caption(f"Load Capacity Envelope (Deflection Limit: **L/{def_val}**)")

    # 1. Prepare Plot Data
    # Set X-axis length to ensure all transition points are visible
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    # 2. Calculate Limit Lines (Formulas must match calculator.py)
    # Shear: w = 2*V_des / L
    ys = (2 * c['V_des'] / (x*100)) * 100 
    
    # Moment: w = 8*M_des / L^2
    ym = (8 * c['M_des'] / (x*100)**2) * 100 
    
    # Deflection: w = (384 EI) / (5 * Limit * L^3)
    # k_def is constant (384 EI / 5 Limit)
    k_def = (384 * c['E_ksc'] * props['Ix']) / (5 * def_val)
    yd = (k_def / (x*100)**3) * 100
    
    # Governing Capacity (Minimum of all 3 lines at any point)
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    y_lim = max(y_gov) * 1.5 # Set Y-axis max limit (1.5x buffer)
    
    fig = go.Figure()

    # 3. Add Safe Zone Fill
    fig.add_trace(go.Scatter(
        x=x, y=y_gov,
        fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', # Faint gray
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=False,
        name='Safe Zone'
    ))

    # 4. Draw Limit Lines (Dashed)
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

    # 5. Governing Capacity Line (Solid Black)
    fig.add_trace(go.Scatter(
        x=x, y=y_gov, 
        name='Governing Capacity', 
        line=dict(color='black', width=4),
        hovertemplate="<b>Governing Capacity</b><br>Span: %{x:.2f} m<br>Load: %{y:,.0f} kg/m<extra></extra>"
    ))

    # 6. User Selected Point (Your Design)
    fig.add_trace(go.Scatter(
        x=[L_input], y=[final_w],
        mode='markers+text',
        marker=dict(size=14, color='#0275d8', symbol='diamond', line=dict(width=2, color='white')),
        text=[f"Current: {final_w:,.0f}"],
        textposition="top right",
        name='Your Design'
    ))

    # 7. Background Zones (Dynamic based on def_val)
    # L_vm and L_md come from core_calculation using the current def_val
    
    # Zone 1: Shear
    fig.add_vrect(x0=0, x1=c['L_vm'], fillcolor="#d9534f", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, 
                       font=dict(color="#d9534f", weight="bold"))
    
    # Zone 2: Moment
    fig.add_vrect(x0=c['L_vm'], x1=c['L_md'], fillcolor="#f0ad4e", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, 
                       font=dict(color="#f0ad4e", weight="bold"))
    
    # Zone 3: Deflection
    fig.add_vrect(x0=c['L_md'], x1=L_max, fillcolor="#5cb85c", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, 
                       font=dict(color="#5cb85c", weight="bold"))

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
    # Pass def_val to ensure the table highlights the correct zone
    render_tab3(props, method, Fy, E_gpa, section, def_val)

# === TAB 4: Master Catalog ===
with t4:
    # Pass def_val to ensure Tab 4 updates based on the dropdown
    render_tab4(method, Fy, E_gpa, def_val)
