# tab5_saved.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import SYS_H_BEAMS

# ==========================================
# 📐 HELPER: RE-CALCULATE LIMITS FOR GRAPH
# ==========================================
def calculate_span_limits(beam_name, load, method, def_limit_ratio, E_gpa=200):
    """
    คำนวณหาจุดเปลี่ยนพฤติกรรม (Limit States) เพื่อวาดกราฟ Timeline
    L_str = ความยาวสูงสุดที่รับได้ด้วย Strength (Moment/Shear)
    L_def = ความยาวสูงสุดที่รับได้ด้วย Deflection
    """
    if beam_name not in SYS_H_BEAMS: return 0, 0, 0

    beam = SYS_H_BEAMS[beam_name]
    Zx = beam['Zx']
    Ix = beam['Ix']
    Fy = 2400 # สมมติฐานมาตรฐาน หรือดึงจาก Saved Data ถ้ามี
    E = E_gpa * 10000 # ksc
    
    # 1. Moment Capacity (Strength Limit)
    # Mn = Fy * Zx
    # Weight is usually small compared to Load, but for strict check:
    # M_u = w * L^2 / 8
    # L_max_str = sqrt( 8 * Cap / w )
    
    # แปลง Load unit (kg/m)
    w = load 
    
    # Moment Capacity
    Mn = (Fy * Zx) / 100.0 # kg-m
    if method == "ASD":
        M_cap = Mn / 1.67
    else:
        M_cap = 0.9 * Mn
        
    # L_strength (m)
    try:
        L_str = (8 * M_cap / w) ** 0.5
    except:
        L_str = 0

    # 2. Deflection Limit
    # Delta = 5 * w * L^4 / (384 * E * I)
    # Limit = L / ratio
    # Solve for L -> L^3 = (384 * E * I) / (5 * w * ratio)
    
    I_cm4 = Ix
    
    # แปลง w (kg/m) -> (kg/cm) = w/100
    w_cm = w / 100.0
    
    try:
        # 5 * w_cm * L_cm^4 / (384 * E * I) = L_cm / ratio
        # L_cm^3 = (384 * E * I) / (5 * w_cm * ratio)
        factor = (384 * E * I_cm4) / (5 * w_cm * def_limit_ratio)
        L_def_cm = factor ** (1/3)
        L_def = L_def_cm / 100.0
    except:
        L_def = 0
        
    return beam['W'], L_str, L_def

