import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section, def_val=360):
    """
    Tab 3: Capacity Overview & Zones
    สรุปภาพรวมศักยภาพของหน้าตัด และตารางรับน้ำหนักตามระยะต่างๆ
    Updated: รับค่า def_val เพื่อคำนวณจุดเปลี่ยนกราฟและตารางให้ถูกต้อง
    """
    st.markdown(f"### 📊 Capacity Summary: {section} ({method})")
    st.caption(f"Deflection Limit Criteria: **L/{def_val}** (เกณฑ์การแอ่นตัวที่เลือก)")
    st.markdown("---")

    # --- 1. คำนวณหาจุดเปลี่ยน (Critical Transitions) ---
    # ใช้ L สมมติส่งเข้า function เพื่อดึงค่า L_vm, L_md ออกมา
    # ต้องส่ง def_val เข้าไปด้วย เพราะจุดเปลี่ยน L_md ขึ้นอยู่กับ Limit ที่เลือก
    dummy_calc = core_calculation(10.0, Fy, E_gpa, props, method, def_val)
    L_vm = dummy_calc['L_vm']
    L_md = dummy_calc['L_md']

    # --- 2. Zone Visualization (สรุปช่วงพฤติกรรม) ---
    st.subheader("1. Governing Control Zones (ช่วงพฤติกรรมที่ควบคุม)")
    
    # แบ่ง 3 คอลัมน์เพื่อโชว์ช่วงระยะ
    z1, z2, z3 = st.columns(3)
    
    with z1:
        st.error(f"**🔴 Short Span (Shear)**")
        st.caption("Shear Force Controls")
        st.metric(label="Span Range", value=f"0.00 - {L_vm:.2f} m")
        st.write("ช่วงสั้นมาก: แรงเฉือนเป็นตัวกำหนด")

    with z2:
        st.warning(f"**🟠 Medium Span (Moment)**")
        st.caption("Bending Moment Controls")
        st.metric(label="Span Range", value=f"{L_vm:.2f} - {L_md:.2f} m")
        st.write("ช่วงใช้งานทั่วไป: โมเมนต์ดัดเป็นตัวกำหนด")

    with z3:
        st.success(f"**🟢 Long Span (Deflection)**")
        st.caption(f"Deflection (L/{def_val}) Controls")
        st.metric(label="Span Range", value=f"> {L_md:.2f} m")
        st.write("ช่วงยาว: ระยะแอ่นเป็นตัวกำหนด")

    st.markdown("---")

    # --- 3. Look-up Table Generation (สร้างตาราง) ---
    st.subheader(f"2. Capacity Look-up Table (L/{def_val})")
    st.write("ตารางแสดงน้ำหนักบรรทุกปลอดภัย (Safe Load) ที่ระยะความยาวต่างๆ")

    # สร้างข้อมูลช่วงระยะ 2m ถึง 15m
    spans = range(2, 16) 
    data = []

    for L in spans:
        # สำคัญ: ส่ง def_val เข้าไปคำนวณด้วย
        c = core_calculation(float(L), Fy, E_gpa, props, method, def_val)
        
        # หาตัว Control (Shear, Moment, Deflection)
        capacities = {'Shear': c['ws'], 'Moment': c['wm'], 'Deflection': c['wd']}
        safe_load = min(capacities.values())
        
        # Determine Control Text & Mode
        if safe_load == c['ws']: 
            control_txt = "Shear"
        elif safe_load == c['wm']: 
            control_txt = "Moment"
        else: 
            control_txt = f"Deflection (L/{def_val})"

        # คำนวณ Net Load (หักน้ำหนักคานออก) เพื่อให้ User ใช้งานได้จริง
        net_load = max(0, safe_load - props['W'])

        data.append({
            "Span (m)": f"{L:.1f}",
            "Shear Cap.": int(c['ws']),
            "Moment Cap.": int(c['wm']),
            "Deflection Cap.": int(c['wd']),
            "✅ Net Safe Load": int(net_load), # น้ำหนักที่รับเพิ่มได้จริง (Safe - Weight)
            "Mode": control_txt
        })

    df = pd.DataFrame(data)

    # Highlight Function สำหรับ Pandas Styler
    def highlight_mode(row):
        mode = row['Mode']
        color = ''
        if 'Shear' in mode: 
            color = 'background-color: #ffcccc; color: black' # Red tint
        elif 'Moment' in mode: 
            color = 'background-color: #ffedcc; color: black' # Orange tint
        elif 'Deflection' in mode: 
            color = 'background-color: #ccffcc; color: black' # Green tint
        return [color if col == 'Mode' else '' for col in row.index]

    # แสดงตารางด้วย Styler
    st.dataframe(
        df.style.apply(highlight_mode, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Span (m)": st.column_config.TextColumn("Span (m)", help="ความยาวคาน"),
            "✅ Net Safe Load": st.column_config.NumberColumn("✅ Safe Load (kg/m)", help="น้ำหนักบรรทุกปลอดภัยสุทธิ (หักน้ำหนักคานแล้ว)"),
            "Mode": st.column_config.TextColumn("Governing Case", width="medium"),
            "Shear Cap.": st.column_config.NumberColumn("Shear Limit", format="%d"),
            "Moment Cap.": st.column_config.NumberColumn("Moment Limit", format="%d"),
            "Deflection Cap.": st.column_config.NumberColumn("Deflect Limit", format="%d"),
        },
        height=600
    )
    
    st.caption(f"**Note:** 'Safe Load' คือน้ำหนักบรรทุกภายนอกที่รับได้ (หักน้ำหนักตัวเองของคาน {props['W']} kg/m ออกแล้ว)")
    
    # Export CSV Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Table as CSV",
        data=csv,
        file_name=f'capacity_{section}_L{def_val}.csv',
        mime='text/csv',
    )
