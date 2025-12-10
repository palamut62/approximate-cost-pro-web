# -*- coding: utf-8 -*-
"""Analyze PDF structure to understand position boundaries"""

import fitz
import re
from pathlib import Path

def analyze_pdf(pdf_path):
    """Analyze PDF structure"""
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        lines.extend(page.get_text().split('\n'))
    doc.close()

    print(f"\n{'='*80}")
    print(f"FILE: {Path(pdf_path).name}")
    print(f"{'='*80}\n")

    # Find all main positions (15.xxx or 19.xxx)
    poz_positions = []
    for idx, line in enumerate(lines):
        if re.match(r'^(15|19)\.\d{3}\.\d{4}$', line.strip()):
            poz_positions.append((idx, line.strip()))

    print(f"Found {len(poz_positions)} main positions\n")

    # Analyze structure of first 10 positions
    for pos_num, (pos_idx, pos_code) in enumerate(poz_positions[:10]):
        print(f"\n{pos_num+1}. Poz {pos_code} at line {pos_idx}")

        # Find where this position ends
        # Look for next poz or end of file
        next_pos_idx = len(lines)
        for i in range(pos_num + 1, len(poz_positions)):
            next_pos_idx = poz_positions[i][0]
            break

        # Show key markers
        pos_end = min(pos_idx + 80, next_pos_idx)

        # Find summary marker
        summary_line = -1
        for i in range(pos_idx, pos_end):
            if "tutar" in lines[i].lower() and ("malzeme" in lines[i].lower() or "malz" in lines[i].lower()):
                summary_line = i
                break

        # Find all sub-analysis codes
        sub_codes = []
        for i in range(pos_idx + 1, pos_end):
            line_stripped = lines[i].strip()
            if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', line_stripped):
                sub_codes.append((i, line_stripped))

        print(f"   Sub-codes found: {len(sub_codes)}")
        for sub_idx, (line_num, sub_code) in enumerate(sub_codes):
            if sub_idx < 3 or sub_idx >= len(sub_codes) - 1:
                print(f"     - {sub_code} at line {line_num}")
            elif sub_idx == 3:
                print(f"     ... ({len(sub_codes) - 4} more)")

        if summary_line > 0:
            print(f"   Summary found at line {summary_line}: '{lines[summary_line][:60]}'")
        else:
            print(f"   No summary found in range {pos_idx} to {pos_end}")

        if next_pos_idx < len(lines):
            print(f"   Next poz at line {next_pos_idx}: {poz_positions[pos_num + 1][1]}")

# Analyze both PDFs
for pdf_file in sorted(Path("ANALIZ").glob("*.pdf")):
    analyze_pdf(str(pdf_file))
