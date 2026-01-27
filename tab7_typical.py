import streamlit as st
import pandas as pd
import math
from database import SYS_H_BEAMS
from calculator import core_calculation
from calculator_tab import calculate_shear_tab

def solve_connection(beam_props, Vu_target, method):
    """
    Super Solver Algorithm:
    พยายามหา Connection ที่ 'เล็กที่สุด' ที่ผ่านเงื่อนไข
    โดยการปรับตัวแปร: Rows -> Plate/Weld -> Bolt Size
    """
    # --- 1. Geometry Constraints ---
    D = beam_props['D']
    Tf = beam_props.get('t2', 10)
    Tw = beam_props.get('t1', 6)
    
    # กำหนด Option ความเป็นไปได้ (เรียงจากเล็กไปใหญ่)
    # Bolt Options: (Dia, Min_Plate_T, Min_Weld)
    bolt_options = [
        {'dia': 12.0, 'p_t': 6.0,  'w_sz': 4.0}, # สำหรับคานเล็กมาก
        {'dia': 16.0, 'p_t': 9.0,  'w_sz': 6.0},
        {'dia': 20.0, 'p_t': 10.0, 'w_sz': 6.0},
        {'dia': 22.0, 'p_t': 12.0, 'w_sz': 8.0},
        {'dia': 24.0, 'p_t': 12.0, 'w_sz': 8.0},
        {'dia': 27.0, 'p_t': 16.0, 'w_sz': 10.0},
        {'dia': 30.0, 'p_t': 19.0, 'w_sz': 12.0}
    ]
    
    # เลือกจุดเริ่มต้นตามขนาดคาน (Best Practice)
    start_idx = 0
    if D >= 600: start_idx = 4 # Start M24
    elif D >= 400: start_idx = 2 # Start M20
    elif D >= 200: start_idx = 1 # Start M16
    
    # --- 2. Optimization Loop ---
    # Loop 1: ไล่ขนาดน็อตจาก (แนะนำ -> ใหญ่สุด)
    for b_idx in range(start_idx, len(bolt_options)):
        opt = bolt_options[b_idx]
        bolt_dia = opt['dia']
        
        # Geometry Parameters
        pitch = 3 * bolt_dia
        lev = 1.5 * bolt_dia
        leh = 35 # Standard edge
        margin = 10
        
        # คำนวณ Max Rows ที่ใส่ได้ในหน้าตัดนี้
        clear_h = D - (2 * Tf) - (2 * margin)
        max_rows_geo = int(((clear_h - (2 * lev)) / pitch) + 1)
        max_rows_geo = max(2, max_rows_geo) # อย่างน้อย 2
        
        # Loop 2: เพิ่มจำนวนแถว (2 -> Max)
        for rows in range(2, max_rows_geo + 1):
            
            # Loop 3: เพิ่มความหนาเพลท/รอยเชื่อม (Normal -> Heavy)
            # กรณีที่น็อตผ่าน แต่เพลทฉีก หรือรอยเชื่อมไม่พอ เราจะลองเพิ่มความหนาดู
            plate_steps = [
                {'t': opt['p_t'],      'w': opt['w_sz']},       # Standard
                {'t': opt['p_t'] + 3,  'w': opt['w_sz'] + 2},   # Stronger
                {'t': opt['p_t'] + 6,  'w': opt['w_sz'] + 4},   # Extra Strong
                {'t': 25.0,            'w': 14.0}               # Maximum Limit
            ]
            
            for p_step in plate_steps:
                plate_t = p_step['t']
                weld_sz = p_step['w']
                plate_h = (2 * lev) + ((rows - 1) * pitch)
                
                inputs = {
                    'load': Vu_target,
                    'method': method,
                    'beam_tw': Tw, 'beam_mat': "SS400", 
                    'plate_t': plate_t, 'plate_h': plate_h, 'plate_mat': "SS400",
                    'bolt_dia': bolt_dia, 'bolt_grade': "A325",
                    'n_rows': rows, 'pitch': pitch,
                    'lev': lev, 'leh': leh, 
                    'weld_sz': weld_sz
                }
                
                try:
                    res = calculate_shear_tab(inputs)
                    if res['summary']['status'] == "PASS":
                        # เย้! เจอแล้ว ส่งคำตอบกลับทันที (เพราะเราเริ่มจากตัวเล็กสุดเสมอ)
                        return {
                            "Rows": rows,
                            "Bolt": f"M{int(bolt_dia)}",
                            "Plate": f"{int(plate_t)}x{int(plate_h)}",
                            "Weld": f"{int(weld_sz)}",
                            "Ratio": res['summary']['utilization'],
                            "Note": "Optimized",
                            "Status": "✅ PASS"
                        }
                except:
                    continue
                    
    # --- 3. Fallback (ถ้าหาทางไม่ได้จริงๆ) ---
    # จะเกิดขึ้นยากมาก นอกจากคานเล็กจิ๋วแต่รับแรงมหาศาล
    return {
        "Rows": max_rows_geo,
        "Bolt": f"M{int(bolt_options[-1]['dia'])}", # ใช้ใหญ่สุด
        "Plate": "Check Detail",
        "Weld": "Check Detail",
        "Ratio": 9.99,
        "Note": "Exceed Capacity",
        "Status": "❌ FAIL"
    }

