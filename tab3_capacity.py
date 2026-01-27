#tab3_capacity.py
import streamlit as st
import pandas as pd
from calculator import core_calculation

def render_tab3(props, method, Fy, E_gpa, section, def_val=360):
    """
    Tab 3: Capacity Overview & Zones (English Version)
    Revised: clear units in every column, full CSV support.
    """
    st.markdown(f"### 📊 Capacity Summary: {section} ({method})")
    
    # Header Info
    c1, c2, c3 = st.columns(3)
    c1.info(f"**Limit Criteria:** L/{def_val}")
    c2.info(f"**Beam Weight:** {props['W']} kg/m")
    c3.info(f"**Span Range:** 1 - 30 m")
    
    st.markdown("---")

    # --- 1. Critical Transitions Calculation ---
    dummy_calc = core_calculation(10.0, Fy, E_gpa, props, method, def_val)
    L_vm = dummy_calc['L_vm']
    L_md = dummy_calc['L_md']

    # --- 2. Zone Visualization ---
    st.subheader("1. Governing Control Zones")
    st.caption("Indicates which failure mode governs the design capacity for a given span length.")
    
    z1, z2, z3 = st.columns(3)
    with z1:
        st.error(f"**🔴 Short Span (Shear)**")
        st.markdown(f"Range: **1.00 - {L_vm:.2f} m**")
    with z2:
        st.warning(f"**🟠 Medium Span (Moment)**")
        st.markdown(f"Range: **{L_vm:.2f} - {L_md:.2f} m**")
    with z3:
        st.success(f"**🟢 Long Span (Deflection)**")
        st.markdown(f"Range: **> {L_md:.2f} m**")

    st.markdown("---")

    # --- 3. Look-up Table Generation ---
    st.subheader(f"2. Capacity Look-up Table")
    
    # Explanation Box
    st.info(f"""
    **📝 Legend & Unit Explanation:**
    * All load values are in **kg/m**.
    * **Gross Capacity:** The total capacity of the section (before deducting beam weight).
    * **✅ Net Safe Load:** The actual usable load (Live Load + Superimposed Dead Load).
    
    $$ \\text{{Net Safe Load}} = \\text{{Min}}(\\text{{Shear}}, \\text{{Moment}}, \\text{{Deflection}}) - \\text{{Beam Weight}} ({props['W']} \\text{{ kg/m}}) $$
    """)

    # Generate data for 1 - 30 meters
    spans = range(1, 31) 
    data = []

    for L in spans:
        # Core Calculation
        c = core_calculation(float(L), Fy, E_gpa, props, method, def_val)
        
        # Gross Capacities
        w_shear = c['ws']
        w_moment = c['wm']
        w_deflect = c['wd']
        
        # Find Governing Gross Capacity
        gross_min = min(w_shear, w_moment, w_deflect)
        
        # Net Load Calculation (Ensure non-negative)
        net_load = max(0, gross_min - props['W'])

        # Determine Control Mode
        if gross_min == w_shear: 
            control_txt = "Shear"
        elif gross_min == w_moment: 
            control_txt = "Moment"
        else: 
            control_txt = f"Deflection"

        # Append Data (English Headers)
        data.append({
            "Span Length (m)": f"{L:.1f}",
            "✅ Net Safe Load (kg/m)": net_load,
            "Governing Mode": control_txt,
            "Shear Cap. (kg/m)": w_shear,
            "Moment Cap. (kg/m)": w_moment,
            "Deflection Limit (kg/m)": w_deflect
        })

    df = pd.DataFrame(data)

    # Highlight Function
    def highlight_mode(row):
        mode = row['Governing Mode']
        color = ''
        if 'Shear' in mode: color = 'background-color: #ffe6e6' # Red tint
        elif 'Moment' in mode: color = 'background-color: #fff4e6' # Orange tint
        elif 'Deflection' in mode: color = 'background-color: #e6ffe6' # Green tint
        return [color if col == 'Governing Mode' else '' for col in row.index]

    # Display Table
    st.dataframe(
        df.style.apply(highlight_mode, axis=1).format({
            "✅ Net Safe Load (kg/m)": "{:,.0f}",
            "Shear Cap. (kg/m)": "{:,.0f}",
            "Moment Cap. (kg/m)": "{:,.0f}",
            "Deflection Limit (kg/m)": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Span Length (m)": st.column_config.TextColumn(
                "Span Length (m)", 
                help="Length of the beam span in meters."
            ),
            "✅ Net Safe Load (kg/m)": st.column_config.NumberColumn(
                "✅ Net Safe Load (kg/m)", 
                help="Usable load capacity after deducting beam self-weight.",
                format="%d"
            ),
            "Governing Mode": st.column_config.TextColumn(
                "Governing Mode",
                help="The factor limiting the design (Shear, Moment, or Deflection)."
            ),
            "Shear Cap. (kg/m)": st.column_config.NumberColumn(
                "Shear Cap. (kg/m)", 
                help="Gross Shear Capacity (V_design)",
                format="%d"
            ),
            "Moment Cap. (kg/m)": st.column_config.NumberColumn(
                "Moment Cap. (kg/m)", 
                help="Gross Moment Capacity (M_design including LTB)",
                format="%d"
            ),
            "Deflection Limit (kg/m)": st.column_config.NumberColumn(
                "Deflection (kg/m)", 
                help=f"Load causing deflection equal to limit L/{def_val}",
                format="%d"
            ),
        },
        height=600
    )
    
    # Export CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV Table",
        data=csv,
        file_name=f'Capacity_Table_{section}_L{def_val}.csv',
        mime='text/csv',
    )
