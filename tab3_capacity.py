# tab3_capacity.py
import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section_name, def_limit):
    st.markdown(f"### 📋 Capacity Check: {section_name}")

    # --- Local Input for Detailed Check ---
    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("ระบุความยาวช่วงคาน (Span) ที่ต้องการตรวจสอบละเอียดใน Tab นี้")
        L_check = st.number_input("Span Length (m)", min_value=1.0, max_value=30.0, value=6.0, step=0.5, key="tab3_L")
        
        use_Lb = st.checkbox("Specify Unbraced Length (Lb)", key="tab3_use_Lb")
        if use_Lb:
            Lb_check = st.number_input("Lb (m)", min_value=0.1, max_value=30.0, value=L_check, key="tab3_Lb")
        else:
            Lb_check = L_check # Default Lb = L

    # --- Calculation ---
    # เรียก core_calculation ใหม่สำหรับค่า L ที่ระบุใน Tab นี้
    c = core_calculation(L_check, Fy, E_gpa, props, method, def_limit, Lb_m=Lb_check)

    # ✅ FIX: Map keys correctly to handle Net vs Gross
    # ใช้ .get() เพื่อป้องกัน KeyError และดึงค่า Net Load มาใช้เป็นหลัก
    ws = c.get('ws_net', 0)
    wm = c.get('wm_net', 0)
    wd = c.get('wd_net', 0)
    
    w_final = min(ws, wm, wd)

    # --- Visualization ---
    with col2:
        st.markdown("#### 🎯 Performance Summary")
        
        # Determine Governing Case
        if w_final == ws:
            gov = "SHEAR"
            color = "red"
        elif w_final == wm:
            gov = "MOMENT (Flexure)"
            color = "orange"
        else:
            gov = "DEFLECTION"
            color = "green"

        st.metric(label=f"Safe Superimposed Load (Net Capacity)", 
                  value=f"{w_final:,.0f} kg/m", 
                  delta=f"Controlled by: {gov}")
        
        # Progress Bars relative to max of the three
        max_val = max(ws, wm, wd)
        if max_val == 0: max_val = 1 # Avoid div/0
        
        st.write(f"**Shear Capacity:** {ws:,.0f} kg/m")
        st.progress(min(ws/max_val, 1.0))
        
        st.write(f"**Moment Capacity:** {wm:,.0f} kg/m")
        st.progress(min(wm/max_val, 1.0))
        
        st.write(f"**Deflection Limit:** {wd:,.0f} kg/m")
        st.progress(min(wd/max_val, 1.0))

    st.markdown("---")

    # --- Detailed Table ---
    st.markdown("#### 📊 Detailed Calculation Breakdown")
    
    # Organize data for DataFrame
    data = [
        {
            "Check Type": "Shear Strength",
            "Nominal Capacity (Rn)": f"{c.get('vn_val', 0):,.0f} kg",
            "Allowable Load (w_net)": f"{ws:,.0f} kg/m",
            "Note": "Based on Web Area"
        },
        {
            "Check Type": "Flexural Strength (Moment)",
            "Nominal Capacity (Mn)": f"{c.get('mn_val', 0):,.0f} kg-m",
            "Allowable Load (w_net)": f"{wm:,.0f} kg/m",
            "Note": f"Lb = {Lb_check} m"
        },
        {
            "Check Type": "Deflection Limit",
            "Nominal Capacity (Ix)": f"{props['Ix']:,.0f} cm4",
            "Allowable Load (w_net)": f"{wd:,.0f} kg/m",
            "Note": f"Limit L/{def_limit}"
        }
    ]
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    # --- Diagnostic Logs (Optional) ---
    with st.expander("Show Diagnostic Logs (Advanced)"):
        st.json(c)
