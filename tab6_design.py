import streamlit as st
from database import SYS_H_BEAMS
import calculator_tab as calc
import drawer_3d as d3

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    if section_name not in SYS_H_BEAMS: 
        section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    
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
            run = st.form_submit_button("Analyze & Render 3D", type="primary")

    if run:
        inputs = {
            'method': method, 'load': Vu, 'plate_mat': 'SS400',
            'plate_t': tp_input, 
            'plate_h': (2 * 35) + ((n_rows - 1) * 70), 
            'plate_w': 100,
            'beam_fy': Fy, 'beam_tw': beam.get('tw', 6.0),
            'bolt_dia': db_input, 'bolt_grade': 'A325', 
            'n_rows': n_rows, 'pitch': 70, 'lev': 35, 'leh_beam': 35
        }
        
        res = calc.calculate_shear_tab(inputs)
        
        if res.get('critical_error'):
            st.error("🛑 **Geometry Failure:**")
            for err in res['errors']: st.warning(err)
            st.stop()

        with col_out:
            # --- 3D Visualization ---
            st.markdown("#### 🧊 3D Connection Visualization")
            beam_dims = {'H': beam['D'], 'B': beam['B'], 'Tw': beam['tw'], 'Tf': beam['tf']}
            plate_dims = {'t': tp_input, 'w': 100, 'h': inputs['plate_h'], 'weld_sz': 6}
            bolt_dims = {'dia': db_input, 'n_rows': n_rows, 'pitch': 70, 'lev': 35, 'leh_beam': 35}
            config = {'setback': 10, 'L_beam_show': 400}
            
            try:
                fig_3d = d3.create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig_3d, use_container_width=True)
            except Exception as e:
                st.error(f"Render Error: {e}")

            st.markdown("---")
            st.markdown("#### 📊 Design Verification")
            
            # --- [NEW] Loop includes 'block_shear' ---
            check_list = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup', 'block_shear']
            
            for key in check_list:
                item = res[key]
                ratio = item['ratio']
                
                with st.expander(f"{item['title']} (Ratio: {ratio:.2f})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Formula & Substitution**")
                        st.latex(item['formula'])
                        # [LaTeX Formatting Fix]
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
                        if ratio > 1.0: st.error("NOT ADEQUATE")
                        else: st.success("PASS")
    else:
        with col_out:
            st.info("💡 Select parameters and click Analyze")
