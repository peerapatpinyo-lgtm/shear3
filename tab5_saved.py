# tab5_saved.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import SYS_H_BEAMS

# ==========================================
# 📐 HELPER: RE-CALCULATE LIMITS FOR GRAPH
# ==========================================
def calculate_span_limits(beam_name, load, method, def_limit_ratio, Fy_global, E_global):
    """
    คำนวณหาจุดเปลี่ยนพฤติกรรม (Limit States)
    รับค่า Fy และ E จาก Global settings เพื่อความแม่นยำ
    """
    if beam_name not in SYS_H_BEAMS: return 0, 0, 0

    beam = SYS_H_BEAMS[beam_name]
    Zx = beam['Zx']
    Ix = beam['Ix']
    
    # ใช้ Fy จากที่ส่งมา (หรือ Default 2400 ถ้าไม่มี)
    Fy = Fy_global if Fy_global > 0 else 2400
    E = E_global * 10000 # แปลง GPa -> ksc
    
    # 1. Moment Capacity (Strength Limit)
    w = load 
    Mn = (Fy * Zx) / 100.0 # kg-m
    if method == "ASD":
        M_cap = Mn / 1.67
    else:
        M_cap = 0.9 * Mn
        
    try:
        L_str = (8 * M_cap / w) ** 0.5
    except:
        L_str = 0

    # 2. Deflection Limit
    I_cm4 = Ix
    w_cm = w / 100.0
    
    try:
        # L = [(384 E I) / (5 w ratio)]^(1/3)
        factor = (384 * E * I_cm4) / (5 * w_cm * def_limit_ratio)
        L_def_cm = factor ** (1/3)
        L_def = L_def_cm / 100.0
    except:
        L_def = 0
        
    return beam['W'], L_str, L_def

# ==========================================
# 📊 MAIN RENDERER
# ==========================================
# แก้ไขบรรทัดนี้: รับ Arguments ให้ตรงกับที่ app.py ส่งมา
def render_tab5(method, Fy, E_gpa, def_limit): 
    st.markdown("### 💾 Saved Designs & Comparison")
    
    if 'saved_designs' not in st.session_state or not st.session_state['saved_designs']:
        st.info("No designs saved yet. Go to 'Design Check' tab and save some designs!")
        return

    # 1. Prepare Data
    saved_list = st.session_state['saved_designs']
    comparison_data = []

    for item in saved_list:
        bm_name = item['section']
        load = item['load'] # kg/m
        
        # ใช้ค่าที่ Save ไว้ ถ้าไม่มีให้ใช้ค่า Global ปัจจุบัน
        item_method = item.get('method', method)
        item_def_limit = item.get('def_limit', def_limit)
        
        # ส่ง Fy, E_gpa เข้าไปคำนวณด้วย
        weight, L_str, L_def = calculate_span_limits(
            bm_name, load, item_method, item_def_limit, Fy, E_gpa
        )
        
        max_span = min(L_str, L_def)
        gov_mode = "Strength" if L_str < L_def else "Deflection"
        
        comparison_data.append({
            "Section": bm_name,
            "Weight": weight,
            "Load": load,
            "Max_Span": max_span,
            "L_str": L_str,
            "L_def": L_def,
            "Mode": gov_mode
        })

    # Create DataFrame & Sort by Weight
    df = pd.DataFrame(comparison_data)
    if not df.empty:
        df = df.sort_values(by="Weight", ascending=True)

    with st.expander("📊 Data Table (Sorted by Weight efficiency)", expanded=False):
        st.dataframe(df.style.format({"Weight": "{:.1f}", "Max_Span": "{:.2f}", "L_str": "{:.2f}", "L_def": "{:.2f}"}))

    # 2. Comparison Chart
    if not df.empty:
        st.markdown("#### 🏆 Weight Efficiency & Max Span Comparison")
        
        fig = go.Figure()

        for i, row in df.iterrows():
            sec = row['Section']
            w = row['Weight']
            
            l_safe = min(row['L_str'], row['L_def'])
            l_extra_strength = max(0, row['L_str'] - row['L_def']) 
            
            # 1. Safe Span (Blue)
            fig.add_trace(go.Bar(
                y=[f"{sec} ({w} kg/m)"],
                x=[l_safe],
                name='Safe Span',
                orientation='h',
                marker_color='#3498db',
                hovertemplate=f"<b>{sec}</b><br>Safe Span: %{{x:.2f}} m<br>Weight: {w} kg/m<extra></extra>"
            ))
            
            # 2. Deflection Critical Zone (Green) - Camber Required
            if l_extra_strength > 0:
                fig.add_trace(go.Bar(
                    y=[f"{sec} ({w} kg/m)"],
                    x=[l_extra_strength],
                    name='Requires Camber',
                    orientation='h',
                    marker_color='#2ecc71',
                    hovertemplate=(
                        f"<b>{sec}</b><br>" +
                        f"Zone: {l_safe:.2f}m - {row['L_str']:.2f}m<br>" +
                        "Status: Strength OK, Deflection Exceeded<br>" +
                        "<b>⚠️ Action: Cambering Required</b><br>" + 
                        "or Increase Section Depth<extra></extra>"
                    )
                ))

        fig.update_layout(
            barmode='stack',
            title="Beam Performance: Safe Span vs. Potential (Weight Sorted)",
            xaxis_title="Span Length (m)",
            yaxis_title="Section (Weight)",
            height=400 + (len(df)*30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=80, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        > **💡 Interpretation:**
        > * **Blue Bar:** ช่วงความยาวที่ปลอดภัยทั้ง Strength และ Deflection
        > * **Green Bar:** ช่วงความยาวที่ **รับแรงไหว (Strength OK)** แต่ **ตกท้องช้างเกินพิกัด (Deflection Fail)** >         * *Engineering Tip:* สามารถใช้ช่วงสีเขียวได้ หากทำการ **"ดัดยก (Camber)"** คานล่วงหน้า หรือยอมรับการแอ่นตัวที่มากขึ้นได้
        """)
