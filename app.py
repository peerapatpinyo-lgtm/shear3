import streamlit as st
from database import SYS_H_BEAMS
from calculator import core_calculation

# Import Modules
from tab1_details import render_tab1
from tab2_graph import render_tab2
from tab3_capacity import render_tab3
from tab4_summary import render_tab4
from tab5_saved import render_tab5    # Timeline/List Analysis (Tab 5 เดิม)
from tab6_design import render_tab6   # Manual Check
from tab7_typical import render_tab7  # [NEW] Typical Detail Summary

# --- Config ---
st.set_page_config(page_title="SYS Structural Report", layout="wide")
st.title("🏗️ SYS H-Beam: Professional Design Tool")

# --- Sidebar ---
with st.sidebar:
    st.header("1. Design Criteria")
    method = st.radio("Method", ["ASD", "LRFD"])
    Fy = st.number_input("Fy (Yield Strength) [ksc]", value=2400)
    E_gpa = st.number_input("E (Modulus) [GPa]", value=200)
    
    st.write("---")
    st.write("**Deflection Limit:**")
    def_option = st.selectbox("Select Limit", 
                              ["L/360 (General/Floor)", "L/240 (Roof)", "L/180 (Industrial)"], 
                              index=0)
    def_val = int(def_option.split('/')[1].split()[0])
    
    st.header("2. Single Section Analysis")
    sort_list = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    section = st.selectbox("Select Size to Analyze", sort_list, index=8)
    L_input = st.slider("Span Length (m)", 2.0, 30.0, 6.0, 0.5)

# --- Process ---
props = SYS_H_BEAMS[section]
c = core_calculation(L_input, Fy, E_gpa, props, method, def_val)
final_w = min(c['ws'], c['wm'], c['wd'])

# --- Display Tabs ---
# [UPDATE] เพิ่ม Tab 7
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "📝 Detail Report", 
    "📊 Behavior Graph", 
    "📋 Capacity Table",
    "📚 Master Catalog",
    "📊 Timeline Analysis",
    "🛠️ Manual Check",
    "🔩 Typical Detail" # [NEW] Tab 7
])

# Render Tab 1: Details
with t1:
    render_tab1(c, props, method, Fy, section)

# Render Tab 2: Graph
with t2:
    render_tab2(c, props, section, L_input, def_val, final_w)

# Render Tab 3: Capacity
with t3:
    render_tab3(props, method, Fy, E_gpa, section, def_val)

# Render Tab 4: Catalog
with t4:
    render_tab4(method, Fy, E_gpa, def_val)

# Render Tab 5: Timeline Analysis (Original Logic)
with t5:
    render_tab5(method, Fy, E_gpa, def_val)

# Render Tab 6: Manual Connection Design
with t6:
    render_tab6(method, Fy, E_gpa, def_val)

# Render Tab 7: Typical Detail Summary (Auto Run 75%)
with t7:
    render_tab7(method, Fy, E_gpa, def_val)
