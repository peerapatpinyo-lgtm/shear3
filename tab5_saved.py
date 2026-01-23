import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Structural Zone Visualization")
    st.caption(f"Visualizing Shear Limit, Moment Zone, and 75% Capacity Span. (Deflection Limit: **L/{def_limit}**)")

    # 1. Prepare Data
    # เรียงจากใหญ่ไปเล็ก เพื่อให้กราฟแท่งใหญ่อยู่ด้านบน (หรือสลับตามต้องการ)
    # ตรงนี้เรียงเล็กไปใหญ่ (Small -> Large) กราฟจะดูง่ายกว่าเหมือนขั้นบันได
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    data_list = []
    
    # Progress Bar
    prog_bar = st.progress(0, text="Generating visualization...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # Critical Lengths
        L_vm = c['L_vm']  # Shear Limit
        L_md = c['L_md']  # Moment Limit (End of Moment Zone)
        
        # 75% Scenario Calculation
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
            "L_shear": L_vm,             # ความยาวช่วง Shear
            "L_moment_width": max(0, L_md - L_vm), # ความกว้างของ Moment Zone
            "L_total_moment": L_md,      # จุดจบ Moment Zone (สำหรับ Tooltip)
            "L_75": L_75,
            "Max_Load": w_max,
            "Load_75": w_75
        })
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # 2. Plotly Visualization (Gantt-Style)
    fig = go.Figure()

    # Layer 1: Shear Zone (0 to L_vm) -> สีแดง
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_shear'],
        name='Shear Zone',
        orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)), # Bootstrap Danger Color
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "🛑 Shear Control Range: 0 - %{x:.2f} m<br>" +
            "Max Load: %{customdata:,.0f} kg/m<extra></extra>"
        ),
        customdata=df['Max_Load']
    ))

    # Layer 2: Moment Zone (L_vm to L_md) -> สีส้ม (Highlight)
    # ใช้การ Stack ต่อจาก Shear Zone
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_moment_width'], # ความกว้างของโซน
        name='Moment Zone',
        orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)), # Bootstrap Warning Color
        hovertemplate=(
            "<b>Moment Zone (Highlight)</b><br>" +
            "⚠️ Range: %{base:.2f} m - %{customdata:.2f} m<br>" +
            "(Distance controlled by Bending)<extra></extra>"
        ),
        base=df['L_shear'], # จุดเริ่มต้นของแท่งนี้คือจุดจบของ Shear
        customdata=df['L_total_moment'] # ส่งค่าจุดจบไปแสดงใน Tooltip
    ))

    # Layer 3: 75% Capacity Marker -> จุดเพชรสีน้ำเงิน
    fig.add_trace(go.Scatter(
        x=df['L_75'],
        y=df['Section'],
        mode='markers',
        name='Span @ 75% Load',
        marker=dict(symbol='diamond', size=10, color='#0275d8', line=dict(width=1, color='white')),
        hovertemplate=(
            "<b>Span @ 75% Capacity</b><br>" +
            "📍 Distance: %{x:.2f} m<br>" +
            "Load: %{customdata:,.0f} kg/m<extra></extra>"
        ),
        customdata=df['Load_75']
    ))

    # Layout Settings
    fig.update_layout(
        title="Structural Zones & Capacity Timeline",
        barmode='stack', # ให้แท่งต่อกัน
        height=800,      # สูงหน่อยเพราะหน้าตัดเยอะ
        xaxis_title="Span Length (m)",
        yaxis_title="Section Size",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
        template="plotly_white",
        yaxis=dict(
            categoryorder='array', 
            categoryarray=df['Section'].tolist() # บังคับเรียงตามที่ส่งไป (เล็ก -> ใหญ่)
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # 3. Show Detailed Table (เหมือนเดิมด้านล่าง)
    st.markdown("---")
    st.markdown("### 📋 Detailed Data Table")
    
    # (ส่วนตาราง Code เดิม แต่เปลี่ยนชื่อตัวแปรนิดหน่อยเพื่อให้สั้นลงในส่วนนี้)
    # Re-map DataFrame columns for display
    df_display = df.copy()
    df_display['Ix'] = [SYS_H_BEAMS[s]['Ix'] for s in df['Section']] # ดึงค่า Ix มาใส่ใหม่
    df_display['Weight'] = [SYS_H_BEAMS[s]['W'] for s in df['Section']]
    
    # สร้าง String Moment Range
    df_display['Moment Range'] = df.apply(lambda row: f"{row['L_shear']:.2f} - {row['L_total_moment']:.2f}", axis=1)

    st.dataframe(
        df_display[['Section', 'Weight', 'Ix', 'L_shear', 'Moment Range', 'Max_Load', 'L_75', 'Load_75']],
        use_container_width=True,
        height=500,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", pinned=True),
            "L_shear": st.column_config.NumberColumn("Shear Limit (m)", format="%.2f"),
            "Moment Range": st.column_config.TextColumn("Moment Zone (m)", width="medium"),
            "L_75": st.column_config.NumberColumn("Span @ 75% (m)", format="%.2f"),
            "Max_Load": st.column_config.NumberColumn("Max Load (kg/m)", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load @ 75%", format="%d")
        }
    )
    
    # CSV Download
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Data CSV", csv, "SYS_Visual_Analysis.csv", "text/csv")
