import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บให้เต็มจอ (ต้องอยู่บรรทัดแรกสุดของ Streamlit) ---
st.set_page_config(page_title="SYS Beam Design", layout="wide")

# --- 2. ฐานข้อมูลหน้าตัดเหล็ก SYS ---
SYS_H_BEAMS = {
    "H-100x50x5x7":     {"W": 9.3,  "D": 100, "tw": 5,   "Ix": 378,    "Zx": 75.6},
    "H-100x100x6x8":    {"W": 17.2, "D": 100, "tw": 6,   "Ix": 383,    "Zx": 76.5},
    "H-125x60x6x8":     {"W": 13.2, "D": 125, "tw": 6,   "Ix": 847,    "Zx": 136},
    "H-150x75x5x7":     {"W": 14.0, "D": 150, "tw": 5,   "Ix": 1050,   "Zx": 140},
    "H-150x150x7x10":   {"W": 31.5, "D": 150, "tw": 7,   "Ix": 1640,   "Zx": 219},
    "H-175x90x5x8":     {"W": 18.1, "D": 175, "tw": 5,   "Ix": 2040,   "Zx": 233},
    "H-200x100x5.5x8":  {"W": 21.3, "D": 200, "tw": 5.5, "Ix": 1840,   "Zx": 184},
    "H-200x200x8x12":   {"W": 49.9, "D": 200, "tw": 8,   "Ix": 4720,   "Zx": 472},
    "H-250x125x6x9":    {"W": 29.6, "D": 250, "tw": 6,   "Ix": 4050,   "Zx": 324},
    "H-250x250x9x14":   {"W": 72.4, "D": 250, "tw": 9,   "Ix": 10800,  "Zx": 867},
    "H-300x150x6.5x9":  {"W": 36.7, "D": 300, "tw": 6.5, "Ix": 7210,   "Zx": 481},
    "H-300x300x10x15":  {"W": 94.0, "D": 300, "tw": 10,  "Ix": 20400,  "Zx": 1360},
    "H-350x175x7x11":   {"W": 49.6, "D": 350, "tw": 7,   "Ix": 13600,  "Zx": 775},
    "H-400x200x8x13":   {"W": 66.0, "D": 400, "tw": 8,   "Ix": 23700,  "Zx": 1190},
    "H-400x400x13x21":  {"W": 172.0,"D": 400, "tw": 13,  "Ix": 66600,  "Zx": 3330},
    "H-500x200x10x16":  {"W": 89.6, "D": 500, "tw": 10,  "Ix": 47800,  "Zx": 1910},
    "H-600x200x11x17":  {"W": 106.0,"D": 600, "tw": 11,  "Ix": 77600,  "Zx": 2590},
}

# --- 3. ฟังก์ชันคำนวณ (Core Logic) ---
def calculate_capacities(lengths, Fy_ksc, E_gpa, props, method):
    # ตัวแปรคงที่และแปลงหน่วย
    g = 9.81
    E = E_gpa * 1e9         
    Ix = props['Ix'] * 1e-8 
    Zx = props['Zx'] * 1e-6 
    Aw = (props['D']/1000) * (props['tw']/1000) 
    Fy_pa = Fy_ksc * 98066.5
    
    # 1. Nominal Strengths (กำลังต้านทานระบุ - เหมือนกันทั้ง 2 วิธี)
    Vn = 0.60 * Fy_pa * Aw  
    Mn = Fy_pa * Zx         
    
    # 2. Apply Factors (จุดต่างสำคัญ)
    if method == "ASD":
        # ASD: หารด้วย Safety Factor
        V_cap = Vn / 1.50 
        M_cap = Mn / 1.67 
    else:
        # LRFD: คูณด้วย Resistance Factor
        V_cap = 1.00 * Vn
        M_cap = 0.90 * Mn

    # 3. วนลูปสร้างข้อมูลกราฟ
    w_shear_list = []
    w_moment_list = []
    w_deflect_list = []
    
    for L in lengths:
        if L == 0: 
            w_shear_list.append(None)
            continue
        
        # Load Capacity (w)
        w_s = (2 * V_cap) / L
        w_m = (8 * M_cap) / (L**2)
        
        # Deflection (ใช้ Service Load เสมอ)
        delta_lim = L / 360.0
        w_d = (384 * E * Ix * delta_lim) / (5 * L**4)
        
        w_shear_list.append(w_s / g)   
        w_moment_list.append(w_m / g)
        w_deflect_list.append(w_d / g)

    return np.array(w_shear_list), np.array(w_moment_list), np.array(w_deflect_list), Vn, Mn

