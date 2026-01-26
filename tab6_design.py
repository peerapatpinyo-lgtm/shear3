import streamlit as st
import calculator_tab
import drawer_3d

def render_tab6():
    st.markdown("## Shear Tab Connection Design (AISC 360-16)")
    st.info("Design Check: Shear Yield, Shear Rupture, Block Shear, Bolt Shear, Bearing & Tearout")

    # INPUT SECTION
    col1, col2, col3 = st.columns([1, 1, 1.2])

    material_list = ["SS400", "A36", "SM520", "A572-50", "A992"]

    with col1:
        st.markdown("### Beam Data")
        beam_span = st.number_input("Beam Span Length (mm)", value=6000.0, step=500.0)
        beam_d = st.number_input("Beam Depth (mm)", value=400.0, step=10.0)
        beam_b = st.number_input("Beam Width (mm)", value=200.0, step=5.0)
        beam_tw = st.number_input("Web Thickness (mm)", value=8.0, step=0.5)
        beam_tf = st.number_input("Flange Thickness (mm)", value=13.0, step=0.5)
        mat_bm = st.selectbox("Beam Material", material_list, index=0)

        st.markdown("---")
        st.markdown("### Loads")
        Vu_input = st.number_input("Shear Load Vu (kg)", value=15000.0, step=1000.0)
        method = st.radio("Design Method", ["LRFD", "ASD"], horizontal=True)

    with col2:
        st.markdown("### Connection Config")
        # Plate
        st.caption("Plate Properties")
        tp = st.selectbox("Plate Thickness (mm)", [6, 9, 10, 12, 16, 19, 25], index=2)
        h_pl = st.number_input("Plate Height (mm)", value=250.0)
        mat_pl = st.selectbox("Plate Material", material_list, index=0)
        
        # Weld
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            weld_sz = st.number_input("Weld Size (mm)", value=6.0, step=1.0)
        with col_w2:
            electrode = st.selectbox("Electrode", ["E70", "E60"], index=0)
        
        # Bolts
        st.caption("Bolt Properties")
        d_b = st.selectbox("Bolt Diameter (mm)", [12, 16, 20, 22, 24], index=2)
        grade_bolt = st.selectbox("Bolt Grade", ["A325", "A490", "Gr.8.8"], index=0)
        n_rows = st.number_input("No. of Rows", value=3, min_value=1)
        
        # Geometry
        st.caption("Geometry")
        pitch = st.number_input("Pitch (s) [mm]", value=75.0)
        lev = st.number_input("Vertical Edge (Lev) [mm]", value=40.0)
        leh = st.number_input("Horizontal Edge (Leh) [mm]", value=35.0)

    # CALCULATION
    inputs = {
        'method': method,
        'load': Vu_input,
        'beam_d': beam_d,
        'beam_tw': beam_tw,
        'beam_span': beam_span,
        'beam_mat': mat_bm,
        'plate_t': tp,
        'plate_h': h_pl,
        'plate_mat': mat_pl,
        'weld_sz': weld_sz,
        'electrode': electrode,
        'bolt_dia': d_b,
        'bolt_grade': grade_bolt,
        'n_rows': int(n_rows),
        'pitch': pitch,
        'lev': lev,
        'leh': leh
    }

    results = calculator_tab.calculate_shear_tab(inputs)

    # DISPLAY RESULTS
    with col3:
        st.markdown("### Check Results")
        
        status = results['summary']['status']
        util = results['summary']['utilization']
        gov = results['summary']['gov_mode']
        
        # Status Box
        color = "#27ae60" if status == "PASS" else "#c0392b"
        st.markdown(
            f"""
            <div style="background-color: {color}; padding: 15px; border-radius: 8px; color: white; text-align: center; margin-bottom: 15px;">
                <h2 style="margin:0;">{status}</h2>
                <p style="margin:0; font-size: 1.1em;">Ratio: {util:.2f} <br><span style="font-size:0.9em; opacity:0.9">({gov})</span></p>
            </div>
            """, unsafe_allow_html=True
        )

        if results.get('warnings'):
            for warn in results['warnings']:
                st.warning(warn)

        check_list = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'weld']
        
        for key in check_list:
            res = results[key]
            ratio = res['ratio']
            icon = "PASS" if ratio <= 1.0 else "FAIL"
            
            with st.expander(f"[{icon}] {res['title']} (Ratio: {ratio:.2f})"):
                st.latex(res['latex_eq'])
                st.markdown(f"**Capacity:**")
                st.latex(f"{res['latex_sub']} = {res['capacity']:,.0f} kg")

    # 3D VISUALIZATION
    st.markdown("---")
    st.markdown("### 3D Connection Preview")
    
    viz_beam = {'H': beam_d, 'B': beam_b, 'Tw': beam_tw, 'Tf': beam_tf}
    plate_width_est = leh + 50.0 
    viz_plate = {'t': tp, 'w': plate_width_est, 'h': h_pl, 'weld_sz': weld_sz}
    viz_bolt = {
        'dia': d_b, 
        'n_rows': int(n_rows), 
        'pitch': pitch, 
        'lev': lev,
        'leh_beam': leh 
    }
    viz_config = {'setback': 15, 'L_beam_show': 600}
    
    fig = drawer_3d.create_connection_figure(viz_beam, viz_plate, viz_bolt, viz_config)
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_tab6()
