import streamlit as st
import pandas as pd
from database import SYS_H_BEAMS
from calculator import core_calculation
from calculator_tab import calculate_shear_tab

def get_optimized_connection(beam_props, Vu_target, method):
    """
    ฟังก์ชันจำลอง Logic ของ Tab 6 (Shear Tab Design)
    แต่ทำงานแบบวนลูปหาจำนวนแถวน็อตที่น้อยที่สุดที่ผ่าน Load 75%
    """
    # 1. Standard Assumptions for Typical Detail
    D = beam_props['D']
    Tf = beam_props.get('t2', 10)
    Tw = beam_props.get('t1', 6)
    
    # เลือกขนาดน็อตและเพลทตามขนาดคาน (Typical Standards)
    if D >= 600:
        bolt_dia = 24.0; plate_t = 12.0; weld_sz = 8.0
    elif D >= 400:
        bolt_dia = 22.0; plate_t = 10.0; weld_sz = 8.0
    elif D >= 200:
        bolt_dia = 20.0; plate_t = 9.0; weld_sz = 6.0
    else:
        bolt_dia = 16.0; plate_t = 6.0; weld_sz = 4.0

    # Geometry Constraints
    pitch = 3 * bolt_dia
    lev = 1.5 * bolt_dia  # Vertical Edge Distance
    leh = 35              # Horizontal Edge Distance (Std)
    margin = 10
    
    # หาจำนวนแถวสูงสุดที่ใส่ได้ใน web (Maximum Rows)
    clear_h = D - (2 * Tf) - (2 * margin)
    max_rows = int(((clear_h - (2 * lev)) / pitch) + 1)
    max_rows = max(2, max_rows) # อย่างน้อยต้อง 2 แถว
    
    # 2. Optimization Loop: เริ่มจาก 2 แถว ไล่ขึ้นไปเรื่อยๆ จนกว่าจะผ่าน
    best_config = None
    
    for rows in range(2, max_rows + 1):
        plate_h = (2 * lev) + ((rows - 1) * pitch)
        
        # เตรียม Input แบบเดียวกับ Tab 6
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
        
        # เรียกคำนวณ (ใช้ Logic เดียวกับ Tab 6)
        try:
            res = calculate_shear_tab(inputs)
            if res['summary']['status'] == "PASS":
                best_config = {
                    "Rows": rows,
                    "Bolt": f"M{int(bolt_dia)}",
                    "Plate": f"{int(plate_t)}x{int(plate_h)} mm",
                    "Weld": f"{int(weld_sz)} mm",
                    "Ratio": res['summary']['utilization'],
                    "Status": "✅ PASS"
                }
                break # เจอตัวที่ผ่านแล้ว หยุดทันที
        except:
            continue

    # กรณีวนจนครบแล้วยังไม่ผ่าน (Fail)
    if best_config is None:
        best_config = {
            "Rows": max_rows,
            "Bolt": f"M{int(bolt_dia)}",
            "Plate": f"{int(plate_t)}x{int((2*lev)+((max_rows-1)*pitch))} mm",
            "Weld": f"{int(weld_sz)} mm",
            "Ratio": 9.99,
            "Status": "❌ FAIL"
        }
        
    return best_config

def render_tab7(method, Fy, E_gpa, def_val):
    st.markdown("### 🛠️ Typical Connection Detail Summary")
    st.markdown("""
    **Criteria:**
    1. **Design Load:** 75% of Beam Shear Capacity ($0.75 \times V_n/\Omega$ or $\phi V_n$)
    2. **Design Logic:** Auto-calculate using Tab 6 Algorithm (Shear Tab Connection)
    3. **Moment Zone:** Calculated based on unbraced length limits ($L_{vm} - L_{md}$)
    """)
    
    # Progress Bar Setup
    progress_text = "Running Auto-Design for all sections..."
    my_bar = st.progress(0, text=progress_text)
    
    # Sort Beams
    beams = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    total = len(beams)
    results = []

    # --- MAIN LOOP ---
    for i, section_name in enumerate(beams):
        props = SYS_H_BEAMS[section_name]
        
        # 1. Core Calculation (เพื่อหา Shear Cap & Zones)
        # ใช้ L=6m เป็นค่ากลาง (ไม่มีผลต่อ Shear Cap แต่มีผลต่อ Zone เล็กน้อย)
        c = core_calculation(6.0, Fy, E_gpa, props, method, def_val)
        
        V_full = c['V_des']
        V_target = 0.75 * V_full # 📌 Key Requirement 75%
        
        # 2. Connection Design (Run Logic Tab 6)
        conn = get_optimized_connection(props, V_target, method)
        
        # 3. Collect Data
        results.append({
            "Section": section_name,
            "Depth": props['D'],
            "Shear Cap (100%)": V_full,
            "Design Load (75%)": V_target,
            "Moment Zone (m)": f"{c['L_vm']:.2f} - {c['L_md']:.2f}",
            "Connection": f"{conn['Rows']} rows - {conn['Bolt']}",
            "Plate Size": conn['Plate'],
            "Weld Size": conn['Weld'],
            "Ratio": conn['Ratio'],
            "Status": conn['Status']
        })
        
        # Update Progress
        my_bar.progress((i + 1) / total, text=f"Designing: {section_name}")

    my_bar.empty() # Clear progress bar
    
    # --- DISPLAY ---
    df = pd.DataFrame(results)
    
    # Format for Display
    st.dataframe(
        df,
        use_container_width=True,
        height=700,
        column_config={
            "Section": st.column_config.TextColumn("Section", width="medium"),
            "Shear Cap (100%)": st.column_config.NumberColumn("V_cap (kg)", format="%d"),
            "Design Load (75%)": st.column_config.NumberColumn("V_design (kg)", format="%d", help="75% of Capacity"),
            "Connection": st.column_config.TextColumn("Bolt Config", help="Auto-designed for 75% load"),
            "Ratio": st.column_config.NumberColumn("U.Ratio", format="%.2f"),
        }
    )
    
    # CSV Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Typical Details (CSV)",
        data=csv,
        file_name=f"SYS_Typical_Details_{method}.csv",
        mime="text/csv"
    )
