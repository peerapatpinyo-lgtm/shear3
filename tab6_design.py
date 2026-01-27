import streamlit as st
from database import SYS_H_BEAMS
import calculator_tab as calc
import drawer_3d as d3

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    # 1. Setup Beam Data
    # ตรวจสอบว่ามี section_name ใน database หรือไม่ ถ้าไม่มีให้ใช้ตัวแรก
    if section_name not in SYS_H_BEAMS: 
        section_name = list(SYS_H_BEAMS.keys())[0]
    
    beam = SYS_H_BEAMS[section_name]
    
    # Layout แยกเป็นฝั่ง Input และ Output
    col_in, col_out = st.columns([1, 2])
    
    with col_in:
        st.info(f"**Selected Beam:** {section_name}")
        with st.form("input_form"):
            st.markdown("#### 📥 Input Parameters")
            Vu = st.number_input("Factored Shear Load (Vu) [kg]", 1000, 50000, 5000, step=500)
            db_input = st.selectbox("Bolt Size (mm)", [16, 20, 22, 24], index=1)
            n_rows = st.slider("Number of Rows (n)", 2, 10, 3)
            tp_input = st.selectbox("Plate Thickness (mm)", [6, 9, 10, 12, 16], index=2)
            
            st.markdown("---")
            st.caption("Standard geometry: Pitch=70mm, Edge=35mm")
            run = st.form_submit_button("Analyze & Render 3D", type="primary")

    if run:
        # เตรียม Dictionary สำหรับส่งเข้า Calculator
        # แก้ไขจาก beam['t1'] เป็น beam['tw'] ให้ตรงกับ database.py
        inputs = {
            'method': method, 
            'load': Vu, 
            'plate_mat': 'SS400',
            'plate_t': tp_input, 
            'plate_h': (2 * 35) + ((n_rows - 1) * 70), 
            'plate_w': 100,
            'beam_fy': Fy, 
            'beam_tw': beam.get('tw', 6.0),
            'bolt_dia': db_input, 
            'bolt_grade': 'A325', 
            'n_rows': n_rows,
            'pitch': 70, 
            'lev': 35, 
            'leh_beam': 35
        }
        
        # 2. ทำการคำนวณผ่าน Engine
        res = calc.calculate_shear_tab(inputs)
        
        if res.get('critical_error'):
            st.error("🛑 **Geometry Failure:** ระยะห่างโบลต์หรือระยะขอบไม่ผ่านเกณฑ์ขั้นต่ำ")
            for err in res.get('errors', []):
                st.warning(err)
            st.stop()

        with col_out:
            # --- 3. แสดงผลโมเดล 3D ---
            st.markdown("#### 🧊 3D Connection Visualization")
            
            # Mapping ข้อมูลเข้ากับ Drawer 3D (หน่วยเป็น mm)
            beam_dims = {
                'H': beam['D'], 
                'B': beam['B'], 
                'Tw': beam['tw'], 
                'Tf': beam['tf']
            }
            plate_dims = {
                't': inputs['plate_t'], 
                'w': inputs['plate_w'], 
                'h': inputs['plate_h'], 
                'weld_sz': 6
            }
            bolt_dims = {
                'dia': inputs['bolt_dia'], 
                'n_rows': inputs['n_rows'], 
                'pitch': inputs['pitch'], 
                'lev': inputs['lev'], 
                'leh_beam': inputs['leh_beam']
            }
            config = {
                'setback': 10, 
                'L_beam_show': 400
            }

            try:
                fig_3d = d3.create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig_3d, use_container_width=True)
            except Exception as e:
                st.error(f"Could not render 3D model: {e}")

            st.markdown("---")
            
            # --- 4. แสดงผลการคำนวณแยกตามหัวข้อ ---
            st.markdown("#### 📊 Design Verification")
            
            # วนลูปแสดงผลจากผลลัพธ์ที่ได้
            for key in ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup']:
                item = res[key]
                ratio = item['ratio']
                
                # เลือกสีตาม Ratio
                color = "green" if ratio < 0.9 else "orange" if ratio < 1.0 else "red"
                
                with st.expander(f"{item['title']} (Ratio: {ratio:.2f})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Formula & Substitution**")
                        st.latex(item['formula'])
                        st.latex(rf" = {item['subst']}")
                        st.latex(rf" \therefore R_n = {item['rn']:,.0f} \text{{ kg}}")
                    with c2:
                        st.markdown(f"**Design Capacity ({method})**")
                        if method == "ASD":
                            st.latex(rf"R_a = \frac{{R_n}}{{\Omega}} = \frac{{{item['rn']:,.0f}}}{{{item['sf']}}}")
                        else:
                            st.latex(rf"\phi R_n = {item['sf']} \times {item['rn']:,.0f}")
                        
                        st.metric(
                            label="Capacity", 
                            value=f"{item['design_val']:,.0f} kg", 
                            delta=f"Ratio: {ratio:.2f}",
                            delta_color="inverse" if ratio > 1.0 else "normal"
                        )
                        
                        if ratio > 1.0:
                            st.error("NOT ADEQUATE")
                        else:
                            st.success("PASS")
    else:
        # กรณีที่ยังไม่ได้กด Analyze
        with col_out:
            st.info("💡 ปรับแต่งพารามิเตอร์ทางซ้ายมือแล้วกดปุ่ม **Analyze** เพื่อดูโมเดล 3 มิติ และผลการคำนวณ")
            # โชว์ภาพ Placeholder หรือคำแนะนำเบื้องต้น
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Shear_tab_connection.png/300px-Shear_tab_connection.png", 
                     caption="Typical Shear Tab Connection", width=300)
