"""
PDF Arama Uygulaması - PyQt5 Versiyonu
Poz No ve Keyword ile Satır Çıkarıcı
CSV dosyalardan veri okuma desteği ile
"""

import sys
import fitz  # PyMuPDF
import re
import pandas as pd
from pathlib import Path
import json
import hashlib
import os
from datetime import datetime
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QTextEdit, QFileDialog, QMessageBox, QProgressBar,
                             QGroupBox, QHeaderView, QSplitter, QTabWidget,
                             QComboBox, QSpinBox, QDoubleSpinBox, QFrame, QCheckBox,
                             QListWidget, QListWidgetItem, QDialog, QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QRect, QUrl, QSize
from PyQt5.QtGui import QFont, QIcon, QDesktopServices, QPixmap, QColor
from cost_estimator import CostEstimator
from analysis_builder import AnalysisBuilder
from custom_analysis_manager import CustomAnalysisManager
from quantity_takeoff_manager import QuantityTakeoffManager

class PDFSearchEngine:
    def __init__(self):
        self.pdf_data = {}
        self.loaded_files = []
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_file = self.cache_dir / "pdf_cache.json"
        self.ensure_cache_dir()

    def ensure_cache_dir(self):
        """Cache klasörünü oluştur"""
        try:
            self.cache_dir.mkdir(exist_ok=True)
        except Exception as e:
            print(f"Cache klasörü oluşturulamadı: {e}")

    def get_file_hash(self, file_path):
        """Dosya hash'i hesapla (dosya değişti mi kontrol için)"""
        try:
            file_path = Path(file_path)
            # Dosya boyutu + değişim tarihi kombinasyonu
            stat = file_path.stat()
            hash_string = f"{file_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        except Exception:
            return None

    def save_cache(self):
        """PDF verilerini cache'e kaydet"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'pdf_data': self.pdf_data,
                'loaded_files': self.loaded_files,
                'file_hashes': {}
            }

            # Her dosya için hash hesapla
            for file_name in self.loaded_files:
                # Dosya yolunu bulmaya çalış
                possible_paths = [
                    Path(__file__).parent / "PDF" / file_name,
                    Path(file_name)  # Tam yol olarak
                ]

                for path in possible_paths:
                    if path.exists():
                        cache_data['file_hashes'][file_name] = self.get_file_hash(path)
                        break

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"Cache kaydedildi: {len(self.loaded_files)} dosya")
            return True
        except Exception as e:
            print(f"Cache kaydetme hatası: {e}")
            return False

    def load_cache(self):
        """Cache'den PDF verilerini yükle"""
        try:
            if not self.cache_file.exists():
                return False

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Dosya hash'lerini kontrol et
            file_hashes = cache_data.get('file_hashes', {})
            invalid_files = []
            changed_files = []

            # PDF klasöründeki mevcut dosyaları al
            pdf_folder = Path(__file__).parent / "PDF"
            current_pdf_files = set()
            if pdf_folder.exists():
                current_pdf_files = {f.name for f in pdf_folder.glob("*.pdf")}

            # Cache'deki dosyaları kontrol et
            cached_files = set(file_hashes.keys())

            # Yeni eklenen dosyaları bul
            new_files = current_pdf_files - cached_files
            if new_files:
                print(f"Yeni PDF dosyaları bulundu: {new_files}")
                return False  # Yeni dosyalar var, cache geçersiz

            # Silinen dosyaları bul
            deleted_files = cached_files - current_pdf_files
            if deleted_files:
                print(f"Silinen PDF dosyaları: {deleted_files}")
                # Silinen dosyaları cache'den çıkar, ama diğerlerini yükle
                for df in deleted_files:
                    invalid_files.append(df)

            for file_name, cached_hash in file_hashes.items():
                if file_name in deleted_files:
                    continue

                # Dosya yolunu bulmaya çalış
                possible_paths = [
                    Path(__file__).parent / "PDF" / file_name,
                    Path(file_name)  # Tam yol olarak
                ]

                file_found = False
                for path in possible_paths:
                    if path.exists():
                        current_hash = self.get_file_hash(path)
                        if current_hash != cached_hash:
                            changed_files.append(file_name)
                        file_found = True
                        break

                if not file_found:
                    invalid_files.append(file_name)

            # Dosyalar değişmişse cache geçersiz
            if changed_files:
                print(f"Değişen dosyalar var, yeniden yüklenecek: {changed_files}")
                return False

            # Cache geçerli, verileri yükle (silinen dosyaları hariç tut)
            self.pdf_data = cache_data.get('pdf_data', {})
            self.loaded_files = cache_data.get('loaded_files', [])

            # Silinen dosyaları çıkar
            for df in deleted_files:
                if df in self.pdf_data:
                    del self.pdf_data[df]
                if df in self.loaded_files:
                    self.loaded_files.remove(df)

            # Cache timestamp bilgisi
            cache_time = cache_data.get('timestamp', '')
            if cache_time:
                try:
                    ct = datetime.fromisoformat(cache_time)
                    self.cache_timestamp = ct.strftime("%d.%m.%Y %H:%M")
                except:
                    self.cache_timestamp = "Bilinmiyor"
            else:
                self.cache_timestamp = "Bilinmiyor"

            print(f"Cache'den yüklendi: {len(self.loaded_files)} dosya (Son güncelleme: {self.cache_timestamp})")
            return True

        except Exception as e:
            print(f"Cache yükleme hatası: {e}")
            return False

    def clear_cache(self):
        """Cache'i temizle"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            print("Cache temizlendi")
            return True
        except Exception as e:
            print(f"Cache temizleme hatası: {e}")
            return False

    def load_pdf(self, pdf_path):
        """PDF dosyasını yükle ve işle - Koordinat tabanlı analiz ile"""
        try:
            doc = fitz.open(pdf_path)
            file_name = Path(pdf_path).name

            lines_data = []

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Koordinat tabanlı metin çıkarma
                blocks = page.get_text("dict")

                # Metinleri koordinatlarına göre grupla
                text_items = []
                for block in blocks["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                if span['text'].strip():
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

                # Satırları grupla (aynı Y koordinatındakiler) - Daha hassas tolerance
                rows = []
                current_row = []
                current_y = None
                tolerance = 3  # Daha hassas koordinat toleransı

                for item in text_items:
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

                # Satırları metin olarak birleştir - Geliştirilmiş format
                for row_num, row in enumerate(rows):
                    if len(row) > 1:  # Çok sütunlu satırlar
                        # Sütunları daha iyi ayırmak için ||| kullan
                        row_text = " ||| ".join([item['text'] for item in row])
                        # Ayrıca orijinal koordinat bilgilerini de sakla
                        coord_info = "[" + ",".join([f"{item['x']:.0f}" for item in row]) + "]"
                        row_text = row_text + " " + coord_info
                    else:
                        # Tek sütunlu satırlar
                        row_text = row[0]['text'] if row else ""

                    if row_text.strip():
                        lines_data.append({
                            'page': page_num + 1,
                            'line_number': row_num + 1,
                            'text': row_text,
                            'file': file_name,
                            'is_table_row': len(row) > 1,
                            'column_count': len(row),
                            'raw_spans': row  # Ham koordinat verilerini de sakla
                        })

                # Fallback: Normal metin çıkarma
                if not lines_data:
                    text = page.get_text()
                    lines = text.split('\n')

                    for line_num, line in enumerate(lines):
                        line = line.strip()
                        if line:
                            lines_data.append({
                                'page': page_num + 1,
                                'line_number': line_num + 1,
                                'text': line,
                                'file': file_name,
                                'is_table_row': False
                            })

            self.pdf_data[file_name] = lines_data
            if file_name not in self.loaded_files:
                self.loaded_files.append(file_name)
            doc.close()

            # PDF yüklendikten sonra cache'e kaydet
            self.save_cache()
            return True

        except Exception as e:
            print(f"Hata: {str(e)}")
            return False

    def search_poz_number(self, poz_no):
        """Poz numarası ile arama"""
        results = []

        # Farklı poz formatları
        patterns = [
            rf'\b{re.escape(poz_no)}\b',  # Tam eşleşme
            rf'{re.escape(poz_no)}\.',    # Nokta ile
            rf'{re.escape(poz_no)}\s',    # Boşluk ile
            rf'^{re.escape(poz_no)}',     # Satır başında
        ]

        for file_name, lines in self.pdf_data.items():
            for line_data in lines:
                text = line_data['text']

                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Satırdan veri çıkar
                        extracted_data = self.extract_line_data(text, poz_no)

                        result = {
                            'file': file_name,
                            'page': line_data['page'],
                            'line_number': line_data['line_number'],
                            'full_text': text,
                            'extracted_data': extracted_data,
                            'search_term': poz_no
                        }
                        results.append(result)
                        break

        return results

    def search_keyword(self, keyword):
        """Anahtar kelime ile arama - Poz no araması gibi"""
        results = []

        # Farklı keyword formatları - daha esnek arama
        patterns = [
            rf'\b{re.escape(keyword)}\b',     # Tam kelime eşleşme
            rf'{re.escape(keyword)}',         # Kısmi eşleşme
            rf'.*{re.escape(keyword)}.*',     # İçerik eşleşme
        ]

        for file_name, lines in self.pdf_data.items():
            for line_data in lines:
                text = line_data['text']

                # Herhangi bir pattern eşleşirse
                found = False
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        found = True
                        break

                if found:
                    # Satırdan veri çıkar - aynı şekilde
                    extracted_data = self.extract_line_data(text, keyword)

                    result = {
                        'file': file_name,
                        'page': line_data['page'],
                        'line_number': line_data['line_number'],
                        'full_text': text,
                        'extracted_data': extracted_data,
                        'search_term': keyword
                    }
                    results.append(result)

        return results

    def extract_line_data(self, text, search_term):
        """Satırdan yapılandırılmış veri çıkar - Gelişmiş Tablo Parser"""
        data = {
            'poz_no': None,
            'description': None,
            'unit': None,
            'quantity': None,
            'unit_price': None,
            'total_price': None,
            'code': None
        }

        # Eğer metin "|" içeriyorsa koordinat tabanlı ayrıştırma kullan
        if '|' in text:
            return self.parse_table_row(text)

        # Normal pattern matching
        # Poz numarası pattern'leri
        poz_patterns = [
            r'([A-Z]?\d{2}\.\d{3}\.\d{4})',  # A01.001.0001 veya 01.001.0001
            r'([A-Z]?\d{2}\.\d{3})',         # A01.001 veya 01.001
            r'(\d+\.\d+\.\d+)',             # 1.2.3
            r'(\d+\.\d+)',                  # 1.2
        ]

        # Birim pattern'leri - Türkçe karakterler dahil
        unit_patterns = [
            r'\b(m³|m²|m|kg|ton|adet|lt|da|gr|cm|mm|Sa)\b',
            r'\b(metre|metrekare|metreküp|kilogram|litre|dekara|saat)\b'
        ]

        # Fiyat pattern'leri - Türk sayı formatı
        price_patterns = [
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|$)',
            r'(\d{1,9}(?:,\d{2})?)\s*(?:TL|₺|$)',
        ]

        # Miktar pattern'leri - Ondalık sayılar dahil
        quantity_patterns = [
            r'(\d+(?:,\d+)?)\s*(?:m³|m²|m|kg|ton|adet|lt|da|Sa)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:m³|m²|m|kg|ton|adet|lt|da|Sa)',
            r'(\d+(?:,\d+)?)',  # Sadece sayı
        ]

        # Poz numarası bul
        for pattern in poz_patterns:
            match = re.search(pattern, text)
            if match:
                data['poz_no'] = match.group(1)
                break

        # Birim bul
        for pattern in unit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['unit'] = match.group(1)
                break

        # Fiyatları bul
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            prices.extend(matches)

        if prices:
            # Fiyatları sayısal değere göre sırala
            try:
                price_values = []
                for p in prices:
                    val = float(p.replace('.', '').replace(',', '.'))
                    price_values.append((val, p))
                price_values.sort()

                if len(price_values) >= 2:
                    data['unit_price'] = price_values[0][1]  # En küçük
                    data['total_price'] = price_values[-1][1]  # En büyük
                else:
                    data['unit_price'] = price_values[0][1]
            except:
                if len(prices) >= 2:
                    data['unit_price'] = prices[0]
                    data['total_price'] = prices[-1]
                else:
                    data['unit_price'] = prices[0]

        # Miktar bul
        for pattern in quantity_patterns:
            match = re.search(pattern, text)
            if match:
                data['quantity'] = match.group(1)
                break

        # Açıklama çıkar
        if data['poz_no']:
            # Poz numarasından sonraki kısmı al, sayıları ve fiyatları çıkar
            desc_pattern = rf"{re.escape(data['poz_no'])}\s*(.+?)(?:\d+(?:,\d{{2}})?.*(?:TL|₺)|$)"
            match = re.search(desc_pattern, text)
            if match:
                desc = match.group(1).strip()
                # Gereksiz sayıları temizle
                desc = re.sub(r'\b\d+(?:,\d+)?\s*(?:m³|m²|m|kg|ton|adet|lt|da|Sa)\b', '', desc)
                desc = re.sub(r'\b\d{1,3}(?:\.\d{3})*(?:,\d{2})?\b', '', desc)
                data['description'] = desc.strip()

        return data

    def parse_table_row(self, text):
        """Koordinat tabanlı tablo satırını ayrıştır - Resimdeki tablo yapısına göre geliştirilmiş"""
        data = {
            'poz_no': None,
            'description': None,
            'unit': None,
            'quantity': None,
            'unit_price': None,
            'total_price': None,
            'code': None
        }

        # Önce ||| ile ayır, sonra | ile ayır
        if '|||' in text:
            columns = [col.strip() for col in text.split('|||')]
        else:
            columns = [col.strip() for col in text.split('|')]

        # Koordinat bilgilerini temizle
        clean_columns = []
        for col in columns:
            # Koordinat kısmını çıkar ([123,456] formatında)
            col_clean = re.sub(r'\[\d+(?:,\d+)*\]', '', col).strip()
            if col_clean:
                clean_columns.append(col_clean)

        columns = clean_columns

        if len(columns) < 2:
            return data

        # Resimdeki tablo yapısı: Poz No | Tanımı | Ölçü Birimi | Miktarı | Birim Fiyatı | Tutarı (TL)
        
        # İlk kolonu poz numarası olarak kontrol et
        first_col = columns[0].strip()
        poz_patterns = [
            r'(\d{2}\.\d{3}\.\d{4})',  # 15.490.1003, 10.170.1203
            r'(\d{2}\.\d{3})',         # 15.490
            r'(\d{1,2}\.\d{1,3}\.\d{1,4})'  # Genel format
        ]

        for pattern in poz_patterns:
            match = re.search(pattern, first_col)
            if match:
                data['poz_no'] = match.group(1)
                break

        # İkinci kolonu açıklama olarak al
        if len(columns) > 1:
            desc = columns[1].strip()
            # Çok uzun açıklamalar için kısalt
            if len(desc) > 100:
                desc = desc[:100] + "..."
            data['description'] = desc

        # Resimdeki tablo yapısına göre kolonları parse et
        # Poz No | Tanımı | Ölçü Birimi | Miktarı | Birim Fiyatı | Tutarı (TL)
        
        if len(columns) >= 3:
            # 3. kolon: Ölçü Birimi
            unit_col = columns[2].strip()
            unit_match = re.search(r'\b(m³|m²|m|kg|ton|adet|lt|da|gr|cm|mm|Sa|saat)\b', unit_col, re.IGNORECASE)
            if unit_match:
                data['unit'] = unit_match.group(1)
        
        if len(columns) >= 4:
            # 4. kolon: Miktarı
            quantity_col = columns[3].strip()
            quantity_match = re.search(r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,3})?)', quantity_col)
            if quantity_match:
                data['quantity'] = quantity_match.group(1)
        
        if len(columns) >= 5:
            # 5. kolon: Birim Fiyatı
            unit_price_col = columns[4].strip()
            unit_price_match = re.search(r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,3})?)', unit_price_col)
            if unit_price_match:
                data['unit_price'] = unit_price_match.group(1)
        
        if len(columns) >= 6:
            # 6. kolon: Tutarı (TL)
            total_price_col = columns[5].strip()
            total_price_match = re.search(r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,3})?)', total_price_col)
            if total_price_match:
                data['total_price'] = total_price_match.group(1)
        
        # Eğer yeterli kolon yoksa, mevcut kolonlarda arama yap
        if not data['unit'] or not data['quantity'] or not data['unit_price']:
            for i, col in enumerate(columns[2:], start=2):
                col = col.strip()
                if not col:
                    continue

                # Birim kontrolü
                if not data['unit']:
                    unit_match = re.search(r'\b(m³|m²|m|kg|ton|adet|lt|da|gr|cm|mm|Sa|saat)\b', col, re.IGNORECASE)
                    if unit_match:
                        data['unit'] = unit_match.group(1)
                        continue

                # Sayısal değer kontrolü
                number_match = re.search(r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,3})?)', col)
                if number_match:
                    number_str = number_match.group(1)
                    try:
                        # Türk sayı formatını normalize et
                        normalized = number_str.replace('.', '').replace(',', '.')
                        if '.' in normalized:
                            parts = normalized.split('.')
                            if len(parts) == 2 and len(parts[1]) == 2:
                                num_val = float(normalized)
                            elif len(parts) == 2 and len(parts[1]) > 2:
                                normalized = parts[0] + parts[1]
                                num_val = float(normalized)
                            else:
                                num_val = float(normalized)
                        else:
                            num_val = float(normalized)

                        # Değer büyüklüğüne göre sınıflandır
                        if num_val < 10 and not data['quantity']:
                            data['quantity'] = number_str
                        elif num_val >= 10 and num_val < 1000 and not data['unit_price']:
                            data['unit_price'] = number_str
                        elif num_val >= 1000 and not data['total_price']:
                            data['total_price'] = number_str
                        elif not data['unit_price']:
                            data['unit_price'] = number_str

                    except ValueError:
                        continue

        return data

    def extract_poz_analysis(self, poz_no):
        """Poz numarasının tam analiz tablosunu çıkar - Gelişmiş Pattern Matching"""
        print(f"\n=== POZ ANALİZİ DEBUG BAŞLANGICI ===")
        print(f"Aranan Poz: {poz_no}")

        analysis_data = {
            'poz_no': poz_no,
            'description': '',
            'unit': '',
            'materials': [],  # Malzeme listesi
            'labor': [],      # İşçilik listesi
            'subtotal': 0,
            'overhead': 0,
            'unit_price': 0,
            'notes': ''
        }

        # SADECE analiz dosyalarında ara
        analysis_files = []

        for file_name in self.pdf_data.keys():
            if 'analiz' in file_name.lower():
                analysis_files.append(file_name)

        if not analysis_files:
            print(f"❌ Analiz dosyası bulunamadı!")
            print(f"📁 Yüklü dosyalar: {list(self.pdf_data.keys())}")
            print(f"💡 Dosya adında 'analiz' kelimesi olmalı")
            return analysis_data

        print(f"✅ Analiz dosyalarında arama yapılacak: {analysis_files}")

        # DEBUG: Analiz dosyalarındaki satır sayılarını göster
        for af in analysis_files:
            line_count = len(self.pdf_data[af])
            print(f"📄 {af}: {line_count} satır")

        # Önce ana poz başlangıcını bul - Daha kapsamlı arama
        analysis_start_page = None
        analysis_start_line = None
        analysis_start_file = None

        # Sadece tam poz formatını destekle
        poz_variations = [
            poz_no,  # Tam poz numarası (15.430.1513)
            poz_no.replace('.', ''),  # Noktaları kaldır (154301513)
        ]

        # DEBUG: Aranacak poz varyasyonlarını göster
        print(f"🔍 Aranacak poz varyasyonları: {poz_variations}")

        for file_name in analysis_files:
            lines = self.pdf_data[file_name]
            print(f"\n📖 {file_name} analiz dosyasında poz arıyor... ({len(lines)} satır)")

            # DEBUG: İlk 10 satırı göster
            print("📋 İlk 10 satır örneği:")
            for idx in range(min(10, len(lines))):
                sample_text = lines[idx]['text'][:80]
                print(f"   {idx+1}: {sample_text}...")

            # DEBUG: Poz geçen satırları ara
            poz_lines_found = []
            all_poz_numbers = []
            for i, line_data in enumerate(lines):
                text = line_data['text']

                # Tüm poz numaralarını bul (15.xxx.xxxx formatında)
                poz_pattern = r'\b(\d{2}\.\d{3}\.\d{4})\b'
                found_pozs = re.findall(poz_pattern, text)
                for found_poz in found_pozs:
                    if found_poz not in all_poz_numbers:
                        all_poz_numbers.append(found_poz)

                # Herhangi bir poz varyasyonu var mı?
                for poz_var in poz_variations:
                    if poz_var in text:
                        poz_lines_found.append((i+1, poz_var, text[:100]))

            print(f"📊 Dosyada bulunan TÜM poz numaraları ({len(all_poz_numbers)} adet):")
            for poz in sorted(all_poz_numbers)[:20]:  # İlk 20'sini göster
                print(f"   {poz}")
            if len(all_poz_numbers) > 20:
                print(f"   ... ve {len(all_poz_numbers) - 20} adet daha")

            if poz_lines_found:
                print(f"🎯 Aranan '{poz_no}' poz varyasyonları için bulunan satırlar:")
                for line_num, found_poz, sample in poz_lines_found[:5]:  # İlk 5'ini göster
                    print(f"   Satır {line_num}: '{found_poz}' -> {sample}...")
            else:
                print(f"❌ '{poz_no}' için hiçbir satırda poz varyasyonu bulunamadı!")
                print(f"💡 15.490.1003 dosyada var mı? {('15.490.1003' in str(all_poz_numbers))}")

            for i, line_data in enumerate(lines):
                text = line_data['text']

                # Tüm poz varyasyonlarını kontrol et - tam eşleşme öncelikli
                found_poz = None
                
                # Önce tam eşleşme ara
                if poz_no in text:
                    found_poz = poz_no
                else:
                    # Sonra varyasyonları ara
                    for poz_var in poz_variations:
                        if poz_var in text:
                            found_poz = poz_var
                            break
                
                # Eğer hala bulunamadıysa, tam poz numarasını regex ile ara
                if not found_poz and '.' in poz_no:
                    # Tam poz numarasını regex ile ara (15.490.1003)
                    escaped_poz = re.escape(poz_no)
                    poz_match = re.search(rf'\b{escaped_poz}\b', text)
                    if poz_match:
                        found_poz = poz_match.group(0)

                if not found_poz:
                    continue

                print(f"✅ Poz bulundu ({found_poz}) - Aranan: ({poz_no}): {text[:100]}...")

                # ÖNEMLI: Eğer aranan poz ile bulunan poz farklıysa uyar
                if found_poz != poz_no:
                    print(f"⚠️  UYARI: Aranan '{poz_no}' ama bulunan '{found_poz}' - Bu yanlış sonuç olabilir!")
                    # Eğer tam poz numarası aranıyorsa ve farklı bir şey bulunduysa devam etme
                    if poz_no != found_poz and poz_no in poz_variations[0:1]:  # Sadece ilk varyasyon tam poz
                        print(f"🚫 Yanlış poz, devam ediliyor...")
                        continue

                # 1) Tam analiz tablosu başlık satırı - resimdeki gibi
                if ('|||' in text or '|' in text) and found_poz in text:
                    # Önce ||| sonra | ile parçala
                    if '|||' in text:
                        parts = [p.strip() for p in text.split('|||')]
                    else:
                        parts = [p.strip() for p in text.split('|')]

                    # Koordinat bilgilerini temizle
                    clean_parts = []
                    for part in parts:
                        clean_part = re.sub(r'\[\d+(?:,\d+)*\]', '', part).strip()
                        if clean_part:
                            clean_parts.append(clean_part)

                    parts = clean_parts

                    # Poz'un hangi sütunda olduğunu bul
                    poz_column = -1
                    for idx, part in enumerate(parts):
                        if any(pv in part for pv in poz_variations):
                            poz_column = idx
                            break

                    if poz_column >= 0 and len(parts) >= 3:
                        # Resimde: Poz No | Analizin Adı | Ölçü Birimi
                        if poz_column == 0:
                            analysis_data['poz_no'] = parts[0].strip()
                            analysis_data['description'] = parts[1].strip() if len(parts) > 1 else ''
                            analysis_data['unit'] = parts[2].strip() if len(parts) > 2 else 'm²'
                        else:
                            # Poz başka sütundaysa
                            analysis_data['poz_no'] = found_poz
                            analysis_data['description'] = parts[1].strip() if len(parts) > 1 else ''
                            analysis_data['unit'] = 'm²'

                        analysis_start_page = line_data['page']
                        analysis_start_line = i
                        analysis_start_file = file_name
                        print(f"Ana tablo başlığı bulundu: {file_name} - Sayfa {analysis_start_page}")
                        print(f"Başlık: {analysis_data['description']} - Birim: {analysis_data['unit']}")
                        break

                # 2) Başlık tablosu formatı (Poz No, Analizin Adı, vb. başlıkları içeren)
                elif any(header in text for header in ['Poz No', 'Analizin Adı', 'Ölçü Birimi', 'Tutarı']):
                    # Sonraki birkaç satırda veri ara
                    for j in range(1, 8):  # 8 satır ileriye bak
                        if i + j >= len(lines):
                            break
                        next_line = lines[i + j]
                        next_text = next_line['text']

                        # Bu satırda poz var mı?
                        if any(pv in next_text for pv in poz_variations):
                            print(f"Başlık altında poz bulundu: {next_text[:100]}...")

                            # Parse et
                            parsed_data = self.parse_table_row(next_text)
                            if parsed_data['poz_no']:
                                analysis_data.update(parsed_data)
                                analysis_start_page = next_line['page']
                                analysis_start_line = i + j
                                analysis_start_file = file_name
                                print(f"Parse edilmiş veri başlığı: {file_name} - Sayfa {analysis_start_page}")
                                break

                    if analysis_start_page is not None:
                        break

                # 3) Basit poz satırı (sadece poz var)
                elif found_poz == text.strip():
                    analysis_data['poz_no'] = found_poz
                    analysis_data['description'] = f"Poz {found_poz} analizi"
                    analysis_data['unit'] = 'm²'
                    analysis_start_page = line_data['page']
                    analysis_start_line = i
                    analysis_start_file = file_name
                    print(f"Basit poz satırı: {file_name} - Sayfa {analysis_start_page}")
                    break

            if analysis_start_page is not None:
                break


        if analysis_start_page is None:
            print(f"Poz '{poz_no}' için başlık bulunamadı!")
            return analysis_data

        print(f"Poz '{poz_no}' analizi başlıyor - Sayfa: {analysis_start_page}, Dosya: {analysis_start_file}")
        print(f"Başlık bilgileri - Açıklama: '{analysis_data['description']}', Birim: '{analysis_data['unit']}')")

        # Analiz içeriğini çıkar - resimdeki tablo yapısına göre
        current_section = None
        analyzing = True

        # Resimdeki gibi kompleks analiz tablolarını desteklemek için
        material_keywords = [
            'Malzeme', 'AC4 Sınıf 32', 'Laminat', 'parke', 'AC4', '2 mm kalınlıkta',
            'şilte', 'polietilen', 'altı', 'kalınlıkta'
        ]

        labor_keywords = [
            'İşçilik', 'Usta', 'İşçi', 'Marangoz', 'ustaş', 'işçi', 'yükleme', 'yatak', 'düşey', 'taşı',
            'düz işçi', 'marangoz ustası'
        ]

        # Başlığın bulunduğu dosyada detaylı arama
        if analysis_start_file:
            lines = self.pdf_data[analysis_start_file]
            print(f"Detaylı analiz arıyor: {analysis_start_file} (Sayfa {analysis_start_page} sonrası)")

            for i, line_data in enumerate(lines):
                # Analiz başladıktan sonraki satırları işle
                if (line_data['page'] < analysis_start_page or
                    (line_data['page'] == analysis_start_page and i <= analysis_start_line)):
                    continue

                text = line_data['text']
                print(f"Kontrol ediliyor ({line_data['page']}-{i}): {text[:120]}...")

                # Çok uzak sayfalara gitme (max 5 sayfa)
                if line_data['page'] > analysis_start_page + 5:
                    print(f"Sayfa sınırı aşıldı, analiz durduruluyor")
                    break

                # Yeni poz başladığında dur (ana poz dışında) - daha akıllı kontrol
                if '|' in text or '|||' in text:
                    # Tablo satırı ise poz numarasını kontrol et
                    text_start = text.split('|||')[0] if '|||' in text else text.split('|')[0]
                    poz_match = re.search(r'(\d{2}\.\d{3}\.\d{4})', text_start.strip())
                    
                    if poz_match:
                        found_poz_in_line = poz_match.group(1)
                        # Sadece aynı kategori ana poz ise dur (15.xxx.xxxx başka ana poz)
                        poz_category = poz_no.split('.')[0] if '.' in poz_no else poz_no[:2]
                        found_category = found_poz_in_line.split('.')[0] if '.' in found_poz_in_line else found_poz_in_line[:2]

                        # Ana tablo başlığı mı kontrol et (format: 15.xxx.xxxx ||| Uzun açıklama ||| birim)
                        columns = text.split('|||') if '|||' in text else text.split('|')
                        is_main_header = False

                        if len(columns) >= 3:
                            # İkinci kolonda uzun açıklama var mı ve üçüncü kolonda birim var mı?
                            second_col = columns[1].strip() if len(columns) > 1 else ""
                            third_col = columns[2].strip() if len(columns) > 2 else ""

                            # Ana başlık özellikleri: uzun açıklama (>30 karakter) ve birim
                            if (len(second_col) > 30 and
                                any(unit in third_col for unit in ['m²', 'm³', 'm', 'Sa', 'Ton', 'kg', 'Adet'])):
                                is_main_header = True

                        if (found_poz_in_line != poz_no and
                            found_poz_in_line not in poz_variations and
                            is_main_header):
                            print(f"Yeni ana poz başlığı bulundu ({found_poz_in_line}), analiz durduruluyor")
                            analyzing = False
                            break

                # Sadece kesin bölüm başlıklarını tespit et - resme göre (tablo satırı olmayan)
                if ('|||' not in text and '|' not in text and
                    any(text.strip() == keyword for keyword in [
                        'Kazı Yapılması:', 'İşçilik:', 'Bentonit Malzeme:', 'Betonlama:'
                    ])):
                    if 'İşçilik:' in text or 'Kazı Yapılması:' in text:
                        current_section = 'labor'
                        print(f"İşçilik bölümü başladı: {text}")
                    else:
                        current_section = 'materials'
                        print(f"Malzeme bölümü başladı: {text}")
                    continue

                # Tablo satırı kontrolü - resimdeki gibi
                if '|' in text or '|||' in text:
                    # Tablo satırını parse et
                    parsed_item = self.parse_table_row(text)
                    print(f"🔍 Parse sonucu: poz='{parsed_item['poz_no']}', açıklama='{parsed_item['description'][:50] if parsed_item['description'] else None}'")

                    if parsed_item['poz_no'] and parsed_item['poz_no'] != poz_no:
                        # Tabloda sadece poz numarası olan satırları atla (başlık satırları)
                        columns = text.split('|||') if '|||' in text else text.split('|')
                        if len(columns) < 4:
                            print(f"Başlık satırı atlandı: {parsed_item['poz_no']} (sadece {len(columns)} sütun)")
                            continue
                        # Bu bir alt poz (malzeme veya işçilik)
                        print(f"Alt poz bulundu: {parsed_item['poz_no']} - {parsed_item['description']}")
                        
                        # Malzeme mi işçilik mi belirle
                        is_material = any(keyword.lower() in parsed_item['description'].lower() 
                                        for keyword in material_keywords)
                        is_labor = any(keyword.lower() in parsed_item['description'].lower() 
                                     for keyword in labor_keywords)
                        
                        # Poz numarasına göre de belirle
                        if parsed_item['poz_no'].startswith('10.170') or parsed_item['poz_no'].startswith('10.330'):
                            is_material = True
                        elif parsed_item['poz_no'].startswith('10.100'):
                            is_labor = True
                        
                        # Önce mevcut bölüme göre ata
                        if current_section == 'labor':
                            analysis_data['labor'].append(parsed_item)
                            print(f"İşçilik eklendi: {parsed_item['poz_no']}")
                        elif current_section == 'materials':
                            analysis_data['materials'].append(parsed_item)
                            print(f"Malzeme eklendi: {parsed_item['poz_no']}")
                        elif is_material:
                            current_section = 'materials'
                            analysis_data['materials'].append(parsed_item)
                            print(f"Malzeme eklendi: {parsed_item['poz_no']}")
                        elif is_labor:
                            current_section = 'labor'
                            analysis_data['labor'].append(parsed_item)
                            print(f"İşçilik eklendi: {parsed_item['poz_no']}")
                        else:
                            # Son çare: poz numarasına göre karar ver
                            if parsed_item['poz_no'].startswith('10.1'):
                                analysis_data['labor'].append(parsed_item)
                                print(f"İşçilik eklendi (poz ile): {parsed_item['poz_no']}")
                            else:
                                analysis_data['materials'].append(parsed_item)
                                print(f"Malzeme eklendi (poz ile): {parsed_item['poz_no']}")

                # Toplam hesaplamaları - resimdeki gibi
                if 'Malzeme + İşçilik' in text and 'Tutarı' in text:
                    # Toplam tutarı çıkar - resimdeki format: "Malzeme + İşçilik Tutarı ||| 11.509,07"
                    total_match = re.search(r'(\d+[.,]\d+)', text)
                    if total_match:
                        analysis_data['subtotal'] = float(total_match.group(1).replace(',', '.'))
                        print(f"Alt toplam bulundu: {analysis_data['subtotal']}")
                    continue
                
                elif '25% Yüklenici' in text or '% Yüklenici' in text or 'Yüklenici kârı' in text:
                    # Kâr ve genel giderleri çıkar
                    overhead_match = re.search(r'(\d+[.,]\d+)', text)
                    if overhead_match:
                        analysis_data['overhead'] = float(overhead_match.group(1).replace(',', '.'))
                        print(f"Kâr ve genel gider bulundu: {analysis_data['overhead']}")
                    continue
                
                elif any(price_pattern in text for price_pattern in [
                    '1 m² Fiyatı', '1 Ton Fiyatı', '1 m³ Fiyatı', '1 Sa Fiyatı', '1 Adet Fiyatı'
                ]):
                    # Birim fiyatı çıkar - resimdeki gibi
                    unit_price_match = re.search(r'(\d+[.,]\d+)', text)
                    if unit_price_match:
                        analysis_data['unit_price'] = float(unit_price_match.group(1).replace(',', '.'))
                        print(f"Birim fiyat bulundu: {analysis_data['unit_price']}")
                    continue

                # Analiz sonu göstergeleri - resimdeki gibi
                elif any(end_marker in text for end_marker in [
                    'Onaylanmış', 'Ölçü:', 'Not:', 'Açıklama:', 'detay projesine',
                    'uygununa projesi', 'teknik şartnamesiyle', 'diyafram duvar',
                    'İnşaat bünyesine giren', 'minimum uzunlukta', 'diyafram duvar kavramı'
                ]):
                    print(f"Analiz sonu bulundu: {text[:50]}...")
                    break


        if analysis_start_page is None:
            print(f"Poz '{poz_no}' için başlık bulunamadı!")
            return analysis_data

        # Son kontrol ve temizlik
        print(f"\nAnaliz tamamlandı:")
        print(f"- Poz: {analysis_data['poz_no']}")
        print(f"- Açıklama: {analysis_data['description']}")
        print(f"- Birim: {analysis_data['unit']}")
        print(f"- Malzeme sayısı: {len(analysis_data['materials'])}")
        print(f"- İşçilik sayısı: {len(analysis_data['labor'])}")
        print(f"- Ara toplam: {analysis_data['subtotal']}")
        print(f"- Yüklenici kârı: {analysis_data['overhead']}")
        print(f"- Birim fiyat: {analysis_data['unit_price']}")

        return analysis_data


