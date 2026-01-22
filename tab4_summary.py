import streamlit as st
import pandas as pd
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab4(method, Fy, E_gpa):
    """
    Tab 4: Master Summary Table
    วนลูปคำนวณเหล็กทุกหน้าตัด เพื่อแสดงตารางเปรียบเทียบและช่วงพฤติกรรม
    """
    st.markdown(f"### 📋 Master Catalog: Section Comparison ({method})")
    st.write("ตารางสรุปพฤติกรรมและกำลังรับน้ำหนักของเหล็กทุกหน้าตัด (All Sections Analysis)")
    
    # --- Control Inputs for Comparison ---
    with st.expander("⚙️ ตั้งค่าการเปรียบเทียบ (Comparison Settings)", expanded=True):
        col_inp1, col_inp2 = st.columns([1, 2])
        with col_inp1:
            # ให้ User เลือกระยะที่จะ Compare Capacity
            compare_L = st.slider("Select Span for Capacity Check (m)", 2.0, 20.0, 6.0, 0.5)
        with col_inp2:
            st.info(f"💡 ตารางจะแสดง Capacity ของเหล็กทุกตัวที่ระยะ **{compare_L} เมตร**")

    # --- Loop Calculation ---
    data = []
    
    # วนลูปเหล็กทุกตัวใน Database
    # เรียงลำดับตามขนาดก่อน (Sort by Height)
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    for section_name in sorted_sections:
        props = SYS_H_BEAMS[section_name]
        
        # 1. คำนวณเพื่อหา Critical Lengths (ใช้ L=10 ไปก่อน เพราะค่า L_vm, L_md เป็นค่าคงที่ของหน้าตัด ไม่ขึ้นกับ L)
        c_const = core_calculation(10.0, Fy, E_gpa, props, method)
        L_vm = c_const['L_vm']
        L_md = c_const['L_md']
        
        # 2. คำนวณ Capacity ที่ระยะที่ User เลือก (compare_L)
        c_active = core_calculation(compare_L, Fy, E_gpa, props, method)
        
        # หาค่าที่ Control ที่ระยะ compare_L
        cap_val = min(c_active['ws'], c_active['wm'], c_active['wd'])
        if cap_val == c_active['ws']: mode = "Shear"
        elif cap_val == c_active['wm']: mode = "Moment"
        else: mode = "Deflection"
        
        # หักน้ำหนักคาน (Net Load)
        net_load = max(0, cap_val - props['W'])

        # เก็บข้อมูลลง List
        data.append({
            "Section": section_name,
            "Weight (kg/m)": props['W'],
            
            # Critical Zones (ช่วงระยะ)
            "L (Shear)": f"0 - {L_vm:.2f} m",
            "L (Moment)": f"{L_vm:.2f} - {L_md:.2f} m",
            "L (Deflection)": f"> {L_md:.2f} m",
            
            # Capacity at Selected Span
            f"Cap @ {compare_L}m": int(cap_val),
            f"Net Load @ {compare_L}m": int(net_load),
            "Control Mode": mode
        })

    # --- Create DataFrame ---
    df = pd.DataFrame(data)

    # --- Display with Formatting ---
    
    # 1. Highlight Control Mode
    def highlight_mode(val):
        color = ''
        if val == 'Shear': color = 'color: #d9534f; font-weight: bold' # Red
        elif val == 'Moment': color = 'color: #f0ad4e; font-weight: bold' # Orange
        elif val == 'Deflection': color = 'color: #5cb85c; font-weight: bold' # Green
        return color

    # 2. Setup Column Config (เพื่อใส่ Bar Chart ในตาราง)
    st.dataframe(
        df.style.applymap(highlight_mode, subset=['Control Mode']),
        use_container_width=True,
        height=600,
        column_config={
            "Section": st.column_config.TextColumn("Section Name", width="medium"),
            "Weight (kg/m)": st.column_config.NumberColumn("Weight", format="%.1f"),
            
            # Critical Lengths
            "L (Shear)": st.column_config.TextColumn("🔴 Shear Zone", help="ช่วงระยะที่ Shear Control"),
            "L (Moment)": st.column_config.TextColumn("🟠 Moment Zone", help="ช่วงระยะที่ Moment Control"),
            "L (Deflection)": st.column_config.TextColumn("🟢 Deflection Zone", help="ช่วงระยะที่ Deflection Control"),
            
            # Capacity (ใส่ Progress Bar ให้เห็นภาพเปรียบเทียบ)
            f"Cap @ {compare_L}m": st.column_config.ProgressColumn(
                f"Total Capacity (kg/m)",
                format="%d",
                min_value=0,
                max_value=int(df[f"Cap @ {compare_L}m"].max()),
            ),
            f"Net Load @ {compare_L}m": st.column_config.NumberColumn(
                "Safe Net Load", format="%d kg/m"
            )
        },
        hide_index=True
    )
    
    # CSV Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Download Summary as CSV",
        data=csv,
        file_name=f"SYS_H_Beam_Summary_{method}_L{compare_L}m.csv",
        mime='text/csv',
    )
