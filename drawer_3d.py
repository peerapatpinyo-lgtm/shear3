import plotly.graph_objects as go
import numpy as np

# --- 1. LOW-LEVEL GEOMETRY HELPERS ---

def make_cuboid(center, size, color, name, opacity=1.0):
    """สร้าง Mesh สี่เหลี่ยม (True Scale)"""
    x, y, z = center
    dx, dy, dz = size
    return go.Mesh3d(
        x=[x-dx/2, x-dx/2, x+dx/2, x+dx/2, x-dx/2, x-dx/2, x+dx/2, x+dx/2],
        y=[y-dy/2, y+dy/2, y+dy/2, y-dy/2, y-dy/2, y+dy/2, y+dy/2, y-dy/2],
        z=[z-dz/2, z-dz/2, z-dz/2, z-dz/2, z+dz/2, z+dz/2, z+dz/2, z+dz/2],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, flatshading=True, name=name,
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.2)
    )

def add_dim_line(fig, p1, p2, text, color="black", offset_z=0):
    """วาดเส้นบอกระยะ (Dimension Line)"""
    mid = (p1 + p2) / 2
    # 1. เส้นหลัก
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+offset_z, p2[2]+offset_z],
        mode='lines+markers', 
        line=dict(color=color, width=4),
        marker=dict(size=4, color=color, symbol='circle'), 
        showlegend=False
    ))
    # 2. ตัวหนังสือ
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+offset_z+15], # ยกตัวหนังสือลอยขึ้น
        mode='text', text=[f"<b>{text}</b>"],
        textposition="middle center", 
        textfont=dict(color=color, size=14, family="Arial Black"), 
        showlegend=False
    ))

# --- 2. MAIN DRAWING FUNCTION ---

def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    """
    ฟังก์ชันหลักสำหรับสร้าง 3D Figure
    beam_dims: dict {H, B, Tw, Tf}
    plate_dims: dict {t, w, h}
    bolt_dims: dict {dia, n_rows, pitch, lev, leh_beam}
    config: dict {setback, L_beam_show}
    """
    
    # Unpack Data
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pl_t, pl_w, pl_h = plate_dims['t'], plate_dims['w'], plate_dims['h']
    d_b, n_rows, pitch = bolt_dims['dia'], bolt_dims['n_rows'], bolt_dims['pitch']
    lev, leh_beam = bolt_dims['lev'], bolt_dims['leh_beam']
    
    setback = config['setback']
    L_beam = config['L_beam_show']
    
    fig = go.Figure()

    # --- A. GHOST COLUMN (Extended) ---
    col_face_y = -setback
    col_width = B * 2.5
    col_height = H * 3.0
    
    fig.add_trace(make_cuboid(
        center=[0, col_face_y - 10, 0], 
        size=[col_width, 20, col_height], 
        color='#bdc3c7', name="Column Face", opacity=0.3
    ))

    # --- B. BEAM (True Scale) ---
    beam_cy = L_beam / 2
    web_h = H - (2 * Tf)
    
    # Web
    fig.add_trace(make_cuboid([0, beam_cy, 0], [Tw, L_beam, web_h], '#7f8c8d', "Web"))
    # Flanges
    z_flange = (web_h/2) + (Tf/2)
    fig.add_trace(make_cuboid([0, beam_cy, z_flange], [B, L_beam, Tf], '#7f8c8d', "Top Flange"))
    fig.add_trace(make_cuboid([0, beam_cy, -z_flange], [B, L_beam, Tf], '#7f8c8d', "Bot Flange"))

    # --- C. SHEAR PLATE ---
    # Center Y of plate = start (-setback) + half width
    pl_y_center = -setback + (pl_w / 2)
    pl_x = (Tw/2) + (pl_t/2)
    
    fig.add_trace(make_cuboid(
        center=[pl_x, pl_y_center, 0],
        size=[pl_t, pl_w, pl_h],
        color='#f1c40f', name="Shear Plate"
    ))

    # --- D. BOLTS ---
    bolt_len = Tw + pl_t + 30
    bx = pl_x - (pl_t/2) + (pl_t/2)
    by = leh_beam # Distance from Beam End (Y=0)
    z_start = (pl_h/2) - lev
    
    for i in range(n_rows):
        bz = z_start - (i * pitch)
        # Bolt Body
        fig.add_trace(go.Scatter3d(
            x=[bx - bolt_len/2, bx + bolt_len/2], y=[by, by], z=[bz, bz],
            mode='lines', line=dict(color='#c0392b', width=d_b), name='Bolt'
        ))
        # Bolt Head (Marker)
        fig.add_trace(go.Scatter3d(
            x=[bx + bolt_len/2], y=[by], z=[bz],
            mode='markers', marker=dict(size=d_b*0.8, color='black', symbol='diamond'), 
            showlegend=False
        ))

    # --- E. DIMENSION LINES ---
    dim_x = -B/2 - 60 # ขยับออกด้านข้าง
    
    # 1. GAP [RED]
    add_dim_line(fig, 
        np.array([dim_x, -setback, 0]), 
        np.array([dim_x, 0, 0]), 
        f"Gap={setback}", "red")

    # 2. LEH [BLUE]
    add_dim_line(fig, 
        np.array([dim_x, 0, 0]), 
        np.array([dim_x, by, 0]), 
        f"Leh={leh_beam}", "blue")

    # 3. PITCH & PLATE HEIGHT
    if n_rows > 1:
        dim_x_p = B/2 + 60
        # Pitch [Green]
        add_dim_line(fig, 
            np.array([dim_x_p, by, z_start]), 
            np.array([dim_x_p, by, z_start - pitch]), 
            f"Pitch={pitch}", "green")
        # Plate Height [Black]
        add_dim_line(fig,
            np.array([dim_x_p, pl_y_center, pl_h/2]),
            np.array([dim_x_p, pl_y_center, -pl_h/2]),
            f"H={pl_h:.0f}", "black")

    # --- F. LAYOUT ---
    fig.update_layout(
        scene=dict(
            aspectmode='data', # Force 1:1 Scale
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=2.2, y=0.8, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0), height=500
    )
    
    return fig
