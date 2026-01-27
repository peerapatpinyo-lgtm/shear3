import streamlit as st

# ==========================================
# 📦 IMPORT MODULES
# ==========================================
from database import SYS_H_BEAMS
from calculator import calculate_capacity

from tab1_details import render_tab1
from tab2_load import render_tab2
from tab3_capacity import render_tab3
from tab4_summary import render_tab4
from tab6_design import render_tab6

# ==========================================
# ⚙️ PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Structural Steel Design",
    page_icon="🏗️",
    layout="wide"
)

# ==========================================
# 🎨 SIDEBAR: GLOBAL INPUTS (MOVED HERE)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/steel-i-beam.png", width=64)
    st.title("Project Config")
    
    # --- 1. General Info ---
    st.text_input("Project Name", value="Warehouse A")
    st.text_input("Engineer", value="Eng. Somsak")
    st.markdown("---")
    
    # --- 2. Design Method ---
    method = st.radio("Design Method", ["ASD", "LRFD"], index=0)
    st.markdown("---")

    # --- 3. Material Properties ---
    st.markdown("### 🧱 Material")
    Fy = st.number_input("Yield Strength (Fy) [ksc]", value=2500.0, step=100.0)
    E_gpa = st.number_input("Elastic Modulus (E) [GPa]", value=200.0, step=10.0)
    
    # --- 4. Geometry ---
    st.markdown("### 📏 Geometry")
    L_span = st.number_input("Beam Span Length (L) [m]", value=6.0, step=0.5)
    
    def_limit_options = {"L/360": 360, "L/240": 240, "L/180": 180}
    def_key = st.selectbox("Deflection Limit", list(def_limit_options.keys()))
    def_limit = def_limit_options[def_key]

    # --- 5. Section Selection ---
    st.markdown("### 📐 Section")
    beam_names = list(SYS_H_BEAMS.keys())
    selected_beam_name = st.selectbox("Select H-Beam (JIS)", beam_names, index=0)
    
    # Load Beam Props immediately
    selected_beam = SYS_H_BEAMS[selected_beam_name]
    selected_beam['name'] = selected_beam_name
    
    st.markdown("---")
    st.caption("v1.3.0 | Sidebar Input Architecture")

# ==========================================
# 🧠 MAIN CALCULATION (Pre-process)
# ==========================================
# คำนวณ Capacity รอไว้เลย เพราะ Tab 1 ต้องการใช้ค่านี้ทันที
c = calculate_capacity(selected_beam, L_span, Fy, E_gpa, method, def_limit)

# ==========================================
# 📑 MAIN TABS LOGIC
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Details", 
    "📊 Load Analysis", 
    "🏗️ Capacity Check", 
    "📑 Summary", 
    "📦 BOQ", 
    "🔩 Connection"
])

# --- TAB 1: Details Report (User's Preferred View) ---
with tab1:
    # ส่งค่า 5 ตัวที่ฟังก์ชันต้องการ: c, props, method, Fy, section
    render_tab1(c, selected_beam, method, Fy, selected_beam_name)

# --- TAB 2: Load Analysis ---
with tab2:
    Mu_cal, Vu_cal = render_tab2()

# --- TAB 3: Capacity Calculation ---
with tab3:
    # ส่งค่าที่คำนวณแล้ว หรือตัวแปรไปให้ Tab 3
    # หมายเหตุ: หาก Tab 3 เขียนแบบรับ Input เอง อาจต้องปรับเล็กน้อย
    # แต่ปกติถ้า Tab 3 รับ arguments ก็ส่งไปได้เลย
    render_tab3(selected_beam, Fy, E_gpa, L_span)

# --- TAB 4: Summary Report ---
with tab4:
    try:
        render_tab4(selected_beam, Fy, E_gpa, L_span, Mu_cal, Vu_cal)
    except:
        render_tab4(selected_beam, Fy, E_gpa, L_span)

# --- TAB 5: BOQ ---
with tab5:
    st.info("📦 Bill of Quantities (Work in Progress)")

# --- TAB 6: Connection Design ---
with tab6:
    render_tab6(method, Fy, E_gpa, def_limit)
