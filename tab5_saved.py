import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Structural Zone Visualization (Full Range)")
    st.caption(f"Timeline แสดงระยะควบคุมครบ 3 พฤติกรรม: Shear ➔ Moment ➔ Deflection (Limit: **L/{def_limit}**)")

    # --- 1. เตรียมข้อมูล ---
    # เรียงหน้าตัดจากเล็กไปใหญ่
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    data_list = []
    
    prog_bar = st.progress(0, text="Calculating physics...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # Critical Lengths
        L_vm = c['L_vm']  # จบ Shear / เริ่ม Moment
        L_md = c['L_md']  # จบ Moment / เริ่ม Deflection
        
        # กำหนดความยาวกราฟสีเขียว (Deflection) ให้ดูสวยงาม (เช่น ยาวต่อออกไปอีก 30-50% ของระยะเดิม)
        # ไม่ใช่ระยะจริงที่คานหัก แต่เป็น Visual เพื่อแสดงว่าโซนนี้ยาวออกไป
        L_visual_deflect = max(2.0, L_md * 0.3) 

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
            
            # Lengths for Graph
            "L_shear": L_vm,             
            "L_moment_width": max(0, L_md - L_vm), 
            "L_deflect_width": L_visual_deflect, # ความยาวกราฟสีเขียว
            
            # Points for Tooltip/Table
            "Start_Moment": L_vm,
            "Start_Deflect": L_md,
            
            "L_75": L_75,
            "Max_Load": w_max,
            "Load_75": w_75
        })
        prog_bar.progress((i + 1) / total, text=f"Processing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- 2. สร้างกราฟ Timeline (3 Zones) ---
    fig = go.Figure()

    # Layer 1: Shear (แดง)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_shear'],
        name='Shear Zone',
        orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)),
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "🔴 Shear Limit: 0 - %{x:.2f} m<br>" +
            "Capacity Control: Shear Force<extra></extra>"
        )
    ))

    # Layer 2: Moment (ส้ม)
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_moment_width'],
        name='Moment Zone',
        orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)),
        base=df['L_shear'], # ต่อท้ายแดง
        hovertemplate=(
            "<b>Moment Zone (Highlight)</b><br>" +
            "🟠 Range: %{base:.2f} - %{customdata:.2f} m<br>" +
            "Capacity Control: Bending Moment<extra></extra>"
        ),
        customdata=df['Start_Deflect'] # ส่งค่าจุดจบ Moment ไปโชว์
    ))

    # Layer 3: Deflection (เขียว) -> [NEW]
    fig.add_trace(go.Bar(
        y=df['Section'],
        x=df['L_deflect_width'],
        name='Deflection Zone',
        orientation='h',
        marker=dict(color='#5cb85c', opacity=0.6, line=dict(width=0)), # เขียวโปร่งแสงนิดหน่อย
        base=df['Start_Deflect'], # ต่อท้ายส้ม
        hovertemplate=(
            "<b>Deflection Zone</b><br>" +
            "🟢 Range: > %{base:.2f} m<br>" +
            "Capacity Control: Deflection (ตกท้องช้าง)<br>" +
            "<i>(Limit L/%s)</i><extra></extra>" % def_limit
        )
    ))

    # Layer 4: Marker 75% (เพชร)
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

    fig.update_layout(
        title="Structural Behavior Timeline (Shear - Moment - Deflection)",
        barmode='stack', 
        height=800,      
        xaxis_title="Span Length (m)",
        yaxis_title="Section Size",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        yaxis=dict(
            categoryorder='array', 
            categoryarray=df['Section'].tolist()
        ),
        margin=dict(l=10, r=10, t=80, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 3. ตารางข้อมูล (Detailed Table) ---
    st.markdown("---")
    st.markdown("### 📋 Detailed Specification Table")
    
    df_display = df.copy()
    
    # สร้าง String แสดงช่วงระยะ
    df_display['Moment Range'] = df.apply(lambda r: f"{r['Start_Moment']:.2f} - {r['Start_Deflect']:.2f}", axis=1)
    df_display['Deflect Start'] = df.apply(lambda r: f"> {r['Start_Deflect']:.2f}", axis=1) # [NEW] แสดงจุดเริ่ม Deflect

    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt", format="%.1f"),
            "Ix": st.column_config.NumberColumn("Ix", format="%d"),
            
            # Shear
            "L_shear": st.column_config.NumberColumn(
                "Shear Limit", 
                format="%.2f", 
                help="ระยะสิ้นสุดโซน Shear (สีแดง)"
            ),
            
            # Moment
            "Moment Range": st.column_config.TextColumn(
                "Moment Zone (m)", 
                width="medium",
                help="ช่วงระยะโซน Moment (สีส้ม)"
            ),
            
            # Deflection [NEW]
            "Deflect Start": st.column_config.TextColumn(
                "Deflection Zone",
                width="small",
                help=f"ระยะที่เริ่มถูกควบคุมด้วย Deflection (สีเขียว) เกินกว่านี้จะตกท้องช้างเกิน L/{def_limit}"
            ),
            
            # 75%
            "L_75": st.column_config.ProgressColumn(
                "Span @ 75%", 
                format="%.2f m",
                min_value=0,
                max_value=float(df["L_75"].max())
            ),
            "Max_Load": st.column_config.NumberColumn("Max Load", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load 75%", format="%d"),
            
            # Hide internals
            "L_moment_width": None,
            "L_deflect_width": None,
            "Start_Moment": None,
            "Start_Deflect": None
        }
    )
    
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Full CSV", csv, "SYS_Full_Timeline.csv", "text/csv")
