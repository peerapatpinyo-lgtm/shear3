# tab6_design.py
import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc

# ==========================================
# HELPER: UI Components
# ==========================================
def get_aisc_min_values(d_b):
    min_spacing = 2.67 * d_b
    pref_spacing = 3.0 * d_b
    if d_b <= 16: min_edge = 22
    elif d_b <= 20: min_edge = 26
    elif d_b <= 22: min_edge = 28
    elif d_b <= 24: min_edge = 30
    elif d_b <= 30: min_edge = 38
    else: min_edge = 1.25 * d_b
    return int(min_edge), round(min_spacing, 1), round(pref_spacing, 1)

def calculate_beam_shear_capacity(beam, Fy, method):
    d_mm = beam['D']
    tw_mm = beam.get('t1') if beam.get('t1') else beam.get('tw', 6.0)
    Aw = (d_mm * tw_mm) / 100.0 
    Vn = 0.6 * Fy * Aw 
    if method == "ASD": return Vn / 1.67
    else: return 0.9 * Vn

# ==========================================
# MAIN RENDERER
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    st.caption("Detailed Calculation according to AISC 360-16 (ASD/LRFD)")
    
    # 1. Prepare Beam Data
    if section_name not in SYS_H_BEAMS: section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    d_factor = 10 if beam['D'] < 100 else 1
    
    bm_D = beam['D'] * d_factor
    bm_Tw = beam.get('t1', beam.get('tw', 6.0))
    bm_Tf = beam.get('t2', beam.get('tf', 9.0))
    bm_B = beam.get('B', 100) * d_factor

    col_l, col_r = st.columns([1.2, 2.0])

    # ==========================================
    # LEFT COLUMN: INPUTS
    # ==========================================
    with col_l:
        with st.expander("🛠️ Design Parameters", expanded=True):
            # A. Load
            st.markdown("##### 1. Load & Beam")
            beam_v_cap = calculate_beam_shear_capacity(beam, Fy, method)
            st.code(f"Beam Shear Cap: {beam_v_cap:,.0f} kg")
            
            load_mode = st.radio("Load Input:", ["Auto (75% of Beam)", "Manual"], horizontal=True, label_visibility="collapsed")
            if "Auto" in load_mode:
                Vu = 0.75 * beam_v_cap
                st.info(f"Design Load ($V_u$): **{Vu:,.0f} kg**")
            else:
                Vu = st.number_input("Design Load (kg)", value=5000.0, step=100.0)

            st.markdown("---")
            
            # B. Connection Config
            st.markdown("##### 2. Plate & Bolts")
            c1, c2 = st.columns(2)
            bolt_str = c1.selectbox("Bolt Size", ["M16", "M20", "M22", "M24"], index=1)
            bolt_gr = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            db = float(bolt_str.replace("M",""))
            
            min_e, min_p, pref_p = get_aisc_min_values(db)
            
            c3, c4 = st.columns(2)
            n_rows = c3.number_input("Rows", 2, 20, 3)
            pitch = c4.number_input("Pitch (mm)", int(min_p), 150, int(max(pref_p, 70)))
            
            c5, c6 = st.columns(2)
            lev = c5.number_input("V-Edge (mm)", int(min_e), 100, 35, help="Vertical Edge Distance")
            leh = c6.number_input("H-Edge (mm)", int(min_e), 100, 35, help="Horizontal Edge Distance (on Beam)")
            
            st.markdown("##### 3. Dimensions")
            c7, c8 = st.columns(2)
            tp = c7.selectbox("Plate T (mm)", [6, 9, 10, 12, 16, 19, 25], index=2)
            weld_sz = c8.selectbox("Weld (mm)", [4, 6, 8, 10, 12], index=1)
            
            # Geometry Calc
            pl_h = (2 * lev) + ((n_rows - 1) * pitch)
            min_w = leh + 50 # minimal clearance
            pl_w = st.number_input("Plate Width (mm)", min_w, 300, min_w + 20)
            
            setback = st.slider("Gap/Setback (mm)", 0, 25, 12)

    # ==========================================
    # RIGHT COLUMN: RESULTS
    # ==========================================
    with col_r:
        # Collect Inputs Dictionary
        calc_inputs = {
            'method': method, 'load': Vu,
            'plate_mat': 'SS400', 'plate_t': tp, 'plate_h': pl_h, 'plate_w': pl_w,
            'beam_fy': Fy, 'beam_tw': bm_Tw,
            'bolt_dia': db, 'bolt_grade': bolt_gr, 'n_rows': n_rows,
            'pitch': pitch, 'lev': lev, 'leh_beam': leh,
            'weld_sz': weld_sz
        }
        
        # ⚠️ CALL CALCULATION
        try:
            res = calc.calculate_shear_tab(calc_inputs)
            
            # Find Max Ratio
            all_ratios = [v['ratio'] for v in res.values()]
            max_r = max(all_ratios)
            status = "PASS" if max_r <= 1.0 else "FAIL"
            status_color = "green" if max_r <= 1.0 else "red"
            
            # Header
            st.title(f"Status: :{status_color}[{status}]")
            st.caption(f"Max Utilization Ratio: {max_r:.2f}")

            # TABS
            tab_eng, tab_3d = st.tabs(["📝 Engineering Report", "🧊 3D Model"])
            
            with tab_eng:
                st.markdown("#### Detailed Calculation Sheet")
                
                check_order = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rup', 'block_shear', 'weld']
                
                for key in check_order:
                    item = res[key]
                    ratio = item['ratio']
                    icon = "✅" if ratio <= 1.0 else "❌"
                    
                    with st.expander(f"{icon} {item['title']} (Ratio: {ratio:.2f})", expanded=(ratio > 1.0)):
                        c_a, c_b = st.columns([2, 1])
                        
                        with c_a:
                            st.markdown(f"**Reference:** {item['ref']}")
                            st.latex(item['formula'])
                            st.markdown(f"**Substitution:**")
                            st.latex(item['subst'])
                            
                        with c_b:
                            st.markdown("**Design Strength:**")
                            st.latex(item['design_eq'])
                            st.metric("Capacity", f"{item['design_val']:,.0f} kg")
                            if ratio > 1.0:
                                st.error(f"Overloaded by {(ratio-1)*100:.1f}%")

            with tab_3d:
                # Prepare Drawing Data
                beam_dims = {'H': bm_D, 'B': bm_B, 'Tw': bm_Tw, 'Tf': bm_Tf}
                plate_dims = {'t': tp, 'w': pl_w, 'h': pl_h, 'weld_sz': weld_sz}
                bolt_dims = {'dia': db, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
                config = {'setback': setback, 'L_beam_show': bm_D*1.5}
                
                try:
                    fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                    st.plotly_chart(fig, use_container_width=True)
                    st.info(f"Plate Size: {pl_w:.0f} x {pl_h:.0f} x {tp} mm")
                except Exception as e:
                    st.error(f"3D Error: {e}")

        except Exception as e:
            st.error(f"Calculation Error: {e}")
