import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📑 Saved Sections Analysis (บันทึกและเปรียบเทียบ)")
    st.caption("เลือกหน้าตัดที่ต้องการเปรียบเทียบ เพื่อดูระยะจุดเปลี่ยน (Transition) และระยะที่รับน้ำหนักได้ที่ 75% ของ Capacity")

    # 1. สร้าง Session State เพื่อเก็บรายการที่เลือก (ถ้ายังไม่มี)
    if 'selected_sections' not in st.session_state:
        st.session_state.selected_sections = []

    # 2. ตัวเลือกหน้าตัด (Multiselect)
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    # ให้ Default เป็นค่าที่เคยเลือกไว้ หรือถ้าไม่มีให้ว่างไว้
    selected = st.multiselect(
        "➕ Add Sections to Compare:", 
        options=all_sections,
        default=st.session_state.selected_sections
    )
    
    # อัปเดต State
    st.session_state.selected_sections = selected

    if not selected:
        st.info("👈 กรุณาเลือกหน้าตัดจากกล่องด้านบน เพื่อเริ่มการวิเคราะห์")
        return

    # 3. คำนวณค่าสำหรับตาราง
    results = []
    
    for section_name in selected:
        props = SYS_H_BEAMS[section_name]
        
        # รัน calculation ครั้งเดียวเพื่อเอาค่า Constant (ใช้ L=10m เป็น dummy เพราะเราต้องการแค่ค่าคงที่)
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # --- A. จุด Max Shear Capacity (ที่ระยะ Transition) ---
        # ระยะ L_vm คือระยะไกลสุดที่ Shear ยัง Control อยู่ (ไกลกว่านี้ Moment Control)
        L_critical = c['L_vm'] 
        
        # Load ที่รับได้ ณ จุดเปลี่ยนนี้ (Max Capacity ของ Shear Zone)
        # w = 2 * V / L
        w_max_shear = (2 * c['V_des'] / (L_critical * 100)) * 100 # kg/m
        
        # --- B. กรณี 75% Shear Capacity ---
        # สมมติว่าเราลดน้ำหนักบรรทุกลงเหลือ 75% ของจุด Max
        w_75 = 0.75 * w_max_shear
        
        # ถามว่า: ที่น้ำหนัก w_75 นี้ เราจะวางพาดได้ไกลกี่เมตร? (Distance @ 75%)
        # เนื่องจาก load ลดลง -> ระยะทางต้องเพิ่มขึ้น -> เข้าสู่ Moment Zone แน่นอน
        # สูตร Moment: w = 8 * M / L^2  --->  L = sqrt(8 * M / w)
        L_at_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 # หาร 100 แปลง cm เป็น m
        
        results.append({
            "Section": section_name,
            "Weight (kg/m)": props['W'],
            "Max Shear (kg)": int(c['V_des']),
            
            # จุด 100%
            "L @ Max Shear (m)": round(L_critical, 2),
            "Load @ Max (kg/m)": int(w_max_shear),
            
            # จุด 75%
            "Load @ 75% (kg/m)": int(w_75),
            "L @ 75% (m)": round(L_at_75, 2)
        })

    # 4. แสดงผลเป็นตาราง
    df = pd.DataFrame(results)
    
    st.write("---")
    st.subheader("📊 Comparison Table")
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="small"),
            "Weight (kg/m)": st.column_config.NumberColumn("Wt", format="%.1f"),
            "Max Shear (kg)": st.column_config.NumberColumn("V_design", format="%d", help="Design Shear Strength"),
            
            "L @ Max Shear (m)": st.column_config.NumberColumn(
                "L (Transition)", 
                format="%.2f m", 
                help="ระยะไกลสุดที่ Shear ยังเป็นตัวควบคุม (Shear-Moment Transition)"
            ),
            "Load @ Max (kg/m)": st.column_config.ProgressColumn(
                "Load Capacity", 
                format="%d", 
                min_value=0, 
                max_value=int(df["Load @ Max (kg/m)"].max() * 1.1),
                help="น้ำหนักบรรทุกปลอดภัยสูงสุด ที่ระยะ Transition"
            ),
            
            "Load @ 75% (kg/m)": st.column_config.NumberColumn(
                "Load (75%)", 
                format="%d", 
                help="ถ้าน้ำหนักลดเหลือ 75% ของจุด Max"
            ),
            "L @ 75% (m)": st.column_config.NumberColumn(
                "Span @ 75%", 
                format="%.2f m", 
                help="ระยะพาดใหม่ที่ทำได้ เมื่อรับน้ำหนักเพียง 75%"
            )
        }
    )
    
    # 5. คำอธิบายเพิ่มเติม
    st.info("""
    **💡 คำอธิบายการคำนวณ:**
    1. **L (Transition):** คือระยะที่พฤติกรรมเปลี่ยนจาก Shear Control เป็น Moment Control (ระยะ $L_{vm}$)
    2. **Load Capacity:** คือน้ำหนักบรรทุกแผ่กั้น (Uniform Load) สูงสุดที่รับได้ ณ ระยะ Transition นั้น
    3. **Span @ 75%:** หากเราออกแบบให้รับน้ำหนักเพียง **75%** ของขีดความสามารถสูงสุด เราจะสามารถยืดระยะเสา (Span) ออกไปได้ถึงระยะนี้
    """)
