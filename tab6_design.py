#tab6_design.py
import streamlit as st
import pandas as pd
import numpy as np
import math
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure
import calculator_tab as calc

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_max_rows(beam_d, beam_tf, k_dist, margin_top, margin_bot, pitch, lev):
    workable_depth = beam_d - (2 * k_dist)
    available_h = beam_d - (2 * beam_tf) - margin_top - margin_bot
    if available_h <= (2 * lev): return 0
    max_n = int(((available_h - (2 * lev)) / pitch) + 1)
    return max(0, max_n)

def get_material_Fu(Fy):
    if Fy <= 2500: return 4000
    elif Fy <= 3000: return 4500
    else: return 5000

def calculate_beam_shear_capacity(beam, Fy, method):
    d_mm = beam['D']
    tw_mm = beam.get('t1', 6.0)
    Aw = (d_mm * tw_mm) / 100.0
    Vn = 0.6 * Fy * Aw
    if method == "ASD": return Vn / 1.67
    else: return 0.9 * Vn

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

def get_min_weld_size(part_t_mm):
    if part_t_mm <= 6: return 3
    elif part_t_mm <= 13: return 5
    elif part_t_mm <= 19: return 6
    else: return 8

def calculate_eccentric_weld(load_kg, e_mm, L_mm, weld_sz_mm, method):
    e_cm = e_mm / 10.0
    L_cm = L_mm / 10.0
    w_cm = weld_sz_mm / 10.0
    te = 0.707 * w_cm
    Aw = 2 * (te * L_cm)
    Sw = (te * (L_cm**2)) / 3.0
    fv = load_kg / Aw
    Moment = load_kg * e_cm
    fb = Moment / Sw
    fr = math.sqrt(fv**2 + fb**2)
    Fexx = 4921
    Fnw = 0.6 * Fexx
    if method == "ASD": F_limit = Fnw / 2.00
    else: F_limit = 0.75 * Fnw
    cap_load = (F_limit / fr) * load_kg if fr > 0 else 0
    ratio = fr / F_limit if F_limit > 0 else 999
    return {
        'title': 'Weld (Eccentric Check)',
        'capacity': cap_load, 'ratio': ratio,
        'ref': 'AISC Part 8', 'latex_eq': r'f_r \leq \phi F_{nw}',
        'calcs': [f"e={e_mm}mm, fr={fr:.2f} ksc"]
    }

def calculate_web_bearing(load_kg, d_b, n_bolts, tw_mm, Fy, method):
    Fu = get_material_Fu(Fy)
    rn_per_bolt = 2.4 * (d_b/10.0) * (tw_mm/10.0) * Fu
    Rn_total = rn_per_bolt * n_bolts
    if method == "ASD": cap = Rn_total / 2.00
    else: cap = 0.75 * Rn_total
    ratio = load_kg / cap
    return {
        'title': 'Bearing on Beam Web',
        'capacity': cap, 'ratio': ratio,
        'ref': 'AISC J3.10', 'latex_eq': r'R_n = n \times 2.4 d t_w F_u',
        'calcs': [f"Web Tw={tw_mm}mm, Cap={cap:.0f} kg"]
    }

