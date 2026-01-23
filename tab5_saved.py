import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 🚀 Master Structural Dashboard")
    st.caption(f"Decision Intelligence Tool: Compare Efficiency, Zones, and Capacity. (Deflection Limit: **L/{def_limit}**)")

    # --- 1. Control Panel (ตัวกรองและการเรียงลำดับ) ---
    col_sort, col_dummy = st.columns([1, 3])
    with col_sort:
        sort_mode = st.radio(
            "⚡ Sort By:",
            ["Section Depth (Size)", "Weight (Lightest First)", "Span @ 75% (Longest First)"],
            horizontal=False
        )

    # --- 2. Data Processing Engine ---
    all_sections = list(SYS_H_BEAMS.keys())
    
    data_list = []
    
    # Progress Bar UI
    prog_text = "Processing structural physics for all sections..."
    prog_bar = st.progress(0, text=prog_text)
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # Zone Boundaries
        L_vm = c['L_vm']  # Shear Limit
        L_md = c['L_md']  # Moment Limit
        
        # Deflection starts governing after L_md. 
        # Let's define a "Visual Max" to plot the Deflection zone reasonably (e.g., +5m from Moment limit)
        L_visual_end = max(15.0, L_md * 1.3) 

        # Load Scenarios
        if L_vm > 0:
            w_max = (2 * c['V_des'] / (L_vm * 100)) * 100
        else:
            w_max = 0
            
        w_75 = 0.75 * w_max
        if w_75 > 0:
            L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100
        else:
            L_75 = 0
            
        # Efficiency Ratio (Span per Weight) -> ยิ่งเยอะยิ่งคุ้ม
        eff_ratio = L_75 / props['W']

        data_list.append({
            "Section": section_name,
            "Depth_Int": int(section_name.split('x')[0].split('-')[1]), # For sorting
            "Weight": props['W'],
            "Ix": props['Ix'],
            "L_shear": L_vm,
            "L_moment_width": max(0, L_md - L_vm),
            "L_deflection_width": max(0, L_visual_end - L_md),
            "L_moment_end": L_md,
            "L_75": L_75,
            "Max_Load": w_max,
            "Load_75": w_75,
            "Efficiency": eff_ratio
        })
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- Sorting Logic ---
    if "Weight" in sort_mode:
        df = df.sort_values(by="Weight", ascending=False) # Heavy top (chart looks like pyramid) or swap
        chart_category_order = df['Section'].tolist() # เรียงตามน้ำหนัก
    elif "Span" in sort_mode:
        df = df.sort_values(by="L_75", ascending=True) # Shortest top
        chart_category_order = df['Section'].tolist()
    else: # Default Depth
        # Sort by depth (numeric)
        df = df.sort_values(by="Depth_Int", ascending=True) # Smallest top
        chart_category_order = df['Section'].tolist()


    # --- 3. The "Efficiency Matrix" (New Feature!) ---
    st.markdown("#### 💎 Efficiency Matrix: Weight vs. Span")
    st.info("💡 **เทคนิคการเลือก:** มองหาจุดที่อยู่ **ขวาล่าง** (น้ำหนักเบา แต่พาดได้ไกล) คือจุดที่คุ้มค่าที่สุด")
    
    fig_scatter = px.scatter(
        df, 
        x="L_75", 
        y="Weight", 
        size="Max_Load", # ขนาดจุด = รับ Load สูงสุดได้มาก
        color="Efficiency", # สี = ความคุ้มค่า
        hover_name="Section",
        text="Section",
        color_continuous_scale="Viridis",
        labels={"L_75": "Achievable Span @ 75% Load (m)", "Weight": "Steel Weight (kg/m)", "Efficiency": "Score"},
        title="Optimization Map (Size of bubble = Max Load Capacity)"
    )
    fig_scatter.update_traces(textposition='top center')
    fig_scatter.update_layout(height=600, template="plotly_white")
    st.plotly_chart(fig_scatter, use_container_width=True)


    # --- 4. The "Complete Timeline" (Upgraded Gantt) ---
    st.markdown("---")
    st.markdown("#### 🚥 Structural Behavior Timeline")
    
    fig_timeline = go.Figure()

    # Layer 1: Shear (Red)
    fig_timeline.add_trace(go.Bar(
        y=df['Section'], x=df['L_shear'],
        name='Shear Zone', orientation='h',
        marker=dict(color='#d9534f'), # Red
        hovertemplate="<b>Shear Control</b><br>Range: 0 - %{x:.2f} m<extra></extra>"
    ))

    # Layer 2: Moment (Orange)
    fig_timeline.add_trace(go.Bar(
        y=df['Section'], x=df['L_moment_width'],
        name='Moment Zone', orientation='h',
        marker=dict(color='#f0ad4e'), # Orange
        base=df['L_shear'], # Stack on Shear
        hovertemplate="<b>Moment Control</b><br>Range: (Shear End) - %{customdata:.2f} m<extra></extra>",
        customdata=df['L_moment_end']
    ))
    
    # Layer 3: Deflection (Green - NEW!)
    fig_timeline.add_trace(go.Bar(
        y=df['Section'], x=df['L_deflection_width'],
        name='Deflection Zone', orientation='h',
        marker=dict(color='#5cb85c', opacity=0.4), # Green (Fade)
        base=df['L_moment_end'], # Stack on Moment
        hovertemplate="<b>Deflection Control</b><br>Range: > %{base:.2f} m<br>(Long span requires checking deflection)<extra></extra>"
    ))

    # Layer 4: Marker @ 75% (Diamond)
    fig_timeline.add_trace(go.Scatter(
        x=df['L_75'], y=df['Section'],
        mode='markers', name='Span @ 75%',
        marker=dict(symbol='diamond', size=9, color='#0275d8', line=dict(width=1, color='white')),
        hovertemplate="<b>Current Design (75%)</b><br>Span: %{x:.2f} m<br>Load: %{customdata:,.0f} kg/m<extra></extra>",
        customdata=df['Load_75']
    ))

    fig_timeline.update_layout(
        barmode='stack',
        height=900, # สูงขึ้นเพื่อให้เห็นทุกตัวชัดๆ
        xaxis_title="Span Length (m)",
        yaxis=dict(categoryorder='array', categoryarray=chart_category_order),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        template="plotly_white",
        margin=dict(l=150) # เผื่อพื้นที่ชื่อแกน Y
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

    # --- 5. Data Table (เหมือนเดิมแต่ครบถ้วน) ---
    with st.expander("📄 Show Detailed Data Table", expanded=False):
        # Format for display
        df_display = df.copy()
        df_display['Moment Range'] = df.apply(lambda r: f"{r['L_shear']:.2f} - {r['L_moment_end']:.2f}", axis=1)
        
        st.dataframe(
            df_display,
            column_config={
                "Section": st.column_config.TextColumn("Section", pinned=True),
                "Efficiency": st.column_config.ProgressColumn(
                    "Efficiency Score", 
                    format="%.2f", 
                    min_value=0, 
                    max_value=float(df['Efficiency'].max()),
                    help="Span Length per unit Weight (Higher is better)"
                ),
                "L_shear": st.column_config.NumberColumn("Shear Limit", format="%.2f m"),
                "Moment Range": st.column_config.TextColumn("Moment Zone", width="medium"),
                "L_75": st.column_config.NumberColumn("Span @ 75%", format="%.2f m"),
                "Weight": st.column_config.NumberColumn("Weight", format="%.1f kg/m"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full CSV", csv, "SYS_Ultimate_Analysis.csv", "text/csv")
