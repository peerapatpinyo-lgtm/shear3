# tab3_capacity.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab3(props_from_app, method, Fy, E_gpa, section_name_from_app, def_limit):
    st.markdown("### 📉 Load Capacity Charts")
    
    # 1. Select Section
    # เรียงลำดับตาม Depth (D) และ Weight (W)
    # ใช้ .get() เพื่อป้องกัน Error หาก Database มี key ไม่ครบ
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x].get('D', 0), SYS_H_BEAMS[x].get('W', 0)))
    
    # พยายามหา Index ของ Section ที่เลือกมาจาก Sidebar (app.py)
    # เพื่อตั้งเป็นค่าเริ่มต้น (Default) ของ Dropdown ในหน้านี้
    try:
        default_index = sorted_sections.index(section_name_from_app)
    except ValueError:
        default_index = 0

    col1, col2 = st.columns([1, 2])
    with col1:
        # Dropdown ให้ User เปลี่ยนดู Section อื่นได้อิสระในหน้านี้
        selected_section = st.selectbox("Select Section to Plot:", sorted_sections, index=default_index)
        
        # ดึง Properties ของ Section ที่เลือกใน Dropdown มาใช้คำนวณกราฟ
        current_props = SYS_H_BEAMS[selected_section]
        
        st.info(f"**{selected_section}**\n\nWeight: {current_props.get('W', 0)} kg/m\nDepth: {current_props.get('D', 0)} mm")

    # 2. Generate Data for Plotting
    # สร้างช่วงความยาว L ตั้งแต่ 1.0m ถึง 12.0m (Step 0.1m)
    L_range = np.arange(1.0, 12.1, 0.1)
    
    w_shear = []
    w_moment = []
    w_deflect = []
    
    # ตัวแปรสำหรับเก็บจุดตัดจริง (Real Intersection)
    real_L_md = None 
    found_intersection = False

    for L in L_range:
        # คำนวณความสามารถรับน้ำหนักทีละระยะ L
        # หมายเหตุ: ในที่นี้ L ทำหน้าที่เป็น Unbraced Length (Lb) ด้วย
        c = core_calculation(L, Fy, E_gpa, current_props, method, def_limit)
        
        # ดึงค่า Safe Uniform Load (kg/m) ของแต่ละเงื่อนไข
        ws = c['ws']
        wm = c['wm'] # ค่านี้จะลดลงเมื่อ L เพิ่มขึ้น (เพราะ LTB Zone 2/3)
        wd = c['wd']
        
        w_shear.append(ws)
        w_moment.append(wm)
        w_deflect.append(wd)
        
        # --- Logic Check: หาจุดตัดจริง (Real Intersection) ---
        # เราหาจุดที่กราฟ Deflection (สีเขียว) เริ่มลงไปต่ำกว่ากราฟ Moment (สีส้ม)
        # นี่คือจุดเปลี่ยน Zone ที่แท้จริงซึ่งรวมผลของ LTB แล้ว
        if not found_intersection and wd < wm:
            real_L_md = L
            found_intersection = True

    # กรณีหาจุดตัดไม่เจอในช่วง 1-12m
    if real_L_md is None:
        if w_deflect[0] < w_moment[0]: 
            real_L_md = 1.0 # Deflection คุมตลอดช่วง
        else:
            real_L_md = 12.0 # Moment คุมตลอดช่วง (หรือตัดกันที่ >12m)

    # 3. Create Chart
    fig = go.Figure()

    # 3.1 Plot Shear Capacity (สีแดง เส้นประ)
    fig.add_trace(go.Scatter(
        x=L_range, y=w_shear, mode='lines', name='Shear Capacity',
        line=dict(color='#d9534f', width=2, dash='dot')
    ))

    # 3.2 Plot Moment Capacity (สีส้ม เส้นทึบ) - รวมผล LTB แล้ว
    fig.add_trace(go.Scatter(
        x=L_range, y=w_moment, mode='lines', name='Moment Capacity (Inc. LTB)',
        line=dict(color='#f0ad4e', width=3)
    ))

    # 3.3 Plot Deflection Limit (สีเขียว เส้นทึบ)
    fig.add_trace(go.Scatter(
        x=L_range, y=w_deflect, mode='lines', name=f'Deflection Limit (L/{def_limit})',
        line=dict(color='#5cb85c', width=3)
    ))
    
    # 3.4 Highlight Safe Zone (พื้นที่แรเงาสีเทา)
    # เลือกค่าต่ำสุดของทั้ง 3 เส้น ณ จุดนั้นๆ
    w_gov = np.minimum(np.minimum(w_shear, w_moment), w_deflect)
    
    fig.add_trace(go.Scatter(
        x=L_range, y=w_gov, mode='none', fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)', name='Safe Zone',
        hoverinfo='skip'
    ))

    # 4. Add Annotation for Real Intersection
    # แสดงจุดตัดเฉพาะเมื่ออยู่ในช่วงกราฟที่มองเห็น (1-12m)
    if real_L_md and 1.0 < real_L_md < 12.0:
        # หาตำแหน่งแกน Y เพื่อวางป้ายกำกับ
        idx = int((real_L_md - 1.0) * 10) # แปลง L กลับเป็น index
        idx = min(idx, len(w_moment)-1)
        val_at_intersect = w_moment[idx]

        # วาดเส้นแนวตั้งตรงจุดตัด
        fig.add_vline(x=real_L_md, line_width=1, line_dash="dash", line_color="grey")
        
        # ใส่ป้ายข้อความ
        fig.add_annotation(
            x=real_L_md, y=val_at_intersect,
            text=f"Transition @ {real_L_md:.2f} m",
            showarrow=True, arrowhead=1,
            ax=40, ay=-40,
            bgcolor="white", bordercolor="black"
        )

    # Layout Settings
    fig.update_layout(
        title=f"Load Capacity Curves: {selected_section}",
        xaxis_title="Span Length (m)",
        yaxis_title="Uniform Load Capacity (kg/m)",
        yaxis_type="log", # ใช้ Log Scale เพื่อให้ดูกราฟง่ายขึ้นเมื่อค่าต่างกันมาก
        template="plotly_white",
        hovermode="x unified", # โชว์ค่าทุกเส้นเมื่อเอาเมาส์ชี้จุดเดียว
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Explanation (English)
    st.markdown(f"""
    ---
    **💡 Analysis Insight:**
    * **Intersection Point ($L_{{md}}$):** The graph calculates the *exact* crossover point where Deflection becomes more critical than Bending Moment.
    * **LTB Effect:** Notice how the **Orange Line (Moment)** drops faster as the span increases. This reflects the reduction in $M_n$ due to Lateral-Torsional Buckling (Zone 2/3).
    * **Governing Load:** The shaded grey area represents the maximum safe load you can apply.
    """)
