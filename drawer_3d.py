import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. GEOMETRY HELPERS (SHAPES)
# ==========================================

def make_cuboid(center, size, color, name, opacity=1.0):
    """สร้างกล่องสี่เหลี่ยม (Plate/Beam Elements)"""
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
    """สร้างทรงกระบอก (ก้านน็อต / แหวน)"""
    v = p2 - p1
    mag = np.linalg.norm(v)
    if mag == 0: return go.Mesh3d()
    v = v / mag
    
    not_v = np.array([1, 0, 0])
    if np.abs(np.dot(v, not_v)) > 0.9: not_v = np.array([0, 1, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    n_sides = 16 # เพิ่มความละเอียดให้กลมขึ้น
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
    """สร้างปริซึมหกเหลี่ยม (หัวน็อต / ตัวเมีย)"""
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

def make_wedge_weld(p_start, p_end, leg_size, normal_up, normal_out, color='#e67e22'):
    """สร้างรอยเชื่อม Fillet (ทรงสามเหลี่ยมยาว)"""
    # p_start, p_end: จุดเริ่มต้นและสิ้นสุดของแนวเชื่อม
    # leg_size: ขนาดขาเชื่อม
    # normal_up: ทิศทางขาตั้งฉาก (เช่น แกน Z)
    # normal_out: ทิศทางขาแนวนอน (เช่น แกน X ออกจากผิว)
    
    v_len = p_end - p_start
    
    # 3 จุดของหน้าตัดสามเหลี่ยม (ที่จุด Start)
    p1 = p_start
    p2 = p_start + (normal_out * leg_size)
    p3 = p_start + (normal_up * leg_size)
    
    # 3 จุดของหน้าตัดสามเหลี่ยม (ที่จุด End)
    p4 = p1 + v_len
    p5 = p2 + v_len
    p6 = p3 + v_len
    
    # รวม Vertices
    verts = np.array([p1, p2, p3, p4, p5, p6])
    
    # Indices สำหรับวาด Mesh
    # Side faces (rectangular) + End caps (triangular)
    i = [0, 1, 0, 2, 1, 2, 0, 3] 
    j = [1, 4, 2, 5, 2, 5, 2, 5] # Simplified logic manually tuned below
    
    # Manual Mesh Definition for Prism
    # Face 1: Bottom (0-1-4-3)
    # Face 2: Back (0-2-5-3)
    # Face 3: Sloped (1-2-5-4)
    # Face 4: Cap1 (0-1-2)
    # Face 5: Cap2 (3-4-5)
    
    return go.Mesh3d(
        x=verts[:,0], y=verts[:,1], z=verts[:,2],
        i=[0, 0, 0, 0, 1, 1, 3, 3], # Just simplified hull
        j=[1, 2, 3, 4, 2, 5, 4, 5], 
        k=[2, 3, 1, 5, 5, 4, 5, 2], # Convex hull will likely work better or explicit
        color=color, name='Weld'
    )
    
    # Better logic for simple wedge via hull usually works, but explicit:
    return go.Mesh3d(
        x=verts[:,0], y=verts[:,1], z=verts[:,2],
        # 0-1-4, 0-4-3 (Bottom)
        # 0-3-5, 0-5-2 (Back)
        # 1-2-5, 1-5-4 (Slope)
        # 0-2-1 (Cap)
        # 3-4-5 (Cap)
        i=[0, 0, 0, 0, 1, 1, 0, 3],
        j=[1, 4, 3, 5, 2, 5, 2, 4],
        k=[4, 3, 5, 2, 5, 4, 1, 5],
        color=color, name='Fillet Weld'
    )

def add_dim_line(fig, p1, p2, text, color="black", offset_z=0, offset_vec=None):
    """วาดเส้นบอกระยะ"""
    mid = (p1 + p2) / 2
    
    if offset_vec is not None:
        p1 = p1 + offset_vec
        p2 = p2 + offset_vec
        mid = mid + offset_vec
    
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+offset_z, p2[2]+offset_z],
        mode='lines+markers', line=dict(color=color, width=3),
        marker=dict(size=3, color=color, symbol='diamond-open'), showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+offset_z+10], # Text ลอยขึ้นนิดนึง
        mode='text', text=[f"<b>{text}</b>"],
        textposition="middle center", textfont=dict(color=color, size=12), showlegend=False
    ))

# ==========================================
# 2. COMPOSITE BUILDER: REAL BOLT
# ==========================================

def add_real_bolt(fig, center, axis_vec, dia, grip_length):
    """สร้างน็อตสมจริง"""
    head_w = dia * 1.6   
    head_h = dia * 0.65  
    nut_h = dia * 0.85   
    washer_t = 3.0       
    washer_d = dia * 2.1 
    stick_out = dia * 0.5 
    
    total_shank_len = grip_length + washer_t + nut_h + stick_out
    
    # 1. HEAD
    head_pos = center - (axis_vec * head_h / 2)
    fig.add_trace(make_hex_prism(head_pos, axis_vec, head_w, head_h, '#2c3e50', "Bolt Head"))
    
    # 2. SHANK
    p_start = center
    p_end = center + (axis_vec * total_shank_len)
    fig.add_trace(make_cylinder(p_start, p_end, dia/2, '#7f8c8d', "Bolt Shank"))
    
    # 3. WASHER
    washer_pos_start = center + (axis_vec * grip_length)
    washer_pos_end = washer_pos_start + (axis_vec * washer_t)
    fig.add_trace(make_cylinder(washer_pos_start, washer_pos_end, washer_d/2, '#bdc3c7', "Washer"))
    
    # 4. NUT
    nut_pos = washer_pos_end + (axis_vec * nut_h / 2)
    fig.add_trace(make_hex_prism(nut_pos, axis_vec, head_w, nut_h, '#2c3e50', "Nut"))

