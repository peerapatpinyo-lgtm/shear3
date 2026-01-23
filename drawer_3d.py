import plotly.graph_objects as go
import numpy as np

def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    """
    สร้าง 3D Model ของ Shear Connection พร้อม Dimension (Lev) และ Weld
    """
    fig = go.Figure()

    # --- 1. Unpack Parameters ---
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pt, pw, ph = plate_dims['t'], plate_dims['w'], plate_dims['h']
    weld_sz = plate_dims.get('weld_sz', 6) # Default 6mm
    
    dia = bolt_dims['dia']
    n_rows = bolt_dims['n_rows']
    pitch = bolt_dims['pitch']
    lev = bolt_dims['lev']
    
    setback = config['setback']
    L_beam = config['L_beam_show']

    # --- 2. Calculate Coordinates ---
    # Center Bolt Group vertically relative to Beam H
    group_height = (n_rows - 1) * pitch
    z_top_bolt = (H / 2) + (group_height / 2)
    
    # Plate Position
    z_plate_top = z_top_bolt + lev
    z_plate_bot = z_plate_top - ph
    
    # Bolt X Position
    bolt_x = setback + bolt_dims['leh_beam']

    # ==========================================
    # 🟦 PART 1: BEAM (Wireframe/Mesh)
    # ==========================================
    # Web (Simplified Box)
    fig.add_trace(go.Mesh3d(
        x=[setback, setback+L_beam, setback+L_beam, setback]*2,
        y=[-Tw/2, -Tw/2, Tw/2, Tw/2]*2,
        z=[0, 0, 0, 0, H, H, H, H],
        i=[0, 1, 2, 0, 4, 5, 6, 4, 0, 1, 5, 4, 1, 2, 6, 5], 
        j=[1, 2, 3, 4, 5, 6, 7, 7, 1, 5, 4, 0, 2, 6, 5, 1], 
        k=[2, 3, 0, 5, 6, 7, 4, 0, 5, 4, 0, 1, 6, 5, 1, 2],
        color='lightgrey', opacity=0.3, name='Beam Web'
    ))
    
    # Flanges (Lines for clarity)
    fig.add_trace(go.Scatter3d(
        x=[setback, setback+L_beam], y=[0,0], z=[0,0],
        mode='lines', line=dict(color='grey', width=8), name='Bot Flange'
    ))
    fig.add_trace(go.Scatter3d(
        x=[setback, setback+L_beam], y=[0,0], z=[H,H],
        mode='lines', line=dict(color='grey', width=8), name='Top Flange'
    ))

    # ==========================================
    # 🟦 PART 2: PLATE (Solid Blue)
    # ==========================================
    fig.add_trace(go.Mesh3d(
        x=[0, pw, pw, 0, 0, pw, pw, 0],
        y=[-pt/2, -pt/2, pt/2, pt/2, -pt/2, -pt/2, pt/2, pt/2],
        z=[z_plate_bot, z_plate_bot, z_plate_bot, z_plate_bot, z_plate_top, z_plate_top, z_plate_top, z_plate_top],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#3498db', opacity=1.0, name='Shear Plate'
    ))

    # ==========================================
    # 🟧 PART 3: WELD (Orange Fillet)
    # ==========================================
    # Side 1 (Y+)
    fig.add_trace(go.Mesh3d(
        x=[0, weld_sz, 0, 0, weld_sz, 0],
        y=[pt/2, pt/2, pt/2 + weld_sz, pt/2, pt/2, pt/2 + weld_sz],
        z=[z_plate_bot, z_plate_bot, z_plate_bot, z_plate_top, z_plate_top, z_plate_top],
        i=[0, 0, 0, 3], j=[1, 2, 3, 4], k=[2, 3, 4, 5],
        color='#e67e22', name='Fillet Weld'
    ))
    # Side 2 (Y-)
    fig.add_trace(go.Mesh3d(
        x=[0, weld_sz, 0, 0, weld_sz, 0],
        y=[-pt/2, -pt/2, -pt/2 - weld_sz, -pt/2, -pt/2, -pt/2 - weld_sz],
        z=[z_plate_bot, z_plate_bot, z_plate_bot, z_plate_top, z_plate_top, z_plate_top],
        i=[0, 0, 0, 3], j=[1, 2, 3, 4], k=[2, 3, 4, 5],
        color='#e67e22', showlegend=False
    ))

    # ==========================================
    # ⚫ PART 4: BOLTS
    # ==========================================
    for i in range(n_rows):
        bz = z_top_bolt - (i * pitch)
        fig.add_trace(go.Scatter3d(
            x=[bolt_x-15, bolt_x+15], 
            y=[0, 0], z=[bz, bz],
            mode='lines+markers',
            marker=dict(size=dia/1.5, color='black'), # Scale visual size
            line=dict(color='black', width=6),
            name='Bolt' if i==0 else None, showlegend=(i==0)
        ))

    # ==========================================
    # 📏 PART 5: DIMENSIONS (LEV)
    # ==========================================
    dim_y = pt/2 + 30 # Shift out from plate
    dim_x = bolt_x
    
    # Arrow Line (Vertical)
    fig.add_trace(go.Scatter3d(
        x=[dim_x, dim_x],
        y=[dim_y, dim_y],
        z=[z_top_bolt, z_plate_top],
        mode='lines+markers+text',
        line=dict(color='blue', width=4),
        marker=dict(symbol='diamond', size=4, color='blue'),
        text=[f"", f"Lev={lev}"],
        textposition="top center",
        name='Lev Dimension'
    ))
    
    # Helper Ticks (Horizontal)
    fig.add_trace(go.Scatter3d(
        x=[dim_x-10, dim_x+10, None, dim_x-10, dim_x+10],
        y=[dim_y, dim_y, None, dim_y, dim_y],
        z=[z_top_bolt, z_top_bolt, None, z_plate_top, z_plate_top],
        mode='lines', line=dict(color='blue', width=2), showlegend=False
    ))

    # Camera & Layout
    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(title='Length (X)', visible=False),
            yaxis=dict(title='Width (Y)', visible=False),
            zaxis=dict(title='Height (Z)', visible=True),
            camera=dict(eye=dict(x=1.8, y=1.8, z=0.5))
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.05)
    )
    
    return fig
