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
    
    # ความละเอียด (8 เหลี่ยมก็พอจะได้ไม่หนักเครื่อง)
    n_sides = 12 
    theta = np.linspace(0, 2*np.pi, n_sides, endpoint=False)
    x_circ = r * np.cos(theta)
    y_circ = r * np.sin(theta)
    
    verts = []
    # Bottom Cap
    for x, y in zip(x_circ, y_circ): verts.append(p1 + x*n1 + y*n2)
    # Top Cap
    for x, y in zip(x_circ, y_circ): verts.append(p2 + x*n1 + y*n2)
    verts = np.array(verts)
    
    # Triangles indices
    i, j, k = [], [], []
    for idx in range(n_sides):
        nxt = (idx + 1) % n_sides
        # Side faces
        i.extend([idx, nxt, idx+n_sides])
        j.extend([nxt, nxt+n_sides, nxt+n_sides])
        k.extend([idx+n_sides, idx+n_sides, idx])
        
        # Caps (Simple fan for caps usually, but side mesh is enough for small bolts)
        # Add Cap logic if needed, but for small bolts, open ends are rarely seen

    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], 
                     i=i, j=j, k=k, color=color, flatshading=False, name=name)

def make_hex_prism(center, normal, width, thick, color, name="Hex"):
    """สร้างปริซึมหกเหลี่ยม (หัวน็อต / ตัวเมีย)"""
    # Normal vector handling
    v = normal / np.linalg.norm(normal)
    not_v = np.array([0, 1, 0]) if np.abs(v[1]) < 0.9 else np.array([1, 0, 0])
    n1 = np.cross(v, not_v); n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    
    # Hexagon Geometry
    r = width / np.sqrt(3) # Convert Flat-to-Flat width to Radius
    theta = np.linspace(0, 2*np.pi, 7)[:-1] # 6 points
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
    # Sides
    for idx in range(n):
        nxt = (idx + 1) % n
        i.extend([idx, nxt, idx+n]); j.extend([nxt, nxt+n, nxt+n]); k.extend([idx+n, idx+n, idx])
        
    # Caps (Front/Back faces)
    # Front (0,1,2), (0,2,3)... fan style
    for idx in range(1, n-1):
        i.extend([0, 0]); j.extend([idx, idx+1]); k.extend([idx+1, idx]) # Front
        i.extend([n, n]); j.extend([n+idx, n+idx+1]); k.extend([n+idx+1, n+idx]) # Back (needs flip check)

    return go.Mesh3d(x=verts[:,0], y=verts[:,1], z=verts[:,2], 
                     i=i, j=j, k=k, color=color, flatshading=True, name=name)

def add_dim_line(fig, p1, p2, text, color="black", offset_z=0):
    """วาดเส้นบอกระยะ"""
    mid = (p1 + p2) / 2
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]], y=[p1[1], p2[1]], z=[p1[2]+offset_z, p2[2]+offset_z],
        mode='lines+markers', line=dict(color=color, width=4),
        marker=dict(size=3, color=color, symbol='circle'), showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[mid[0]], y=[mid[1]], z=[mid[2]+offset_z+15],
        mode='text', text=[f"<b>{text}</b>"],
        textposition="middle center", textfont=dict(color=color, size=14, family="Arial Black"), showlegend=False
    ))

# ==========================================
# 2. COMPOSITE BUILDER: REAL BOLT
# ==========================================

def add_real_bolt(fig, center, axis_vec, dia, grip_length):
    """
    สร้างน็อตสมจริง (Head + Shank + Washer + Nut)
    center: จุดกึ่งกลางแกน bolt (ที่ผิว Web ด้านหัวน็อต)
    axis_vec: เวกเตอร์ทิศทาง (ปกติคือแกน X)
    grip_length: ความหนารวมที่หนีบ (Tw + Plate_t)
    """
    # Dimension Standards (Approx ISO/AISC)
    head_w = dia * 1.6   # Width across flats
    head_h = dia * 0.65  # Head thickness
    nut_h = dia * 0.85   # Nut thickness
    washer_t = 3.0       # Washer thickness
    washer_d = dia * 2.1 # Washer diameter
    stick_out = dia * 0.5 # ปลายเกลียวโผล่
    
    total_shank_len = grip_length + washer_t + nut_h + stick_out
    
    # 1. HEAD (Hexagon)
    # จุดวางหัว = center ถอยหลังไปครึ่งหนึ่งของความหนาหัว
    head_pos = center - (axis_vec * head_h / 2)
    fig.add_trace(make_hex_prism(head_pos, axis_vec, head_w, head_h, '#2c3e50', "Bolt Head"))
    
    # 2. SHANK (Cylinder)
    # เริ่มจากผิว Web (center) ยาวทะลุไปจนจบ
    p_start = center
    p_end = center + (axis_vec * total_shank_len)
    fig.add_trace(make_cylinder(p_start, p_end, dia/2, '#95a5a6', "Bolt Shank"))
    
    # 3. WASHER (Cylinder flat)
    # อยู่ต่อจาก Grip Length
    washer_pos_start = center + (axis_vec * grip_length)
    washer_pos_end = washer_pos_start + (axis_vec * washer_t)
    fig.add_trace(make_cylinder(washer_pos_start, washer_pos_end, washer_d/2, '#bdc3c7', "Washer"))
    
    # 4. NUT (Hexagon)
    # อยู่ต่อจาก Washer
    nut_pos = washer_pos_end + (axis_vec * nut_h / 2)
    fig.add_trace(make_hex_prism(nut_pos, axis_vec, head_w, nut_h, '#2c3e50', "Nut"))

