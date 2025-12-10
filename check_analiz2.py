# -*- coding: utf-8 -*-
"""Check Analiz-2 structure"""

import fitz

doc = fitz.open("ANALIZ/Analiz-2.pdf")
lines = []
for page in doc:
    lines.extend(page.get_text().split('\n'))
doc.close()

# Show lines 0-70 (around first poz)
print("Lines 0-70 from Analiz-2.pdf:")
for i in range(min(70, len(lines))):
    print(f"{i:3d}: {lines[i][:70]}")
