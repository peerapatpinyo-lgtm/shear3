import plotly.graph_objects as go
import numpy as np

# ==========================================
# 🧊 HELPER: SOLID BLOCK GENERATOR
# ==========================================
def make_solid_block(x_c, y_c, z_c, dx, dy, dz, color, name, opacity=1.0):
    """สร้างก้อนสี่เหลี่ยมตัน มีแสงเงาโลหะ"""
    return go.Mesh3d(
        x=[x_c-dx/2, x_c-dx/2, x_c+dx/2, x_c+dx/2, x_c-dx/2, x_c-dx/2, x_c+dx/2, x_c+dx/2],
        y=[y_c-dy/2, y_c+dy/2, y_c+dy/2, y_c-dy/2, y_c-dy/2, y_c+dy/2, y_c+dy/2, y_c-dy/2],
        z=[z_c-dz/2, z_c-dz/2, z_c-dz/2, z_c-dz/2, z_c+dz/2, z_c+dz/2, z_c+dz/2, z_c+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name,
        # เพิ่มแสงเงาให้ดูเป็นโลหะ
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.3, roughness=0.1)
    )

# ==========================================
# 🏗️ MAIN DRAWING FUNCTION
# ==========================================
def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    fig = go.Figure()

    # --- 1. Unpack ---
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pt, pw, ph = plate_dims['t'], plate_dims['w'], plate_dims['h']
    weld_sz = plate_dims.get('weld_sz', 6)
    
    dia = bolt_dims['dia']
    n_rows = bolt_dims['n_rows']
    pitch = bolt_dims['pitch']
    lev = bolt_dims['lev']
    
    setback = config['setback']
    L_beam = config['L_beam_show']

    # --- 2. Coordinates ---
    # Beam center Y=0. 
    # Beam starts at X = setback.
    beam_center_x = setback + (L_beam / 2)
    
    # Plate position (Attached to Web face at Y = Tw/2)
    pl_x_center = setback + (pw / 2) # Center of plate along beam length
    pl_y_center = (Tw / 2) + (pt / 2) # Offset from web
    
    # Bolt vertical positions (Centered on Beam Height)
    group_height = (n_rows - 1) * pitch
    z_top_bolt = (H / 2) + (group_height / 2)
    
    # Plate vertical positions relative to top bolt
    z_plate_top = z_top_bolt + lev
    z_plate_center = z_plate_top - (ph / 2)

    # ==========================================
    # 🏗️ PART 1: SOLID STEEL BEAM (Grey)
    # ==========================================
    steel_color = '#7f8c8d' # Industrial Grey
    
    # 1.1 Web (เอวกลาง)
    web_h = H - (2 * Tf)
    fig.add_trace(make_solid_block(
        beam_center_x, 0, H/2,  # Center X, Y, Z
        L_beam, Tw, web_h,      # Size dX, dY, dZ
        steel_color, 'Beam Web'
    ))
    
    # 1.2 Top Flange (ปีกบน)
    fig.add_trace(make_solid_block(
        beam_center_x, 0, H - (Tf/2),
        L_beam, B, Tf,
        steel_color, 'Top Flange'
    ))
    
    # 1.3 Bottom Flange (ปีกล่าง)
    fig.add_trace(make_solid_block(
        beam_center_x, 0, Tf/2,
        L_beam, B, Tf,
        steel_color, 'Bottom Flange'
    ))

    # ==========================================
    # 🟨 PART 2: SHEAR PLATE (Yellow)
    # ==========================================
    fig.add_trace(make_solid_block(
        pl_x_center, pl_y_center, z_plate_center, # Center
        pw, pt, ph,                               # Size
        '#f1c40f', 'Shear Plate' # Yellow
    ))

    # ==========================================
    # 🟧 PART 3: FILLET WELD (Orange)
    # ==========================================
    # Weld stays at X=setback (Support face)
    # Need to shift coordinates back to support face for weld creation
    weld_x = setback
    weld_y_base = Tw/2
    z_pl_bot = z_plate_top - ph
    
    # Side 1 (Upper fillet relative to plate thickness direction)
    fig.add_trace(go.Mesh3d(
        x=[weld_x, weld_x+weld_sz, weld_x, weld_x, weld_x+weld_sz, weld_x],
        y=[weld_y_base, weld_y_base, weld_y_base+weld_sz, weld_y_base, weld_y_base, weld_y_base+weld_sz],
        z=[z_pl_bot, z_pl_bot, z_pl_bot, z_plate_top, z_plate_top, z_plate_top],
        i=[0, 0, 0, 3], j=[1, 2, 3, 4], k=[2, 3, 4, 5],
        color='#e67e22', name='Weld'
    ))
    # Side 2 (Lower fillet - assuming welding both sides of plate attachment)
    # (Simplified: showing only one side for clarity depending on view, or add another block)
    # Let's stick to one prominent weld bead for visual clarity.

    # ==========================================
    # 🔩 PART 4: REALISTIC BOLTS (Hex)
    # ==========================================
    bolt_x = setback + bolt_dims['leh_beam']
    bolt_color = '#2c3e50' # Dark Grey/Black

    # Grip = Web + Plate
    grip_length = Tw + pt
    # Bolt Start Y (Head side - Web outer face)
    bolt_y_start = -Tw/2 
    # Bolt End Y (Nut side - Plate outer face)
    bolt_y_end = (Tw/2) + pt
    
    for i in range(n_rows):
        bz = z_top_bolt - (i * pitch)
        
        # 4.1 Shank (ก้านน็อต) - Thick line
        fig.add_trace(go.Scatter3d(
            x=[bolt_x, bolt_x],
            y=[bolt_y_start, bolt_y_end+5], # Extend slightly for thread Stick-out
            z=[bz, bz],
            mode='lines',
            line=dict(color=bolt_color, width=dia*0.8), # Width scale roughly to dia
            name='Bolt Shank' if i==0 else None, showlegend=False
        ))
        
        # 4.2 Bolt Head (หัวน็อต) - Hexagon Marker
        fig.add_trace(go.Scatter3d(
            x=[bolt_x], y=[bolt_y_start], z=[bz],
            mode='markers',
            marker=dict(symbol='hexagon', size=dia*1.2, color=bolt_color), # Size scaled to dia
            name='Bolt Head' if i==0 else None, showlegend=(i==0)
        ))
        
        # 4.3 Nut (ตัวเมีย) - Hexagon Marker
        fig.add_trace(go.Scatter3d(
            x=[bolt_x], y=[bolt_y_end], z=[bz],
            mode='markers',
            marker=dict(symbol='hexagon', size=dia*1.2, color=bolt_color),
            name='Nut' if i==0 else None, showlegend=False
        ))

    # ==========================================
    # 📏 PART 5: DIMENSIONS (LEV)
    # ==========================================
    dim_x = bolt_x
    dim_y = pl_y_center + (pt/2) + 20 # Pull out from plate face
    
    fig.add_trace(go.Scatter3d(
        x=[dim_x, dim_x],
        y=[dim_y, dim_y],
        z=[z_top_bolt, z_plate_top],
        mode='lines+markers+text',
        line=dict(color='blue', width=3),
        marker=dict(symbol='diamond-open', size=6, color='blue'),
        text=[f"", f"Lev={lev}"], textposition="top center",
        name='Lev Dim'
    ))

    # ==========================================
    # ⚙️ LAYOUT CONFIG
    # ==========================================
    fig.update_layout(
        scene=dict(
            aspectmode='data', # True Scale 1:1
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            # มุมมอง Isometric สวยๆ
            camera=dict(eye=dict(x=1.6, y=1.6, z=0.6), center=dict(x=0, y=0, z=-0.2))
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        # พื้นหลังใสๆ ให้เหล็กเด่น
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig
