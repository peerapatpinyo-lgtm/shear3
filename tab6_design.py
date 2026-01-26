import streamlit as st
import pandas as pd
import calculator_tab  # ไฟล์คำนวณ (Engine)
import drawer_3d       # ไฟล์วาดรูป (3D Viz)

def render_tab():
    st.markdown("## 🔩 Shear Tab Connection Design (AISC 360-16)")
    st.info("💡 Design Check: Shear Yield, Shear Rupture, Block Shear, Bolt Shear, Bearing & Tearout")

    # ==========================================
    # 1. INPUT SECTION
    # ==========================================
    col1, col2, col3 = st.columns([1, 1, 1.2])

    with col1:
        st.markdown("### 🏗️ Beam Data")
        # รับค่าหน้าตัดคาน (สมมติว่าดึงมาจาก Tab 1 หรือกรอกใหม่)
        beam_d = st.number_input("Beam Depth (mm)", value=400.0, step=10.0)
        beam_b = st.number_input("Beam Width (mm)", value=200.0, step=5.0)
        beam_tw = st.number_input("Web Thickness (mm)", value=8.0, step=0.5)
        beam_tf = st.number_input("Flange Thickness (mm)", value=13.0, step=0.5)
        mat_bm = st.selectbox("Beam Material", ["SS400", "A36", "SM520"], index=0)

        st.markdown("---")
        st.markdown("### 📥 Loads")
        Vu_input = st.number_input("Shear Load Vu (kg)", value=15000.0, step=1000.0)
        method = st.radio("Design Method", ["LRFD", "ASD"], horizontal=True)

    with col2:
        st.markdown("### 🔧 Connection Config")
        # Plate
        st.caption("Plate Properties")
        tp = st.selectbox("Plate Thickness (mm)", [6, 9, 10, 12, 16, 19, 25], index=2)
        h_pl = st.number_input("Plate Height (mm)", value=250.0)
        mat_pl = st.selectbox("Plate Material", ["SS400", "A36", "SM520"], index=0)
        weld_sz = st.number_input("Weld Size (mm)", value=6.0, step=1.0)
        
        # Bolts
        st.caption("Bolt Properties")
        d_b = st.selectbox("Bolt Diameter (mm)", [12, 16, 20, 22, 24], index=2)
        grade_bolt = st.selectbox("Bolt Grade", ["A325", "A490", "Gr.8.8"], index=0)
        n_rows = st.number_input("No. of Rows", value=3, min_value=1)
        
        # Geometry
        st.caption("Geometry")
        pitch = st.number_input("Pitch (s) [mm]", value=75.0)
        lev = st.number_input("Vertical Edge (Lev) [mm]", value=40.0, help="ระยะขอบบนสุดถึงน็อตตัวแรก")
        leh = st.number_input("Horizontal Edge (Leh) [mm]", value=35.0, help="ระยะขอบข้างถึงเซนเตอร์รูเจาะ (สำหรับเช็ค Block Shear)")

    # ==========================================
    # 2. CALCULATION & PROCESSING
    # ==========================================
    # รวบรวม Inputs เป็น Dictionary เพื่อส่งให้ calculator_tab
    inputs = {
        'method': method,
        'load': Vu_input,
        
        # Beam
        'beam_tw': beam_tw,
        'beam_mat': mat_bm,
        
        # Plate
        'plate_t': tp,
        'plate_h': h_pl,
        'plate_mat': mat_pl,
        'weld_sz': weld_sz,
        
        # Bolt & Geom
        'bolt_dia': d_b,
        'bolt_grade': grade_bolt,
        'n_rows': int(n_rows),
        'pitch': pitch,
        'lev': lev,    # ใช้เช็ค Bearing แนวตั้ง (Vertical Edge)
        'leh': leh     # ใช้เช็ค Block Shear (Horizontal Edge)
    }

    # 🔥 เรียกใช้ Engine คำนวณ (calculator_tab.py)
    # ซึ่งข้างในมีฟังก์ชัน calc_bearing_detail ที่เช็ค Lc และ Tearout ให้แล้ว
    results = calculator_tab.calculate_shear_tab(inputs)

    # ==========================================
    # 3. DISPLAY RESULTS
    # ==========================================
    with col3:
        st.markdown("### 📊 Check Results")
        
        # Status Box
        status_color = "green" if results['summary']['status'] == "PASS" else "red"
        st.markdown(
            f"""
            <div style="background-color: {status_color}; padding: 15px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
                <h2 style="margin:0;">{results['summary']['status']}</h2>
                <p style="margin:0;">Ratio: {results['summary']['utilization']:.2f} ({results['summary']['gov_mode']})</p>
            </div>
            """, unsafe_allow_html=True
        )

        # Detailed Breakdown (Loop through results)
        check_list = ['bolt_shear', 'bearing', 'shear_yield', 'shear_rupture', 'block_shear', 'weld']
        
        for key in check_list:
            res = results[key]
            ratio = res['ratio']
            icon = "✅" if ratio <= 1.0 else "❌"
            
            with st.expander(f"{icon} {res['title']} (Ratio: {ratio:.2f})"):
                # แสดงสูตร LaTeX
                st.latex(res['latex_eq'])
                st.latex(f"Capacity = {res['latex_sub']} = {res['capacity']:,.0f} kg")
                
                # แสดงรายละเอียดเพิ่มเติม
                for line in res['calcs']:
                    st.caption(f"- {line}")
                st.markdown(f"**Reference:** {res['ref']}")

    # ==========================================
    # 4. 3D VISUALIZATION
    # ==========================================
    st.markdown("---")
    st.markdown("### 🧊 3D Connection Preview")
    
    # เตรียมข้อมูลสำหรับวาดรูป
    viz_beam = {'H': beam_d, 'B': beam_b, 'Tw': beam_tw, 'Tf': beam_tf}
    viz_plate = {'t': tp, 'w': 100.0, 'h': h_pl, 'weld_sz': weld_sz} # w สมมติ 100 หรือคำนวณจาก Leh
    viz_bolt = {
        'dia': d_b, 
        'n_rows': int(n_rows), 
        'pitch': pitch, 
        'lev': lev,
        'leh_beam': leh # ใช้ Leh ในการวาดตำแหน่งน็อตแนวนอน
    }
    viz_config = {'setback': 15, 'L_beam_show': 600}
    
    # ปรับความกว้าง Plate ให้สัมพันธ์กับ Leh
    # Plate Width = Setback + Leh + Clearance (หรือกำหนดค่าคงที่)
    # ในที่นี้สมมติ: Width = Leh + 40mm (ระยะเจาะถึงขอบเชื่อม)
    viz_plate['w'] = leh + 50.0 
    
    # เรียก drawer_3d
    fig = drawer_3d.create_connection_figure(viz_beam, viz_plate, viz_bolt, viz_config)
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_tab()
