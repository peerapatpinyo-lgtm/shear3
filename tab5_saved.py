import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Structural Zone Visualization (Verified)")
    st.caption(f"Timeline วิเคราะห์พฤติกรรมคาน: Shear (แดง) ➔ Moment (ส้ม) ➔ Deflection (เขียว) | Limit: **L/{def_limit}**")

    # --- 1. Data Processing Engine ---
    # เรียงหน้าตัดจากเล็กไปใหญ่ เพื่อความสวยงามของกราฟขั้นบันได
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    data_list = []
    
    # Progress Bar
    prog_bar = st.progress(0, text="Verifying calculation logic...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # Core Calculation (Physics)
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # A. Critical Transition Points
        L_vm = c['L_vm']  # จุดสิ้นสุด Shear Zone
        L_md = c['L_md']  # จุดสิ้นสุด Moment Zone (เริ่มเข้า Deflection Zone)
        
        # B. Load Scenarios Calculation
        # คำนวณ Max Load ณ จุดเปลี่ยน Shear->Moment (จุดที่คุ้มค่าที่สุดทางทฤษฎี)
        if L_vm > 0:
            w_max = (2 * c['V_des'] / (L_vm * 100)) * 100 # kg/m
        else:
            w_max = 0
            
        # คำนวณที่ 75% Capacity
        w_75 = 0.75 * w_max
        
        # หา Span ที่รับ w_75 ไหว (คิดจาก Strength/Moment)
        if w_75 > 0:
            L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 # meters
        else:
            L_75 = 0

        # C. Graph Scaling Logic (Fix: ป้องกันจุด L_75 ลอยออกนอกกราฟ)
        # ปลายสุดของกราฟต้องยาวกว่าทั้ง L_md และ L_75 อย่างน้อย 10-20%
        max_visual_point = max(L_md, L_75)
        visual_end = max_visual_point * 1.15 # เผื่อที่ว่างด้านขวา 15%
        
        # ความกว้างของแท่งสีเขียว (Deflection Zone Width)
        # ต้องเริ่มจาก L_md ไปจนถึง visual_end
        deflect_bar_width = max(0, visual_end - L_md)

        data_list.append({
            "Section": section_name,
            "Weight": props['W'],
            "Ix": props['Ix'],
            
            # Graph Plotting Data
            "L_shear": L_vm,
            "L_moment_width": max(0, L_md - L_vm),
            "L_deflect_width": deflect_bar_width, 
            
            # Reference Points
            "Start_Moment": L_vm,
            "Start_Deflect": L_md,
            
            # Scenario Data
            "L_75": L_75,
            "Max_Load": w_max,
            "Load_75": w_75
        })
        
        prog_bar.progress((i + 1) / total, text=f"Checking {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- 2. Visualization (Timeline Chart) ---
    fig = go.Figure()

    # Layer 1: Shear Zone (Red)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_shear'],
        name='Shear Control',
        orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)),
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "🔴 <b>Shear Zone</b>: 0 - %{x:.2f} m<br>" +
            "ควบคุมโดยแรงเฉือน (Short Span)<extra></extra>"
        )
    ))

    # Layer 2: Moment Zone (Orange)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_moment_width'],
        name='Moment Control',
        orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)),
        base=df['L_shear'], # Stack ต่อจาก Shear
        hovertemplate=(
            "<b>Moment Zone (Highlight)</b><br>" +
            "🟠 <b>Range</b>: %{base:.2f} - %{customdata:.2f} m<br>" +
            "ควบคุมโดยโมเมนต์ดัด (Optimal Range)<extra></extra>"
        ),
        customdata=df['Start_Deflect']
    ))

    # Layer 3: Deflection Zone (Green)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_deflect_width'],
        name='Deflection Control',
        orientation='h',
        marker=dict(color='#5cb85c', opacity=0.5, line=dict(width=0)),
        base=df['Start_Deflect'], # Stack ต่อจาก Moment
        hovertemplate=(
            "<b>Deflection Zone</b><br>" +
            "🟢 <b>Range</b>: > %{base:.2f} m<br>" +
            "ควบคุมโดยการแอ่นตัว (Long Span)<br>" +
            "<i>(เกินระยะนี้จะตกท้องช้างเกินพิกัด)</i><extra></extra>"
        )
    ))

    # Layer 4: 75% Capacity Marker (Blue Diamond)
    fig.add_trace(go.Scatter(
        x=df['L_75'],
        y=df['Section'],
        mode='markers',
        name='Point @ 75% Load',
        marker=dict(symbol='diamond', size=9, color='#0275d8', line=dict(width=1, color='white')),
        hovertemplate=(
            "<b>Scenario: 75% Max Load</b><br>" +
            "🔷 <b>Span</b>: %{x:.2f} m<br>" +
            "Load: %{customdata:,.0f} kg/m<br>" +
            "<i>(สังเกต: หากจุดนี้อยู่ในโซนสีเขียว<br>แสดงว่าแอ่นเกินพิกัดแม้จะรับ นน. ไหว)</i><extra></extra>"
        ),
        customdata=df['Load_75']
    ))

    fig.update_layout(
        title="Structural Behavior Timeline",
        barmode='stack',
        height=850,
        xaxis_title="Span Length (m)",
        yaxis_title="Section Size",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        yaxis=dict(categoryorder='array', categoryarray=df['Section'].tolist()),
        margin=dict(l=10, r=10, t=80, b=10),
        hoverlabel=dict(bgcolor="white", font_size=14)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 3. Detailed Data Table ---
    st.markdown("---")
    st.markdown("### 📋 Specification Table")

    df_display = df.copy()
    
    # Format Range Strings
    df_display['Moment Range'] = df.apply(lambda r: f"{r['Start_Moment']:.2f} - {r['Start_Deflect']:.2f}", axis=1)
    df_display['Deflect Zone'] = df.apply(lambda r: f"> {r['Start_Deflect']:.2f}", axis=1)

    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            "Ix": st.column_config.NumberColumn("Ix (cm⁴)", format="%d"),
            
            # Zone 1
            "L_shear": st.column_config.NumberColumn(
                "Shear Limit", 
                format="%.2f",
                help="ระยะสิ้นสุด Shear Zone (สีแดง)"
            ),
            
            # Zone 2
            "Moment Range": st.column_config.TextColumn(
                "Moment Zone (m)", 
                width="medium",
                help="ช่วงระยะรับโมเมนต์ (สีส้ม)"
            ),
            
            # Zone 3
            "Deflect Zone": st.column_config.TextColumn(
                "Deflect Start",
                width="small",
                help="ระยะเริ่มควบคุมด้วยการแอ่นตัว (สีเขียว)"
            ),
            
            # Scenario
            "L_75": st.column_config.ProgressColumn(
                "Span @ 75%", 
                format="%.2f m",
                min_value=0,
                max_value=float(df["L_75"].max()),
                help="ระยะพาดที่ทำได้จริงที่ 75% Load"
            ),
            "Max_Load": st.column_config.NumberColumn("Max Load", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load 75%", format="%d"),
            
            # Hidden Cols
            "L_moment_width": None, "L_deflect_width": None, 
            "Start_Moment": None, "Start_Deflect": None
        }
    )
    
    # Download
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Verified Data CSV", csv, "SYS_Verified_Timeline.csv", "text/csv")