# ==========================================
# 3. MAIN DRAWING FUNCTION
# ==========================================

def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pl_t, pl_w, pl_h = plate_dims['t'], plate_dims['w'], plate_dims['h']
    # รับค่า weld_sz ถ้าไม่มีให้ default 6
    weld_sz = plate_dims.get('weld_sz', 6)
    
    d_b, n_rows, pitch = bolt_dims['dia'], bolt_dims['n_rows'], bolt_dims['pitch']
    lev, leh_beam = bolt_dims['lev'], bolt_dims['leh_beam']
    setback, L_beam = config['setback'], config['L_beam_show']
    
    fig = go.Figure()

    # --- A. BEAM (Aligned along Y-Axis in this code base) ---
    # Center of beam web is at X=0
    # Beam starts at Y=0 (setback gap is separate visually or part of it)
    # Let's keep consistent: Beam starts at Y=0 and goes +Y
    beam_cy = L_beam / 2
    web_h = H - (2 * Tf)
    
    # Beam Web
    fig.add_trace(make_cuboid([0, beam_cy, 0], [Tw, L_beam, web_h], '#95a5a6', "Web"))
    # Flanges
    z_flange = (web_h/2) + (Tf/2)
    fig.add_trace(make_cuboid([0, beam_cy, z_flange], [B, L_beam, Tf], '#7f8c8d', "Top Flange"))
    fig.add_trace(make_cuboid([0, beam_cy, -z_flange], [B, L_beam, Tf], '#7f8c8d', "Bot Flange"))

    # --- B. SHEAR PLATE ---
    # Plate attached to Web (X+)
    # Plate Y Start = -setback (Support Face)
    # Plate Center Y = -setback + (pl_w / 2)
    pl_y_center = -setback + (pl_w / 2)
    pl_x_center = (Tw/2) + (pl_t/2)
    
    # Bolt Z reference
    # Center group vertically
    z_group_center = 0 # Assume beam center is 0
    # Top Bolt Z (relative to center)
    z_top_bolt = ((n_rows - 1) * pitch) / 2
    
    # Recalculate Plate Z based on Lev
    # Plate Top = Top Bolt + Lev
    z_pl_top = z_top_bolt + lev
    z_pl_center = z_pl_top - (pl_h / 2)
    
    fig.add_trace(make_cuboid([pl_x_center, pl_y_center, z_pl_center], [pl_t, pl_w, pl_h], '#f1c40f', "Shear Plate"))

    # --- C. WELD (FILLET) --- 🟧 ADDED THIS BACK
    # Weld is at Support Face (Y = -setback)
    # At junction of Plate and Support (assumed logical support plane)
    weld_y = -setback
    weld_x = (Tw/2) 
    weld_z_start = z_pl_top - pl_h
    weld_z_end = z_pl_top
    
    # Create simple vertical bars for Weld representation (easier than complex wedge math for now)
    # Side 1 (Top/Bot logic or Side logic) -> Vertical Fillet along the plate height
    # Let's assume weld is on the 'back' of the plate connecting to a column flange at Y=-setback
    
    # Vertical Weld (Left side of plate if looking from X)
    fig.add_trace(make_cuboid(
        [weld_x + pl_t, weld_y, z_pl_center], # Pos
        [weld_sz, weld_sz, pl_h], # Size
        '#e67e22', "Weld Back"
    ))
    
    # --- D. REAL BOLTS ---
    grip = Tw + pl_t
    bolt_start_x = -Tw/2 
    # Bolt Y position: From beam start (0) + leh_beam? 
    # Usually 'leh' is from Beam End. Beam End is at Y=0.
    # So Bolt Y = 0 + leh
    bolt_y = leh_beam 
    
    bolt_axis = np.array([1, 0, 0]) # X+
    
    for i in range(n_rows):
        bz = z_top_bolt - (i * pitch)
        bolt_center = np.array([bolt_start_x, bolt_y, bz])
        add_real_bolt(fig, bolt_center, bolt_axis, d_b, grip)

    # --- E. DIMENSIONS (LEV & OTHERS) ---
    
    # 1. Lev Dimension 📏 (Top Bolt to Top Plate)
    dim_x_lev = pl_x_center + pl_t + 20 # Move out from plate
    add_dim_line(fig, 
                 np.array([dim_x_lev, bolt_y, z_top_bolt]), 
                 np.array([dim_x_lev, bolt_y, z_pl_top]), 
                 f"Lev={lev}", "blue")

    # 2. Gap (Setback)
    dim_x_gap = -B/2 - 40
    add_dim_line(fig, 
                 np.array([dim_x_gap, -setback, 0]), 
                 np.array([dim_x_gap, 0, 0]), 
                 f"c={setback}", "red")

    # 3. Leh
    add_dim_line(fig, 
                 np.array([dim_x_gap, 0, 0]), 
                 np.array([dim_x_gap, bolt_y, 0]), 
                 f"Leh={leh_beam}", "black")

    # Layout Config
    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.8, y=-1.5, z=0.6), up=dict(x=0, y=0, z=1))
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig
