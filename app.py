import streamlit as st

# ==========================================
# 📦 IMPORT MODULES
# ==========================================
# Import หน้าจอแยกแต่ละ Tab
from tab1_details import render_tab1
from tab2_load import render_tab2       # [NEW] Load Analysis
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
# 🎨 SIDEBAR: GLOBAL SETTINGS
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/steel-i-beam.png", width=64)
    st.title("Project Config")
    
    # Project Details
    st.text_input("Project Name", value="Warehouse A")
    st.text_input("Engineer", value="Eng. Somsak")
    
    st.markdown("---")
    
    # Design Method (ส่งค่าไปใช้ใน Tab 6)
    method = st.radio("Design Method", ["ASD", "LRFD"], index=0)
    
    st.markdown("---")
    st.caption("v1.2.0 | Modular Architecture")

# ==========================================
# 📑 MAIN TABS LOGIC
# ==========================================
# สร้าง Tabs ทั้งหมด 6 หัวข้อ
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Details", 
    "📊 Load Analysis", 
    "🏗️ Capacity Check", 
    "📑 Summary", 
    "📦 BOQ", 
    "🔩 Connection"
])

# --- TAB 1: Geometric & Material Inputs ---
with tab1:
    # รับค่า Beam, Fy, E, Deflection Limit, Span จาก Tab 1
    # ตรวจสอบว่า tab1_details.py คืนค่าครบ 5 ตัวแปรหรือไม่
    try:
        selected_beam, Fy, E_gpa, def_limit, L_span = render_tab1()
    except Exception as e:
        st.error(f"Error loading Tab 1: {e}")
        st.stop()

# --- TAB 2: Load Analysis (New!) ---
with tab2:
    # เรียกใช้ไฟล์ใหม่ tab2_load.py
    # รับค่า Moment (Mu) และ Shear (Vu) ที่คำนวณได้กลับมา
    Mu_cal, Vu_cal = render_tab2()

# --- TAB 3: Capacity Calculation ---
with tab3:
    # ส่งข้อมูล Beam และ Material ไปคำนวณ Capacity
    render_tab3(selected_beam, Fy, E_gpa, L_span)

# --- TAB 4: Summary Report ---
with tab4:
    # ส่งข้อมูลทั้งหมดไปสรุปผล (Beam + Load)
    # หมายเหตุ: หากไฟล์ tab4_summary.py ของคุณยังไม่รับค่า Mu, Vu 
    # Python อาจแจ้ง error ตรงนี้ ให้แก้เป็น render_tab4(selected_beam, Fy, E_gpa, L_span) ชั่วคราว
    try:
        render_tab4(selected_beam, Fy, E_gpa, L_span, Mu_cal, Vu_cal)
    except TypeError:
        # Fallback กรณีไฟล์ tab4 เก่ายังไม่รับค่า Load
        render_tab4(selected_beam, Fy, E_gpa, L_span)

# --- TAB 5: BOQ (Placeholder) ---
with tab5:
    st.info("📦 Bill of Quantities (Work in Progress)")
    st.markdown("""
    - Steel Weight Calculation
    - Painting Area
    - Bolt Count
    """)

# --- TAB 6: Connection Design ---
with tab6:
    # ส่ง Method (ASD/LRFD) และค่า Material ไปออกแบบ Connection
    render_tab6(method, Fy, E_gpa, def_limit)
