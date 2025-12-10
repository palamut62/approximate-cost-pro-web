# -*- coding: utf-8 -*-
"""Debug script to examine PDF structure around poz 15.100.1001"""

import fitz
from pathlib import Path

def debug_around_poz(pdf_path, target_poz, lines_before=5, lines_after=40):
    """Print lines around a specific poz"""
    doc = fitz.open(pdf_path)
    lines_all = []

    # Extract all lines
    for page in doc:
        text = page.get_text()
        lines = text.split('\n')
        lines_all.extend(lines)

    doc.close()

    # Find the poz
    for idx, line in enumerate(lines_all):
        if line.strip() == target_poz:
            print(f"\nFOUND: '{target_poz}' at line {idx}\n")
            print(f"Context (lines {max(0, idx-lines_before)} to {min(len(lines_all), idx+lines_after)}):\n")

            for i in range(max(0, idx-lines_before), min(len(lines_all), idx+lines_after)):
                marker = ">>>" if i == idx else "   "
                print(f"{marker} {i:4d}: {lines_all[i][:80]}")

            return True

    return False

if __name__ == "__main__":
    pdf1 = Path("C:/Users/umuti/Desktop/deneembos/yaklasik_maliyet_pro/ANALIZ/Analiz-1.pdf")
    pdf2 = Path("C:/Users/umuti/Desktop/deneembos/yaklasik_maliyet_pro/ANALIZ/Analiz-2.pdf")

    print("=" * 80)
    print("DEBUG: PDF Structure Around Key Pozlar")
    print("=" * 80)

    # Test poz 15.100.1001
    print("\n\n### POZ 15.100.1001 (should have 1 sub: 10.100.1062) ###")
    if pdf1.exists():
        if not debug_around_poz(str(pdf1), "15.100.1001"):
            print("Not found in Analiz-1.pdf")
        if not debug_around_poz(str(pdf2), "15.100.1001"):
            print("Not found in Analiz-2.pdf")

    # Test poz 15.115.1208
    print("\n\n### POZ 15.115.1208 (should have 7 sub with 15.115.1207) ###")
    if pdf1.exists():
        if not debug_around_poz(str(pdf1), "15.115.1208"):
            print("Not found in Analiz-1.pdf")
        if not debug_around_poz(str(pdf2), "15.115.1208"):
            print("Not found in Analiz-2.pdf")
