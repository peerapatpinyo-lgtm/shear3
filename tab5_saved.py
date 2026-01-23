import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Master Structural Timeline")
    st.caption(f"Timeline วิเคราะห์พฤติกรรมคาน: Shear (แดง) ➔ Moment (ส้ม) ➔ Deflection (เขียว) | Criteria: **L/{def_limit}**")

    # --- 1. Data Processing ---
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    data_list = []
    
    prog_bar = st.progress(0, text="Performing structural analysis...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # 1.1 Core Calculation
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # 1.2 Critical Points
        L_vm = c['L_vm']  # Shear Limit
        L_md = c['L_md']  # Moment Limit / Deflect Start
        
        # 1.3 Load Scenarios
        # Max Load at Shear Limit (Strength Based)
        if L_vm > 0:
            w_max_shear_limit = (2 * c['V_des'] / (L_vm * 100)) * 100 # kg/m
        else:
            w_max_shear_limit = 0
            
        # 75% Load Scenario
        w_75 = 0.75 * w_max_shear_limit
        
        # Span at 75% Load (Moment Based)
        if w_75 > 0:
            L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 # m
        else:
            L_75 = 0

        # 1.4 Auto-Scaling for Graph
        # Ensure Green Zone covers the L_75 point
        max_dist = max(L_md, L_75)
        visual_end_point = max(max_dist * 1.15, L_md + 1.0) 
        L_deflect_width = max(0, visual_end_point - L_md)

        data_list.append({
            "Section": section_name,
            "Weight": props['W'],
            "Ix": props['Ix'],
            # Graph
            "L_shear": L_vm,
            "L_moment_width": max(0, L_md - L_vm),
            "L_deflect_width": L_deflect_width,
            # Refs
            "Ref_Start_Moment": L_vm,
            "Ref_Start_Deflect": L_md,
            # Scenario
            "L_75": L_75,
            "Max_Load": w_max_shear_limit,
            "Load_75": w_75
        })
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    df = pd.DataFrame(data_list)

    # --- 2. Visualization ---
    fig = go.Figure()

    # Layer 1: Shear (Red)
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_shear'],
        name='Shear Control', orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>🔴 <b>Shear Zone</b>: 0 - %{x:.2f} m<extra></extra>"
    ))

    # Layer 2: Moment (Orange)
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_moment_width'],
        name='Moment Control', orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)),
        base=df['L_shear'],
        hovertemplate="🟠 <b>Moment Zone</b>: %{base:.2f} - %{customdata:.2f} m<extra></extra>",
        customdata=df['Ref_Start_Deflect']
    ))

    # Layer 3: Deflection (Green)
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_deflect_width'],
        name='Deflection Control', orientation='h',
        marker=dict(color='#5cb85c', opacity=0.4, line=dict(width=0)),
        base=df['Ref_Start_Deflect'],
        hovertemplate="🟢 <b>Deflection Zone</b>: > %{base:.2f} m<br><i>(Check L/%s)</i><extra></extra>" % def_limit
    ))

    # Layer 4: 75% Point
    fig.add_trace(go.Scatter(
        x=df['L_75'], y=df['Section'],
        mode='markers', name='Point @ 75%',
        marker=dict(symbol='diamond', size=9, color='#0275d8', line=dict(width=1, color='white')),
        hovertemplate="🔷 <b>Span @ 75% Load</b>: %{x:.2f} m<br>Load: %{customdata:,.0f} kg/m<extra></extra>",
        customdata=df['Load_75']
    ))

    fig.update_layout(
        title="Structural Behavior Timeline",
        barmode='stack', height=850,
        xaxis_title="Span Length (m)", yaxis_title="Section Size",
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        template="plotly_white",
        yaxis=dict(categoryorder='array', categoryarray=df['Section'].tolist()),
        margin=dict(l=10, r=10, t=80, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 3. Table ---
    st.markdown("---")
    st.markdown("### 📋 Detailed Specification Table")
    
    df_display = df.copy()
    df_display['Moment Range'] = df.apply(lambda r: f"{r['Ref_Start_Moment']:.2f} - {r['Ref_Start_Deflect']:.2f}", axis=1)
    df_display['Deflect Start'] = df.apply(lambda r: f"> {r['Ref_Start_Deflect']:.2f}", axis=1)

    st.dataframe(
        df_display,
        use_container_width=True, height=600, hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            "Ix": st.column_config.NumberColumn("Ix (cm⁴)", format="%d"),
            "L_shear": st.column_config.NumberColumn("Shear Limit", format="%.2f", help="ระยะสิ้นสุด Shear Zone (m)"),
            "Moment Range": st.column_config.TextColumn("Moment Zone (m)", width="medium"),
            "Deflect Start": st.column_config.TextColumn("Deflect Zone", width="small"),
            "L_75": st.column_config.ProgressColumn("Span @ 75%", format="%.2f m", min_value=0, max_value=float(df["L_75"].max())),
            "Max_Load": st.column_config.NumberColumn("Max Load", format="%d"),
            "Load_75": st.column_config.NumberColumn("Load 75%", format="%d"),
            "L_moment_width": None, "L_deflect_width": None, "Ref_Start_Moment": None, "Ref_Start_Deflect": None
        }
    )
    
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Data CSV", csv, "SYS_Full_Data.csv", "text/csv")

    # --- 4. Methodology Explanation (NEW!) ---
    st.markdown("---")
    with st.expander("🧮 ที่มาการคำนวณ Span @ 75% (Calculation Methodology)", expanded=True):
        st.markdown("""
        ค่า **Span @ 75%** คำนวณตามหลักการ **Strength Limit State** เพื่อหาระยะพาดที่เหมาะสมเมื่อลดน้ำหนักบรรทุกลง:
        
        **1. หาค่า Max Load ($w_{max}$):**
        คำนวณจากจุดที่รับแรงเฉือนได้สูงสุด (Shear Capacity Limit) ซึ่งถือเป็นจุดที่หน้าตัดทำงานได้เต็มประสิทธิภาพที่สุด
        $$ w_{max} = \\frac{2 \\times V_{design}}{L_{shear}} $$
        
        **2. ลดน้ำหนักลงเหลือ 75%:**
        จำลองสถานการณ์ใช้งานจริง โดยลดน้ำหนักบรรทุกลงจากจุดวิกฤต
        $$ w_{75\\%} = 0.75 \\times w_{max} $$
        
        **3. คำนวณระยะพาดใหม่ ($L_{75}$):**
        คำนวณหาว่าเมื่อ Load เบาลง คานจะยื่นยาวออกไปได้ไกลแค่ไหน จนกว่าจะชนขีดจำกัดของโมเมนต์ดัด ($M_{design}$)
        
        $$ M_{design} = \\frac{w L^2}{8} \\quad \\Rightarrow \\quad L_{75} = \\sqrt{\\frac{8 \\times M_{design}}{w_{75\\%}}} $$
        
        ---
        > **⚠️ ข้อควรระวัง (Note):** > การคำนวณนี้คิดจากความแข็งแรง (Strength) เป็นหลัก หากจุด **Span @ 75%** ในกราฟตกอยู่ใน **โซนสีเขียว (Deflection Zone)** > แสดงว่าคานรับน้ำหนักไหว แต่จะเกิดการแอ่นตัวเกินพิกัด (ตกท้องช้าง) จำเป็นต้องตรวจสอบระยะแอ่นตัวหน้างานอีกครั้ง
        """)