# ==========================================
# MAIN RENDERER
# ==========================================
def render_tab6(method, Fy, E_gpa, def_limit, section_name, span_m):
    st.markdown(f"### 🏗️ Shear Plate Design ({method})")
    
    if section_name not in SYS_H_BEAMS:
        section_name = list(SYS_H_BEAMS.keys())[0]
    beam = SYS_H_BEAMS[section_name]
    
    # Dimensions
    d_factor = 10 if beam['D'] < 100 else 1
    bm_D = beam['D'] * d_factor
    bm_Tw = beam.get('t1', 6.0)
    bm_Tf = beam.get('t2', 9.0)
    k_des = 30
    
    col1, col2 = st.columns([1.3, 2.5])
    
    with col1:
        with st.expander("Design Input", expanded=True):
            st.info(f"Beam: {section_name}")
            beam_cap = calculate_beam_shear_capacity(beam, Fy, method)
            load_opt = st.radio("Load:", ["Auto (75%)", "Manual"], horizontal=True)
            if "Auto" in load_opt:
                Vu = 0.75 * beam_cap
                st.write(f"Load: {Vu:,.0f} kg")
            else:
                Vu = st.number_input("Load (kg)", value=5000.0)
            
            mat = st.selectbox("Plate Mat", ["SS400", "A36", "A572-50"])
            
            c1, c2 = st.columns(2)
            bolt_d_str = c1.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            bolt_gr = c2.selectbox("Grade", ["A325", "A490", "Gr.8.8"])
            db = float(bolt_d_str.replace("M",""))
            
            pitch = st.number_input("Pitch", value=int(3*db))
            lev = st.number_input("V-Edge", value=int(1.5*db))
            
            max_r = get_max_rows(bm_D, bm_Tf, k_des, 10, 10, pitch, lev)
            rows = st.number_input("Rows", 2, max(2, max_r), 3)
            
            setback = st.slider("Setback", 0, 25, 12)
            leh = st.number_input("H-Edge", value=40)
            
            c3, c4 = st.columns(2)
            tp = c3.selectbox("Thick", [6,9,10,12,16,20], index=2)
            weld = c4.selectbox("Weld", [4,6,8,10], index=1)
            
            min_w = setback + leh + int(1.25*db)
            pl_w = st.selectbox("Width", [min_w, min_w+10, 100, 125, 150], index=0)
            pl_h = (2*lev) + ((rows-1)*pitch)

    # Calculation
    inputs = {
        'method': method, 'load': Vu,
        'beam_tw': bm_Tw, 'beam_mat': mat,
        'plate_t': tp, 'plate_h': pl_h, 'plate_mat': mat,
        'bolt_dia': db, 'bolt_grade': bolt_gr,
        'n_rows': rows, 'pitch': pitch,
        'lev': lev, 'leh': leh, 'weld_sz': weld
    }
    
    try:
        results = calc.calculate_shear_tab(inputs)
    except Exception as e:
        st.error(f"Calc Error: {e}")
        return

    # Extra Checks
    ecc_chk = calculate_eccentric_weld(Vu, max(0, pl_w-leh), pl_h, weld, method)
    web_chk = calculate_web_bearing(Vu, db, rows, bm_Tw, Fy, method)
    
    results['weld_ecc'] = ecc_chk
    results['web_bearing'] = web_chk
    
    # Summary
    all_r = [results[k]['ratio'] for k in results if 'ratio' in results[k]]
    all_r.append(ecc_chk['ratio'])
    all_r.append(web_chk['ratio'])
    max_r = max(all_r)
    status = "PASS" if max_r <= 1.0 else "FAIL"
    color = "green" if status == "PASS" else "red"
    
    with col2:
        st.markdown(f"### Status: :{color}[{status}] (Ratio {max_r:.2f})")
        
        tab_list = ["Engineering Check", "Drawing"]
        t1, t2 = st.tabs(tab_list)
        
        with t1:
            # Display Checks
            check_order = ['bolt_shear', 'bearing', 'web_bearing', 'shear_yield', 'shear_rupture', 'weld', 'weld_ecc']
            for k in check_order:
                if k in results:
                    r = results[k]
                    icon = "✅" if r['ratio']<=1.0 else "❌"
                    with st.expander(f"{icon} {r['title']} (Ratio: {r['ratio']:.2f})"):
                        st.latex(r.get('latex_eq', ''))
                        st.write(f"Capacity: {r['capacity']:,.0f} kg")
                        if 'calcs' in r:
                            for c in r['calcs']: st.caption(c)

        with t2:
            st.info("Drawing module loaded")
            # Draw
            beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_Tw, 'Tf': bm_Tf}
            bolt_dims = {'dia': db, 'n_rows': rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
            plate_dims = {'t': tp, 'w': pl_w, 'h': pl_h, 'weld_sz': weld}
            config = {'setback': setback, 'L_beam_show': bm_D*1.5}
            
            try:
                fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
                st.plotly_chart(fig)
            except Exception as e:
                st.warning(f"Plot Error: {e}")
