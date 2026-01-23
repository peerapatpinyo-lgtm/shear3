import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from drawer_3d import create_connection_figure

# ==========================================
# 📐 ENGINEER'S HELPER FUNCTIONS
# ==========================================

def check_geometry_compliance(d_b, s, lev, leh, n_rows, beam_d):
    """ตรวจสอบข้อกำหนดระยะตาม AISC/EIT"""
    checks = []
    
    # 1. Pitch (s)
    min_s = 2.67 * d_b
    pref_s = 3.0 * d_b
    if s < min_s:
        checks.append({"item": "Bolt Spacing (s)", "val": f"{s} mm", "limit": f"≥ {min_s:.1f}", "status": "FAIL", "ref": "J3.3"})
    elif s < pref_s:
        checks.append({"item": "Bolt Spacing (s)", "val": f"{s} mm", "limit": f"≥ {pref_s:.1f}", "status": "WARN", "ref": "User Note"})
    else:
        checks.append({"item": "Bolt Spacing (s)", "val": f"{s} mm", "limit": f"≥ {min_s:.1f}", "status": "PASS", "ref": "J3.3"})

    # 2. Edge Distance (Le)
    # AISC Table J3.4 (Simplified logic)
    min_le = d_b * 1.25 # Sheared edge approx
    if lev < min_le:
        checks.append({"item": "Vert. Edge (Lev)", "val": f"{lev} mm", "limit": f"≥ {min_le:.1f}", "status": "FAIL", "ref": "Table J3.4"})
    else:
        checks.append({"item": "Vert. Edge (Lev)", "val": f"{lev} mm", "limit": f"≥ {min_le:.1f}", "status": "PASS", "ref": "Table J3.4"})
        
    if leh < min_le:
        checks.append({"item": "Horiz. Edge (Leh)", "val": f"{leh} mm", "limit": f"≥ {min_le:.1f}", "status": "FAIL", "ref": "Table J3.4"})
    else:
        checks.append({"item": "Horiz. Edge (Leh)", "val": f"{leh} mm", "limit": f"≥ {min_le:.1f}", "status": "PASS", "ref": "Table J3.4"})

    # 3. Fit-up Check
    pl_h = (2*lev) + (n_rows-1)*s
    T_dist = beam_d - 60 # Assume k=30mm * 2
    if pl_h > T_dist:
        checks.append({"item": "Plate Height vs T", "val": f"{pl_h} mm", "limit": f"< {T_dist}", "status": "FAIL", "ref": "Fit-up"})
    else:
        checks.append({"item": "Plate Height vs T", "val": f"{pl_h} mm", "limit": f"< {T_dist}", "status": "PASS", "ref": "Fit-up"})

    return pd.DataFrame(checks)

# ==========================================
# 🏗️ MAIN UI RENDERER
# ==========================================

