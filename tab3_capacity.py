# tab3_capacity.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab3(props_from_app, method, Fy, E_gpa, section_name_from_app, def_limit):
    st.markdown("### 📉 Load Capacity Analysis")
    
    # --- 1. Control Section (เลือก Section ที่จะดู) ---
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x].get('D', 0), SYS_H_BEAMS[x].get('W', 0)))
    
    try:
        default_index = sorted_sections.index(section_name_from_app)
    except ValueError:
        default_index = 0

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_section = st.selectbox("Select Section to Analyze:", sorted_sections, index=default_index)
        current_props = SYS_H_BEAMS[selected_section]
        st.info(f"**{selected_section}**\n\nWeight: {current_props.get('W', 0)} kg/m\nDepth: {current_props.get('D', 0)} mm")

    st.markdown("---")

    # ==========================================
    # PART 1: The Graph (Logic ใหม่ที่หาจุดตัดจริง)
    # ==========================================
    st.subheader("1. Capacity Charts (Graphical)")
    
    L_range = np.arange(1.0, 12.1, 0.1)
    w_shear, w_moment, w_deflect = [], [], []
    real_L_md = None 
    found_intersection = False

    for L in L_range:
        c = core_calculation(L, Fy, E_gpa, current_props, method, def_limit)
        ws, wm, wd = c['ws'], c['wm'], c['wd']
        
        w_shear.append(ws)
        w_moment.append(wm)
        w_deflect.append(wd)
        
        # Check intersection for Graph Annotation
        if not found_intersection and wd < wm:
            real_L_md = L
            found_intersection = True

    # Plotting
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_shear, mode='lines', name='Shear', line=dict(color='#d9534f', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_moment, mode='lines', name='Moment (Inc. LTB)', line=dict(color='#f0ad4e')))
    fig.add_trace(go.Scatter(x=L_range, y=w_deflect, mode='lines', name=f'Deflection (L/{def_limit})', line=dict(color='#5cb85c')))
    
    w_gov = np.minimum(np.minimum(w_shear, w_moment), w_deflect)
    fig.add_trace(go.Scatter(x=L_range, y=w_gov, mode='none', fill='tozeroy', fillcolor='rgba(100, 100, 100, 0.1)', name='Safe Zone', hoverinfo='skip'))

    if real_L_md and 1.0 < real_L_md < 12.0:
        idx = min(int((real_L_md - 1.0) * 10), len(w_moment)-1)
        fig.add_vline(x=real_L_md, line_width=1, line_dash="dash", line_color="grey")
        fig.add_annotation(x=real_L_md, y=w_moment[idx], text=f"Transition @ {real_L_md:.2f} m", showarrow=True, arrowhead=1, ax=40, ay=-40, bgcolor="white")

    fig.update_layout(
        height=450,
        xaxis_title="Span Length (m)", yaxis_title="Uniform Load Capacity (kg/m)", yaxis_type="log",
        template="plotly_white", hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # PART 2: The Table (Code ที่คุณส่งมา)
    # ==========================================
    st.subheader(f"2. Detailed Look-up Table")
    
    # Info Box
    st.info(f"""
    **📝 Table Legend:**
    * **Gross Capacity:** Total capacity before deducting beam weight.
    * **✅ Net Safe Load:** The actual usable load (Live + Superimposed Dead).
    * $$ \\text{{Net Safe Load}} = \\text{{Min}}(\\text{{Shear}}, \\text{{Moment}}, \\text{{Deflection}}) - \\text{{Beam Weight}} ({current_props['W']} \\text{{ kg/m}}) $$
    """)

    # Generate Table Data for 1 - 30 meters
    spans = range(1, 31) 
    data = []

    for L in spans:
        c = core_calculation(float(L), Fy, E_gpa, current_props, method, def_limit)
        
        ws, wm, wd = c['ws'], c['wm'], c['wd']
        gross_min = min(ws, wm, wd)
        net_load = max(0, gross_min - current_props['W'])

        if gross_min == ws: control_txt = "Shear"
        elif gross_min == wm: control_txt = "Moment"
        else: control_txt = "Deflection"

        data.append({
            "Span Length (m)": f"{L:.1f}",
            "✅ Net Safe Load (kg/m)": net_load,
            "Governing Mode": control_txt,
            "Shear Cap. (kg/m)": ws,
            "Moment Cap. (kg/m)": wm,
            "Deflection Limit (kg/m)": wd
        })

    df = pd.DataFrame(data)

    # Styling
    def highlight_mode(row):
        mode = row['Governing Mode']
        color = ''
        if 'Shear' in mode: color = 'background-color: #ffe6e6'
        elif 'Moment' in mode: color = 'background-color: #fff4e6'
        elif 'Deflection' in mode: color = 'background-color: #e6ffe6'
        return [color if col == 'Governing Mode' else '' for col in row.index]

    # Show Table
    st.dataframe(
        df.style.apply(highlight_mode, axis=1).format({
            "✅ Net Safe Load (kg/m)": "{:,.0f}",
            "Shear Cap. (kg/m)": "{:,.0f}",
            "Moment Cap. (kg/m)": "{:,.0f}",
            "Deflection Limit (kg/m)": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Span Length (m)": st.column_config.TextColumn("Span (m)"),
            "✅ Net Safe Load (kg/m)": st.column_config.NumberColumn("✅ Net Safe Load", format="%d"),
            "Shear Cap. (kg/m)": st.column_config.NumberColumn("Shear Cap", format="%d"),
            "Moment Cap. (kg/m)": st.column_config.NumberColumn("Moment Cap", format="%d"),
            "Deflection Limit (kg/m)": st.column_config.NumberColumn("Deflection Limit", format="%d"),
        },
        height=500
    )
    
    # CSV Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download Table for {selected_section}",
        data=csv,
        file_name=f'Capacity_{selected_section}_Limit{def_limit}.csv',
        mime='text/csv',
    )
