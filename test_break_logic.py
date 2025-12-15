# -*- coding: utf-8 -*-
"""Test the break logic"""

import fitz

pdf = "ANALIZ/Analiz-1.pdf"
doc = fitz.open(pdf)
lines = []
for page in doc:
    lines.extend(page.get_text().split('\n'))
doc.close()

# Find poz 15.100.1001
for idx, line in enumerate(lines):
    if line.strip() == "15.100.1001":
        print(f"Found 15.100.1001 at line {idx}\n")
        print("Looking for break points from line 132 to 170:\n")

        for i in range(132, 170):
            line_stripped = lines[i].strip()
            line_lower = line_stripped.lower()

            # Check our break condition
            if ("malzeme" in line_lower or "malz" in line_lower) and \
               ("işçilik" in line_lower or "isçilik" in line_lower or "iscilik" in line_lower or "iş" in line_lower):
                print(f">>> BREAK at line {i}: '{line_stripped}'")
            elif line_stripped == "Poz No" and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                import re
                if re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                    print(f">>> BREAK at line {i}: 'Poz No' -> '{next_line}'")
            else:
                print(f"    Line {i}: '{line_stripped[:60]}'")

        break
