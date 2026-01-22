import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="SYS H-Beam Design: Verified", layout="wide")

# --- 2. DATABASE (Standard JIS/SYS H-Beam) ---
# หน่วย: D, tw (mm) | W (kg/m) | Ix (cm4) | Zx (cm3)
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

# --- 3. CALCULATION ENGINE (PURE METRIC: KG-CM) ---
def calculate_capacities(lengths_m, Fy_ksc, E_gpa, props, method):
    # Convert Units
    E_ksc = E_gpa * 10197.16    # 1 GPa = 10197.16 ksc
    Ix = props['Ix']            # cm4
    Zx = props['Zx']            # cm3 (Plastic Modulus for Mn)
    
    # Area Web for Shear (d * tw) -> Convert mm to cm
    Aw = (props['D'] / 10.0) * (props['tw'] / 10.0) 
    
    # 1. Nominal Strength
    # Shear: Vn = 0.6 * Fy * Aw (AISC 360 Eq. G2-1)
    Vn = 0.60 * Fy_ksc * Aw    
    
    # Moment: Mn = Fy * Zx (AISC 360 Eq. F2-1 for Compact)
    # Note: Assumes Fully Braced (L_b = 0 or sufficient bracing)
    Mn = Fy_ksc * Zx           
    
    # 2. Design Factors
    if method == "ASD":
        # AISC 360 Factors
        Omega_v = 1.50
        Omega_b = 1.67
        V_cap = Vn / Omega_v
        M_cap = Mn / Omega_b
    else:
        # LRFD Factors
        Phi_v = 1.00
        Phi_b = 0.90
        V_cap = Phi_v * Vn
        M_cap = Phi_b * Mn

    # 3. Compute Load for each Length
    w_shear, w_moment, w_deflect = [], [], []
    
    for L_m in lengths_m:
        if L_m == 0: 
            w_shear.append(None)
            continue
            
        L_cm = L_m * 100.0
        
        # Load based on Shear: w = 2V/L
        ws = (2 * V_cap) / L_cm  # kg/cm
        w_shear.append(ws * 100) # kg/m
        
        # Load based on Moment: w = 8M/L^2
        wm = (8 * M_cap) / (L_cm**2) # kg/cm
        w_moment.append(wm * 100)    # kg/m
        
        # Load based on Deflection: w = (384 E I Delta) / (5 L^4)
        # Delta limit = L/360
        delta = L_cm / 360.0
        wd = (384 * E_ksc * Ix * delta) / (5 * (L_cm**4)) # kg/cm
        w_deflect.append(wd * 100) # kg/m

    return np.array(w_shear), np.array(w_moment), np.array(w_deflect), Vn, Mn, Aw, E_ksc

# --- 4. UI SETUP ---
st.title("🏗️ SYS H-Beam Design: Verified (AISC 360/EIT)")

col_ui1, col_ui2 = st.columns([1, 3])
with col_ui1:
    st.subheader("1. Design Inputs")
    method = st.radio("Method:", ["ASD", "LRFD"], help="ASD (Allowable Strength) / LRFD (Load & Resistance Factor)")
    section_name = st.selectbox("Section:", list(SYS_H_BEAMS.keys()))
    props = SYS_H_BEAMS[section_name]
    Fy = st.number_input("Fy (ksc):", value=2400)
    E_gpa = st.number_input("E (GPa):", value=200)
    L_input = st.slider("Span (m):", 1.0, 24.0, 6.0, 0.5)

# --- 5. EXECUTE CALCULATION ---
# Generate Graph Data
L_max = max(15.0, L_input * 1.5)
L_range = np.linspace(0.5, L_max, 200)
w_s, w_m, w_d, Vn, Mn, Aw, E_ksc = calculate_capacities(L_range, Fy, E_gpa, props, method)

# Governing Logic
w_gross = np.minimum(np.minimum(w_s, w_m), w_d)
w_net = np.maximum(w_gross - props['W'], 0)

# Extract Values for Current Span
idx = (np.abs(L_range - L_input)).argmin()
cur_ws, cur_wm, cur_wd = w_s[idx], w_m[idx], w_d[idx]
cur_gov = w_gross[idx]

