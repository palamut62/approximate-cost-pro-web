# -*- coding: utf-8 -*-
"""Minimal test that exactly mimics _extract_sub_analyses"""

import fitz
import re
from pathlib import Path

def extract_sub_analyses_exact(lines, start_idx):
    """EXACT copy of the method from poz_analiz_viewer.py"""
    sub_analyses = []
    current_type = ""

    start_poz_no = lines[start_idx].strip() if start_idx < len(lines) else ""

    i = start_idx + 1
    break_count = 0
    print(f"    Loop from {i} to {min(start_idx + 500, len(lines))}")
    while i < min(start_idx + 500, len(lines)):
        line = lines[i].strip()

        # Yeni pozun başlangıç işareti: "Poz No" başlığı + sonra bir 15/19.xxx kodu
        # Bu şekilde ana poz sınırını belirleyebiliriz
        # Special logging for line 167
        if i == 167:
            print(f"    *** LINE 167: line='{line}', next='{lines[i+1].strip() if i+1 < len(lines) else 'EOF'}'")

        if line == "Poz No":
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if i >= 165 and i <= 170:
                print(f"    Line {i}: 'Poz No' -> next line {i+1}: '{next_line[:30]}'... (FULL: '{lines[i]}')")
            if i + 1 < len(lines) and re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                # Yeni bir ana poz bulundu, çık
                print(f"    BREAK at line {i}: 'Poz No' + '{next_line}'")
                break
            break_count += 1

        # Malzeme/İşçilik başlıklarını tespit et
        line_lower = line.lower()
        is_type_header = (line in ["Malzeme", "İşçilik", "MALZEME", "İŞÇİLİK"] or
                         line_lower in ["malzeme", "işçilik"] or
                         line_lower.startswith("malz") or
                         line_lower.startswith("isç") or
                         line_lower == "iscilik" or
                         (len(line) < 15 and line_lower.startswith("is") and
                          len(line) > 4))

        if is_type_header and line.strip():
            current_type = line
            i += 1
            while i < min(start_idx + 500, len(lines)):
                if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', lines[i].strip()):
                    break
                i += 1
            continue

        # Alt analiz kodu tespiti
        if line.startswith("(") or line.startswith(")"):
            i += 1
            continue

        if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', line):
            code = line
            name = ""
            unit = ""
            qty_str = ""
            price_str = ""

            j = i + 1
            name_lines = []

            while j < len(lines):
                current = lines[j].strip()

                if not current:
                    j += 1
                    continue

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
                    qty_str = lines[j + 1].strip() if j + 1 < len(lines) else ""
                    price_str = lines[j + 2].strip() if j + 2 < len(lines) else ""
                    break
                else:
                    name_lines.append(current)

                j += 1

            name = " ".join(name_lines)

            if name and unit and qty_str and price_str:
                try:
                    qty = float(qty_str.replace(',', '.'))
                    price = float(price_str.replace('.', '').replace(',', '.'))
                    total = qty * price

                    sub_analyses.append({
                        'type': current_type,
                        'code': code,
                        'name': name,
                        'unit': unit,
                        'quantity': f"{qty:.3f}".replace('.', ','),
                        'unit_price': f"{price:.2f}".replace('.', ','),
                        'total': f"{total:.2f}".replace('.', ',')
                    })
                    print(f"    ADDED: {code} - {name[:40]}")
                except Exception as e:
                    pass

        i += 1

    return sub_analyses

# Test
pdf = Path("ANALIZ/Analiz-1.pdf")
doc = fitz.open(str(pdf))
lines_all = []
for page in doc:
    lines_all.extend(page.get_text().split('\n'))
doc.close()

# Find and test poz 15.100.1001
for idx, line in enumerate(lines_all):
    if line.strip() == "15.100.1001":
        print("Testing 15.100.1001:")
        result = extract_sub_analyses_exact(lines_all, idx)
        print(f"\nTotal: {len(result)} sub-analyses\n")
        for item in result:
            print(f"  - {item['code']}: {item['name'][:40]}")
        break
