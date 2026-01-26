# tab5_saved.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import SYS_H_BEAMS

# ==========================================
# 📐 HELPER
# ==========================================
def calculate_span_limits(beam_name, load, method, def_limit_ratio):
    # ใช้ค่า Default ในตัวฟังก์ชันเอง เหมือนเวอร์ชั่นเก่า
    if beam_name not in SYS_H_BEAMS: return 0, 0, 0

    beam = SYS_H_BEAMS[beam_name]
    Zx = beam['Zx']
    Ix = beam['Ix']
    Fy = 2400 
    E = 200 * 10000 # 200 GPa -> ksc
    
    # 1. Moment Capacity
    w = load 
    Mn = (Fy * Zx) / 100.0
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
# ใส่ *args เพื่อดักทุกอย่างที่ app.py ส่งมา (method, Fy, etc.) 
# แต่เราจะไม่ใช้มัน เราจะใช้ logic เดิมข้างใน
def render_tab5(*args): 
    st.markdown("### 💾 Saved Designs & Comparison")
    
    if 'saved_designs' not in st.session_state or not st.session_state['saved_designs']:
        st.info("No designs saved yet. Go to 'Design Check' tab and save some designs!")
        return

    # 1. Prepare Data
    saved_list = st.session_state['saved_designs']
    comparison_data = []

    for item in saved_list:
        bm_name = item['section']
        load = item['load']
        
        # ดึงค่าที่ Save ไว้มาใช้โดยตรง (Original Logic)
        method = item.get('method', 'ASD')
        d_ratio = item.get('def_limit', 300) 
        
        weight, L_str, L_def = calculate_span_limits(bm_name, load, method, d_ratio)
        
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

    # Create DataFrame
    df = pd.DataFrame(comparison_data)
    # คงการเรียงตามน้ำหนักไว้ เพราะมีประโยชน์มาก
    df = df.sort_values(by="Weight", ascending=True)

    with st.expander("📊 Data Table", expanded=False):
        st.dataframe(df.style.format({"Weight": "{:.1f}", "Max_Span": "{:.2f}", "L_str": "{:.2f}", "L_def": "{:.2f}"}))

    # 2. Chart
    st.markdown("#### 🏆 Weight Efficiency & Max Span Comparison")
    
    fig = go.Figure()

    for i, row in df.iterrows():
        sec = row['Section']
        w = row['Weight']
        
        l_safe = min(row['L_str'], row['L_def'])
        l_extra_strength = max(0, row['L_str'] - row['L_def']) 
        
        # Safe Span
        fig.add_trace(go.Bar(
            y=[f"{sec} ({w} kg/m)"],
            x=[l_safe],
            name='Safe Span',
            orientation='h',
            marker_color='#3498db',
            hovertemplate=f"<b>{sec}</b><br>Safe: %{{x:.2f}} m<br>Weight: {w}<extra></extra>"
        ))
        
        # Deflection Warning Zone
        if l_extra_strength > 0:
            fig.add_trace(go.Bar(
                y=[f"{sec} ({w} kg/m)"],
                x=[l_extra_strength],
                name='Camber Required',
                orientation='h',
                marker_color='#2ecc71',
                hovertemplate="<b>Requires Camber</b><br>Strength OK, Deflection Fail<extra></extra>"
            ))

    fig.update_layout(
        barmode='stack',
        xaxis_title="Span (m)",
        yaxis_title="Section",
        height=400 + (len(df)*30),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)
