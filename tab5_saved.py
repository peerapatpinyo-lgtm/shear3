import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📑 Master Structural Zones Analysis")
    st.caption(f"ตารางแสดงช่วงระยะ (Zones Range) และสมรรถนะที่ 75% (Deflection Limit: **L/{def_limit}**)")

    # 1. ดึงหน้าตัดทั้งหมดและเรียงลำดับ
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    results = []
    
    prog_bar = st.progress(0, text="Calculating critical zones...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # คำนวณ Core Calculation
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # --- Critical Lengths ---
        L_vm = c['L_vm']  # จุดสิ้นสุด Shear / จุดเริ่ม Moment
        L_md = c['L_md']  # จุดสิ้นสุด Moment / จุดเริ่ม Deflection
        
        # จัดรูปแบบ string สำหรับแสดงช่วง (เช่น "2.50 - 5.00")
        moment_zone_str = f"{L_vm:.2f} - {L_md:.2f}"
        
        # --- Load Analysis ---
        if L_vm > 0:
            w_max_shear = (2 * c['V_des'] / (L_vm * 100)) * 100
        else:
            w_max_shear = 0
            
        # --- 75% Scenario ---
        w_75 = 0.75 * w_max_shear
        
        # Span ที่ 75% (Moment Formula)
        if w_75 > 0:
            L_at_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100
        else:
            L_at_75 = 0

        # เก็บข้อมูลลง List
        results.append({
            "Section": section_name,
            "Weight": props['W'],
            
            # ข้อมูลดิบสำหรับคำนวณ/เรียงลำดับ (Hidden later or used in CSV)
            "_L_vm": L_vm,
            "_L_md": L_md,
            
            # Shear Zone (0 -> L_vm)
            "Shear Limit (m)": L_vm,
            "Max Load": int(w_max_shear),
            
            # Moment Zone (L_vm -> L_md) -> [NEW REQUEST]
            "Moment Zone Range (m)": moment_zone_str,
            
            # 75% Scenario
            "Load @ 75%": int(w_75),
            "Span @ 75%": L_at_75
        })
        
        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")

    prog_bar.empty()

    # 2. สร้าง DataFrame
    df = pd.DataFrame(results)

    # 3. แสดงผลตาราง
    st.dataframe(
        df,
        use_container_width=True,
        height=700,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="small", pinned=True),
            "Weight": st.column_config.NumberColumn("Wt", format="%.1f"),
            
            # Column ที่ซ่อนไว้ (ใช้เพื่อการจัดเรียงหรือ CSV แต่ไม่โชว์ใน Web)
            "_L_vm": None,
            "_L_md": None,
            
            # --- SHEAR ---
            "Max Load": st.column_config.NumberColumn(
                "Max Cap (kg/m)", 
                format="%d",
                help="น้ำหนักบรรทุกสูงสุด ณ จุดสิ้นสุด Shear Zone"
            ),
            "Shear Limit (m)": st.column_config.NumberColumn(
                "Shear Limit (m)", 
                format="%.2f",
                help="ระยะสิ้นสุดของ Shear Zone (0 ถึงระยะนี้)"
            ),
            
            # --- MOMENT RANGE (Highlight) ---
            "Moment Zone Range (m)": st.column_config.TextColumn(
                "Moment Zone (m)",
                width="medium",
                help="ช่วงระยะที่ถูกควบคุมด้วย Moment (จากระยะเริ่ม - ถึงระยะสุด)"
            ),
            
            # --- 75% ---
            "Load @ 75%": st.column_config.NumberColumn(
                "Load 75%", 
                format="%d"
            ),
            "Span @ 75%": st.column_config.ProgressColumn(
                "Span @ 75% (m)", 
                format="%.2f",
                min_value=0,
                max_value=float(df["Span @ 75%"].max()),
                help="ระยะ Span ที่ทำได้เมื่อรับน้ำหนักเพียง 75%"
            )
        }
    )
    
    st.info("""
    **📖 วิธีอ่านค่า Moment Zone:**
    * **ตัวอย่าง:** ถ้าช่อง Moment Zone แสดงค่า `2.15 - 5.60`
    * หมายความว่า:
        * ระยะ **0 ถึง 2.15 ม.** $\to$ **Shear Control**
        * ระยะ **2.15 ถึง 5.60 ม.** $\to$ **Moment Control** (ช่วงนี้คือ Moment Zone)
        * ระยะ **มากกว่า 5.60 ม.** $\to$ **Deflection Control**
    """)

    # ปุ่ม Download CSV (มีข้อมูลครบถ้วนรวมถึงค่าที่ซ่อน)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Analysis CSV",
        data=csv,
        file_name=f"SYS_Zone_Range_Analysis_{method}.csv",
        mime='text/csv',
    )
