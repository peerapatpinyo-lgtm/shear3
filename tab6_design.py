# tab6_design.py
import streamlit as st
from database import SYS_H_BEAMS
import calculator_tab as calc

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    # 1. Setup Beam Data
    if section_name not in SYS_H_BEAMS: section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    
    col_in, col_out = st.columns([1, 2])
    
    with col_in:
        with st.form("input_form"):
            Vu = st.number_input("Shear Load (Vu) [kg]", 1000, 50000, 5000)
            db = st.selectbox("Bolt Size", [16, 20, 22, 24], index=1)
            n_rows = st.slider("Number of Rows", 2, 10, 3)
            tp = st.selectbox("Plate Thickness [mm]", [6, 9, 10, 12, 16], index=2)
            run = st.form_submit_button("Analyze", type="primary")

    if run:
        # Calculate Input Logic
        pl_h = (2 * 35) + ((n_rows - 1) * 70) # Simplified geometry
        inputs = {
            'method': method, 'load': Vu, 'plate_mat': 'SS400',
            'plate_t': tp, 'plate_h': pl_h, 'plate_w': 100,
            'beam_fy': Fy, 'beam_tw': beam.get('t1', 6.0),
            'bolt_dia': db, 'bolt_grade': 'A325', 'n_rows': n_rows,
            'pitch': 70, 'lev': 35, 'leh_beam': 35
        }
        
        res = calc.calculate_shear_tab(inputs)
        
        if res.get('critical_error'):
            st.error("Geometry Fail"); st.stop()

        with col_out:
            for key in ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup']:
                item = res[key]
                with st.expander(f"{item['title']} - Ratio: {item['ratio']:.2f}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Formula & Substitution**")
                        st.latex(item['formula'])
                        st.latex(rf" = {item['subst']}")
                        st.latex(rf" \therefore R_n = {item['rn']:,.0f} \text{{ kg}}")
                    with c2:
                        st.markdown(f"**Design Capacity ({method})**")
                        # การใช้ปีกกาซ้อน {{ }} เพื่อป้องกัน SyntaxError ใน f-string
                        if method == "ASD":
                            st.latex(rf"R_a = \frac{{R_n}}{{\Omega}} = \frac{{{item['rn']:,.0f}}}{{{item['sf']}}}")
                        else:
                            st.latex(rf"\phi R_n = {item['sf']} \times {item['rn']:,.0f}")
                        
                        st.metric("Capacity", f"{item['design_val']:,.0f} kg", delta=f"Ratio: {item['ratio']:.2f}")
