import plotly.graph_objects as go
import numpy as np

def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    """
    สร้าง 3D Model ของ Shear Connection พร้อม Dimension และ Weld
    """
    fig = go.Figure()

    # --- Unpack Parameters ---
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pt, pw, ph = plate_dims['t'], plate_dims['w'], plate_dims['h']
    weld_sz = plate_dims.get('weld_sz', 6) # Default 6mm if not sent
    
    dia = bolt_dims['dia']
    n_rows = bolt_dims['n_rows']
    pitch = bolt_dims['pitch']
    lev = bolt_dims['lev']
    
    setback = config['setback']
    L_beam = config['L_beam_show']

    # Coordinate System:
    # X=0 is Support Face.
    # Beam starts at X=setback.
    # Plate starts at X=0 (welded to support).
    
    # ==========================================
    # 1. DRAW BEAM (I-SHAPE)
    # ==========================================
    # Web
    x_beam = [setback, setback+L_beam, setback+L_beam, setback]
    y_web = [-Tw/2, -Tw/2, Tw/2, Tw/2]
    z_web = [0, 0, H, H]
    
    # Create simple mesh for Beam Web
    # (Simplified as planes for performance)
    fig.add_trace(go.Mesh3d(
        x=[setback, setback+L_beam, setback+L_beam, setback]*2,
        y=[-Tw/2, -Tw/2, Tw/2, Tw/2]*2,
        z=[0, 0, 0, 0, H, H, H, H],
        i=[0, 1, 2, 0, 4, 5, 6, 4, 0, 1, 5, 4, 1, 2, 6, 5], # Basic Cube logic (simplified)
        j=[1, 2, 3, 4, 5, 6, 7, 7, 1, 5, 4, 0, 2, 6, 5, 1], # Just visual representation
        k=[2, 3, 0, 5, 6, 7, 4, 0, 5, 4, 0, 1, 6, 5, 1, 2],
        color='lightgrey', opacity=0.5, name='Beam Web'
    ))
    
    # Flanges (Top & Bottom) - Draw as thick lines for simple viz or boxes
    # Let's use simple lines for flanges to reduce clutter
    fig.add_trace(go.Scatter3d(
        x=[setback, setback+L_beam], y=[0,0], z=[0,0],
        mode='lines', line=dict(color='grey', width=10), name='Bot Flange'
    ))
    fig.add_trace(go.Scatter3d(
        x=[setback, setback+L_beam], y=[0,0], z=[H,H],
        mode='lines', line=dict(color='grey', width=10), name='Top Flange'
    ))

    # ==========================================
    # 2. DRAW PLATE (SHEAR TAB)
    # ==========================================
    # Plate center at Beam Centerline (assume beam vertical center aligned with plate vertical center? 
    # Usually plate is centered vertically on the bolt group, but let's align top of plate relative to beam)
    
    # Position: Plate top is usually below Top Flange.
    # Let's anchor Plate Top at: H - (some clearance). 
    # BUT, to match Lev logic: 
    # Top Bolt Z = H/2 + ((n-1)*s)/2 (if centered).
    # Let's simplify: Place Top Bolt at H - 100 (arbitrary) or center the group.
    
    # Better: Center the bolt group on the Beam Web Height
    group_height = (n_rows - 1) * pitch
    z_top_bolt = (H / 2) + (group_height / 2)
    z_plate_top = z_top_bolt + lev
    z_plate_bot = z_plate_top - ph
    
    # Plate Geometry (Box)
    fig.add_trace(go.Mesh3d(
        x=[0, pw, pw, 0, 0, pw, pw, 0],
        y=[-pt/2, -pt/2, pt/2, pt/2, -pt/2, -pt/2, pt/2, pt/2],
        z=[z_plate_bot, z_plate_bot, z_plate_bot, z_plate_bot, z_plate_top, z_plate_top, z_plate_top, z_plate_top],
        # Cube indices
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color='#3498db', opacity=0.9, name='Shear Plate'
    ))

    # ==========================================
    # 3. DRAW WELD (FILLET) 🟧
    # ==========================================
    # Weld is at X=0, along the Z-axis of the plate, on both sides (Y+ and Y-)
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
    # 4. DRAW BOLTS
    # ==========================================
    bolt_x = setback + bolt_dims['leh_beam'] # This is bolt center X
    
    # Calculate bolt Z positions
    bolt_z_list = []
    for i in range(n_rows):
        bz = z_top_bolt - (i * pitch)
        bolt_z_list.append(bz)
        
        # Draw Bolt (Cylinder representation - horizontal line for simple viz)
        fig.add_trace(go.Scatter3d(
            x=[bolt_x-10, bolt_x+10], # Head and nut
            y=[0, 0],
            z=[bz, bz],
            mode='lines+markers',
            marker=dict(size=dia/2, color='black'),
            line=dict(color='black', width=5),
            name='Bolt' if i==0 else None, showlegend=(i==0)
        ))

    # ==========================================
    # 5. DIMENSIONS & ANNOTATIONS (LEV) 📏
    # ==========================================
    # Draw Lev Dimension Line (Plate Top to Top Bolt)
    # Offset slightly in Y so it doesn't overlap plate
    dim_y = pt/2 + 20 
    dim_x = bolt_x
    
    # Vertical Line
    fig.add_trace(go.Scatter3d(
        x=[dim_x, dim_x],
        y=[dim_y, dim_y],
        z=[z_top_bolt, z_plate_top],
        mode='lines+markers+text',
        line=dict(color='blue', width=4),
        marker=dict(symbol='arrow', size=5, color='blue'), # Arrow simulation
        text=[f"", f"Lev = {lev}"],
        textposition="top right",
        name='Lev Dim'
    ))
    
    # Helper horizontal ticks for dimension
    fig.add_trace(go.Scatter3d(
        x=[dim_x-5, dim_x+5, None, dim_x-5, dim_x+5],
        y=[dim_y, dim_y, None, dim_y, dim_y],
        z=[z_top_bolt, z_top_bolt, None, z_plate_top, z_plate_top],
        mode='lines', line=dict(color='blue', width=2), showlegend=False
    ))

    # ==========================================
    # 6. CONFIGURATION
    # ==========================================
    fig.update_layout(
        scene=dict(
            aspectmode='data', # True scale
            xaxis_title='Length (mm)',
            yaxis_title='Width (mm)',
            zaxis_title='Height (mm)',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.5) # Nice Isometric View
            )
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        legend=dict(yanchor="top", y=0.9, xanchor="left", x=0.1)
    )
    
    return fig
