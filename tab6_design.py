# tab6_design.py
import streamlit as st
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    # --- Input Setup (ย่อ) ---
    if section_name not in SYS_H_BEAMS: section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    d_factor = 10 if beam['D'] < 100 else 1 

    col1, col2 = st.columns([1, 2])
    
    # --- UI INPUTS ---
    with col1:
        st.info(f"**Section:** {section_name}")
        with st.form("conn_input"):
            st.markdown("#### 1. Loads & Bolts")
            Vu = st.number_input("Shear Load (Vu) [kg]", value=5000.0, step=100.0)
            c_a, c_b = st.columns(2)
            db_str = c_a.selectbox("Bolt", ["M16","M20","M22","M24"], index=1)
            gr = c_b.selectbox("Grade", ["A325","A490","Gr.8.8"])
            db = float(db_str.replace("M",""))
            
            st.markdown("#### 2. Geometry")
            c3, c4 = st.columns(2)
            n_rows = c3.number_input("Rows", 2, 12, 3)
            pitch = c4.number_input("Pitch", 30, 150, 70)
            c5, c6 = st.columns(2)
            lev = c5.number_input("V-Edge", 20, 80, 35)
            leh = c6.number_input("H-Edge", 20, 80, 35)
            
            st.markdown("#### 3. Plate")
            c7, c8 = st.columns(2)
            tp = c7.selectbox("Thick (mm)", [6,9,10,12,16,19], index=2)
            weld = c8.selectbox("Weld (mm)", [4,6,8,10,12], index=1)
            pl_w = st.number_input("Plate Width", 60, 300, 100)
            setback = st.slider("Setback", 0, 25, 12)
            
            run_btn = st.form_submit_button("Run Analysis", type="primary")

    # --- UI RESULTS ---
    with col2:
        if run_btn:
            # Inputs Dict
            pl_h = (2*lev) + ((n_rows-1)*pitch)
            inputs = {
                'method': method, 'load': Vu,
                'plate_mat': 'SS400', 'plate_t': tp, 'plate_h': pl_h, 'plate_w': pl_w,
                'beam_fy': Fy, 'beam_tw': beam.get('t1', beam.get('tw', 6.0)),
                'bolt_dia': db, 'bolt_grade': gr, 'n_rows': n_rows,
                'pitch': pitch, 'lev': lev, 'leh_beam': leh, 'weld_sz': weld
            }
            
            # Run Calc
            try:
                res = calc.calculate_shear_tab(inputs)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()
            
            # Check Geo Errors
            if res.get('critical_error'):
                st.error("⛔ **Geometry Violation:**")
                for err in res['errors']: st.write(f"- {err}")
                st.stop()

            # Status Box
            calc_vals = [v for k,v in res.items() if 'ratio' in v]
            max_r = max([x['ratio'] for x in calc_vals])
            status = "PASS" if max_r <= 1.0 else "FAIL"
            st.markdown(f"""
            <div style="padding:15px; border:2px solid {'green' if max_r<=1 else 'red'}; border-radius:8px; text-align:center;">
                <h3 style="margin:0; color:{'green' if max_r<=1 else 'red'};">{status} (Ratio: {max_r:.2f})</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # TABS
            t1, t2 = st.tabs(["📝 Detailed Calculation", "🧊 3D Model"])
            
            with t1:
                st.markdown("---")
                # Define check order
                checks = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup', 'block_shear', 'weld']
                
                for key in checks:
                    if key not in res: continue
                    item = res[key]
                    
                    # Header
                    icon = "✅" if item['ratio'] <= 1.0 else "❌"
                    st.markdown(f"##### {icon} {item['title']}")
                    st.caption(f"Ref: {item['ref']}")
                    
                    # 3-Column Layout for clear math
                    # Col 1: Formula | Col 2: Substitution | Col 3: Result
                    c_eq, c_sub, c_res = st.columns([1.2, 2.0, 1.2])
                    
                    with c_eq:
                        st.markdown("**Formula:**")
                        st.latex(item['formula'])
                    
                    with c_sub:
                        st.markdown("**Substitution:**")
                        # แสดงผลแทนค่าพร้อมหน่วย
                        st.latex(item['subst'])
                        # แสดงบรรทัด = Rn ตัวเลขเพียวๆ
                        if 'rn' in item and key != 'weld':
                            st.latex(rf"= {item['rn']:,.0f} \text{{ kg}}")
                    
                    with c_res:
                        st.markdown(f"**Design Capacity:**")
                        # ส่วนนี้แหละที่แก้ปัญหาเรื่อง 1/Omega
                        # เราจะสร้าง Latex string สำหรับแสดงผลลัพธ์สุดท้าย
                        if method == "ASD":
                            design_eq = rf"\frac{{R_n}}{{{item['factor_txt'].replace('Omega = ', '')}}}"
                        else:
                            design_eq = rf"{item['factor_txt'].replace('phi = ', '')} R_n"
                            
                        # ถ้าเป็น Weld ใช้ Logic ต่างหาก (Stress based)
                        if key == 'weld':
                            st.latex(rf"F_{{allow}} = {item['rn']:,.0f} \text{{ ksc}}")
                            st.metric("Ratio", f"{item['ratio']:.2f}")
                        else:
                            st.latex(design_eq + rf" = {item['design_val']:,.0f} \text{{ kg}}")
                            st.metric("Ratio", f"{item['ratio']:.2f}", 
                                      delta=f"Load: {Vu:,.0f} kg", delta_color="off")
                    
                    st.divider()

            with t2:
                # 3D Visual code (same as before)
                beam_dims = {'H': beam['D']*d_factor, 'B': beam.get('B', 100)*d_factor, 'Tw': inputs['beam_tw'], 'Tf': beam.get('t2', 9)}
                plate_dims = {'t': tp, 'w': pl_w, 'h': pl_h, 'weld_sz': weld}
                bolt_dims = {'dia': db, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
                config = {'setback': setback, 'L_beam_show': beam_dims['H']*1.5}
                try:
                    fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                    st.plotly_chart(fig, use_container_width=True)
                except: st.write("Visualizer Error")
