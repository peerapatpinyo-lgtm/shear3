import math

# ==============================================================================
# 🧠 CALCULATOR MODULE: SHEAR TAB (SINGLE PLATE)
# ==============================================================================
# ไฟล์นี้ทำหน้าที่คำนวณกำลังรับน้ำหนัก (Capacity) ของจุดต่อ
# ตามมาตรฐาน AISC 360-16 (LRFD)
# หน่วยที่ใช้คำนวณภายใน: kg, cm (ksc)
# ==============================================================================

# 1. ฐานข้อมูลวัสดุ (Material Database) -- หน่วย ksc (kg/cm2)
MATERIALS = {
    # เหล็กรูปพรรณ/เพลท
    "A36":     {"Fy": 2500, "Fu": 4000},  # ~Fy 250 MPa
    "A572-50": {"Fy": 3450, "Fu": 4500},  # ~Fy 345 MPa
    "SS400":   {"Fy": 2400, "Fu": 4100},  # JIS Standard
    "SM490":   {"Fy": 3300, "Fu": 5000},
    
    # น็อต (Bolt) -- Fnv = Shear Strength
    "A325":    {"Fnv": 3720, "Fnt": 6200}, # Fnv ~ 372 MPa
    "A490":    {"Fnv": 4690, "Fnt": 7800},
    "Gr.8.8":  {"Fnv": 3750, "Fnt": 8000}
}

# 2. ตัวคูณลดกำลัง (Resistance Factors - LRFD)
PHI = {
    "yield": 1.00,       # Plate Yielding
    "rupture": 0.75,     # Plate Rupture
    "bolt_shear": 0.75,  # Bolt Shear
    "bearing": 0.75,     # Bolt Bearing
    "block": 0.75,       # Block Shear
    "weld": 0.75         # Weld Strength
}

