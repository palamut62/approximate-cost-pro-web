# -*- coding: utf-8 -*-
"""Debug extraction for a single poz"""

import fitz
import re
from pathlib import Path

def extract_with_debug(pdf_path, target_poz_start_idx, max_lines=500):
    """Extract and debug sub-analyses for a specific poz"""
    doc = fitz.open(pdf_path)
    lines_all = []

    # Extract all lines
    for page in doc:
        text = page.get_text()
        lines = text.split('\n')
        lines_all.extend(lines)

    doc.close()

    # Find the poz
    start_idx = None
    for idx, line in enumerate(lines_all):
        if line.strip() == "15.100.1001" and target_poz_start_idx == 1:
            start_idx = idx
            break
        if line.strip() == "15.115.1208" and target_poz_start_idx == 2:
            start_idx = idx
            break

    if start_idx is None:
        print(f"Poz not found!")
        return

    print(f"\nDEBUG: Starting from line {start_idx} ('{lines_all[start_idx].strip()}')\n")

    sub_analyses = []
    current_type = ""
    i = start_idx + 1

    while i < min(start_idx + max_lines, len(lines_all)):
        line = lines_all[i].strip()

        # Check for "Poz No" + next line with 15/19.xxx
        if line == "Poz No" and i + 1 < len(lines_all):
            next_line = lines_all[i + 1].strip()
            if re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                print(f">>> BREAK: Found 'Poz No' at line {i}, next is '{next_line}' - BREAKING")
                break
            else:
                print(f"    Line {i}: 'Poz No' but next is '{next_line}' - continuing")

        # Code detection
        if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', line):
            code = line
            print(f"    Line {i}: FOUND CODE '{code}'")

            # Try to extract data
            j = i + 1
            name_lines = []
            unit = ""
            qty_str = ""
            price_str = ""

            while j < len(lines_all):
                current = lines_all[j].strip()
                if not current:
                    j += 1
                    continue

                # Check if it's a unit
                known_units = ["Sa", "Kg", "m³", "m", "m²", "L", "dk", "Saat", "kg", "ha", "gün",
                              "ton", "Ton", "mL", "cm", "mm", "km", "t", "hm"]
                is_unit = current in known_units

                if not is_unit:
                    cleaned = current.replace('³', '').replace('²', '')
                    is_unit = (len(current) <= 3 and
                              all(c.isalpha() or c in '³²' for c in current) and
                              current not in ["Su", "Yal", "Bez", "Cam", "Yer", "Yol"])

                if is_unit:
                    unit = current
                    qty_str = lines_all[j + 1].strip() if j + 1 < len(lines_all) else ""
                    price_str = lines_all[j + 2].strip() if j + 2 < len(lines_all) else ""
                    print(f"      -> Found unit '{unit}' at line {j}, qty='{qty_str}', price='{price_str}'")
                    break
                else:
                    name_lines.append(current)
                    print(f"        Line {j}: '{current[:50]}...'")

                j += 1

            name = " ".join(name_lines)
            if name and unit and qty_str and price_str:
                print(f"      => EXTRACTED: {code} | {name[:30]} | {unit} | {qty_str} | {price_str}")
                sub_analyses.append({'code': code, 'name': name[:30]})
            else:
                print(f"      => INCOMPLETE: name={bool(name)}, unit={bool(unit)}, qty={bool(qty_str)}, price={bool(price_str)}")

        i += 1

    print(f"\nTotal extracted: {len(sub_analyses)}")
    for sub in sub_analyses:
        print(f"  - {sub['code']}: {sub['name']}")

if __name__ == "__main__":
    pdf1 = Path("C:/Users/umuti/Desktop/deneembos/yaklasik_maliyet_pro/ANALIZ/Analiz-1.pdf")

    print("=" * 80)
    print("DEBUG: Extract sub-analyses with detailed tracing")
    print("=" * 80)

    print("\n### TESTING: POZ 15.100.1001 ###")
    extract_with_debug(str(pdf1), 1, max_lines=500)

    print("\n\n### TESTING: POZ 15.115.1208 ###")
    extract_with_debug(str(pdf1), 2, max_lines=500)
