import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Master Structural Timeline")
    st.caption(f"Timeline วิเคราะห์พฤติกรรมคาน: Shear (แดง) ➔ Moment (ส้ม) ➔ Deflection (เขียว) | Criteria: **L/{def_limit}**")

    # --- 1. Data Processing & Physics Engine ---
    # เรียงหน้าตัดจากเล็กไปใหญ่ (Small -> Large) เพื่อให้กราฟเป็นขั้นบันไดสวยงาม
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    data_list = []
    
    # Progress Bar (User Experience)
    prog_bar = st.progress(0, text="Performing structural analysis...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # 1.1 Core Calculation
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # 1.2 Critical Transition Points (Zone Boundaries)
        L_vm = c['L_vm']  # สิ้นสุด Shear Zone / เริ่ม Moment Zone
        L_md = c['L_md']  # สิ้นสุด Moment Zone / เริ่ม Deflection Zone
        
        # 1.3 Load Scenarios Calculation
        # คำนวณ Max Load ที่จุดเปลี่ยน Shear->Moment (จุดที่ Strength สูงสุดก่อนเข้า Moment Control)
        if L_vm > 0:
            w_max_shear_limit = (2 * c['V_des'] / (L_vm * 100)) * 100 # kg/m
        else:
            w_max_shear_limit = 0
            
        # Scenario: 75% of Max Capacity
        w_75 = 0.75 * w_max_shear_limit
        
        # คำนวณ Span ที่รับ w_75 ได้ (โดยใช้สูตร Moment Strength)
        if w_75 > 0:
            L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 # meters
        else:
            L_75 = 0

        # 1.4 Smart Visualization Logic (Auto-Scaling)
        # ปัญหา: ถ้า L_75 ยาวมากๆ มันอาจจะทะลุจอกราฟสีเขียว
        # แก้ไข: คำนวณความยาวกราฟสีเขียวให้ครอบคลุม L_75 เสมอ
        
        # หาจุดที่ไกลที่สุดที่ต้องแสดงในกราฟ
        max_dist = max(L_md, L_75)
        # เผื่อพื้นที่ด้านขวาอีก 15% เพื่อความสวยงาม
        visual_end_point = max(max_dist * 1.15, L_md + 1.0) 
        
        # ความกว้างของแท่งสีเขียว (Deflection Zone Width)
        L_deflect_width = max(0, visual_end_point - L_md)

        data_list.append({
            "Section": section_name,
            "Weight": props['W'],
            "Ix": props['Ix'],
            
            # --- Graph Data ---
            "L_shear": L_vm,
            "L_moment_width": max(0, L_md - L_vm),
            "L_deflect_width": L_deflect_width,
            
            # --- Tooltip/Table References ---
            "Ref_Start_Moment": L_vm,
            "Ref_Start_Deflect": L_md,
            
            # --- Scenarios ---
            "L_75": L_75,
            "Max_Load": w_max_shear_limit,
            "Load_75": w_75
        })
        
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- 2. Visualization (Stacked Bar Timeline) ---
    fig = go.Figure()

    # Layer 1: Shear Zone (Red)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_shear'],
        name='Shear Control',
        orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)), # Danger Red
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "🔴 <b>Shear Zone</b>: 0 - %{x:.2f} m<br>" +
            "<i>(ช่วงสั้น รับแรงเฉือนเป็นหลัก)</i><extra></extra>"
        )
    ))

    # Layer 2: Moment Zone (Orange) -> Highlight
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_moment_width'],
        name='Moment Control',
        orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)), # Warning Orange
        base=df['L_shear'], # Stack ต่อจาก Shear
        hovertemplate=(
            "<b>Moment Zone (Highlight)</b><br>" +
            "🟠 <b>Range</b>: %{base:.2f} - %{customdata:.2f} m<br>" +
            "<i>(ช่วงระยะที่เหมาะสมที่สุด ควบคุมด้วยโมเมนต์)</i><extra></extra>"
        ),
        customdata=df['Ref_Start_Deflect']
    ))

    # Layer 3: Deflection Zone (Green) -> Warning for Long Span
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_deflect_width'],
        name='Deflection Control',
        orientation='h',
        marker=dict(color='#5cb85c', opacity=0.4, line=dict(width=0)), # Green (Fade)
        base=df['Ref_Start_Deflect'], # Stack ต่อจาก Moment
        hovertemplate=(
            "<b>Deflection Zone</b><br>" +
            "🟢 <b>Range</b>: > %{base:.2f} m<br>" +
            "<i>(ระวัง! ช่วงนี้คานจะตกท้องช้างเกิน L/%s)</i><extra></extra>" % def_limit
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
            "<b>Scenario: 75% Load</b><br>" +
            "🔷 <b>Span</b>: %{x:.2f} m<br>" +
            "Load: %{customdata:,.0f} kg/m<br>" +
            "<i>(ตำแหน่งระยะพาดจริงเมื่อรับโหลด 75%)</i><extra></extra>"
        ),
        customdata=df['Load_75']
    ))

    # Graph Layout
    fig.update_layout(
        title="Structural Behavior Timeline (Shear → Moment → Deflection)",
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

    # --- 3. Detailed Specification Table ---
    st.markdown("---")
    st.markdown("### 📋 Detailed Specification Table")

    # Clone df for display formatting
    df_display = df.copy()
    
    # Format Ranges as Strings
    df_display['Moment Range'] = df.apply(lambda r: f"{r['Ref_Start_Moment']:.2f} - {r['Ref_Start_Deflect']:.2f}", axis=1)
    df_display['Deflect Start'] = df.apply(lambda r: f"> {r['Ref_Start_Deflect']:.2f}", axis=1)

    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            "Ix": st.column_config.NumberColumn("Ix (cm⁴)", format="%d"),
            
            # Zone 1: Shear
            "L_shear": st.column_config.NumberColumn(
                "Shear Limit", 
                format="%.2f",
                help="ระยะสิ้นสุด Shear Zone (สีแดง) หน่วย: เมตร"
            ),
            
            # Zone 2: Moment (Main Focus)
            "Moment Range": st.column_config.TextColumn(
                "Moment Zone (m)", 
                width="medium",
                help="ช่วงระยะที่ควบคุมด้วย Moment (สีส้ม) [ระยะเริ่ม - ระยะจบ]"
            ),
            
            # Zone 3: Deflection
            "Deflect Start": st.column_config.TextColumn(
                "Deflect Zone",
                width="small",
                help=f"ระยะที่เริ่มมีปัญหาการตกท้องช้างเกิน L/{def_limit} (สีเขียว)"
            ),
            
            # Scenario: 75%
            "L_75": st.column_config.ProgressColumn(
                "Span @ 75%", 
                format="%.2f m",
                min_value=0,
                max_value=float(df["L_75"].max()),
                help="ระยะพาดสูงสุดที่ทำได้เมื่อลด Load เหลือ 75%"
            ),
            "Max_Load": st.column_config.NumberColumn("Max Load (kg/m)", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load 75% (kg/m)", format="%d"),
            
            # Hide internal calculation columns
            "L_moment_width": None, "L_deflect_width": None, 
            "Ref_Start_Moment": None, "Ref_Start_Deflect": None
        }
    )
    
    # Download Button
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Verified CSV", 
        data=csv, 
        file_name="SYS_Master_Timeline.csv", 
        mime="text/csv"
    )
