import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Tabs
from tab1_details import render_tab1
from tab3_capacity import render_tab3
from tab4_summary import render_tab4
from tab5_saved import render_tab5
from tab6_design import render_tab6

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Professional Design Tool")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    
    # [Fixed] Prevent ZeroDivisionError
    Fy = st.number_input("Fy (Yield Strength) [ksc]", min_value=100, value=2400, step=100)
    E_gpa = st.number_input("E (Modulus) [GPa]", min_value=1, value=200)
    
    st.write("---")
    st.write("**Deflection Limit:**")
    def_option = st.selectbox("Select Limit", 
                              ["L/360 (General/Floor)", "L/240 (Roof)", "L/180 (Industrial)"], 
                              index=0)
    def_val = int(def_option.split('/')[1].split()[0])
    
    st.header("2. Analysis Parameters")
    # [Fixed] Robust Sorting (Depth, Weight)
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x]['D'], SYS_H_BEAMS[x]['W']))
    
    default_idx = 8 if len(sort_list) > 8 else 0
    section = st.selectbox("Select Size", sort_list, index=default_idx)
    
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)
    
    # [NEW] Unbraced Length Input
    use_custom_Lb = st.checkbox("Specify Unbraced Length (Lb)")
    if use_custom_Lb:
        Lb_input = st.number_input("Unbraced Length (Lb) [m]", min_value=0.1, max_value=30.0, value=L_input)
    else:
        Lb_input = None # Will default to L_input in calculator

# --- Process ---
props = SYS_H_BEAMS[section]
# [NEW] Pass Lb_input to calculator
c = core_calculation(L_input, Fy, E_gpa, props, method, def_val, Lb_m=Lb_input)
final_w = min(c['ws'], c['wm'], c['wd'])

# --- Display Tabs ---
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📝 Detail Report", "📊 Behavior Graph", "📋 Capacity Table",
    "📚 Master Catalog", "📊 Timeline Analysis", "🛠️ Connection Design"        
])

with t1: render_tab1(c, props, method, Fy, section)

with t2:
    st.subheader(f"📈 Capacity Envelope Analysis: {section}")
    st.caption(f"Lb Used = {c['Lb_used']:.2f} m | Deflection Limit: L/{def_val}")

    L_max = max(15, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    ys = (2 * c['V_des'] / (x*100)) * 100 
    # Note: Envelope assumes Lb = L for the curve generation normally, 
    # but strictly speaking, changing L changes Lb if unbraced. 
    # For this simple envelope, we assume Lb = L for the whole curve 
    # unless logic is complex. Here we keep simple scaling.
    ym = (8 * c['M_des'] / (x*100)**2) * 100 
    
    k_def = (384 * c['E_ksc'] * props['Ix']) / (5 * def_val)
    yd = (k_def / (x*100)**3) * 100
    
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    y_lim = max(y_gov) * 1.5 
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y_gov, fill='tozeroy', fillcolor='rgba(100,100,100,0.1)', line=dict(color='rgba(0,0,0,0)'), showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=ys, name='Shear Limit', line=dict(color='#d9534f', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=ym, name='Moment Limit', line=dict(color='#f0ad4e', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=yd, name=f'Defl (L/{def_val})', line=dict(color='#5cb85c', dash='dash')))
    fig.add_trace(go.Scatter(x=x, y=y_gov, name='Governing', line=dict(color='black', width=3)))
    
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w], mode='markers+text', 
                             marker=dict(size=12, color='blue', symbol='diamond'),
                             text=[f"{final_w:,.0f}"], textposition="top right", name='Design Point'))
    
    fig.update_layout(title=f"Capacity Envelope: {section}", height=500, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with t3: render_tab3(props, method, Fy, E_gpa, section, def_val)
with t4: render_tab4(method, Fy, E_gpa, def_val)
with t5: render_tab5(method, Fy, E_gpa, def_val)
with t6: render_tab6(method, Fy, E_gpa, def_val, section, L_input)