def calculate_shear_tab(inputs):
    """
    ฟังก์ชันหลักคำนวณกำลังรับแรงเฉือนของ Shear Tab
    
    Args:
        inputs (dict): รับค่าจาก UI (หน่วย mm และ kg)
    
    Returns:
        dict: ผลลัพธ์การคำนวณแต่ละ Mode และสรุป Pass/Fail
    """
    
    # --- A. แปลงหน่วย (Input mm -> Calc cm) ---
    Vu = float(inputs.get('load', 0))       # kg
    
    t_w = inputs['beam_tw'] / 10.0          # cm (Web Thickness)
    t_p = inputs['plate_t'] / 10.0          # cm (Plate Thickness)
    h_p = inputs['plate_h'] / 10.0          # cm (Plate Height)
    d_b = inputs['bolt_dia'] / 10.0         # cm (Bolt Diameter)
    w_sz = inputs['weld_sz'] / 10.0         # cm (Weld Size)
    
    pitch = inputs['pitch'] / 10.0          # cm
    lev = inputs['lev'] / 10.0              # cm (Dist to Top/Bot edge)
    leh = inputs['leh'] / 10.0              # cm (Dist to Side edge)
    n_rows = int(inputs['n_rows'])
    
    # ดึงค่าวัสดุ
    mat_bm = MATERIALS.get(inputs.get('beam_mat', 'A36'), MATERIALS['A36'])
    mat_pl = MATERIALS.get(inputs.get('plate_mat', 'A36'), MATERIALS['A36'])
    mat_bolt = MATERIALS.get(inputs.get('bolt_grade', 'A325'), MATERIALS['A325'])
    
    # ขนาดรูเจาะ (Bolt Hole) = dia + 2mm (มาตรฐานทั่วไป)
    d_hole = d_b + 0.2 
    
    results = {}
    
    # ==========================================================================
    # 1. 🔩 BOLT SHEAR (แรงเฉือนน็อต)
    # ==========================================================================
    # สูตร: Phi * Fnv * Ab * N
    Ab = math.pi * (d_b**2) / 4
    Fnv = mat_bolt['Fnv']
    
    # ถ้าเกลียวอยู่ในระนาบเฉือน (N) ใช้ค่าปกติ, ถ้าไม่อยู่ (X) เพิ่มกำลัง (แล้วแต่ Code)
    # ในที่นี้สมมติว่าเป็น Type N (Included) เป็น Default เพื่อความปลอดภัย
    
    Rn_bolt = Fnv * Ab * n_rows
    phi_Rn_bolt = PHI['bolt_shear'] * Rn_bolt
    
    results['bolt_shear'] = {
        "title": "Bolt Shear",
        "phi_Rn": phi_Rn_bolt,
        "ratio": Vu / phi_Rn_bolt if phi_Rn_bolt > 0 else 999,
        "desc": f"φRn = {PHI['bolt_shear']} × {n_rows} × {Fnv}ksc × {Ab:.2f}cm²"
    }

    # ==========================================================================
    # 2. 🧱 BEARING STRENGTH (แรงแบกทาน) - เช็คทั้ง Plate และ Beam Web
    # ==========================================================================
    # สูตร: 1.2 * Lc * t * Fu <= 2.4 * d * t * Fu
    
    def calc_bearing(t, Fu, edge_dist):
        # รูริม (Edge Bolt)
        Lc_edge = edge_dist - (d_hole / 2)
        Rn_edge = min(1.2 * Lc_edge * t * Fu, 2.4 * d_b * t * Fu)
        
        # รูใน (Inner Bolts)
        Rn_inner = 0
        if n_rows > 1:
            Lc_inner = pitch - d_hole
            Rn_inner_1 = min(1.2 * Lc_inner * t * Fu, 2.4 * d_b * t * Fu)
            Rn_inner = Rn_inner_1 * (n_rows - 1)
            
        return PHI['bearing'] * (Rn_edge + Rn_inner)

    # 2.1 Check Plate
    phi_bear_pl = calc_bearing(t_p, mat_pl['Fu'], lev) # ใช้ lev หรือ leh ขึ้นกับทิศทางแรง (แรงลงแนวดิ่ง ใช้ lev)
    # หมายเหตุ: Shear Tab รับแรงแนวดิ่ง (Shear) ระยะฉีกขาดคือ Lev (ระยะขอบล่างของรูล่างสุด)
    # แต่ปกติเราเช็ค Lev ของรูล่างสุด สมมติว่า Lev บนล่างเท่ากัน
    
    # 2.2 Check Beam Web
    # คานมักจะมีระยะ Lev beam มากกว่าเพลท แต่เพื่อความชัวร์ใช้ lev เพลทเป็นตัวเทียบเคียงกรณีวิกฤต หรือรับค่าแยก
    # ในที่นี้สมมติ Beam Web แข็งแรงพอที่ระยะขอบ หรือใช้ค่าเดียวกันคำนวณ
    phi_bear_bm = calc_bearing(t_w, mat_bm['Fu'], lev) 
    
    # เลือกค่าน้อยที่สุดเป็นตัวคุม (Governing)
    if phi_bear_pl < phi_bear_bm:
        bear_val = phi_bear_pl
        bear_txt = f"Plate (t={t_p*10:.0f}mm) Controls"
    else:
        bear_val = phi_bear_bm
        bear_txt = f"Beam Web (tw={t_w*10:.0f}mm) Controls"
        
    results['bearing'] = {
        "title": "Bolt Bearing",
        "phi_Rn": bear_val,
        "ratio": Vu / bear_val if bear_val > 0 else 999,
        "desc": bear_txt
    }

    # ==========================================================================
    # 3. 📏 SHEAR YIELDING (เพลทคราก)
    # ==========================================================================
    # สูตร: Phi * 0.60 * Fy * Ag
    Ag = h_p * t_p
    Rn_y = 0.60 * mat_pl['Fy'] * Ag
    phi_Rn_y = PHI['yield'] * Rn_y
    
    results['shear_yield'] = {
        "title": "Shear Yielding",
        "phi_Rn": phi_Rn_y,
        "ratio": Vu / phi_Rn_y if phi_Rn_y > 0 else 999,
        "desc": f"φRn = 1.0 × 0.6Fy × {Ag:.1f}cm²"
    }

    # ==========================================================================
    # 4. ✂️ SHEAR RUPTURE (เพลทขาด)
    # ==========================================================================
    # สูตร: Phi * 0.60 * Fu * Anv
    # Anv = พื้นที่หน้าตัดสุทธิในแนวแรงเฉือน
    Anv = (h_p - (n_rows * d_hole)) * t_p
    Rn_r = 0.60 * mat_pl['Fu'] * Anv
    phi_Rn_r = PHI['rupture'] * Rn_r
    
    results['shear_rupture'] = {
        "title": "Shear Rupture",
        "phi_Rn": phi_Rn_r,
        "ratio": Vu / phi_Rn_r if phi_Rn_r > 0 else 999,
        "desc": f"Anv = {Anv:.2f}cm² (Hole -{n_rows})"
    }

    # ==========================================================================
    # 5. 🔥 WELD STRENGTH (รอยเชื่อม)
    # ==========================================================================
    # สูตร: Phi * 0.707 * w * L * 0.60 * Fexx * 2 sides
    # สมมติใช้ลวดเชื่อม E70xx (Fu = 4900 ksc / 70 ksi)
    Fexx = 4900 
    L_weld = h_p # ความยาวเชื่อมเท่ากับความสูงเพลท
    
    Rn_weld = 0.707 * w_sz * L_weld * 0.60 * Fexx * 2 # 2 ด้าน
    phi_Rn_weld = PHI['weld'] * Rn_weld
    
    results['weld'] = {
        "title": "Weld Strength",
        "phi_Rn": phi_Rn_weld,
        "ratio": Vu / phi_Rn_weld if phi_Rn_weld > 0 else 999,
        "desc": f"Fillet {w_sz*10:.0f}mm, L={L_weld*10:.0f}mm (2 Sides)"
    }

    # ==========================================================================
    # 🏁 SUMMARY (สรุปผล)
    # ==========================================================================
    # หาค่าที่รับได้น้อยที่สุด (Governing Capacity)
    min_phi_Rn = min(phi_Rn_bolt, bear_val, phi_Rn_y, phi_Rn_r, phi_Rn_weld)
    
    status = "✅ PASS" if min_phi_Rn >= Vu else "❌ FAIL"
    
    # เรียงลำดับโหมดความเสียหายที่วิกฤตที่สุด
    sorted_modes = sorted(results.items(), key=lambda item: item[1]['ratio'], reverse=True)
    critical_mode = sorted_modes[0][1]['title']
    
    results['summary'] = {
        "status": status,
        "gov_capacity": min_phi_Rn,
        "gov_mode": critical_mode,
        "utilization": Vu / min_phi_Rn if min_phi_Rn > 0 else 0.0
    }
    
    return results

# ==============================================================================
# TESTER (สำหรับรันทดสอบไฟล์นี้เดี่ยวๆ)
# ==============================================================================
if __name__ == "__main__":
    # ลองใส่ค่ามั่วๆ ทดสอบดู
    test_input = {
        'load': 5000, 'beam_tw': 8, 'plate_t': 10, 'plate_h': 200,
        'bolt_dia': 20, 'n_rows': 3, 'pitch': 70, 'lev': 35, 'leh': 35, 'weld_sz': 6
    }
    print(calculate_shear_tab(test_input))
