#drawer_3d.py
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. GEOMETRY HELPERS
# ==========================================

def make_cuboid(center, size, color, name, opacity=1.0):
    """สร้างกล่องสี่เหลี่ยม"""
    # Auto-convert inputs to simple variables
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

def make_cylinder(p1, p2, r, color, name="Cylinder"):
    """สร้างทรงกระบอก"""
    # 🛠️ FIX: Force convert to numpy array to avoid List Math Error
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    
    v = p2 - p1
    mag = np.linalg.norm(v)
    if mag == 0: return go.Mesh3d()
    v = v / mag
    
    not_v = np.array([1, 0, 0])
    if np.abs(np.dot(v, not_v)) > 0.9: not_v = np.array([0, 1, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    n_sides = 16 
    theta = np.linspace(0, 2*np.pi, n_sides, endpoint=False)
    x_circ = r * np.cos(theta)
    y_circ = r * np.sin(theta)
    
    verts = []
    for x, y in zip(x_circ, y_circ): verts.append(p1 + x*n1 + y*n2)
    for x, y in zip(x_circ, y_circ): verts.append(p2 + x*n1 + y*n2)
    verts = np.array(verts)
    
    i, j, k = [], [], []
    for idx in range(n_sides):
        nxt = (idx + 1) % n_sides
        i.extend([idx, nxt, idx+n_sides])
        j.extend([nxt, nxt+n_sides, nxt+n_sides])
        k.extend([idx+n_sides, idx+n_sides, idx])

    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], 
                     i=i, j=j, k=k, color=color, flatshading=False, name=name)

def make_hex_prism(center, normal, width, thick, color, name="Hex"):
    """สร้างปริซึมหกเหลี่ยม"""
    # 🛠️ FIX: Force convert inputs
    center = np.array(center, dtype=float)
    normal = np.array(normal, dtype=float)
    
    v = normal / np.linalg.norm(normal)
    not_v = np.array([0, 1, 0]) if np.abs(v[1]) < 0.9 else np.array([1, 0, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    r = width / np.sqrt(3) 
    theta = np.linspace(0, 2*np.pi, 7)[:-1]
    x_c = r * np.cos(theta)
    y_c = r * np.sin(theta)
    
    p_start = center - (v * thick / 2)
    p_end = center + (v * thick / 2)
    
    verts = []
    for x, y in zip(x_c, y_c): verts.append(p_start + x*n1 + y*n2)
    for x, y in zip(x_c, y_c): verts.append(p_end + x*n1 + y*n2)
    verts = np.array(verts)
    
    n = 6
    i, j, k = [], [], []
    for idx in range(n):
        nxt = (idx + 1) % n
        i.extend([idx, nxt, idx+n]); j.extend([nxt, nxt+n, nxt+n]); k.extend([idx+n, idx+n, idx])
    
    for idx in range(1, n-1):
        i.extend([0, 0]); j.extend([idx, idx+1]); k.extend([idx+1, idx]) 
        i.extend([n, n]); j.extend([n+idx, n+idx+1]); k.extend([n+idx+1, n+idx]) 

    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], 
                     i=i, j=j, k=k, color=color, flatshading=True, name=name)

def add_dim_line(fig, p1, p2, text, color="black", offset_z=0, offset_vec=None):
    """วาดเส้นบอกระยะ"""
    # 🛠️ FIX: Main Error Source - Force convert lists to arrays
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    
    mid = (p1 + p2) / 2
    
    if offset_vec is not None:
        ov = np.array(offset_vec, dtype=float)
        p1 = p1 + ov
        p2 = p2 + ov
        mid = mid + ov
    
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+offset_z, p2[2]+offset_z],
        mode='lines+markers', line=dict(color=color, width=3),
        marker=dict(size=3, color=color, symbol='diamond-open'), showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+offset_z+15], 
        mode='text', text=[f"<b>{text}</b>"],
        textposition="middle center", textfont=dict(color=color, size=12), showlegend=False
    ))

