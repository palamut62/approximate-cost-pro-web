"""
PDF Tablo Yapısı Analiz Aracı
"""

import fitz  # PyMuPDF
import pandas as pd
import re
from pathlib import Path

def analyze_table_structure(pdf_path):
    """PDF'deki tablo yapısını analiz et"""
    doc = fitz.open(pdf_path)

    print(f"\n{'='*60}")
    print(f"PDF: {Path(pdf_path).name}")
    print(f"{'='*60}")

    for page_num in range(min(3, len(doc))):  # İlk 3 sayfayı incele
        page = doc[page_num]

        print(f"\n--- SAYFA {page_num + 1} ---")

        # 1. Metni satır satır al
        text = page.get_text()
        lines = text.split('\n')

        print(f"Toplam satır sayısı: {len(lines)}")

        # 2. Tablo başlıklarını ara
        header_patterns = [
            r'Poz\s*No',
            r'Yapılacak\s*İşin\s*Cinsi',
            r'Montajlı',
            r'Birim\s*Fiyat',
            r'Montaj\s*Bedeli',
            r'TL'
        ]

        header_lines = []
        for i, line in enumerate(lines):
            for pattern in header_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    header_lines.append((i, line.strip()))
                    break

        print(f"\nBulunan başlık satırları:")
        for line_num, line_text in header_lines[:5]:
            print(f"  {line_num:3d}: {line_text}")

        # 3. Poz numarası içeren satırları bul
        poz_lines = []
        for i, line in enumerate(lines):
            if re.search(r'[A-Z]?\d{2}\.?\d{3}\.?\d{4}', line):
                poz_lines.append((i, line.strip()))

        print(f"\nPoz numarası içeren satırlar:")
        for line_num, line_text in poz_lines[:5]:
            print(f"  {line_num:3d}: {line_text}")

        # 4. Koordinat tabanlı analiz
        print(f"\n--- KOORDİNAT ANALİZİ ---")
        blocks = page.get_text("dict")

        # Metinleri koordinatlarına göre grupla
        text_items = []
        for block in blocks["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_items.append({
                            'text': span['text'].strip(),
                            'x': span['bbox'][0],
                            'y': span['bbox'][1],
                            'width': span['bbox'][2] - span['bbox'][0],
                            'height': span['bbox'][3] - span['bbox'][1],
                            'font_size': span['size']
                        })

        # Y koordinatına göre sırala (satırlar)
        text_items.sort(key=lambda x: x['y'])

        # Satırları grupla (aynı Y koordinatındakiler)
        rows = []
        current_row = []
        current_y = None
        tolerance = 5  # Koordinat toleransı

        for item in text_items:
            if item['text'].strip():
                if current_y is None or abs(item['y'] - current_y) <= tolerance:
                    current_row.append(item)
                    current_y = item['y'] if current_y is None else current_y
                else:
                    if current_row:
                        # X koordinatına göre sırala (sütunlar)
                        current_row.sort(key=lambda x: x['x'])
                        rows.append(current_row)
                    current_row = [item]
                    current_y = item['y']

        if current_row:
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)

        print(f"Koordinat tabanlı satır sayısı: {len(rows)}")

        # İlk birkaç satırı göster
        for i, row in enumerate(rows[:10]):
            if len(row) > 1:  # Çok sütunlu satırlar
                row_text = " | ".join([item['text'] for item in row])
                print(f"  Satır {i:2d}: {row_text}")

        # 5. Tablo tespiti (PyMuPDF)
        print(f"\n--- TABLO TESPİTİ ---")
        try:
            tables = page.find_tables()
            print(f"Bulunan tablo sayısı: {len(tables)}")

            for table_num, table in enumerate(tables):
                print(f"\nTablo {table_num + 1}:")
                print(f"  Koordinat: {table.bbox}")

                table_data = table.extract()
                if table_data:
                    print(f"  Satır sayısı: {len(table_data)}")
                    print(f"  Sütun sayısı: {len(table_data[0]) if table_data else 0}")

                    # İlk birkaç satırı göster
                    for row_num, row in enumerate(table_data[:5]):
                        clean_row = [str(cell).strip() if cell else '' for cell in row]
                        print(f"    {row_num}: {clean_row}")

        except Exception as e:
            print(f"Tablo tespit hatası: {e}")

    doc.close()

if __name__ == "__main__":
    # Mevcut dizindeki PDF dosyalarını analiz et
    pdf_files = list(Path('.').glob('*.pdf'))

    if not pdf_files:
        print("PDF dosyası bulunamadı!")
        exit()

    for pdf_file in pdf_files:
        try:
            analyze_table_structure(str(pdf_file))
        except Exception as e:
            print(f"Hata - {pdf_file.name}: {str(e)}")