# ไฟล์: tab4_summary.py
import streamlit as st
import pandas as pd
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab4(method, Fy, E_gpa, def_limit):
    """
    Tab 4: Master Summary Table
    แสดงตารางเปรียบเทียบหน้าตัดทั้งหมด โดยอัปเดตตาม Deflection Limit ที่เลือก
    """
    st.markdown(f"### 📋 Master Catalog: Section Comparison ({method})")
    
    # แสดงค่า Limit ปัจจุบัน
    st.info(f"ℹ️ Current Criteria: Deflection Limit = **L/{def_limit}**")

    # --- Comparison Settings ---
    with st.expander("⚙️ Comparison Settings (ตั้งค่าระยะเปรียบเทียบ)", expanded=True):
        col_inp1, col_inp2 = st.columns([1, 2])
        with col_inp1:
            compare_L = st.slider("Select Span (m)", 2.0, 20.0, 6.0, 0.5)
        with col_inp2:
            st.caption(f"Comparing capacity of all sections at Span = **{compare_L} m**")

    # --- Loop Calculation ---
    data = []
    
    # Sort sections by size
    sorted_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    
    for section_name in sorted_sections:
        props = SYS_H_BEAMS[section_name]
        
        # [IMPORTANT] ส่ง def_limit เข้าไปคำนวณหา Critical Lengths ใหม่
        c_const = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        L_vm = c_const['L_vm']
        L_md = c_const['L_md']
        
        # [IMPORTANT] คำนวณ Capacity ที่ระยะ compare_L โดยใช้ def_limit ใหม่
        c_active = core_calculation(compare_L, Fy, E_gpa, props, method, def_limit)
        
        # หาค่า Control
        cap_val = min(c_active['ws'], c_active['wm'], c_active['wd'])
        
        if cap_val == c_active['ws']: mode = "Shear"
        elif cap_val == c_active['wm']: mode = "Moment"
        else: mode = "Deflection"
        
        net_load = max(0, cap_val - props['W'])

        data.append({
            "Section": section_name,
            "Weight": props['W'],
            "L_Shear_End": L_vm,  
            "L_Deflect_Start": L_md,
            
            # Display Strings
            "Shear Zone": f"0 - {L_vm:.2f} m",
            "Moment Zone": f"{L_vm:.2f} - {L_md:.2f} m",
            "Deflect Zone": f"> {L_md:.2f} m",
            
            f"Cap @ {compare_L}m": int(cap_val),
            f"Net @ {compare_L}m": int(net_load),
            "Mode": mode
        })

    df = pd.DataFrame(data)

    # --- Styling ---
    def highlight_mode(val):
        color = ''
        if val == 'Shear': color = 'color: #d9534f; font-weight: bold'
        elif val == 'Moment': color = 'color: #f0ad4e; font-weight: bold'
        elif val == 'Deflection': color = 'color: #5cb85c; font-weight: bold'
        return color

    st.dataframe(
        df.style.map(highlight_mode, subset=['Mode']),
        use_container_width=True,
        height=600,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="small"),
            "Weight": st.column_config.NumberColumn("Wt (kg/m)", format="%.1f"),
            
            "Shear Zone": st.column_config.TextColumn("🔴 Shear Zone", width="small"),
            "Moment Zone": st.column_config.TextColumn("🟠 Moment Zone", width="small"),
            "Deflect Zone": st.column_config.TextColumn("🟢 Deflect Zone", width="small", help=f"Starts when Deflection > L/{def_limit}"),
            
            f"Cap @ {compare_L}m": st.column_config.ProgressColumn(
                f"Cap (kg/m)",
                format="%d",
                min_value=0,
                max_value=int(df[f"Cap @ {compare_L}m"].max()),
            ),
            f"Net @ {compare_L}m": st.column_config.NumberColumn(
                "Net Load", format="%d"
            )
        },
        hide_index=True
    )
    
    # Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"Master_Catalog_{method}_L{def_limit}.csv",
        mime='text/csv',
    )