# --- 4. ส่วนหน้าจอ UI (Sidebar) ---
st.title("🏗️ SYS H-Beam Design: ASD vs LRFD")

st.sidebar.header("⚙️ ตั้งค่าการคำนวณ")
# เลือกวิธีการคำนวณ
method = st.sidebar.radio("1. เลือกวิธีออกแบบ (Method):", ["ASD", "LRFD"])

# เลือกหน้าตัด
section_name = st.sidebar.selectbox("2. เลือกหน้าตัด (Section):", list(SYS_H_BEAMS.keys()))
props = SYS_H_BEAMS[section_name]

# ใส่ค่าวัสดุและระยะ
Fy = st.sidebar.number_input("Fy (ksc):", value=2400)
E_val_gpa = st.sidebar.number_input("E (GPa):", value=200)
L_input = st.sidebar.slider("ความยาวคาน L (m):", 1.0, 24.0, 6.0, 0.5)

# --- 5. ประมวลผล (Processing) ---
max_graph_len = max(24.0, L_input * 1.5)
L_range = np.linspace(0.5, max_graph_len, 300)
w_s, w_m, w_d, Vn_raw, Mn_raw = calculate_capacities(L_range, Fy, E_val_gpa, props, method)

# คำนวณ Net Safe Load
w_safe = np.minimum(np.minimum(w_s, w_m), w_d) - props['W']
w_safe = np.maximum(w_safe, 0)
w_total_safe = w_safe + props['W']

# หาค่าที่จุด L ปัจจุบันเพื่อแสดงผลตัวเลข
cur_idx = (np.abs(L_range - L_input)).argmin()
res_w_s = w_s[cur_idx]
res_w_m = w_m[cur_idx]
res_w_d = w_d[cur_idx]

# เตรียมตัวแปรสำหรับแสดงในสมการ
Vn_kg = Vn_raw / 9.81
Mn_kgcm = (Mn_raw / 9.81) * 100
Aw_cm2 = (props['D'] * props['tw']) / 100
Zx_cm3 = props['Zx']

# --- 6. แสดงผล Tabs ---
tab1, tab2 = st.tabs(["📊 กราฟ (Chart)", "📝 รายการคำนวณ (Calculation)"])