# ==========================================
# 3. MAIN DRAWING FUNCTION
# ==========================================

def create_connection_figure(beam_dims, plate_dims, bolt_dims, config):
    H, B, Tw, Tf = beam_dims['H'], beam_dims['B'], beam_dims['Tw'], beam_dims['Tf']
    pl_t, pl_w, pl_h = plate_dims['t'], plate_dims['w'], plate_dims['h']
    d_b, n_rows, pitch = bolt_dims['dia'], bolt_dims['n_rows'], bolt_dims['pitch']
    lev, leh_beam = bolt_dims['lev'], bolt_dims['leh_beam']
    setback, L_beam = config['setback'], config['L_beam_show']
    
    fig = go.Figure()

    # --- A. GHOST COLUMN ---
    col_face_y = -setback
    fig.add_trace(make_cuboid([0, col_face_y - 10, 0], [B*2.5, 20, H*3.0], '#bdc3c7', "Column", opacity=0.3))

    # --- B. BEAM ---
    beam_cy = L_beam / 2
    web_h = H - (2 * Tf)
    fig.add_trace(make_cuboid([0, beam_cy, 0], [Tw, L_beam, web_h], '#7f8c8d', "Web"))
    z_flange = (web_h/2) + (Tf/2)
    fig.add_trace(make_cuboid([0, beam_cy, z_flange], [B, L_beam, Tf], '#7f8c8d', "Top Flange"))
    fig.add_trace(make_cuboid([0, beam_cy, -z_flange], [B, L_beam, Tf], '#7f8c8d', "Bot Flange"))

    # --- C. SHEAR PLATE ---
    pl_y_center = -setback + (pl_w / 2)
    # Plate ติดด้านขวาของ Web (X+)
    pl_x = (Tw/2) + (pl_t/2)
    fig.add_trace(make_cuboid([pl_x, pl_y_center, 0], [pl_t, pl_w, pl_h], '#f1c40f', "Shear Plate"))

    # --- D. REAL BOLTS ---
    # Grip Length = Web + Plate
    grip = Tw + pl_t
    
    # Start Position (ที่ผิว Web ด้านซ้าย เพื่อร้อยไปทางขวา)
    # Web ผิวซ้ายอยู่ที่ x = -Tw/2
    bolt_start_x = -Tw/2 
    bolt_y = leh_beam
    z_start = (pl_h/2) - lev
    
    bolt_axis = np.array([1, 0, 0]) # ชี้ไปทาง X+
    
    for i in range(n_rows):
        bz = z_start - (i * pitch)
        bolt_center = np.array([bolt_start_x, bolt_y, bz])
        
        # เรียกฟังก์ชันสร้างน็อตจริง
        add_real_bolt(fig, bolt_center, bolt_axis, d_b, grip)

    # --- E. DIMENSIONS ---
    dim_x = -B/2 - 60
    add_dim_line(fig, np.array([dim_x, -setback, 0]), np.array([dim_x, 0, 0]), f"Gap={setback}", "red")
    add_dim_line(fig, np.array([dim_x, 0, 0]), np.array([dim_x, bolt_y, 0]), f"Leh={leh_beam}", "blue")

    if n_rows > 1:
        dim_x_p = B/2 + 60
        add_dim_line(fig, np.array([dim_x_p, bolt_y, z_start]), np.array([dim_x_p, bolt_y, z_start-pitch]), f"Pitch={pitch}", "green")
        add_dim_line(fig, np.array([dim_x_p, pl_y_center, pl_h/2]), np.array([dim_x_p, pl_y_center, -pl_h/2]), f"H={pl_h:.0f}", "black")

    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.8, y=0.8, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0), height=500
    )
    
    return fig
