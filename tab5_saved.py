import streamlit as st
import pandas as pd
import numpy as np
from database import SYS_H_BEAMS
from calculator import core_calculation

def render_tab5(method, Fy, E_gpa, def_limit):
    st.markdown("### 📑 Master Structural Analysis Table")
    st.caption(f"Detailed analysis of all sections with transition zones and capacity limits. (Deflection Limit: **L/{def_limit}**)")

    # 1. Prepare Data
    all_sections = sorted(SYS_H_BEAMS.keys(), key=lambda x: int(x.split('x')[0].split('-')[1]))
    results = []
    
    prog_bar = st.progress(0, text="Analyzing structural behaviors...")
    total = len(all_sections)

    for i, section_name in enumerate(all_sections):
        props = SYS_H_BEAMS[section_name]
        
        # Calculate Core Physics
        c = core_calculation(10.0, Fy, E_gpa, props, method, def_limit)
        
        # --- 1. Critical Lengths (Zone Boundaries) ---
        L_vm = c['L_vm']  # Shear ends here
        L_md = c['L_md']  # Moment ends here
        
        # Zone Range String
        moment_range = f"{L_vm:.2f} - {L_md:.2f}"
        
        # --- 2. Load Scenarios ---
        # Case A: Max Theoretical Load (At the end of Shear Zone)
        if L_vm > 0:
            w_max = (2 * c['V_des'] / (L_vm * 100)) * 100
        else:
            w_max = 0
            
        # Case B: 75% Usage Scenario
        w_75 = 0.75 * w_max
        if w_75 > 0:
            L_75 = np.sqrt((8 * c['M_des']) / (w_75 / 100)) / 100
        else:
            L_75 = 0

        # --- 3. Collect Detailed Data ---
        results.append({
            # A. Section Properties
            "Section": section_name,
            "Weight": props['W'],
            "Ix": props['Ix'],
            
            # B. Structural Capacities (Design Values)
            "V_design": c['V_des'],
            "M_design": c['M_des'],
            
            # C. Zone Boundaries (Critical Lengths)
            "Shear_Limit_L": L_vm,
            "Moment_Zone_Range": moment_range,
            
            # D. Load Scenarios
            "Max_Load_Capacity": int(w_max),
            "Load_at_75": int(w_75),
            "Span_at_75": L_75
        })
        
        prog_bar.progress((i + 1) / total, text=f"Processing {section_name}...")

    prog_bar.empty()

    # 2. Create DataFrame
    df = pd.DataFrame(results)

    # 3. Display Detailed Table
    st.dataframe(
        df,
        use_container_width=True,
        height=700,
        hide_index=True,
        column_config={
            # --- GROUP 1: SECTION INFO ---
            "Section": st.column_config.TextColumn("Section Name", width="small", pinned=True),
            "Weight": st.column_config.NumberColumn("Weight (kg/m)", format="%.1f"),
            "Ix": st.column_config.NumberColumn(
                "Inertia Ix (cm⁴)", 
                format="%d", 
                help="Moment of Inertia around X-axis (Controls Deflection)"
            ),
            
            # --- GROUP 2: STRENGTH CAPACITIES ---
            "V_design": st.column_config.NumberColumn(
                "Shear Cap (kg)", 
                format="%d", 
                help=f"Design Shear Strength ($V_{{design}}$) based on {method}"
            ),
            "M_design": st.column_config.NumberColumn(
                "Moment Cap (kg-cm)", 
                format="%d", 
                help=f"Design Moment Strength ($M_{{design}}$) based on {method}"
            ),
            
            # --- GROUP 3: ZONES (LENGTHS) ---
            "Shear_Limit_L": st.column_config.NumberColumn(
                "Shear Limit (m)", 
                format="%.2f", 
                help="Maximum length where Shear is the governing factor ($L_{vm}$)"
            ),
            "Moment_Zone_Range": st.column_config.TextColumn(
                "Moment Zone (m)", 
                width="medium",
                help="Range where Moment controls: [Start (Shear End) - End (Deflection Start)]"
            ),
            
            # --- GROUP 4: LOADS & SCENARIOS ---
            "Max_Load_Capacity": st.column_config.NumberColumn(
                "Max Load (kg/m)", 
                format="%d", 
                help="Maximum Safe Uniform Load at the transition point (Full Capacity)"
            ),
            "Load_at_75": st.column_config.NumberColumn(
                "Load @ 75% (kg/m)", 
                format="%d",
                help="Load reduced to 75% of Max Capacity"
            ),
            "Span_at_75": st.column_config.ProgressColumn(
                "Span @ 75% (m)", 
                format="%.2f m",
                min_value=0, 
                max_value=float(df["Span_at_75"].max()),
                help="Achievable span length when carrying 75% load"
            )
        }
    )
    
    # 4. Footer & Download
    c1, c2 = st.columns([3, 1])
    with c1:
        st.info(
            "**💡 Note on Units:**\n"
            "- **Force/Load:** kg (kilogram-force)\n"
            "- **Length/Span:** m (meters) for span, cm for section properties\n"
            "- **Moment:** kg-cm\n"
            "- **Inertia:** cm⁴"
        )
    with c2:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Detailed CSV",
            data=csv,
            file_name=f"SYS_Detailed_Analysis_{method}.csv",
            mime='text/csv',
            use_container_width=True
        )
