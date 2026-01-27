import streamlit as st
import numpy as np
import plotly.graph_objects as go

def render_tab2(c, props, section, L_input, def_val, final_w):
    """
    Render Behavior Graph (Capacity Envelope)
    """
    st.subheader(f"📈 Capacity Envelope Analysis: {section}")
    st.caption(f"Load Capacity Envelope (Deflection Limit: **L/{def_val}**)")

    # 1. Prepare X-axis (Span)
    L_max = max(15, c['L_md']*1.2, L_input*1.5)
    x = np.linspace(0.5, L_max, 400)
    
    # 2. Calculate Capacities at each x
    # Shear Limit (Inverse relationship with x)
    ys = (2 * c['V_des'] / (x*100)) * 100 
    
    # Moment Limit (Inverse square relationship with x)
    ym = (8 * c['M_des'] / (x*100)**2) * 100 
    
    # Deflection Limit (Inverse cubic relationship with x)
    k_def = (384 * c['E_ksc'] * props['Ix']) / (5 * def_val)
    yd = (k_def / (x*100)**3) * 100
    
    # 3. Determine Governing Curve
    y_gov = np.minimum(np.minimum(ys, ym), yd)
    y_lim = max(y_gov) * 1.5 
    
    # 4. Plotting
    fig = go.Figure()

    # Fill Safe Zone
    fig.add_trace(go.Scatter(
        x=x, y=y_gov,
        fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', 
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo='skip',
        showlegend=False,
        name='Safe Zone'
    ))

    # Add Limit Lines
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

    # Add Governing Line (Solid Black)
    fig.add_trace(go.Scatter(
        x=x, y=y_gov, 
        name='Governing Capacity', 
        line=dict(color='black', width=4),
        hovertemplate="<b>Governing Capacity</b><br>Span: %{x:.2f} m<br>Load: %{y:,.0f} kg/m<extra></extra>"
    ))

    # Add Current Design Point
    fig.add_trace(go.Scatter(
        x=[L_input], y=[final_w],
        mode='markers+text',
        marker=dict(size=14, color='#0275d8', symbol='diamond', line=dict(width=2, color='white')),
        text=[f"Current: {final_w:,.0f}"],
        textposition="top right",
        name='Your Design'
    ))

    # 5. Add Zone Annotations (Vertical Areas)
    # Shear Zone
    fig.add_vrect(x0=0, x1=c['L_vm'], fillcolor="#d9534f", opacity=0.05, layer="below", line_width=0)
    if c['L_vm'] > 0:
        fig.add_annotation(x=c['L_vm']/2, y=y_lim*0.9, text="SHEAR", showarrow=False, font=dict(color="#d9534f", weight="bold"))
    
    # Moment Zone
    fig.add_vrect(x0=c['L_vm'], x1=c['L_md'], fillcolor="#f0ad4e", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_vm']+c['L_md'])/2, y=y_lim*0.9, text="MOMENT", showarrow=False, font=dict(color="#f0ad4e", weight="bold"))
    
    # Deflection Zone
    fig.add_vrect(x0=c['L_md'], x1=L_max, fillcolor="#5cb85c", opacity=0.05, layer="below", line_width=0)
    fig.add_annotation(x=(c['L_md']+L_max)/2, y=y_lim*0.9, text="DEFLECTION", showarrow=False, font=dict(color="#5cb85c", weight="bold"))

    # 6. Final Layout
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
