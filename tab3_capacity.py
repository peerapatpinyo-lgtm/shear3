import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section, def_val=360):
    """
    Tab 3: Capacity Overview & Zones (Revised for Precision)
    แก้ไข: เริ่มต้น Span ที่ 1 เมตร - 30 เมตร (เริ่ม 0 ไม่ได้เพราะจะเกิด Divide by Zero Error)
    """
    st.markdown(f"### 📊 Capacity Summary: {section} ({method})")
    st.caption(f"Deflection Limit Criteria: **L/{def_val}**")
    st.markdown("---")

    # --- 1. คำนวณหาจุดเปลี่ยน (Critical Transitions) ---
    # ใช้ค่าคงที่ M_des_full ในการหาจุดเปลี่ยน เพื่อให้แม่นยำและเท่ากันทุก Span
    dummy_calc = core_calculation(10.0, Fy, E_gpa, props, method, def_val)
    L_vm = dummy_calc['L_vm']
    L_md = dummy_calc['L_md']

    # --- 2. Zone Visualization ---
    st.subheader("1. Governing Control Zones")
    z1, z2, z3 = st.columns(3)
    
    with z1:
        st.error(f"**🔴 Short Span (Shear)**")
        st.caption(f"0.00 - {L_vm:.2f} m")
    with z2:
        st.warning(f"**🟠 Medium Span (Moment)**")
        st.caption(f"{L_vm:.2f} - {L_md:.2f} m")
    with z3:
        st.success(f"**🟢 Long Span (Deflection)**")
        st.caption(f"> {L_md:.2f} m")

    st.markdown("---")

    # --- 3. Look-up Table Generation ---
    st.subheader(f"2. Capacity Look-up Table (L/{def_val})")
    
    st.info(f"""
    **วิธีอ่านค่า:**
    * **✅ Net Safe Load:** น้ำหนักบรรทุกใช้งานจริง (หักน้ำหนักคาน {props['W']} kg/m แล้ว)
    * **Gross Capacity:** ความสามารถรับน้ำหนักรวม (Shear/Moment/Deflection) ตรงกับ Tab 1
    """)

    # [CHANGE] เริ่มต้นที่ 1 เมตร ถึง 30 เมตร (range 1 ถึง 31)
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
        
        # Net Load Calculation
        net_load = max(0, gross_min - props['W'])

        # Determine Control Mode
        if gross_min == w_shear: 
            control_txt = "Shear"
        elif gross_min == w_moment: 
            control_txt = "Moment"
        else: 
            control_txt = f"Deflection"

        data.append({
            "Span (m)": f"{L:.1f}",
            "✅ Net Safe Load": net_load,
            "Mode": control_txt,
            "Shear (Gross)": w_shear,
            "Moment (Gross)": w_moment,
            "Deflect (Gross)": w_deflect
        })

    df = pd.DataFrame(data)

    # Highlight Function
    def highlight_mode(row):
        mode = row['Mode']
        color = ''
        if 'Shear' in mode: color = 'background-color: #ffcccc'
        elif 'Moment' in mode: color = 'background-color: #ffedcc'
        elif 'Deflection' in mode: color = 'background-color: #ccffcc'
        return [color if col == 'Mode' else '' for col in row.index]

    # Display Table
    st.dataframe(
        df.style.apply(highlight_mode, axis=1).format({
            "✅ Net Safe Load": "{:,.0f}",
            "Shear (Gross)": "{:,.0f}",
            "Moment (Gross)": "{:,.0f}",
            "Deflect (Gross)": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Span (m)": st.column_config.TextColumn("Span (m)"),
            "✅ Net Safe Load": st.column_config.Column("✅ Net Safe Load (kg/m)", help="Safe Load - Beam Weight"),
            "Shear (Gross)": st.column_config.Column("Shear Cap.", help="ตรงกับ Tab 1"),
            "Moment (Gross)": st.column_config.Column("Moment Cap.", help="ตรงกับ Tab 1"),
            "Deflect (Gross)": st.column_config.Column("Deflection Cap.", help="ตรงกับ Tab 1"),
        },
        height=600
    )
    
    # Export CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f'capacity_{section}_L{def_val}.csv',
        mime='text/csv',
    )
