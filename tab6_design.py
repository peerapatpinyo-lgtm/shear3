# tab6_design.py
import streamlit as st
import pandas as pd
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc

# ==========================================
# HELPER UI
# ==========================================
def render_gauge_bar(ratio):
    """Render a D/C ratio bar with color coding"""
    color = "green" if ratio < 0.8 else ("orange" if ratio <= 1.0 else "red")
    pct = min(ratio * 100, 100)
    st.markdown(
        f"""
        <div style="background-color: #e0e0e0; border-radius: 5px; width: 100%; height: 10px;">
            <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 5px;"></div>
        </div>
        """, unsafe_allow_html=True
    )

def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Connection Design: Shear Tab ({method})")
    
    # --- 1. SETUP ---
    if section_name not in SYS_H_BEAMS: section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    d_factor = 10 if beam['D'] < 100 else 1 # Adjust for cm/mm DB
    
    col_inp, col_res = st.columns([1, 2])
    
    # --- 2. INPUTS ---
    with col_inp:
        st.info(f"**Section:** {section_name}")
        
        with st.form("design_form"):
            st.markdown("##### 1. Forces")
            Vu_inp = st.number_input("Shear Load (Vu) [kg]", value=5000.0, step=500.0)
            
            st.markdown("##### 2. Bolt Config")
            c1, c2 = st.columns(2)
            db_str = c1.selectbox("Size", ["M16", "M20", "M22", "M24"], index=1)
            grade = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            db = float(db_str.replace("M",""))
            
            c3, c4 = st.columns(2)
            nrows = c3.number_input("Rows", 2, 15, 3)
            pitch = c4.number_input("Pitch", 30, 150, 70)
            
            st.markdown("##### 3. Plate Config")
            c5, c6 = st.columns(2)
            tp = c5.selectbox("Thick (t)", [6,9,10,12,16,19,25], index=2)
            weld = c6.selectbox("Weld", [4,6,8,10], index=1)
            
            c7, c8 = st.columns(2)
            lev = c7.number_input("V-Edge (lev)", 20, 100, 35)
            leh = c8.number_input("H-Edge (leh)", 20, 100, 35)
            
            pl_w = st.number_input("Plate Width", 50, 400, 100)
            setback = st.slider("Setback", 0, 30, 12)
            
            calc_btn = st.form_submit_button("Run Verification", type="primary")

    # --- 3. LOGIC & RESULTS ---
    if calc_btn:
        pl_h = (2*lev) + ((nrows-1)*pitch)
        
        inputs = {
            'method': method, 'load': Vu_inp,
            'plate_mat': 'SS400', 'plate_t': tp, 'plate_h': pl_h, 'plate_w': pl_w,
            'beam_fy': Fy, 'beam_tw': beam.get('t1', beam.get('tw', 6.0)),
            'bolt_dia': db, 'bolt_grade': grade, 'n_rows': nrows,
            'pitch': pitch, 'lev': lev, 'leh_beam': leh,
            'weld_sz': weld
        }
        
        # Call Calculation
        try:
            res = calc.calculate_shear_tab(inputs)
        except Exception as e:
            st.error(f"System Error: {e}")
            return

        with col_res:
            # --- A. GEOMETRY VALIDATION ---
            geo = res.get('geometry', {})
            errs = geo.get('errors', [])
            warns = geo.get('warnings', [])
            
            if errs:
                st.error("⛔ Geometry Violation Found!")
                for e in errs: st.markdown(f"- {e}")
                st.stop() # Stop rendering further
            
            if warns:
                with st.expander("⚠️ Geometry Warnings", expanded=True):
                    for w in warns: st.caption(f"- {w}")

            # --- B. SUMMARY STATUS ---
            # Exclude non-calc keys
            calc_keys = [k for k in res.keys() if k not in ['geometry', 'critical_error']]
            max_r = max([res[k]['ratio'] for k in calc_keys])
            
            status = "PASS" if max_r <= 1.0 else "FAIL"
            s_color = "green" if status == "PASS" else "red"
            
            st.markdown(f"""
            <div style="border: 2px solid {s_color}; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: {s_color}; margin:0;">{status}</h2>
                <p style="margin:0;">Max Utilization Ratio: <b>{max_r:.2f}</b></p>
            </div>
            """, unsafe_allow_html=True)

            # --- C. TABS ---
            tab_rpt, tab_vis = st.tabs(["📝 Engineering Report", "🧊 3D Visualization"])
            
            with tab_rpt:
                st.markdown("#### Detailed Calculation Sheet")
                
                # Check List Order
                order = [
                    'bolt_shear', 'bearing', 
                    'shear_yield', 'shear_rup', 'block_shear', 
                    'flex_yield', 'flex_rup', # New Items
                    'weld'
                ]
                
                for k in order:
                    if k not in res: continue
                    item = res[k]
                    
                    # Row Layout
                    c_icon, c_tit, c_val, c_bar = st.columns([0.5, 3, 1.5, 1.5])
                    
                    ratio = item['ratio']
                    icon = "✅" if ratio <= 1.0 else "❌"
                    
                    with c_icon: st.write(f"### {icon}")
                    with c_tit: 
                        st.markdown(f"**{item['title']}**")
                        st.caption(f"Ref: {item['ref']}")
                    with c_val:
                        st.metric("Ratio", f"{ratio:.2f}", label_visibility="collapsed")
                    with c_bar:
                        st.write("") # Spacer
                        render_gauge_bar(ratio)
                    
                    # Expandable Details
                    with st.expander(f"Show Formula & Calculation"):
                        st.latex(item['eq'])
                        st.markdown("**Substitution:**")
                        st.latex(item['sub'])
                        st.markdown(f"**Capacity:** {item['cap']:,.0f} kg  VS  **Load:** {Vu_inp:,.0f} kg")
                    
                    st.divider()

            with tab_vis:
                # 3D Plotting
                beam_dims = {
                    'H': beam['D']*d_factor, 'B': beam.get('B', 100)*d_factor, 
                    'Tw': inputs['beam_tw'], 'Tf': beam.get('t2', beam.get('tf', 9.0))
                }
                plate_dims = {'t': tp, 'w': pl_w, 'h': pl_h, 'weld_sz': weld}
                bolt_dims = {'dia': db, 'n_rows': nrows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
                config = {'setback': setback, 'L_beam_show': beam['D']*d_factor*1.5}
                
                try:
                    fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning("3D Model unavailable for this config.")

    else:
        st.info("👈 Please Configure Parameters and Click 'Run Verification'")