# --- 6. VISUALIZATION ---
with col_ui2:
    tab_graph, tab_calc = st.tabs(["📊 Capacity Graph", "📝 Step-by-Step Calculation"])

    # ===== TAB 1: GRAPH =====
    with tab_graph:
        y_label = "Allowable Load (kg/m)" if method == "ASD" else "Factored Load Wu (kg/m)"
        fig = go.Figure()
        
        # Curves
        fig.add_trace(go.Scatter(x=L_range, y=w_s, name='Shear Limit', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=w_m, name='Moment Limit', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=L_range, y=w_d, name='Deflection (L/360)', line=dict(color='green', dash='dot')))
        fig.add_trace(go.Scatter(x=L_range, y=w_gross, name='Governing Capacity', line=dict(color='black', width=4)))
        
        # Current Point
        fig.add_trace(go.Scatter(x=[L_input], y=[cur_gov], mode='markers', marker=dict(size=14, color='blue', symbol='x'), name=f'Current @ {L_input}m'))
        
        # Background Zones
        gov_idx = np.argmin([w_s, w_m, w_d], axis=0)
        colors = ['rgba(255,0,0,0.1)', 'rgba(255,165,0,0.1)', 'rgba(0,128,0,0.1)'] # Red, Orange, Green
        labels = ['Shear Control', 'Moment Control', 'Deflection Control']
        
        start_i = 0
        for i in range(1, len(L_range)):
            if gov_idx[i] != gov_idx[i-1] or i == len(L_range)-1:
                fig.add_vrect(x0=L_range[start_i], x1=L_range[i], fillcolor=colors[gov_idx[start_i]], line_width=0, 
                              annotation_text=labels[gov_idx[start_i]], annotation_position="top right")
                start_i = i

        fig.update_layout(height=500, xaxis_title="Span Length (m)", yaxis_title=y_label, hovermode="x unified", margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    # ===== TAB 2: DETAILED CALCULATION =====
    with tab_calc:
        st.markdown(f"#### รายการคำนวณ: **{method} Method**")
        st.caption("อ้างอิงมาตรฐาน AISC 360 / วสท. 1020-59 (Unified Design)")
        
        # Section Properties
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Section", section_name)
        c2.metric("Depth (D)", f"{props['D']} mm")
        c3.metric("Web (tw)", f"{props['tw']} mm")
        c4.metric("Weight", f"{props['W']} kg/m")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Area Web (Aw)", f"{Aw:.2f} cm²")
        c2.metric("Plastic Mod (Zx)", f"{props['Zx']} cm³")
        c3.metric("Inertia (Ix)", f"{props['Ix']:,} cm⁴")
        c4.metric("Modulus E", f"{E_ksc:,.0f} ksc")
        st.divider()

        L_cm = L_input * 100
        
        if method == "ASD":
            # =================== ASD DISPLAY ===================
            st.info("📌 **ASD: Allowable Strength Design** (ใช้ Safety Factor $\Omega$ หาร)")
            
            # 1. SHEAR
            st.markdown("##### 1️⃣ Shear Capacity ($V_n / \Omega_v$)")
            st.write(f"Safety Factor $\Omega_v = 1.50$")
            st.latex(rf"V_n = 0.60 \times F_y \times A_w = 0.60 \times {Fy} \times {Aw:.2f} = {Vn:,.0f} \text{{ kg}}")
            st.latex(rf"V_{{allow}} = \frac{{{Vn:,.0f}}}{{1.50}} = \mathbf{{{Vn/1.50:,.0f}}} \text{{ kg}}")
            st.write("แปลงเป็นน้ำหนักแผ่ ($w = 2V/L$):")
            st.latex(rf"w_{{shear}} = \frac{{2 \times {Vn/1.50:,.0f}}}{{{L_cm:.0f} \text{{ cm}}}} \times 100 = \mathbf{{{cur_ws:,.0f}}} \text{{ kg/m}}")
            
            # 2. MOMENT
            st.markdown("##### 2️⃣ Moment Capacity ($M_n / \Omega_b$)")
            st.write(f"Safety Factor $\Omega_b = 1.67$ (Compact Section)")
            st.latex(rf"M_n = F_y \times Z_x = {Fy} \times {props['Zx']} = {Mn:,.0f} \text{{ kg-cm}}")
            st.latex(rf"M_{{allow}} = \frac{{{Mn:,.0f}}}{{1.67}} = \mathbf{{{Mn/1.67:,.0f}}} \text{{ kg-cm}}")
            st.write("แปลงเป็นน้ำหนักแผ่ ($w = 8M/L^2$):")
            st.latex(rf"w_{{moment}} = \frac{{8 \times {Mn/1.67:,.0f}}}{{{L_cm:.0f}^2}} \times 100 = \mathbf{{{cur_wm:,.0f}}} \text{{ kg/m}}")

        else:
            # =================== LRFD DISPLAY ===================
            st.error("📌 **LRFD: Load & Resistance Factor Design** (ใช้ Factor $\phi$ คูณ)")
            
            # 1. SHEAR
            st.markdown("##### 1️⃣ Shear Capacity ($\phi_v V_n$)")
            st.write(f"Resistance Factor $\phi_v = 1.00$")
            st.latex(rf"V_n = 0.60 \times {Fy} \times {Aw:.2f} = {Vn:,.0f} \text{{ kg}}")
            st.latex(rf"V_u = 1.00 \times {Vn:,.0f} = \mathbf{{{Vn:,.0f}}} \text{{ kg}}")
            st.write("แปลงเป็นน้ำหนักแผ่ ($w_u = 2V_u/L$):")
            st.latex(rf"w_{{shear}} = \frac{{2 \times {Vn:,.0f}}}{{{L_cm:.0f}}} \times 100 = \mathbf{{{cur_ws:,.0f}}} \text{{ kg/m}}")
            
            # 2. MOMENT
            st.markdown("##### 2️⃣ Moment Capacity ($\phi_b M_n$)")
            st.write(f"Resistance Factor $\phi_b = 0.90$")
            st.latex(rf"M_n = {Fy} \times {props['Zx']} = {Mn:,.0f} \text{{ kg-cm}}")
            st.latex(rf"M_u = 0.90 \times {Mn:,.0f} = \mathbf{{{0.90*Mn:,.0f}}} \text{{ kg-cm}}")
            st.write("แปลงเป็นน้ำหนักแผ่ ($w_u = 8M_u/L^2$):")
            st.latex(rf"w_{{moment}} = \frac{{8 \times {0.90*Mn:,.0f}}}{{{L_cm:.0f}^2}} \times 100 = \mathbf{{{cur_wm:,.0f}}} \text{{ kg/m}}")

        st.divider()
        
        # 3. DEFLECTION (COMMON)
        st.markdown("##### 3️⃣ Deflection Check (Serviceability)")
        delta = L_cm / 360.0
        st.latex(rf"\delta_{{allow}} = L/360 = {L_cm:.0f}/360 = \mathbf{{{delta:.2f}}} \text{{ cm}}")
        st.write("น้ำหนักแผ่สูงสุดที่ทำให้แอ่นตัวไม่เกินกำหนด:")
        
        # แสดงตัวเลขในสูตรยาวๆ ให้ดูง่ายขึ้น
        numerator = 384 * E_ksc * props['Ix'] * delta
        denominator = 5 * (L_cm**4)
        st.latex(rf"w = \frac{{384 E I \delta}}{{5 L^4}} = \frac{{384 \times {E_ksc:,.0f} \times {props['Ix']:,} \times {delta:.2f}}}{{5 \times {L_cm:.0f}^4}}")
        st.latex(rf"w_{{deflect}} = {numerator/denominator:.4f} \text{{ kg/cm}} \times 100 = \mathbf{{{cur_wd:,.0f}}} \text{{ kg/m}}")
        
        st.divider()
        st.success(f"✅ **Governing Capacity (Gross): {cur_gov:,.0f} kg/m**")
        st.warning(f"**Net Safe Load** (หักน้ำหนักคาน) = {cur_gov:,.0f} - {props['W']} = **{max(cur_gov - props['W'], 0):,.0f} kg/m**")
        st.caption("*หมายเหตุ: การคำนวณโมเมนต์สมมติว่ามีการค้ำยันปีกอัดเพียงพอ (Fully Braced) หากระยะค้ำยันห่าง อาจเกิดการโก่งเดาะด้านข้าง (LTB) ได้")
