
"""
PozExtractorApp (Legacy Wrapper)
This module provides backward compatibility for ExtractorWorkerThread which expects
a 'poz_extractor_app' module with a 'PDFPozExtractor' class.
Ideally, the logic in core/data_manager.py should be updated to use core/pdf_engine.py directly,
but this wrapper restores functionality immediately for the user.
"""

import sys
import fitz  # PyMuPDF
import re
import pandas as pd
from pathlib import Path

class PDFPozExtractor:
    def __init__(self):
        self.extracted_data = []

    def extract_poz_from_pdf(self, pdf_path):
        """PDF dosyasından pozları çıkar"""
        try:
            doc = fitz.open(pdf_path)
            results = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Satır satır işle
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Poz numarası pattern'leri
                    poz_patterns = [
                        r'^(\d{2}\.\d{3}\.\d{4})',  # 10.110.1003
                        r'^(\d{2}\.\d{3})',         # 02.017
                        r'^([A-Z]{1,3}\.\d{2,3}\.\d{3})',  # Y.15.140
                        r'^([A-Z]{2,3}\.\d{3})',    # MSB.700
                    ]
                    
                    poz_no = None
                    for pattern in poz_patterns:
                        match = re.match(pattern, line)
                        if match:
                            poz_no = match.group(1)
                            break
                            
                    if poz_no:
                        # Açıklama ve fiyat çıkar
                        remaining = line[len(poz_no):].strip()
                        
                        # Fiyat bulmaya çalış (sayısal değer)
                        # Örnek: ... 1.234,56 TL
                        price_match = re.search(r'([\d.,]+)\s*(?:TL)?$', remaining)
                        unit_price = '0,00'
                        description = remaining
                        
                        if price_match:
                            try:
                                price_str = price_match.group(1).replace('.', '').replace(',', '.')
                                float(price_str) # Geçerli sayı mı?
                                unit_price = price_match.group(1)
                                description = remaining[:price_match.start()].strip()
                            except ValueError:
                                pass
                        
                        # Birim bulmaya çalış
                        unit = ''
                        unit_patterns = ['m³', 'm²', 'm2', 'm3', 'ton', 'kg', 'adet', 'lt', 'sa', 'gün', 'ay']
                        for u in unit_patterns:
                            pattern = r'\b' + re.escape(u) + r'\b'
                            if re.search(pattern, description, re.IGNORECASE):
                                unit = u
                                break
                        
                        poz_info = {
                            'poz_no': poz_no,
                            'description': description[:200] if description else f"PDF Poz: {poz_no}",
                            'unit': unit,
                            'quantity': '',
                            'institution': 'PDF',
                            'unit_price': unit_price,
                            'source_file': Path(pdf_path).name,
                            'page': page_num + 1
                        }
                        
                        results.append(poz_info)
            
            doc.close()
            return results
            
        except Exception as e:
            print(f"PDF poz çıkarma hatası {pdf_path}: {e}")
            return []

    def export_to_csv(self, output_path, data):
        """Verileri CSV olarak kaydet"""
        try:
            if not data:
                return False
                
            df = pd.DataFrame(data)
            
            # Kolon isimlerini düzenle (standart format)
            df = df.rename(columns={
                'poz_no': 'Poz No',
                'description': 'Açıklama',
                'unit': 'Birim',
                'quantity': 'Miktar',
                'unit_price': 'Birim Fiyat',
                'institution': 'Kurum',
                'source_file': 'Kaynak Dosya'
            })
            
            cols = ['Poz No', 'Açıklama', 'Birim', 'Miktar', 'Birim Fiyat', 'Kurum', 'Kaynak Dosya']
            # Var olmayan kolonlar için boş string ata
            for col in cols:
                if col not in df.columns:
                    df[col] = ''
            
            # Sadece istenen kolonları sıralı olarak al
            df = df[cols]
            
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            return True
            
        except Exception as e:
            print(f"CSV kaydetme hatası: {e}")
            return False
