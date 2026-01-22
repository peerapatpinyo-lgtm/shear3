import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section):
    """
    Tab 3: Capacity Overview & Zones
    สรุปภาพรวมศักยภาพของหน้าตัด และตารางรับน้ำหนักตามระยะต่างๆ
    """
    st.markdown(f"### 📊 Capacity Summary: {section} ({method})")
    st.write("Overview of load capacity across different spans and governing failure modes.")
    st.markdown("---")

    # --- 1. คำนวณหาจุดเปลี่ยน (Critical Transitions) ---
    # เราใช้ L สมมติ (เช่น 10m) เพื่อส่งเข้า function ไปก่อน เพื่อดึงค่า L_vm, L_md ออกมา
    # เพราะค่า L_vm, L_md ไม่ขึ้นกับความยาวคาน L ที่เปลี่ยนไป (ขึ้นกับ Section properties เท่านั้น)
    dummy_calc = core_calculation(10.0, Fy, E_gpa, props, method)
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
        st.caption("Deflection Controls")
        st.metric(label="Span Range", value=f"> {L_md:.2f} m")
        st.write("ช่วงยาว: ระยะแอ่นเป็นตัวกำหนด")

    st.markdown("---")

    # --- 3. Look-up Table Generation (สร้างตาราง) ---
    st.subheader("2. Capacity Look-up Table (ตารางรับน้ำหนัก)")
    st.write("ตารางแสดงน้ำหนักบรรทุกปลอดภัย (Safe Load) ที่ระยะความยาวต่างๆ")

    # สร้างข้อมูลช่วงระยะ 2m ถึง 15m (หรือมากกว่าตามความเหมาะสม)
    spans = range(2, 16) # 2m to 15m
    data = []

    for L in spans:
        c = core_calculation(float(L), Fy, E_gpa, props, method)
        
        # หาตัว Control
        capacities = {'Shear': c['ws'], 'Moment': c['wm'], 'Deflection': c['wd']}
        safe_load = min(capacities.values())
        
        # Determine Control Text
        if safe_load == c['ws']: control = "Shear"
        elif safe_load == c['wm']: control = "Moment"
        else: control = "Deflection"

        data.append({
            "Span (m)": f"{L:.1f}",
            "Shear Cap. (kg/m)": int(c['ws']),
            "Moment Cap. (kg/m)": int(c['wm']),
            "Deflection Lim. (kg/m)": int(c['wd']),
            "✅ Safe Load (kg/m)": int(safe_load),
            "Mode": control
        })

    df = pd.DataFrame(data)

    # Highlight Function
    def highlight_mode(row):
        mode = row['Mode']
        color = ''
        if mode == 'Shear': color = 'background-color: #ffcccc' # Red tint
        elif mode == 'Moment': color = 'background-color: #ffedcc' # Orange tint
        elif mode == 'Deflection': color = 'background-color: #ccffcc' # Green tint
        return [color if col == 'Mode' else '' for col in row.index]

    # แสดงตาราง
    st.dataframe(
        df.style.apply(highlight_mode, axis=1),
        use_container_width=True,
        hide_index=True,
        height=500
    )
    
    st.caption("*Safe Load shown includes beam weight. (น้ำหนักที่แสดงรวมน้ำหนักตัวเองของคานแล้ว)")