# ==========================================
# 📊 MAIN RENDERER
# ==========================================
def render_tab5_saved():
    st.markdown("### 💾 Saved Designs & Comparison")
    
    if 'saved_designs' not in st.session_state or not st.session_state['saved_designs']:
        st.info("No designs saved yet. Go to 'Design Check' tab and save some designs!")
        return

    # 1. Prepare Data
    saved_list = st.session_state['saved_designs']
    comparison_data = []

    for item in saved_list:
        # Extract saved parameters
        bm_name = item['section']
        load = item['load'] # kg/m
        method = item.get('method', 'ASD')
        d_ratio = item.get('def_limit', 300) # L/300 default
        
        # Calculate Limits
        weight, L_str, L_def = calculate_span_limits(bm_name, load, method, d_ratio)
        
        # Logic: Determine Zones
        # Zone 1: Strength Controlled (Blue) -> 0 to Min(L_str, L_def)
        # Zone 2: Deflection Controlled (Green) -> If L_def > L_str ?? No.
        # Typically:
        # Case A: Strength Controls (L_str < L_def) -> Blue bar full length. Green = 0.
        # Case B: Deflection Controls (L_def < L_str) -> Blue bar up to L_def? 
        #         NO, usually we show: 
        #         - Blue: "Efficient Zone" (Both Pass)
        #         - Green: "Deflection Governed Zone" (Pass Strength, Fail Deflection? No, that's unsafe)
        #         
        # Let's use the standard "Capacity Visualization":
        # Bar Length = The allowable span.
        # Color = What governs it.
        #
        # BUT, the user asked for "Moment Zone" vs "Deflection Zone".
        # Let's interpret as:
        # - L_md (Transition Point): The length where Deflection starts to govern over Strength.
        #   (Actually, it's usually where Strength curve intersects Deflection curve).
        # 
        # Simplified for visualization:
        # Valid Span = Min(L_str, L_def)
        # If L_str < L_def: Entirely Strength Governed.
        # If L_def < L_str: 
        #    - 0 to L_def is Valid (Governed by Deflection).
        #    - L_def to L_str is "Strength OK, but Deflection Fails".
        
        # Let's try the "Weight Efficiency" approach requested:
        # We want to show the Max Valid Span.
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
    
    # --- 🎯 IMPROVEMENT 1: Sort by Weight (Efficiency) ---
    # เรียงจากน้ำหนักน้อย -> มาก เพื่อให้ User เห็นตัวที่เบาที่สุดที่ทำ Span ได้
    df = df.sort_values(by="Weight", ascending=True)

    # Display Table
    with st.expander("📊 Data Table (Sorted by Weight efficiency)", expanded=False):
        st.dataframe(df.style.format({"Weight": "{:.1f}", "Max_Span": "{:.2f}", "L_str": "{:.2f}", "L_def": "{:.2f}"}))

    # --- 🎯 IMPROVEMENT 2 & 3: Comparison Chart with Safety Notice ---
    st.markdown("#### 🏆 Weight Efficiency & Max Span Comparison")
    
    fig = go.Figure()

    # เราจะวาด Bar 2 ส่วนซ้อนกัน (Stacked) เพื่อโชว์ Behavior
    # ส่วนที่ 1: Moment/Strength Zone (สีน้ำเงิน) -> ยาวไปจนถึงจุดที่ Deflection เริ่มคุม หรือจุดที่พัง
    # ส่วนที่ 2: Deflection Zone (สีเขียว) -> ถ้า Deflection ยอมให้ยาวกว่า Strength (ซึ่งไม่ควรเกิดในการออกแบบจริง)
    # แต่เพื่อให้ตอบโจทย์ User ที่ต้องการเห็น "L_md" (จุดเปลี่ยน):
    
    # Logic:
    # ถ้า L_def < L_str: 
    #   - ช่วง 0 ถึง L_def: ผ่านทั้งคู่ (Color: Green - Deflection Controls Limit)
    #   - ช่วง L_def ถึง L_str: รับแรงไหว แต่แอ่นตัวเกิน (Color: Red/Warning - Requires Camber?)
    
    # ปรับใหม่ตามความต้องการ User: "Moment Zone" (Blue) -> "Deflection Zone" (Green)
    # ตีความ: ช่วงที่ Strength รับไหวแน่นอน (Blue) และช่วงที่ต้องระวัง Deflection (Green)
    
    for i, row in df.iterrows():
        sec = row['Section']
        w = row['Weight']
        
        # Calculate lengths for stacking
        # Ref_Start_Deflect (L_md) logic:
        # สมมติเราแบ่งเป็น:
        # 1. ช่วงที่ Strength ทำงานได้เต็มที่โดยไม่ห่วง Deflection (Blue) -> L_md
        # 2. ช่วงที่ Deflection เริ่มมีผล (Green)
        
        # เพื่อความง่ายและถูกต้องทางวิศวกรรม:
        # Bar = Max Valid Span.
        # Color = Governing Mode.
        
        # แต่ User ขอ "Green Zone" และ "Hovertemplate"
        # ผมจะทำเป็น Stacked Bar:
        # - Base Bar (Blue): Span ที่ปลอดภัย 100% ทั้ง Strength & Deflection
        # - Extension (Green): ถ้า L_str > L_def -> ส่วนนี้คือส่วนที่ Strength ยังรับได้ แต่ Deflection เกิน
        #   นี่คือจุดที่ใส่ "Cambering Required" ได้เหมาะที่สุด!
        
        l_safe = min(row['L_str'], row['L_def'])
        l_extra_strength = max(0, row['L_str'] - row['L_def']) # ส่วนที่แรงรับไหว แต่แอ่นเกิน
        
        # 1. Safe Span (Blue)
        fig.add_trace(go.Bar(
            y=[f"{sec} ({w} kg/m)"],
            x=[l_safe],
            name='Safe Span',
            orientation='h',
            marker_color='#3498db',
            hovertemplate=f"<b>{sec}</b><br>Safe Span: %{{x:.2f}} m<br>Weight: {w} kg/m<extra></extra>"
        ))
        
        # 2. Deflection Critical Zone (Green/Orange) - The "Camber" Zone
        # นี่คือโซนที่ Strength ผ่าน แต่ Deflection ไม่ผ่าน -> ต้องดัด Camber ช่วย
        if l_extra_strength > 0:
            fig.add_trace(go.Bar(
                y=[f"{sec} ({w} kg/m)"],
                x=[l_extra_strength],
                name='Requires Camber',
                orientation='h',
                marker_color='#2ecc71', # Green as requested
                # --- 🎯 SAFETY NOTICE IN HOVER ---
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
    > * **Green Bar:** ช่วงความยาวที่ **รับแรงไหว (Strength OK)** แต่ **ตกท้องช้างเกินพิกัด (Deflection Fail)** >     * *Engineering Tip:* สามารถใช้ช่วงสีเขียวได้ หากทำการ **"ดัดยก (Camber)"** คานล่วงหน้า หรือยอมรับการแอ่นตัวที่มากขึ้นได้
    """)
