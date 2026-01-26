# tab5_saved.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Master Structural Timeline")
    st.caption(f"Analysis Parameters: Fy={Fy} ksc, E={E_gpa} GPa, Limit=L/{def_limit} | Method: {method}")

    # --- 1. Data Processing ---
    # Sort by Depth (D) then Weight (W). Using .get() to prevent KeyErrors.
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x].get('D', 0), SYS_H_BEAMS[x].get('W', 0)))
    
    data_list = []
    
    prog_bar = st.progress(0, text="Performing structural analysis...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # 1.1 Calculate Critical Lengths
        # We pass a dummy length (10.0m) because transition points (L_vm, L_md) 
        # depend on section properties, not the span itself.
        try:
            c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
            
            L_vm = c['L_vm']  # Shear -> Moment transition
            L_md = c['L_md']  # Moment -> Deflection transition
            
            # 1.2 Calculate Load Scenarios (for the Blue Diamond)
            if L_vm > 0:
                # Find max load at Shear limit
                w_max_shear_limit = (2 * c['V_des'] / (L_vm * 100)) * 100 
            else:
                w_max_shear_limit = 0
                
            w_75 = 0.75 * w_max_shear_limit
            
            if w_75 > 0:
                # Find span that can hold 75% load
                L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 
            else:
                L_75 = 0

            # Determine visual range for graph
            max_dist = max(L_md, L_75)
            visual_end_point = max(max_dist * 1.15, L_md + 1.0) 
            L_deflect_width = max(0, visual_end_point - L_md)

            data_list.append({
                "Section": section_name,
                "Weight": props.get('W', 0),
                "Ix": props.get('Ix', 0),
                "L_shear": L_vm,
                "L_moment_width": max(0, L_md - L_vm),
                "L_deflect_width": L_deflect_width,
                "Ref_Start_Moment": L_vm,
                "Ref_Start_Deflect": L_md,
                "L_75": L_75,
                "Load_75": w_75,
                # Store Lp and Lr for the tooltip instead of generic Zone
                "Lp": c.get('Lp', 0),
                "Lr": c.get('Lr', 0)
            })
        except Exception as e:
            # Skip invalid sections to prevent app crash
            print(f"Error calculating {section_name}: {e}")
            continue

        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    
    if not data_list:
        st.error("No valid beam data found or calculation error.")
        return

    df = pd.DataFrame(data_list)

    # --- 2. Visualization (Graph) ---
    fig = go.Figure()

    # Layer 1: Shear Control (Red)
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_shear'],
        name='Shear Control', orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>🔴 Shear Zone: 0 - %{x:.2f} m<extra></extra>"
    ))

    # Layer 2: Moment Control (Orange)
    # Using customdata to pass [DeflectionStart, Lp, Lr] to the tooltip
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_moment_width'],
        name='Moment Control', orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)),
        base=df['L_shear'],
        customdata=np.stack((df['Ref_Start_Deflect'], df['Lp'], df['Lr']), axis=-1),
        hovertemplate="🟠 <b>Moment Zone</b><br>Range: %{base:.2f} - %{customdata[0]:.2f} m<br>⚠️ <b>LTB Limits (Unbraced):</b><br> - Max Plastic (Lp): %{customdata[1]:.2f} m<br> - Max Inelastic (Lr): %{customdata[2]:.2f} m<extra></extra>"
    ))

    # Layer 3: Deflection Control (Green)
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_deflect_width'],
        name='Deflection Control', orientation='h',
        marker=dict(color='#5cb85c', opacity=0.4, line=dict(width=0)),
        base=df['Ref_Start_Deflect'],
        hovertemplate=f"🟢 Deflection Zone (L/{def_limit}): > %{{base:.2f}} m<extra></extra>"
    ))

    # Layer 4: 75% Load Point (Blue Diamond)
    fig.add_trace(go.Scatter(
        x=df['L_75'], y=df['Section'],
        mode='markers', name='Span @ 75% Cap.',
        marker=dict(symbol='diamond', size=6, color='blue'),
        hovertemplate="🔷 Span @ 75% Load: %{x:.2f} m<br>Load: %{customdata:,.0f} kg/m<extra></extra>",
        customdata=df['Load_75']
    ))

    fig.update_layout(
        title="Structural Behavior Timeline (All Beams)",
        barmode='stack', 
        height=max(600, len(df) * 25), # Auto-height
        xaxis_title="Span Length (m)", 
        yaxis_title="Section",
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=80, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 3. Explanation (English) ---
    st.markdown("---")
    st.markdown("### 📖 How to Read This Timeline")
    st.markdown(f"""
    This chart visualizes the **governing failure mode** of each beam section as the span length increases (from left to right).
    
    * 🔴 **Shear Control (Red Zone):**
        At very short spans, the beam's capacity is limited by **Shear Force**. The beam is strong enough in bending, but may fail in shear.
    
    * 🟠 **Moment Control (Orange Zone):**
        This is the **Structural Efficiency Zone**. In this range, the beam's design is governed by its **Bending Moment** capacity.
        * *Tip:* Hover over this bar to see **LTB Limits ($L_p$)**. If your actual unbraced length > $L_p$, the moment capacity will decrease due to Lateral-Torsional Buckling.
    
    * 🟢 **Deflection Control (Green Zone):**
        Beyond the orange zone, the beam is still strong enough to carry the load, but it fails the **Serviceability Limit** (it sags too much).
        * *Criterion:* Deflection > Span / {def_limit}
    
    * 🔷 **Span @ 75% Capacity (Blue Diamond):**
        A reference point indicating the maximum span if the beam is utilized at **75% of its maximum load capacity**. This helps in selecting a conservative design quickly.
    """)

    # --- 4. Table ---
    with st.expander("📄 View Detailed Data Table"):
        st.dataframe(
            df[['Section', 'Weight', 'Ref_Start_Deflect', 'L_75', 'Load_75', 'Lp']],
            column_config={
                "Ref_Start_Deflect": st.column_config.NumberColumn("Deflection Starts (m)", format="%.2f"),
                "L_75": st.column_config.NumberColumn("Span @ 75% Load (m)", format="%.2f"),
                "Load_75": st.column_config.NumberColumn("Load @ 75% (kg/m)", format="%d"),
                "Lp": st.column_config.NumberColumn("Max Unbraced (Lp)", format="%.2f m", help="Max unbraced length to maintain full plastic moment capacity.")
            },
            hide_index=True, use_container_width=True
        )
