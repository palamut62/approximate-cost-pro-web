# -*- coding: utf-8 -*-
"""Check exact lines around boundary"""

import fitz

pdf = "ANALIZ/Analiz-1.pdf"
doc = fitz.open(pdf)
lines = []
for page in doc:
    lines.extend(page.get_text().split('\n'))
doc.close()

# Find poz 15.100.1001 and show lines 165-172
for idx, line in enumerate(lines):
    if line.strip() == "15.100.1001":
        print(f"Found 15.100.1001 at line {idx}\n")
        print("Lines 165-172:")
        for i in range(165, 173):
            print(f"  Line {i}: '{lines[i]}'")
        print("\n")
        print(f"Now showing lines 131-175 around the position:\n")
        for i in range(131, min(176, len(lines))):
            print(f"  {i:3d}: '{lines[i]}'")
        break
