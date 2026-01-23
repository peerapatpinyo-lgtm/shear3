import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Structural Zone Visualization")
    st.caption(f"Timeline แสดงระยะ Shear Limit (สีแดง), Moment Zone (สีส้ม) และจุดใช้งานจริงที่ 75% (Deflection Limit: **L/{def_limit}**)")

    # --- 1. เตรียมข้อมูล ---
    # เรียงหน้าตัดจากเล็กไปใหญ่ (เพื่อให้กราฟดูง่ายเป็นขั้นบันได)
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    data_list = []
    
    # Progress Bar
    prog_bar = st.progress(0, text="Analyzing sections...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # Critical Lengths
        L_vm = c['L_vm']  # จุดสิ้นสุด Shear
        L_md = c['L_md']  # จุดสิ้นสุด Moment
        
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

        data_list.append({
            "Section": section_name,
            "Weight": props['W'],
            "Ix": props['Ix'],
            "L_shear": L_vm,             # ความยาว Shear Zone
            "L_moment_width": max(0, L_md - L_vm), # ความยาว Moment Zone (ส่วนต่าง)
            "L_moment_end": L_md,        # จุดจบ Moment Zone
            "L_75": L_75,
            "Max_Load": w_max,
            "Load_75": w_75
        })
        prog_bar.progress((i + 1) / total, text=f"Processing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- 2. สร้างกราฟ (Timeline Style) ---
    fig = go.Figure()

    # Layer 1: Shear Zone (สีแดง)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_shear'],
        name='Shear Zone (V)',
        orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)), # สีแดง
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "🔴 Shear Limit: 0 - %{x:.2f} m<br>" +
            "Max Load: %{customdata:,.0f} kg/m<extra></extra>"
        ),
        customdata=df['Max_Load']
    ))

    # Layer 2: Moment Zone (สีส้ม - Highlight)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_moment_width'], # ความกว้างของโซน
        name='Moment Zone (M)',
        orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)), # สีส้ม
        base=df['L_shear'], # ต่อท้าย Shear
        hovertemplate=(
            "<b>Moment Zone (Highlight)</b><br>" +
            "🟠 Range: (Shear End) - %{customdata:.2f} m<br>" +
            "Control by Bending Moment<extra></extra>"
        ),
        customdata=df['L_moment_end']
    ))

    # Layer 3: จุด 75% Capacity (เพชรสีน้ำเงิน)
    fig.add_trace(go.Scatter(
        x=df['L_75'],
        y=df['Section'],
        mode='markers',
        name='Span @ 75%',
        marker=dict(symbol='diamond', size=10, color='#0275d8', line=dict(width=1, color='white')),
        hovertemplate=(
            "<b>Span @ 75% Capacity</b><br>" +
            "🔷 Distance: %{x:.2f} m<br>" +
            "Load: %{customdata:,.0f} kg/m<extra></extra>"
        ),
        customdata=df['Load_75']
    ))

    # Config กราฟ
    fig.update_layout(
        title="Structural Zones Timeline (Shear vs Moment)",
        barmode='stack', # ให้แท่งต่อกัน
        height=800,      # ความสูงกราฟ
        xaxis_title="Span Length (m)",
        yaxis_title="Section Size",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        yaxis=dict(
            categoryorder='array', 
            categoryarray=df['Section'].tolist() # บังคับเรียง เล็ก -> ใหญ่
        ),
        margin=dict(l=10, r=10, t=80, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 3. ตารางข้อมูลละเอียด (Detailed Table) ---
    st.markdown("---")
    st.markdown("### 📋 Detailed Specification Table")
    
    # จัดเตรียมข้อมูลตาราง
    df_display = df.copy()
    # สร้างข้อความช่วงระยะ (Range String)
    df_display['Moment Range'] = df.apply(lambda row: f"{row['L_shear']:.2f} - {row['L_moment_end']:.2f}", axis=1)

    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section Name", width="small", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            "Ix": st.column_config.NumberColumn("Ix (cm⁴)", format="%d"),
            
            # Shear Zone
            "L_shear": st.column_config.NumberColumn(
                "Shear Limit (m)", 
                format="%.2f",
                help="ระยะสูงสุดที่ Shear ยังควบคุมอยู่ (0 ถึงระยะนี้)"
            ),
            
            # Moment Zone (Highlight)
            "Moment Range": st.column_config.TextColumn(
                "Moment Zone (m)", 
                width="medium",
                help="ช่วงระยะที่ควบคุมด้วย Moment (เริ่ม - จบ)"
            ),
            
            # 75% Scenario
            "L_75": st.column_config.ProgressColumn(
                "Span @ 75% (m)", 
                format="%.2f",
                min_value=0,
                max_value=float(df["L_75"].max()),
                help="ระยะที่ทำได้จริงเมื่อลด Load เหลือ 75%"
            ),
            "Max_Load": st.column_config.NumberColumn("Max Cap (kg/m)", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load 75% (kg/m)", format="%d"),
            
            # ซ่อนคอลัมน์คำนวณ
            "L_moment_width": None,
            "L_moment_end": None
        }
    )
    
    # Download Button
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Table CSV", csv, "SYS_Structural_Timeline.csv", "text/csv")
