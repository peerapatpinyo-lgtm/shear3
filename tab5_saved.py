import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📑 Master Structural Zones Analysis")
    st.caption(f"ตารางแสดงระยะควบคุม (Control Zones) และระยะ Span ที่ทำได้เมื่อใช้งาน 75% (Deflection Limit: **L/{def_limit}**)")

    # 1. ดึงหน้าตัดทั้งหมดและเรียงลำดับ
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    results = []
    
    # Progress bar
    prog_bar = st.progress(0, text="Calculating critical zones...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # คำนวณ Core Calculation
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # --- Critical Lengths (จุดเปลี่ยนพฤติกรรม) ---
        # L_vm = จุดสิ้นสุด Shear / จุดเริ่ม Moment
        L_start_moment = c['L_vm'] 
        
        # L_md = จุดสิ้นสุด Moment / จุดเริ่ม Deflection
        L_end_moment = c['L_md']
        
        # --- Load Analysis ---
        # Load ที่รับได้สูงสุด ณ จุดเปลี่ยน Shear -> Moment
        if L_start_moment > 0:
            w_max_shear = (2 * c['V_des'] / (L_start_moment * 100)) * 100
        else:
            w_max_shear = 0
            
        # --- 75% Scenario ---
        w_75 = 0.75 * w_max_shear
        
        # หาระยะ Span ที่รับ w_75 ได้ (โดยใช้สูตร Moment)
        if w_75 > 0:
            L_at_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100
        else:
            L_at_75 = 0

        results.append({
            "Section": section_name,
            "Weight": props['W'],
            
            # Zone 1: Shear Limit
            "L (Shear Limit)": L_start_moment,
            "Max Load": int(w_max_shear),
            
            # Zone 2: Moment Zone Range
            "L (Moment Limit)": L_end_moment,
            
            # Scenario: 75% Check
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
            
            # --- SHEAR ZONE & TRANSITION ---
            "Max Load": st.column_config.NumberColumn(
                "Max Cap (kg/m)", 
                format="%d",
                help="Maximum Uniform Load Capacity (controlled by Shear)"
            ),
            "L (Shear Limit)": st.column_config.NumberColumn(
                "Shear Zone End (m)", 
                format="%.2f", 
                help="ระยะสูงสุดที่ Shear ยังควบคุมอยู่ ($L_{vm}$)"
            ),
            
            # --- MOMENT ZONE (New Request) ---
            "L (Moment Limit)": st.column_config.NumberColumn(
                "Moment Zone End (m)", 
                format="%.2f",
                help="ระยะสูงสุดที่รับได้ก่อนจะตกท้องช้างเกินพิกัด ($L_{md}$)"
            ),
            
            # --- 75% SCENARIO ---
            "Load @ 75%": st.column_config.NumberColumn(
                "Load 75%", 
                format="%d",
                help="โหลดที่ลดลงเหลือ 75%"
            ),
            "Span @ 75%": st.column_config.ProgressColumn(
                "Span @ 75% (m)", 
                format="%.2f",
                min_value=0,
                max_value=float(df["Span @ 75%"].max()),
                help="ระยะ Span ที่ยืดออกไปได้เมื่อลดโหลดเหลือ 75%"
            )
        }
    )
    
    # คำอธิบายเพิ่มเติมเกี่ยวกับ Zone
    st.info("""
    **📏 คำอธิบายระยะ (Zones Definition):**
    1. **Shear Zone End ($L_{vm}$):** ระยะ 0 ถึงค่านี้ คือช่วงที่ **แรงเฉือน (Shear)** เป็นตัวควบคุม
    2. **Moment Zone End ($L_{md}$):** ช่วงระยะระหว่าง $L_{vm}$ ถึง $L_{md}$ คือช่วงที่ **โมเมนต์ดัด (Moment)** เป็นตัวควบคุม
    3. **Deflection Zone:** ถ้าระยะ Span ยาวเกินกว่า $L_{md}$ จะถูกควบคุมด้วย **การแอ่นตัว (Deflection)**
    """)

    # ปุ่ม Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Analysis CSV",
        data=csv,
        file_name=f"SYS_Full_Zone_Analysis_{method}.csv",
        mime='text/csv',
    )