def render_tab7(method, Fy, E_gpa, def_val):
    st.markdown("### 🛠️ Intelligent Typical Detail Summary")
    st.markdown("""
    **Algorithm:** The system uses a **multi-variable solver** to find the most economical connection that passes.
    1. **Target Load:** 75% of Beam Shear Capacity.
    2. **Optimization Strategy:** Try Standard Config → Increase Rows → Upgrade Plate/Weld → Upgrade Bolt Size.
    """)
    
    # Progress Bar Setup
    progress_text = "Running AI Solver for all sections..."
    my_bar = st.progress(0, text=progress_text)
    
    # Sort Beams
    beams = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    total = len(beams)
    results = []

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Total Sections:** {total}")
    
    # --- MAIN LOOP ---
    pass_count = 0
    
    for i, section_name in enumerate(beams):
        props = SYS_H_BEAMS[section_name]
        
        # 1. Core Calculation
        c = core_calculation(6.0, Fy, E_gpa, props, method, def_val)
        V_full = c['V_des']
        V_target = 0.75 * V_full # Target 75%
        
        # 2. AI Solver Design
        conn = solve_connection(props, V_target, method)
        
        if conn['Status'] == "✅ PASS":
            pass_count += 1
        
        # 3. Collect Data
        results.append({
            "Section": section_name,
            "D": props['D'],
            "Shear (100%)": V_full,
            "Design (75%)": V_target,
            "Zone (m)": f"{c['L_vm']:.2f}-{c['L_md']:.2f}",
            "Bolt": conn['Bolt'],
            "Rows": conn['Rows'],
            "Plate (mm)": conn['Plate'],
            "Weld (mm)": conn['Weld'],
            "Ratio": conn['Ratio'],
            "Status": conn['Status']
        })
        
        # Update Progress
        my_bar.progress((i + 1) / total, text=f"Solving: {section_name}...")

    my_bar.empty() # Clear progress bar
    
    with col2:
        st.success(f"**Passed:** {pass_count}/{total}")
    with col3:
        if pass_count < total:
            st.error(f"**Failed:** {total - pass_count}")
        else:
            st.success("**Performance:** 100% Solved")
    
    # --- DISPLAY ---
    df = pd.DataFrame(results)
    
    # Styling logic for Ratio (Green/Red)
    st.dataframe(
        df,
        use_container_width=True,
        height=800,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="medium", disabled=True),
            "Shear (100%)": st.column_config.NumberColumn("V_cap", format="%d"),
            "Design (75%)": st.column_config.NumberColumn("V_u", format="%d"),
            "Bolt": st.column_config.TextColumn("Bolt Size"),
            "Rows": st.column_config.NumberColumn("Rows"),
            "Ratio": st.column_config.ProgressColumn(
                "Util. Ratio",
                format="%.2f",
                min_value=0,
                max_value=1.5,
            ),
            "Status": st.column_config.TextColumn("Result"),
        }
    )
    
    # CSV Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Smart Typical Details (CSV)",
        data=csv,
        file_name=f"SYS_Smart_Typical_{method}.csv",
        mime="text/csv"
    )
