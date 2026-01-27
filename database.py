# database.py
import math

# Dictionary เก็บคุณสมบัติหน้าตัดเหล็ก H-Beam (JIS/TIS Standard)
# หน่วย: Dimension=mm, Weight=kg/m, Area=cm2, Inertia=cm4, Modulus=cm3

SYS_H_BEAMS = {
    "H-100x50x5x7": { 
        "D": 100, "B": 50, "tw": 5, "tf": 7, 
        "W": 9.30, "Ix": 378, "Zx": 75.6, "Iy": 26, "Zy": 10 
    },
    "H-100x100x6x8": { 
        "D": 100, "B": 100, "tw": 6, "tf": 8, 
        "W": 17.2, "Ix": 383, "Zx": 76.6, "Iy": 134, "Zy": 26.8 
    },
    "H-125x60x6x8": { 
        "D": 125, "B": 60, "tw": 6, "tf": 8, 
        "W": 13.2, "Ix": 843, "Zx": 135, "Iy": 56, "Zy": 18 
    },
    "H-125x125x6.5x9": { 
        "D": 125, "B": 125, "tw": 6.5, "tf": 9, 
        "W": 23.8, "Ix": 847, "Zx": 136, "Iy": 293, "Zy": 47 
    },
    "H-148x100x6x9": { 
        "D": 148, "B": 100, "tw": 6, "tf": 9, 
        "W": 21.1, "Ix": 1020, "Zx": 138, "Iy": 151, "Zy": 30 
    },
    "H-150x75x5x7": { 
        "D": 150, "B": 75, "tw": 5, "tf": 7, 
        "W": 14.0, "Ix": 666, "Zx": 88.8, "Iy": 49.5, "Zy": 13.2 
    },
    "H-150x150x7x10": { 
        "D": 150, "B": 150, "tw": 7, "tf": 10, 
        "W": 31.5, "Ix": 1640, "Zx": 219, "Iy": 563, "Zy": 75 
    },
    "H-175x90x5x8": { 
        "D": 175, "B": 90, "tw": 5, "tf": 8, 
        "W": 18.1, "Ix": 1210, "Zx": 138, "Iy": 89, "Zy": 20 
    },
    "H-175x175x7.5x11": { 
        "D": 175, "B": 175, "tw": 7.5, "tf": 11, 
        "W": 40.2, "Ix": 2900, "Zx": 331, "Iy": 984, "Zy": 112 
    },
    "H-194x150x6x9": { 
        "D": 194, "B": 150, "tw": 6, "tf": 9, 
        "W": 29.9, "Ix": 2690, "Zx": 277, "Iy": 507, "Zy": 67.6 
    },
    "H-200x100x5.5x8": { 
        "D": 200, "B": 100, "tw": 5.5, "tf": 8, 
        "W": 21.3, "Ix": 1840, "Zx": 184, "Iy": 134, "Zy": 26.8 
    },
    "H-200x200x8x12": { 
        "D": 200, "B": 200, "tw": 8, "tf": 12, 
        "W": 49.9, "Ix": 4720, "Zx": 472, "Iy": 1600, "Zy": 160 
    },
    "H-244x175x7x11": { 
        "D": 244, "B": 175, "tw": 7, "tf": 11, 
        "W": 44.1, "Ix": 6120, "Zx": 502, "Iy": 984, "Zy": 112 
    },
    "H-248x124x5x8": { 
        "D": 248, "B": 124, "tw": 5, "tf": 8, 
        "W": 25.7, "Ix": 3540, "Zx": 285, "Iy": 255, "Zy": 41.1 
    },
    "H-250x125x6x9": { 
        "D": 250, "B": 125, "tw": 6, "tf": 9, 
        "W": 29.6, "Ix": 4050, "Zx": 324, "Iy": 294, "Zy": 47 
    },
    "H-250x250x9x14": { 
        "D": 250, "B": 250, "tw": 9, "tf": 14, 
        "W": 72.4, "Ix": 10800, "Zx": 864, "Iy": 3650, "Zy": 292 
    },
    "H-294x200x8x12": { 
        "D": 294, "B": 200, "tw": 8, "tf": 12, 
        "W": 56.8, "Ix": 11300, "Zx": 771, "Iy": 1600, "Zy": 160 
    },
    "H-300x150x6.5x9": { 
        "D": 300, "B": 150, "tw": 6.5, "tf": 9, 
        "W": 36.7, "Ix": 7210, "Zx": 481, "Iy": 508, "Zy": 67.7 
    },
    "H-300x300x10x15": { 
        "D": 300, "B": 300, "tw": 10, "tf": 15, 
        "W": 94.0, "Ix": 20400, "Zx": 1360, "Iy": 6750, "Zy": 450 
    },
    "H-340x250x9x14": { 
        "D": 340, "B": 250, "tw": 9, "tf": 14, 
        "W": 79.7, "Ix": 21700, "Zx": 1280, "Iy": 3650, "Zy": 292 
    },
    "H-350x175x7x11": { 
        "D": 350, "B": 175, "tw": 7, "tf": 11, 
        "W": 49.6, "Ix": 13600, "Zx": 775, "Iy": 984, "Zy": 112 
    },
    "H-350x350x12x19": { 
        "D": 350, "B": 350, "tw": 12, "tf": 19, 
        "W": 137.0, "Ix": 40300, "Zx": 2300, "Iy": 13600, "Zy": 776 
    },
    "H-390x300x10x16": { 
        "D": 390, "B": 300, "tw": 10, "tf": 16, 
        "W": 107.0, "Ix": 38700, "Zx": 1980, "Iy": 7210, "Zy": 481 
    },
    "H-400x200x8x13": { 
        "D": 400, "B": 200, "tw": 8, "tf": 13, 
        "W": 66.0, "Ix": 23700, "Zx": 1190, "Iy": 1740, "Zy": 174 
    },
    "H-400x400x13x21": { 
        "D": 400, "B": 400, "tw": 13, "tf": 21, 
        "W": 172.0, "Ix": 66600, "Zx": 3330, "Iy": 22400, "Zy": 1120 
    },
    "H-440x300x11x18": { 
        "D": 440, "B": 300, "tw": 11, "tf": 18, 
        "W": 124.0, "Ix": 56100, "Zx": 2550, "Iy": 8110, "Zy": 541 
    },
    "H-450x200x9x14": { 
        "D": 450, "B": 200, "tw": 9, "tf": 14, 
        "W": 76.0, "Ix": 33500, "Zx": 1490, "Iy": 1870, "Zy": 187 
    },
    "H-500x200x10x16": { 
        "D": 500, "B": 200, "tw": 10, "tf": 16, 
        "W": 89.6, "Ix": 47800, "Zx": 1910, "Iy": 2140, "Zy": 214 
    },
    "H-588x300x12x20": { 
        "D": 588, "B": 300, "tw": 12, "tf": 20, 
        "W": 151.0, "Ix": 118000, "Zx": 4020, "Iy": 9020, "Zy": 601 
    },
    "H-600x200x11x17": { 
        "D": 600, "B": 200, "tw": 11, "tf": 17, 
        "W": 106.0, "Ix": 77600, "Zx": 2590, "Iy": 2280, "Zy": 228 
    },
    "H-700x300x13x24": { 
        "D": 700, "B": 300, "tw": 13, "tf": 24, 
        "W": 185.0, "Ix": 201000, "Zx": 5760, "Iy": 10800, "Zy": 722 
    },
    "H-800x300x14x26": { 
        "D": 800, "B": 300, "tw": 14, "tf": 26, 
        "W": 210.0, "Ix": 292000, "Zx": 7290, "Iy": 11700, "Zy": 780 
    },
    "H-900x300x16x28": { 
        "D": 900, "B": 300, "tw": 16, "tf": 28, 
        "W": 243.0, "Ix": 404000, "Zx": 8980, "Iy": 12600, "Zy": 841 
    }
}

# --- Post-Processing to Ensure Completeness (Engineering Fix) ---
for key, val in SYS_H_BEAMS.items():
    # Convert dimensions from mm to cm for calculation check
    D_cm = val['D'] / 10
    B_cm = val['B'] / 10
    tw_cm = val['tw'] / 10
    tf_cm = val['tf'] / 10
    
    # 1. Fill missing 'r' (Radius of fillet)
    # Estimate r approx equal to tf if not present (Safe assumption for general hot-rolled)
    if 'r' not in val:
        val['r'] = val['tf'] 
    
    # 2. Fill missing 'A' (Area in cm2)
    # If not present, calculate precisely from Weight (kg/m) / 0.785 (Steel Density)
    if 'A' not in val:
        val['A'] = val['W'] / 0.785
    
    # 3. Fill missing 'ry' (Radius of Gyration Y-axis in cm)
    # ry = sqrt(Iy / A)
    if 'ry' not in val:
        val['ry'] = math.sqrt(val['Iy'] / val['A'])

    # 4. Fill missing 'Sx' (Elastic Modulus)
    if 'Sx' not in val:
        val['Sx'] = val['Ix'] / (D_cm / 2)
