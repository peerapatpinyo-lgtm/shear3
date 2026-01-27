import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 🏗️ TAB 2: LOAD ANALYSIS & DIAGRAMS
# ==========================================
def render_tab2():
    st.markdown("### 📊 Load Analysis (Simply Supported Beam)")
    
    col1, col2 = st.columns([1, 2])

    with col1:
        st.info("📥 Input Parameters")
        L = st.number_input("Span Length (m)", value=6.0, step=0.5, format="%.2f")
        
        st.markdown("---")
        st.markdown("**Distributed Load (Uniform)**")
        wdl = st.number_input("Dead Load (kg/m)", value=500.0, step=50.0)
        wll = st.number_input("Live Load (kg/m)", value=300.0, step=50.0)
        
        # Factor Load (Ultimate)
        wu = (1.2 * wdl) + (1.6 * wll)
        
        st.markdown("---")
        st.markdown("**Point Load (Center)**")
        P_live = st.number_input("Point Load LL (kg)", value=0.0, step=100.0)
        Pu = 1.6 * P_live

    # --- CALCULATION ---
    # Reactions
    R_uniform = (wu * L) / 2
    R_point = Pu / 2
    R_total = R_uniform + R_point
    
    # Max Values
    V_max = R_total
    M_max_uniform = (wu * L**2) / 8
    M_max_point = (Pu * L) / 4
    M_max = M_max_uniform + M_max_point

    # --- PLOTTING ---
    with col2:
        # Create X array
        x = np.linspace(0, L, 100)
        
        # Shear Equation: V(x) = R - w*x - P(if x > L/2)
        V_uniform = R_uniform - (wu * x)
        V_point = np.where(x < L/2, Pu/2, -Pu/2)
        V_total = V_uniform + V_point
        
        # Moment Equation: M(x) = R*x - (w*x^2)/2 - P*(x-L/2)
        M_uniform = (R_uniform * x) - (wu * x**2 / 2)
        M_point = np.where(x < L/2, (Pu/2)*x, (Pu/2)*x - Pu*(x - L/2))
        M_total = M_uniform + M_point

        # Display Summary Cards
        c1, c2, c3 = st.columns(3)
        c1.metric("Factored Load (Wu)", f"{wu:,.0f} kg/m")
        c2.metric("Max Shear (Vu)", f"{V_max:,.0f} kg")
        c3.metric("Max Moment (Mu)", f"{M_max:,.0f} kg-m")

        # Plotting with Matplotlib
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        
        # Shear Diagram
        ax1.plot(x, V_total, label='Shear (V)', color='#e74c3c', linewidth=2)
        ax1.fill_between(x, V_total, 0, alpha=0.1, color='#e74c3c')
        ax1.set_ylabel('Shear Force (kg)')
        ax1.set_title('Shear Force Diagram (SFD)')
        ax1.grid(True, linestyle='--', alpha=0.6)
        ax1.axhline(0, color='black', linewidth=1)

        # Moment Diagram
        ax2.plot(x, M_total, label='Moment (M)', color='#3498db', linewidth=2)
        ax2.fill_between(x, M_total, 0, alpha=0.1, color='#3498db')
        ax2.set_xlabel('Distance (m)')
        ax2.set_ylabel('Moment (kg-m)')
        ax2.set_title('Bending Moment Diagram (BMD)')
        ax2.grid(True, linestyle='--', alpha=0.6)
        ax2.axhline(0, color='black', linewidth=1)

        st.pyplot(fig)
        
        # Note for user
        st.caption("ℹ️ Note: This analysis assumes a Simply Supported Beam.")

    # Return values if needed for other tabs (Optional)
    return M_max, V_max