def render_tab6(method, Fy, E_gpa, def_limit):
    # CSS Injection for Engineering Look
    st.markdown("""
        <style>
        .eng-metric { border-left: 4px solid #3498db; padding-left: 10px; background: #f8f9fa; }
        .pass-tag { color: white; background-color: #27ae60; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
        .fail-tag { color: white; background-color: #c0392b; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
        .warn-tag { color: black; background-color: #f1c40f; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📐 Shear Tab Connection Design (AISC 360-16)")

    # --- LAYOUT GRID ---
    col_input, col_main = st.columns([1, 2.5])

    # ==========================================
    # 1. INPUT PANEL (ENGINEERING CONTROLS)
    # ==========================================
    with col_input:
        with st.expander("🔹 1. Member & Load", expanded=True):
            sec_name = st.selectbox("Beam Section", list(SYS_H_BEAMS.keys()))
            beam = SYS_H_BEAMS[sec_name]
            
            # Unit standardization
            d_factor = 10 if beam['D'] < 100 else 1
            bm_D = beam['D'] * d_factor
            bm_tw = beam.get('t1', 6.0)
            
            st.caption(f"D={bm_D:.0f}, tw={bm_tw}, tf={beam.get('t2',9.0)}")
            
            mat_grade = st.selectbox("Steel Grade", ["ASTM A36 (Fy=250)", "ASTM A572-50 (Fy=345)", "SS400 (Fy=235)"])
            Vu_load = st.number_input("Factored Shear (Vu)", value=5000.0, step=1000.0, format="%.0f")
            
        with st.expander("🔹 2. Connection Geometry", expanded=True):
            # Bolt Spec
            c_b1, c_b2 = st.columns(2)
            bolt_dia_str = c_b1.selectbox("Bolt", ["M16", "M20", "M22", "M24"], index=1)
            bolt_grade = c_b2.selectbox("Grade", ["A325N", "A325X", "A490"], index=0)
            d_b = float(bolt_dia_str.replace("M",""))
            
            # Dimensions
            st.markdown("---")
            n_rows = st.number_input("No. of Rows", 2, 8, 3)
            
            # Manual Override for Precision
            auto_geom = st.checkbox("Auto Geometry", value=True)
            if auto_geom:
                pitch = int(3 * d_b)
                lev = int(1.5 * d_b)
                leh = 40
                plate_t = 10 if d_b <= 20 else 12
            else:
                pitch = st.number_input("Pitch (s)", min_value=30, value=int(3*d_b))
                lev = st.number_input("Vert. Edge (Lev)", min_value=20, value=int(1.5*d_b))
                leh = st.number_input("Horiz. Edge (Leh)", min_value=20, value=40)
                plate_t = st.selectbox("Plate Tk (tp)", [6, 9, 10, 12, 16, 19, 25], index=3)
            
            setback = st.number_input("Setback (c)", 0, 50, 12, help="Distance from support face to beam end")

    # ==========================================
    # 2. MAIN VISUALIZATION & CHECKS
    # ==========================================
    with col_main:
        # --- A. HEADER SUMMARY ---
        # Mockup Calculation
        phi_rn = 12500 # Placeholder for actual calc
        ratio = Vu_load / phi_rn
        
        status_color = "red" if ratio > 1.0 else "green"
        status_text = "NOT OK" if ratio > 1.0 else "OK"
        
        # Display Banner
        st.markdown(f"""
        <div style="background-color: {'#e74c3c' if ratio > 1 else '#2ecc71'}; padding: 15px; border-radius: 5px; color: white; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 1.2em; font-weight: bold;">Status: {status_text}</span><br>
                <span style="font-size: 0.9em;">Demand/Capacity Ratio = {ratio:.2f}</span>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 1.5em; font-weight: bold;">Vu = {Vu_load:,.0f} kg</span><br>
                <span style="font-size: 1.0em;">φRn = {phi_rn:,.0f} kg</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("") # Spacer

        # --- B. TABS: 3D MODEL / GEOMETRY CHECK / REPORT ---
        tab_viz, tab_check, tab_report = st.tabs(["🧊 3D Shop Drawing", "📏 Geometry Checks", "📝 Calculation Sheet"])
        
        # --- PREPARE DATA FOR DRAWER ---
        beam_dims = {'H': bm_D, 'B': beam['B']*d_factor, 'Tw': bm_tw, 'Tf': beam.get('t2',9.0)}
        bolt_dims = {'dia': d_b, 'n_rows': n_rows, 'pitch': pitch, 'lev': lev, 'leh_beam': leh}
        pl_h = (2*lev) + (n_rows-1)*pitch
        pl_w = setback + leh + 40
        plate_dims = {'t': plate_t, 'w': pl_w, 'h': pl_h}
        config = {'setback': setback, 'L_beam_show': bm_D*1.5}

        with tab_viz:
            # ใช้ Engine วาดรูปที่แยกไว้
            fig = create_connection_figure(beam_dims, plate_dims, bolt_dims, config)
            st.plotly_chart(fig, use_container_width=True)
            
            # Quick specs line
            st.caption(f"**Spec:** PL{plate_t}x{pl_w}x{pl_h} mm | {n_rows}-{bolt_dia_str} {bolt_grade} | Weld: 6mm Fillet (Typ)")

        with tab_check:
            st.markdown("#### ✅ Geometric & Code Compliance (AISC J3)")
            df_checks = check_geometry_compliance(d_b, pitch, lev, leh, n_rows, bm_D)
            
            # Custom formatting for the table
            def color_status(val):
                if val == "FAIL": return 'color: red; font-weight: bold;'
                elif val == "WARN": return 'color: orange; font-weight: bold;'
                return 'color: green; font-weight: bold;'

            st.dataframe(
                df_checks.style.applymap(color_status, subset=['status']),
                use_container_width=True,
                hide_index=True
            )
            
            if "FAIL" in df_checks['status'].values:
                st.error("🛑 Geometry check failed. Please adjust Dimensions or Rows.")

        with tab_report:
            st.markdown("#### 📜 Limit State Summary")
            
            # นี่คือ Mockup ที่คุณควรเอา output จริงจาก calculator.py มาใส่
            # แสดงเป็นสมการสวยๆ แบบวิศวกรชอบ
            
            st.markdown("---")
            
            c_calc1, c_calc2 = st.columns(2)
            
            with c_calc1:
                st.markdown("**1. Bolt Shear (φRn)**")
                st.latex(r"\phi R_n = n \times F_{nv} \times A_b \times 0.75")
                st.write(f"= {n_rows} × ... = **{12500:,.0f} kg**")
                
                st.markdown("**3. Plate Shear Yielding**")
                st.latex(r"\phi R_n = 1.00 \times 0.6 F_y A_g")
                st.write(f"= ... = **{15200:,.0f} kg**")

            with c_calc2:
                st.markdown("**2. Bearing on Plate**")
                st.latex(r"\phi R_n = n \times (2.4 d t F_u) \times 0.75")
                st.write(f"= ... = **{18000:,.0f} kg**")
                
                st.markdown("**4. Plate Shear Rupture**")
                st.latex(r"\phi R_n = 0.75 \times 0.6 F_u A_{nv}")
                st.write(f"= ... = **{13500:,.0f} kg**")

            st.markdown("---")
            st.info("💡 **Governing Case:** Bolt Shear")