# ==========================================
# 2. REAL BOLT BUILDER
# ==========================================
def add_real_bolt(fig, center, axis_vec, dia, grip_length):
    # Ensure numpy arrays
    center = np.array(center, dtype=float)
    axis_vec = np.array(axis_vec, dtype=float)
    
    head_w = dia * 1.6; head_h = dia * 0.65; nut_h = dia * 0.85
    washer_t = 3.0; washer_d = dia * 2.1; stick_out = dia * 0.5 
    total_shank_len = grip_length + washer_t + nut_h + stick_out
    
    # Head
    fig.add_trace(make_hex_prism(center - (axis_vec*head_h/2), axis_vec, head_w, head_h, '#2c3e50', "Head"))
    # Shank
    fig.add_trace(make_cylinder(center, center + (axis_vec*total_shank_len), dia/2, '#7f8c8d', "Shank"))
    # Nut
    nut_pos = center + (axis_vec * (grip_length + washer_t + nut_h/2))
    fig.add_trace(make_hex_prism(nut_pos, axis_vec, head_w, nut_h, '#2c3e50', "Nut"))

# ==========================================
# 3. MAIN LOGIC
# ==========================================
def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pl_t, pl_w, pl_h = plate_dims['t'], plate_dims['w'], plate_dims['h']
    weld_sz = plate_dims.get('weld_sz', 6)
    d_b, n_rows, pitch = bolt_dims['dia'], bolt_dims['n_rows'], bolt_dims['pitch']
    lev, leh_beam = bolt_dims['lev'], bolt_dims['leh_beam']
    setback, L_beam = config['setback'], config['L_beam_show']
    
    fig = go.Figure()

    # --- 0. SUPPORT COLUMN (THE WALL) ---
    col_thick = 20
    col_face_loc = -setback
    col_center_y = col_face_loc - (col_thick / 2)
    
    # Draw huge vertical plate (Column Flange)
    fig.add_trace(make_cuboid(
        [0, col_center_y, 0],       
        [B*2.5, col_thick, H*2.0],  
        '#bdc3c7', "Support Column", opacity=0.6
    ))

    # --- A. BEAM ---
    beam_cy = L_beam / 2
    web_h = H - (2 * Tf)
    fig.add_trace(make_cuboid([0, beam_cy, 0], [Tw, L_beam, web_h], '#95a5a6', "Web"))
    z_flange = (web_h/2) + (Tf/2)
    fig.add_trace(make_cuboid([0, beam_cy, z_flange], [B, L_beam, Tf], '#7f8c8d', "Top Flange"))
    fig.add_trace(make_cuboid([0, beam_cy, -z_flange], [B, L_beam, Tf], '#7f8c8d', "Bot Flange"))

    # --- B. SHEAR PLATE ---
    pl_y_center = -setback + (pl_w / 2)
    pl_x_center = (Tw/2) + (pl_t/2)
    
    z_top_bolt = ((n_rows - 1) * pitch) / 2
    z_pl_top = z_top_bolt + lev
    z_pl_center = z_pl_top - (pl_h / 2)
    
    fig.add_trace(make_cuboid([pl_x_center, pl_y_center, z_pl_center], [pl_t, pl_w, pl_h], '#f1c40f', "Shear Plate"))

    # --- C. WELD (DOUBLE FILLET) ---
    weld_y = -setback + (weld_sz/2) 
    weld_x_base = (Tw/2) 
    
    # Side 1
    fig.add_trace(make_cuboid(
        [weld_x_base + pl_t + weld_sz/2, weld_y, z_pl_center], 
        [weld_sz, weld_sz, pl_h], '#e67e22', "Weld R"
    ))
    # Side 2
    fig.add_trace(make_cuboid(
        [weld_x_base - weld_sz/2, weld_y, z_pl_center], 
        [weld_sz, weld_sz, pl_h], '#e67e22', "Weld L"
    ))

    # --- D. BOLTS ---
    grip = Tw + pl_t
    bolt_start_x = -Tw/2 
    bolt_y = leh_beam
    
    for i in range(n_rows):
        bz = z_top_bolt - (i * pitch)
        add_real_bolt(fig, [bolt_start_x, bolt_y, bz], [1, 0, 0], d_b, grip)

    # --- E. DIMS ---
    # Lev
    dim_x = pl_x_center + pl_t + 30
    add_dim_line(fig, [dim_x, bolt_y, z_top_bolt], [dim_x, bolt_y, z_pl_top], f"Lev={lev}", "blue")
    
    # Setback (Gap)
    dim_gap_x = -B/2 - 50
    add_dim_line(fig, [dim_gap_x, -setback, 0], [dim_gap_x, 0, 0], f"Gap={setback}", "red")

    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=2.0, y=-1.5, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig
