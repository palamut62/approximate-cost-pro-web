# -*- coding: utf-8 -*-
"""Find all codes under a specific poz"""

import fitz
import re
from pathlib import Path

pdf = Path("ANALIZ/Analiz-1.pdf")
doc = fitz.open(str(pdf))
lines = []
for page in doc:
    lines.extend(page.get_text().split('\n'))
doc.close()

# Find poz 15.115.1208
target_poz = "15.115.1208"
for idx, line in enumerate(lines):
    if line.strip() == target_poz:
        print(f"Found '{target_poz}' at line {idx}")
        print(f"\nAll codes found in next 150 lines:\n")

        for i in range(idx, min(idx + 150, len(lines))):
            line_stripped = lines[i].strip()
            if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', line_stripped):
                # Check what's before (type if any)
                prev_type = ""
                for j in range(max(0, i-5), i):
                    if "Malzeme" in lines[j] or "İşçilik" in lines[j] or "MALZEME" in lines[j]:
                        prev_type = lines[j].strip()[:20]
                        break

                print(f"  Line {i:4d}: {line_stripped} {('('+prev_type+')' if prev_type else '')}")

            # Check for "Poz No" followed by main poz
            if line_stripped == "Poz No" and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                    print(f"  >>> NEW POZ at line {i}: 'Poz No' -> '{next_line}'")
                    break

        break
