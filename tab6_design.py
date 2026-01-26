# tab6_design.py
import streamlit as st
import pandas as pd
# ตรวจสอบว่ามีไฟล์ database.py และ drawer_3d.py อยู่จริง
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    # --- 1. Data Preparation ---
    if section_name not in SYS_H_BEAMS: 
        section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    
    # Factor สำหรับปรับหน่วย (ถ้า Database เป็น cm ต้อง *10 เป็น mm)
    # สมมติว่า Database เก็บเป็น mm อยู่แล้ว หรือถ้าเก็บเป็น cm ให้แก้ตรงนี้
    d_factor = 10 if beam['D'] < 100 else 1 
    
    # --- 2. Input Section (Left Column) ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info(f"**Section:** {section_name}")
        with st.form("conn_input"):
            st.markdown("#### 1. Load & Bolt")
            Vu = st.number_input("Shear Load (Vu) [kg]", value=5000.0, step=100.0)
            
            c1, c2 = st.columns(2)
            db_str = c1.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            gr = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            db = float(db_str.replace("M",""))
            
            st.markdown("#### 2. Geometry")
            c3, c4 = st.columns(2)
            n_rows = c3.number_input("Rows", 2, 15, 3)
            pitch = c4.number_input("Pitch (mm)", 30, 150, 70)
            
            c5, c6 = st.columns(2)
            lev = c5.number_input("V-Edge (mm)", 20, 100, 35, help="Vertical Edge Distance")
            leh = c6.number_input("H-Edge (mm)", 20, 100, 35, help="Horizontal Edge Distance (on Beam)")
            
            st.markdown("#### 3. Plate")
            c7, c8 = st.columns(2)
            tp = c7.selectbox("Thick (mm)", [6,9,10,12,16,19,25], index=2)
            weld = c8.selectbox("Weld (mm)", [4,6,8,10,12], index=1)
            
            min_w_rec = leh + 50
            pl_w = st.number_input("Plate Width (mm)", min_w_rec, 400, min_w_rec+10)
            setback = st.slider("Setback", 0, 30, 12)
            
            run_btn = st.form_submit_button("Run Analysis", type="primary")

    # --- 3. Results Section (Right Column) ---
    with col2:
        if run_btn:
            # Calculate Derived Geometry
            pl_h = (2 * lev) + ((n_rows - 1) * pitch)
            
            # Prepare Inputs Dictionary
            inputs = {
                'method': method, 
                'load': Vu,
                'plate_mat': 'SS400', 
                'plate_t': tp, 
                'plate_h': pl_h, 
                'plate_w': pl_w,
                'beam_fy': Fy, 
                # ดึงค่า tw จาก database (เช็ค key t1 หรือ tw)
                'beam_tw': beam.get('t1') if beam.get('t1') else beam.get('tw', 6.0),
                'bolt_dia': db, 
                'bolt_grade': gr, 
                'n_rows': n_rows,
                'pitch': pitch, 
                'lev': lev, 
                'leh_beam': leh,
                'weld_sz': weld
            }
            
            # --- CALL CALCULATION ---
            try:
                res = calc.calculate_shear_tab(inputs)
            except Exception as e:
                st.error(f"Calculation Module Error: {e}")
                st.stop()
            
            # 1. Check Critical Errors (Geometry)
            if res.get('critical_error'):
                st.error("⛔ **Geometry Constraints Failed:**")
                for err in res['errors']:
                    st.write(f"- {err}")
                st.stop()
                
            # 2. Overall Status
            # กรองเฉพาะ key ที่เป็นผลลัพธ์การคำนวณ (ตัด keys อื่นๆ ออก)
            calc_items = [v for k, v in res.items() if isinstance(v, dict) and 'ratio' in v]
            if not calc_items:
                st.error("No calculation results returned.")
                st.stop()
                
            max_r = max([item['ratio'] for item in calc_items])
            status = "PASS" if max_r <= 1.0 else "FAIL"
            color = "green" if max_r <= 1.0 else "red"
            
            st.markdown(f"""
            <div style="text-align:center; padding:10px; border:2px solid {color}; border-radius:10px; margin-bottom:15px; background-color: rgba(0,0,0,0.05);">
                <h2 style="color:{color}; margin:0;">{status}</h2>
                <p style="margin:0;">Max Utilization Ratio: <b>{max_r:.2f}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. Tabs Display
            t1, t2 = st.tabs(["📝 Calculation Sheet", "🧊 3D Model"])
            
            with t1:
                # Define Order of Checks
                order = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup', 'block_shear', 'plate_flex', 'weld']
                
                for key in order:
                    if key not in res: continue
                    
                    item = res[key]
                    ratio = item['ratio']
                    icon = "✅" if ratio <= 1.0 else "❌"
                    
                    # --- FIXED KEY NAMES HERE ---
                    with st.expander(f"{icon} {item['title']} (Ratio: {ratio:.2f})", expanded=(ratio > 1.0)):
                        c_left, c_right = st.columns([1.5, 1])
                        
                        with c_left:
                            st.caption(f"Ref: {item['ref']}")
                            # ใช้ .get() เพื่อความปลอดภัย หาก key หาย
                            st.latex(item.get('eq_code', ''))
                            st.markdown("**Substitution:**")
                            st.latex(item.get('subst', ''))
                            
                        with c_right:
                            st.markdown(f"**Design Capacity ({item.get('eq_design', '')}):**")
                            st.metric("Capacity", f"{item['design_val']:,.0f} kg")
                            st.metric("Demand", f"{Vu:,.0f} kg")
                            
                            if ratio > 1.0:
                                st.error(f"Overloaded by {(ratio-1)*100:.1f}%")

            with t2:
                # 3D Visualization Logic
                beam_dims = {
                    'H': beam['D'] * d_factor, 
                    'B': beam.get('B', 100) * d_factor, 
                    'Tw': inputs['beam_tw'], 
                    'Tf': beam.get('t2') if beam.get('t2') else beam.get('tf', 9.0)
                }
                plate_dims = {'t': tp, 'w': pl_w, 'h': pl_h, 'weld_sz': weld}
                bolt_dims = {'dia': db, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
                config = {'setback': setback, 'L_beam_show': beam_dims['H'] * 1.5}
                
                try:
                    fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Visualizer Error: {e}")

        else:
            st.info("👈 Please configure parameters and Click 'Run Analysis'")
