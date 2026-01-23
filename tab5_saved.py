import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📑 Master Shear & Span Analysis (All Sections)")
    st.caption("ตารางวิเคราะห์ระยะจุดเปลี่ยน (Transition Length) และระยะ Span ที่ทำได้เมื่อใช้งานที่ 75% ของ Capacity สำหรับทุกหน้าตัด")

    # 1. ดึงหน้าตัดทั้งหมดและเรียงลำดับตามความสูง (Depth)
    # Sorting key: H-Height (e.g., H-100 -> 100)
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    # 2. Loop คำนวณทุกหน้าตัด
    results = []
    
    # ใช้ Progress bar เผื่อในอนาคตหน้าตัดเยอะ (แต่น้อยกว่า 100 ตัวจะเร็วมาก)
    prog_bar = st.progress(0, text="Calculating all sections...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # คำนวณ Core Calculation (ใช้ L=10m เป็น dummy เพื่อเอาค่าคงที่)
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # --- A. จุด Max Shear Capacity (ที่ระยะ Transition) ---
        # L_vm = Shear-Moment Transition Length
        L_critical = c['L_vm'] 
        
        # Load ที่รับได้ ณ จุดเปลี่ยนนี้ (Max Capacity ที่ Shear Zone สิ้นสุด)
        # สูตร: w = 2 * V_des / L
        if L_critical > 0:
            w_max_shear = (2 * c['V_des'] / (L_critical * 100)) * 100 # kg/m
        else:
            w_max_shear = 0
        
        # --- B. กรณี 75% Capacity ---
        # ลดน้ำหนักบรรทุกลงเหลือ 75% ของจุด Max
        w_75 = 0.75 * w_max_shear
        
        # คำนวณหา Span ใหม่ (L_at_75)
        # เมื่อ Load ลดลง -> Span ยาวขึ้น -> เข้าสู่ Moment Zone 
        # ใช้สูตร Moment: L = sqrt(8 * M_des / w)
        if w_75 > 0:
            L_at_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 # เมตร
        else:
            L_at_75 = 0
            
        # คำนวณ Net Load (หักน้ำหนักคาน)
        net_w_max = max(0, w_max_shear - props['W'])
        net_w_75 = max(0, w_75 - props['W'])

        results.append({
            "Section": section_name,
            "Weight": props['W'],
            "Shear Cap (kg)": int(c['V_des']),
            
            # 100% Capacity Data
            "L (Transition)": L_critical,
            "Max Load (kg/m)": int(w_max_shear),
            "Net Load (kg/m)": int(net_w_max),
            
            # 75% Capacity Data
            "Load @ 75%": int(w_75),
            "Span @ 75%": L_at_75
        })
        
        # Update progress
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")

    prog_bar.empty() # ลบ Progress bar เมื่อเสร็จ

    # 3. สร้าง DataFrame
    df = pd.DataFrame(results)

    # 4. แสดงผลตาราง (Config ให้สวยงาม)
    st.dataframe(
        df,
        use_container_width=True,
        height=700, # กำหนดความสูงให้เห็นข้อมูลเยอะๆ
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="small", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            "Shear Cap (kg)": st.column_config.NumberColumn("V_design (kg)", format="%d"),
            
            # Group: Transition Point
            "L (Transition)": st.column_config.NumberColumn(
                "L_trans (m)", 
                format="%.2f", 
                help="ระยะที่เปลี่ยนจาก Shear Control เป็น Moment Control"
            ),
            "Max Load (kg/m)": st.column_config.NumberColumn(
                "Max Load (kg/m)", 
                format="%d",
                help="Total Uniform Load ที่รับได้ ณ ระยะ Transition"
            ),
            
            # Group: 75% Scenario
            "Load @ 75%": st.column_config.NumberColumn(
                "Load 75% (kg/m)", 
                format="%d",
                help="ถ้าน้ำหนักลดเหลือ 75% ของ Max Load"
            ),
            "Span @ 75%": st.column_config.ProgressColumn(
                "Span @ 75% (m)", 
                format="%.2f m",
                min_value=0,
                max_value=float(df["Span @ 75%"].max()),
                help="ระยะเสาที่ยืดออกไปได้ เมื่อรับน้ำหนักเพียง 75%"
            )
        }
    )
    
    # 5. ปุ่ม Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full Analysis CSV",
        data=csv,
        file_name=f"SYS_Shear_Span_Analysis_{method}.csv",
        mime='text/csv',
    )
