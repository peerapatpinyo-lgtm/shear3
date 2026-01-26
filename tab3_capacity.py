# tab3_capacity.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

# แก้ไขบรรทัดนี้: รับ Arguments ให้ครบ 6 ตัว ตามที่ app.py ส่งมา
def render_tab3(props_from_app, method, Fy, E_gpa, section_name_from_app, def_limit):
    st.markdown("### 📉 Load Capacity Charts")
    
    # 1. Select Section
    # เรียงตาม Depth แล้ว Weight
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x].get('D',0), SYS_H_BEAMS[x].get('W',0)))
    
    # หา index ของคานที่เลือกมาจาก Sidebar (app.py) เพื่อตั้งเป็นค่าเริ่มต้น
    try:
        default_index = sorted_sections.index(section_name_from_app)
    except ValueError:
        default_index = 0

    col1, col2 = st.columns([1, 2])
    with col1:
        # ให้ User เปลี่ยนคานดูในหน้านี้ได้ด้วย โดยเริ่มจากตัวที่เลือกใน Sidebar
        selected_section = st.selectbox("Select Section to Plot:", sorted_sections, index=default_index)
        
        # ดึง Props ใหม่ตามที่เลือกใน Dropdown (เผื่อ User เปลี่ยนใจในหน้านี้)
        current_props = SYS_H_BEAMS[selected_section]
        
        st.info(f"**{selected_section}**\n\nWeight: {current_props.get('W',0)} kg/m\nDepth: {current_props.get('D',0)} mm")

    # 2. Generate Data for Plotting
    # สร้างช่วงความยาว 1m ถึง 12m (ละเอียด 0.1m)
    L_range = np.arange(1.0, 12.1, 0.1)
    
    w_shear = []
    w_moment = []
    w_deflect = []
    
    # ตัวแปรสำหรับเก็บจุดตัดที่แท้จริง
    real_L_md = None 
    found_intersection = False

    for L in L_range:
        # คำนวณทีละความยาว โดยใช้ current_props ที่เลือกในหน้านี้
        c = core_calculation(L, Fy, E_gpa, current_props, method, def_limit)
        
        # Load Capacity (kg/m)
        ws = c['ws']
        wm = c['wm'] # ค่านี้จะลดลงถ้า L เพิ่มขึ้น (คิด LTB แล้ว)
        wd = c['wd']
        
        w_shear.append(ws)
        w_moment.append(wm)
        w_deflect.append(wd)
        
        # --- Logic Check จุดตัดที่แท้จริง ---
        # หาจุดที่ Deflection เริ่มกลายเป็นตัวควบคุม (ค่า load น้อยกว่า Moment)
        if not found_intersection and wd < wm:
            real_L_md = L
            found_intersection = True

    # ถ้าหาไม่เจอ
    if real_L_md is None:
        if w_deflect[0] < w_moment[0]: 
            real_L_md = 1.0 # Deflection คุมตั้งแต่ต้น
        else:
            real_L_md = 12.0 # Moment คุมตลอดช่วง

    # 3. Create Chart
    fig = go.Figure()

    # Plot Shear (สีแดง)
    fig.add_trace(go.Scatter(
        x=L_range, y=w_shear, mode='lines', name='Shear Capacity',
        line=dict(color='#d9534f', width=2, dash='dot')
    ))

    # Plot Moment (สีส้ม) - กราฟนี้จะโค้งลงตาม LTB
    fig.add_trace(go.Scatter(
        x=L_range, y=w_moment, mode='lines', name='Moment Capacity (Inc. LTB)',
        line=dict(color='#f0ad4e', width=3)
    ))

    # Plot Deflection (สีเขียว)
    fig.add_trace(go.Scatter(
        x=L_range, y=w_deflect, mode='lines', name=f'Deflection Limit (L/{def_limit})',
        line=dict(color='#5cb85c', width=3)
    ))
    
    # 4. Highlight Governing Zone
    w_gov = np.minimum(np.minimum(w_shear, w_moment), w_deflect)
    
    fig.add_trace(go.Scatter(
        x=L_range, y=w_gov, mode='none', fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', name='Safe Zone',
        hoverinfo='skip'
    ))

    # 5. Add Annotation for Real Intersection
    if real_L_md and 1.0 < real_L_md < 12.0:
        idx = int((real_L_md - 1.0) * 10)
        idx = min(idx, len(w_moment)-1)
        val_at_intersect = w_moment[idx]

        fig.add_vline(x=real_L_md, line_width=1, line_dash="dash", line_color="grey")
        fig.add_annotation(
            x=real_L_md, y=val_at_intersect,
            text=f"Transition @ {real_L_md:.2f} m",
            showarrow=True, arrowhead=1,
            ax=40, ay=-40,
            bgcolor="white", bordercolor="black"
        )

    # Layout Decoration
    fig.update_layout(
        title=f"Load Capacity Curves: {selected_section}",
        xaxis_title="Span Length (m)",
        yaxis_title="Uniform Load Capacity (kg/m)",
        yaxis_type="log",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 6. Explanation
    st.markdown(f"""
    ---
    **💡 Analysis Insight:**
    * **Intersection Point ($L_{{md}}$):** The graph calculates the *exact* crossover point where Deflection becomes more critical than Bending Moment.
    * **LTB Effect:** Notice how the **Orange Line (Moment)** drops faster as the span increases. This reflects the reduction in $M_n$ due to Lateral-Torsional Buckling (Zone 2/3).
    * **Governing Load:** The shaded grey area represents the maximum safe load you can apply.
    """)
