import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section, def_val=360):
    """
    Tab 3: Capacity Overview & Zones (Revised for Clarity & Units)
    แก้ไข: ระบุหน่วยชัดเจนในทุก Column และรองรับการ Export CSV ที่สมบูรณ์
    """
    st.markdown(f"### 📊 Capacity Summary: {section} ({method})")
    
    # Header Info
    c1, c2, c3 = st.columns(3)
    c1.info(f"**Limit Criteria:** L/{def_val}")
    c2.info(f"**Beam Weight:** {props['W']} kg/m")
    c3.info(f"**Span Range:** 1 - 30 m")
    
    st.markdown("---")

    # --- 1. คำนวณหาจุดเปลี่ยน (Critical Transitions) ---
    dummy_calc = core_calculation(10.0, Fy, E_gpa, props, method, def_val)
    L_vm = dummy_calc['L_vm']
    L_md = dummy_calc['L_md']

    # --- 2. Zone Visualization ---
    st.subheader("1. Governing Control Zones (ช่วงความยาวที่ควบคุมการวิบัติ)")
    st.caption("แสดงช่วงความยาวที่พฤติกรรมแต่ละแบบมีผลต่อการรับน้ำหนักสูงสุด")
    
    z1, z2, z3 = st.columns(3)
    with z1:
        st.error(f"**🔴 Short Span (แรงเฉือน)**")
        st.markdown(f"ความยาว: **1.00 - {L_vm:.2f} m**")
    with z2:
        st.warning(f"**🟠 Medium Span (แรงดัด)**")
        st.markdown(f"ความยาว: **{L_vm:.2f} - {L_md:.2f} m**")
    with z3:
        st.success(f"**🟢 Long Span (ระยะแอ่น)**")
        st.markdown(f"ความยาว: **> {L_md:.2f} m**")

    st.markdown("---")

    # --- 3. Look-up Table Generation ---
    st.subheader(f"2. Capacity Look-up Table (ตารางรับน้ำหนัก)")
    
    # คำอธิบายวิธีคำนวณ Net Load
    st.info(f"""
    **📝 คำอธิบายหน่วยและที่มาของค่า:**
    * หน่วยของน้ำหนักทั้งหมดในตารางคือ **kg/m (กิโลกรัมต่อเมตร)**
    * **Gross Capacity:** คือความสามารถรับน้ำหนักรวมของหน้าตัด (ยังไม่ได้หักน้ำหนักตัวคาน)
    * **✅ Net Safe Load:** คือน้ำหนักบรรทุกปลอดภัยที่ใช้งานได้จริง (Live Load + Superimposed Dead Load)
    
    $$ \\text{{Net Safe Load}} = \\text{{Min}}(\\text{{Shear}}, \\text{{Moment}}, \\text{{Deflection}}) - \\text{{Beam Weight}} ({props['W']} \\text{{ kg/m}}) $$
    """)

    # สร้างข้อมูลช่วง 1 - 30 เมตร
    spans = range(1, 31) 
    data = []

    for L in spans:
        # คำนวณ
        c = core_calculation(float(L), Fy, E_gpa, props, method, def_val)
        
        # Gross Capacities
        w_shear = c['ws']
        w_moment = c['wm']
        w_deflect = c['wd']
        
        # หาค่า Control (Gross)
        gross_min = min(w_shear, w_moment, w_deflect)
        
        # Net Load Calculation (ห้ามติดลบ)
        net_load = max(0, gross_min - props['W'])

        # Determine Control Mode
        if gross_min == w_shear: 
            control_txt = "Shear (แรงเฉือน)"
        elif gross_min == w_moment: 
            control_txt = "Moment (แรงดัด)"
        else: 
            control_txt = f"Deflection (ระยะแอ่น)"

        # ใช้ชื่อ Column ภาษาอังกฤษที่มีหน่วยกำกับ เพื่อให้ CSV นำไปใช้ต่อได้ง่าย
        data.append({
            "Span Length (m)": f"{L:.1f}",
            "✅ Net Safe Load (kg/m)": net_load,
            "Governing Mode": control_txt,
            "Shear Cap. (kg/m)": w_shear,
            "Moment Cap. (kg/m)": w_moment,
            "Deflection Limit (kg/m)": w_deflect
        })

    df = pd.DataFrame(data)

    # Highlight Function
    def highlight_mode(row):
        mode = row['Governing Mode']
        color = ''
        if 'Shear' in mode: color = 'background-color: #ffe6e6' # Red tint
        elif 'Moment' in mode: color = 'background-color: #fff4e6' # Orange tint
        elif 'Deflection' in mode: color = 'background-color: #e6ffe6' # Green tint
        return [color if col == 'Governing Mode' else '' for col in row.index]

    # Display Table
    st.dataframe(
        df.style.apply(highlight_mode, axis=1).format({
            "✅ Net Safe Load (kg/m)": "{:,.0f}",
            "Shear Cap. (kg/m)": "{:,.0f}",
            "Moment Cap. (kg/m)": "{:,.0f}",
            "Deflection Limit (kg/m)": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Span Length (m)": st.column_config.TextColumn(
                "Span Length (m)", 
                help="ความยาวช่วงคาน (เมตร)"
            ),
            "✅ Net Safe Load (kg/m)": st.column_config.NumberColumn(
                "✅ Net Safe Load (kg/m)", 
                help="น้ำหนักที่รับได้จริง (หักน้ำหนักคานออกแล้ว)",
                format="%d"
            ),
            "Governing Mode": st.column_config.TextColumn(
                "Governing Mode",
                help="ตัวแปรที่ควบคุมการออกแบบ (Shear/Moment/Deflection)"
            ),
            "Shear Cap. (kg/m)": st.column_config.NumberColumn(
                "Shear Cap. (kg/m)", 
                help="การรับแรงเฉือนสูงสุด (V_design)",
                format="%d"
            ),
            "Moment Cap. (kg/m)": st.column_config.NumberColumn(
                "Moment Cap. (kg/m)", 
                help="การรับแรงดัดสูงสุด (M_design รวมผล LTB)",
                format="%d"
            ),
            "Deflection Limit (kg/m)": st.column_config.NumberColumn(
                "Deflection (kg/m)", 
                help=f"น้ำหนักที่ทำให้แอ่นตัวถึงพิกัด L/{def_val}",
                format="%d"
            ),
        },
        height=600
    )
    
    # Export CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Table (with Units)",
        data=csv,
        file_name=f'Capacity_Table_{section}_L{def_val}.csv',
        mime='text/csv',
    )
