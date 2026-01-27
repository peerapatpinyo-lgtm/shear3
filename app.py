# app.py
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Tabs (Assuming these files exist and handle the dictionary correctly)
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
    
    Fy = st.number_input("Fy (Yield Strength) [ksc]", min_value=100, value=2400, step=100)
    E_gpa = st.number_input("E (Modulus) [GPa]", min_value=1, value=200)
    
    st.write("---")
    st.write("**Deflection Limit:**")
    def_option = st.selectbox("Select Limit", 
                              ["L/360 (General/Floor)", "L/240 (Roof)", "L/180 (Industrial)"], 
                              index=0)
    def_val = int(def_option.split('/')[1].split()[0])
    
    st.header("2. Analysis Parameters")
    # Robust Sorting
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x]['D'], SYS_H_BEAMS[x]['W']))
    
    default_idx = 8 if len(sort_list) > 8 else 0
    section = st.selectbox("Select Size", sort_list, index=default_idx)
    
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)
    
    use_custom_Lb = st.checkbox("Specify Unbraced Length (Lb)")
    if use_custom_Lb:
        Lb_input = st.number_input("Unbraced Length (Lb) [m]", min_value=0.1, max_value=30.0, value=L_input)
    else:
        Lb_input = None # Defaults to L_input inside calculator

# --- Process ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method, def_val, Lb_m=Lb_input)

# Final allowable uniform load (Net Load)
final_w_net = min(c['ws_net'], c['wm_net'], c['wd_net'])

# --- Display Tabs ---
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📝 Detail Report", "📊 Behavior Graph", "📋 Capacity Table",
    "📚 Master Catalog", "📊 Timeline Analysis", "🛠️ Connection Design"        
])

with t1: render_tab1(c, props, method, Fy, section)

with t2:
    st.subheader(f"📈 Net Capacity Envelope: {section}")
    st.caption(f"Lb Used = {c['Lb_used']:.2f} m | Deflection Limit: L/{def_val} | Values are NET Safe Load (Beam Weight Deducted)")

    # --- Engineering Fix: Dynamic Curve Calculation ---
    # We must calculate the actual Moment Capacity at each span length to plot the curve correctly,
    # because Mn depends on Lb (which equals Span in this simple envelope check).
    
    L_max = max(15, L_input*1.5)
    x_vals = np.linspace(0.5, L_max, 100) # 100 points for smoothness
    
    y_shear = []
    y_moment = []
    y_defl = []
    
    w_beam = props['W']
    
    for x_span in x_vals:
        # Calculate Capacity for this specific span (Assuming Lb = L_span for the graph envelope)
        # We use a lightweight call or full call. 
        # Note: If user specified fixed Lb, we should respect that, but usually envelope implies Lb=L varies.
        # Here we assume Lb varies with Span for the general capacity curve unless fixed Lb is physically braced.
        # For safety/standard envelope, we usually assume Lb = Span.
        
        sim_c = core_calculation(x_span, Fy, E_gpa, props, method, def_val, Lb_m=x_span)
        
        # Net loads
        y_shear.append(max(0, sim_c['ws'] - w_beam))
        y_moment.append(max(0, sim_c['wm'] - w_beam))
        y_defl.append(max(0, sim_c['wd'] - w_beam))

    y_gov = np.minimum(np.minimum(y_shear, y_moment), y_defl)
    
    fig = go.Figure()
    
    # Plot Governing Area
    fig.add_trace(go.Scatter(x=x_vals, y=y_gov, fill='tozeroy', fillcolor='rgba(100,100,100,0.1)', 
                             line=dict(color='rgba(0,0,0,0)'), showlegend=False))
    
    # Plot Limit Lines
    fig.add_trace(go.Scatter(x=x_vals, y=y_shear, name='Shear Limit', line=dict(color='#d9534f', dash='dash')))
    fig.add_trace(go.Scatter(x=x_vals, y=y_moment, name='Moment Limit (LTB)', line=dict(color='#f0ad4e', dash='dash')))
    fig.add_trace(go.Scatter(x=x_vals, y=y_defl, name=f'Defl (L/{def_val})', line=dict(color='#5cb85c', dash='dash')))
    fig.add_trace(go.Scatter(x=x_vals, y=y_gov, name='Safe Load (Net)', line=dict(color='black', width=3)))
    
    # Plot Current Design Point
    fig.add_trace(go.Scatter(x=[L_input], y=[final_w_net], mode='markers+text', 
                             marker=dict(size=14, color='blue', symbol='diamond'),
                             text=[f"{final_w_net:,.0f} kg/m"], textposition="top right", name='Your Design'))
    
    fig.update_layout(
        title=f"Allowable Net Uniform Load vs Span ({section})", 
        xaxis_title="Span Length (m)",
        yaxis_title="Safe Superimposed Load (kg/m)",
        height=500, template="plotly_white",
        yaxis_range=[0, max(y_gov)*1.2 if len(y_gov)>0 else 1000]
    )
    st.plotly_chart(fig, use_container_width=True)

with t3: render_tab3(props, method, Fy, E_gpa, section, def_val)
with t4: render_tab4(method, Fy, E_gpa, def_val)
with t5: render_tab5(method, Fy, E_gpa, def_val)
with t6: render_tab6(method, Fy, E_gpa, def_val, section, L_input)