# ===== TAB 1: กราฟ =====
with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=L_range, y=w_s, name=f'Shear ({method})', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_m, name=f'Moment ({method})', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=L_range, y=w_total_safe, name='Capacity', line=dict(color='black', width=4)))
    
    # จุดปัจจุบัน
    fig.add_trace(go.Scatter(x=[L_input], y=[w_total_safe[cur_idx]], mode='markers', marker=dict(size=12, color='blue'), name='Current Length'))
    
    y_label = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load (kg/m)"
    fig.update_layout(height=500, xaxis_title="Length (m)", yaxis_title=y_label, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 2: รายการคำนวณ =====
with tab2:
    st.markdown(f"## รายการคำนวณแบบ: **{method}**")
    st.markdown(f"**Section:** {section_name} | **Length:** {L_input} m | **Fy:** {Fy} ksc")
    
    # -------------------------------------------------------------
    # แยก Logic การแสดงผล ASD และ LRFD ออกจากกัน 100%
    # -------------------------------------------------------------
    
    if method == "ASD":
        # >>>>>>>>>>>> ส่วนของ ASD <<<<<<<<<<<<<<<
        st.success("📌 **โหมด ASD:** ใช้ Safety Factor ($\Omega$) หารค่ากำลังระบุ")
        
        # 1. SHEAR
        st.markdown("### 1. แรงเฉือน (Shear Check - ASD)")
        st.latex(r"V_n = 0.60 F_y A_w")
        st.write(f"Nominal Strength ($V_n$): {Vn_kg:,.0f} kg")
        
        st.latex(r"V_{allow} = \frac{V_n}{\Omega_v} = \frac{V_n}{1.50}") # สูตรหาร
        st.latex(rf"V_{{allow}} = \frac{{{Vn_kg:,.0f}}}{{1.50}} = \mathbf{{{Vn_kg/1.50:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{shear}} = \frac{{2 V_{{allow}}}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")
        
        # 2. MOMENT
        st.markdown("### 2. โมเมนต์ดัด (Moment Check - ASD)")
        st.latex(r"M_n = F_y Z_x")
        st.write(f"Nominal Strength ($M_n$): {Mn_kgcm:,.0f} kg-cm")
        
        st.latex(r"M_{allow} = \frac{M_n}{\Omega_b} = \frac{M_n}{1.67}") # สูตรหาร
        st.latex(rf"M_{{allow}} = \frac{{{Mn_kgcm:,.0f}}}{{1.67}} = \mathbf{{{Mn_kgcm/1.67:,.0f}}} \text{{ kg-cm}}")
        st.latex(rf"w_{{moment}} = \frac{{8 M_{{allow}}}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    else:
        # >>>>>>>>>>>> ส่วนของ LRFD <<<<<<<<<<<<<<<
        st.error("📌 **โหมด LRFD:** ใช้ Resistance Factor ($\phi$) คูณค่ากำลังระบุ")
        
        # 1. SHEAR
        st.markdown("### 1. แรงเฉือน (Shear Check - LRFD)")
        st.latex(r"V_n = 0.60 F_y A_w")
        st.write(f"Nominal Strength ($V_n$): {Vn_kg:,.0f} kg")
        
        st.latex(r"V_u = \phi_v V_n = 1.00 \cdot V_n") # สูตรคูณ
        st.latex(rf"V_u = 1.00 \times {Vn_kg:,.0f} = \mathbf{{{Vn_kg:,.0f}}} \text{{ kg}}")
        st.latex(rf"w_{{u,shear}} = \frac{{2 V_u}}{{L}} = \mathbf{{{res_w_s:,.0f}}} \text{{ kg/m}}")
        
        st.markdown("---")
        
        # 2. MOMENT
        st.markdown("### 2. โมเมนต์ดัด (Moment Check - LRFD)")
        st.latex(r"M_n = F_y Z_x")
        st.write(f"Nominal Strength ($M_n$): {Mn_kgcm:,.0f} kg-cm")
        
        st.latex(r"M_u = \phi_b M_n = 0.90 \cdot M_n") # สูตรคูณ
        st.latex(rf"M_u = 0.90 \times {Mn_kgcm:,.0f} = \mathbf{{{0.90*Mn_kgcm:,.0f}}} \text{{ kg-cm}}")
        st.latex(rf"w_{{u,moment}} = \frac{{8 M_u}}{{L^2}} = \mathbf{{{res_w_m:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # 3. DEFLECTION (เหมือนกันทั้งคู่)
    st.markdown("### 3. การแอ่นตัว (Deflection Check)")
    st.info("ใช้ Service Load ตรวจสอบที่เกณฑ์ L/360")
    st.latex(rf"w_{{deflect}} = \mathbf{{{res_w_d:,.0f}}} \text{{ kg/m}}")

    st.markdown("---")
    
    # 4. สรุป
    gov_val = w_total_safe[cur_idx]
    st.success(f"✅ **ความสามารถในการรับน้ำหนัก (Governing Capacity): {gov_val:,.0f} kg/m**")
    st.write(f"*(หักน้ำหนักคาน {props['W']} kg/m ออกแล้ว เหลือ Safe Load สุทธิ = {max(gov_val - props['W'], 0):,.0f} kg/m)*")
