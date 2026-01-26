# tab5_saved.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📊 Master Structural Timeline")
    st.caption(f"Analysis Parameters: Fy={Fy} ksc, E={E_gpa} GPa, Limit=L/{def_limit} | Method: {method}")

    # --- 1. Data Processing ---
    # แก้ไขจุดที่ Error: เปลี่ยนจาก 'Depth' เป็น 'D' และใส่ .get() กันพลาด
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: (SYS_H_BEAMS[x].get('D', 0), SYS_H_BEAMS[x].get('W', 0)))
    
    data_list = []
    
    prog_bar = st.progress(0, text="Performing structural analysis...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # 1.1 คำนวณค่าวิกฤต
        # ส่งค่า D, B, tw, tf ให้ calculator ผ่านตัวแปร props
        try:
            c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
            
            L_vm = c['L_vm']
            L_md = c['L_md']
            
            # 1.2 คำนวณ Load Scenarios
            if L_vm > 0:
                # คำนวณ Load กลับจาก Shear Capacity
                # V_des = w * L / 2  ->  w = 2 * V / L
                w_max_shear_limit = (2 * c['V_des'] / (L_vm * 100)) * 100 
            else:
                w_max_shear_limit = 0
                
            w_75 = 0.75 * w_max_shear_limit
            
            if w_75 > 0:
                # L = sqrt(8 * M / w)
                L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100 
            else:
                L_75 = 0

            max_dist = max(L_md, L_75)
            visual_end_point = max(max_dist * 1.15, L_md + 1.0) 
            L_deflect_width = max(0, visual_end_point - L_md)

            data_list.append({
                "Section": section_name,
                "Weight": props.get('W', 0), # ใช้ .get กันพลาด
                "Ix": props.get('Ix', 0),
                "L_shear": L_vm,
                "L_moment_width": max(0, L_md - L_vm),
                "L_deflect_width": L_deflect_width,
                "Ref_Start_Moment": L_vm,
                "Ref_Start_Deflect": L_md,
                "L_75": L_75,
                "Load_75": w_75,
                "LTB_Zone": c.get('Zone', 'N/A')
            })
        except Exception as e:
            # ถ้าคานตัวไหนคำนวณไม่ได้ ให้ข้ามไปก่อน (จะได้ไม่พังทั้งแอป)
            print(f"Error calculating {section_name}: {e}")
            continue

        prog_bar.progress((i + 1) / total, text=f"Analyzing {section_name}...")
    
    prog_bar.empty()
    
    if not data_list:
        st.error("No valid beam data found or calculation error.")
        return

    df = pd.DataFrame(data_list)

    # --- 2. Visualization (Graph) ---
    fig = go.Figure()

    # Layer 1: Shear
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_shear'],
        name='Shear Control', orientation='h',
        marker=dict(color='#d9534f', line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>🔴 Shear Zone: 0 - %{x:.2f} m<extra></extra>"
    ))

    # Layer 2: Moment
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_moment_width'],
        name='Moment Control', orientation='h',
        marker=dict(color='#f0ad4e', line=dict(width=0)),
        base=df['L_shear'],
        customdata=np.stack((df['Ref_Start_Deflect'], df['LTB_Zone']), axis=-1),
        hovertemplate="🟠 <b>Moment Zone</b><br>Range: %{base:.2f} - %{customdata[0]:.2f} m<br>Behavior: <b>%{customdata[1]}</b><extra></extra>"
    ))

    # Layer 3: Deflection
    fig.add_trace(go.Bar(
        y=df['Section'], x=df['L_deflect_width'],
        name='Deflection Control', orientation='h',
        marker=dict(color='#5cb85c', opacity=0.4, line=dict(width=0)),
        base=df['Ref_Start_Deflect'],
        hovertemplate=f"🟢 Deflection Zone (L/{def_limit}): > %{{base:.2f}} m<extra></extra>"
    ))

    # Layer 4: 75% Load
    fig.add_trace(go.Scatter(
        x=df['L_75'], y=df['Section'],
        mode='markers', name='Span @ 75% Cap.',
        marker=dict(symbol='diamond', size=6, color='blue'),
        hovertemplate="🔷 Span @ 75% Load: %{x:.2f} m<br>Load: %{customdata:,.0f} kg/m<extra></extra>",
        customdata=df['Load_75']
    ))

    fig.update_layout(
        title="Structural Behavior Timeline (All Beams)",
        barmode='stack', 
        height=max(600, len(df) * 25),
        xaxis_title="Span Length (m)", 
        yaxis_title="Section",
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=80, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 3. Table ---
    with st.expander("📄 View Detailed Data Table"):
        st.dataframe(
            df[['Section', 'Weight', 'Ref_Start_Deflect', 'L_75', 'Load_75', 'LTB_Zone']],
            column_config={
                "Ref_Start_Deflect": st.column_config.NumberColumn("Deflection Starts (m)", format="%.2f"),
                "L_75": st.column_config.NumberColumn("Span @ 75% Load (m)", format="%.2f"),
                "Load_75": st.column_config.NumberColumn("Load @ 75% (kg/m)", format="%d"),
                "LTB_Zone": "Buckling Mode"
            },
            hide_index=True, use_container_width=True
        )
