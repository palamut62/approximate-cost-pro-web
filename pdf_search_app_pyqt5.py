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


class CSVDataManager:
    """PDF klasöründeki CSV dosyalarından pozları yönetir"""

    def __init__(self):
        self.csv_folder = Path(__file__).parent / "PDF"
        self.poz_data = {}  # Poz No -> Poz Verisi
        # self.load_csv_files() # Blocking call removed

    def load_csv_files(self):
        """PDF klasöründeki tüm CSV dosyalarını yükle (Sync)"""
        # Kept for backward compatibility if needed logic
        if not self.csv_folder.exists():
            print(f"CSV klasörü bulunamadı: {self.csv_folder}")
            return

        csv_files = list(self.csv_folder.glob("*.csv"))
        if not csv_files:
            return

        print(f"Bulunan CSV dosyaları (Sync): {len(csv_files)}")
        for csv_file in csv_files:
            self.load_single_csv(csv_file)

        csv_files = list(self.csv_folder.glob("*.csv"))
        if not csv_files:
            print("CSV dosyası bulunamadı")
            return

        print(f"Bulunan CSV dosyaları: {len(csv_files)}")
        for csv_file in csv_files:
            self.load_single_csv(csv_file)

    def load_single_csv(self, csv_path):
        """Tek bir CSV dosyasını yükle"""
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            print(f"CSV yüklendi: {csv_path.name} ({len(df)} satır)")

            # Gerekli sütunları kontrol et
            required_columns = ['Poz No', 'Açıklama', 'Kurum']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"⚠️ Uyarı: {csv_path.name} dosyasında eksik sütunlar: {missing_columns}")
                return

            # Pozları indexe ekle
            for idx, row in df.iterrows():
                poz_no = str(row['Poz No']).strip()

                poz_info = {
                    'poz_no': poz_no,
                    'description': str(row.get('Açıklama', '')).strip(),
                    'unit': str(row.get('Birim', '')).strip(),
                    'quantity': str(row.get('Miktar', '')).strip(),
                    'quantity': str(row.get('Miktar', '')).strip(),
                    'institution': str(row.get('Kurum', '')).strip(),
                    'source_file': csv_path.name
                }
                
                # Fiyat sütununu bulmak için alternatifleri kontrol et
                price_cols = ['Birim Fiyatı (TL)', 'Birim Fiyatı', 'Birim Fiyat', 'Fiyat', 'Fiyatı', '2024 Birim Fiyatı', '2025 Birim Fiyatı']
                for col in price_cols:
                    if col in row:
                        val = str(row.get(col, '')).strip()
                        if val and val.lower() != 'nan':
                            poz_info['unit_price'] = val
                            break
                            
                if 'unit_price' not in poz_info:
                     poz_info['unit_price'] = '0,00'

                self.poz_data[poz_no] = poz_info

        except Exception as e:
            print(f"CSV yükleme hatası ({csv_path.name}): {str(e)}")

    def search_poz(self, poz_no: str):
        """Poz numarası ile arama"""
        poz_no = poz_no.strip()
        if poz_no in self.poz_data:
            return self.poz_data[poz_no]
        return None

    def search_keyword(self, keyword: str):
        """Anahtar kelime ile arama"""
        results = []
        keyword_lower = keyword.lower()

        for poz_no, poz_info in self.poz_data.items():
            if (keyword_lower in poz_info['description'].lower() or
                    keyword_lower in poz_info['institution'].lower() or
                    keyword_lower in poz_no):
                results.append(poz_info)

        return results

    def get_all_pozlar(self):
        """Tüm pozları getir"""
        return list(self.poz_data.values())

    def get_institutions(self):
        """Tüm benzersiz kurumları getir"""
        institutions = set()
        for poz_info in self.poz_data.values():
            if poz_info['institution']:
                institutions.add(poz_info['institution'])
        return sorted(list(institutions))


class LoadingThread(QThread):
    progress_signal = pyqtSignal(str, int, int)
    finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, search_engine, files):
        super().__init__()
        self.search_engine = search_engine
        self.files = files
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        loaded_count = 0
        for i, file_path in enumerate(self.files):
            if self._stop_requested:
                break
            try:
                file_name = Path(file_path).name
                self.progress_signal.emit(file_name, i + 1, len(self.files))

                if self.search_engine.load_pdf(str(file_path)):
                    loaded_count += 1

            except Exception as e:
                self.error_signal.emit(f"Hata - {file_name}: {str(e)}")

        self.finished_signal.emit(loaded_count)


class PozAnalyzer(QThread):
    """PDF'lerden poz analizlerini çeken sınıf"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, analiz_folder):
        super().__init__()
        self.analiz_folder = Path(analiz_folder)
        self.poz_analyses = {}
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        """PDF'leri analiz et"""
        pdf_files = sorted(self.analiz_folder.glob("*.pdf"))

        if not pdf_files:
            self.progress.emit("ANALIZ klasöründe PDF bulunamadı!")
            self.finished.emit({})
            return

        self.progress.emit(f"Bulunan {len(pdf_files)} PDF analiz ediliyor...")

        for pdf_file in pdf_files:
            if self._stop_requested:
                break
            self.progress.emit(f"İşleniyor: {pdf_file.name}")
            self._extract_from_pdf(str(pdf_file))

        self.progress.emit(f"Toplam {len(self.poz_analyses)} poz analizi bulundu")
        self.finished.emit(self.poz_analyses)

    def _extract_from_pdf(self, pdf_path):
        """PDF'den poz analizlerini çıkar"""
        try:
            doc = fitz.open(pdf_path)
            lines_all = []

            # Tüm sayfaları birleştir
            for page in doc:
                text = page.get_text()
                lines = text.split('\n')
                lines_all.extend(lines)

            doc.close()

            # Poz analizlerini çıkar
            i = 0
            while i < len(lines_all):
                line = lines_all[i].strip()

                # POZ NUMARASI TESPİTİ (15.xxx.xxxx veya 19.xxx.xxxx)
                if re.match(r'^(15|19)\.\d{3}\.\d{4}$', line):
                    poz_no = line

                    # Poz açıklaması - genellikle 3. satır sonrası
                    description = ""
                    unit = ""

                    # Sayfanın sonraki 20 satırında açıklamayı ve birimi ara
                    for j in range(i + 1, min(i + 20, len(lines_all))):
                        current = lines_all[j].strip()

                        # İlk satırı atla (genellikle "Poz No" veya "Analizin Adı")
                        if j == i + 1 or j == i + 2:
                            continue

                        # Açıklamayı bul (genellikle 3. satır)
                        if j == i + 3 and not description:
                            description = current

                        # Ölçü birimini bul
                        if "Ölçü Birimi" in current and not unit:
                            if j + 1 < len(lines_all):
                                unit_candidate = lines_all[j + 1].strip()
                                if unit_candidate and unit_candidate not in ["Miktarı", "Birim Fiyatı", "Tutarı (TL)"]:
                                    unit = unit_candidate
                                    break

                    # Alt analizleri çıkar
                    sub_analyses = self._extract_sub_analyses(lines_all, i)

                    # Özet bilgileri çıkar
                    summary = self._extract_summary(lines_all, i)

                    # Poz analizini kaydet
                    self.poz_analyses[poz_no] = {
                        'poz_no': poz_no,
                        'description': description,
                        'unit': unit,
                        'sub_analyses': sub_analyses,
                        'summary': summary,
                        'file': Path(pdf_path).name
                    }

                i += 1

        except Exception as e:
            print(f"PDF işleme hatası {pdf_path}: {e}")

    def _extract_sub_analyses(self, lines, start_idx):
        """Alt analizleri çıkar (10.xxx.xxxx veya 19.xxx.xxxx)"""
        sub_analyses = []
        current_type = ""  # "Malzeme" veya "İşçilik"

        # Başlangıç pozunu sakla (kendi kodunu almamak için)
        start_poz_no = lines[start_idx].strip() if start_idx < len(lines) else ""

        # NEXT POZ SINIRINII BUL: Sonraki ana poz'un satır numarasını bul
        next_poz_idx = len(lines)
        for next_idx in range(start_idx + 1, min(start_idx + 500, len(lines))):
            line_stripped = lines[next_idx].strip()
            if re.match(r'^(15|19)\.\d{3}\.\d{4}$', line_stripped):
                # Bu 15/19.xxx kodu, "Poz No" başlığının hemen sonrasında mı?
                is_main_poz = False
                for prev_idx in range(max(0, next_idx - 3), next_idx):
                    if lines[prev_idx].strip() == "Poz No":
                        is_main_poz = True
                        break

                if is_main_poz:
                    # Sonraki ana poz bulundu
                    next_poz_idx = next_idx
                    break

        # Alt analiz kodlarını ara (10.100.xxxx veya 19.100.xxxx)
        i = start_idx + 1  # Başlangıç pozü atla
        while i < min(next_poz_idx, start_idx + 500, len(lines)):
            line = lines[i].strip()

            # Poz'un ÖZET bölümüne ulaştık demek ki daha fazla sub-analiz yok
            line_lower = line.lower()

            # Analiz-1: Malzeme + İşçilik Tutar
            # if ("tutar" in line_lower and ("malzeme" in line_lower or "malz" in line_lower) and
            #     (any(variant in line_lower for variant in ["işçilik", "isçilik", "iscilik", "iş", "~"]) or
            #      len(line) > 10 and "+" in line)):
            #     pass # break removed to ensure full scan

            # Analiz-2: unit + "Fiyatı" pattern
            # if ("fiyat" in line_lower and line.startswith("1 ") and
            #     any(unit in line_lower for unit in ["sa ", "m3 ", "m² ", "m2 ", "ton ", "kg ", "dk ", "gün ", "l ", "lt"])):
            #     pass # break removed

            # Yeni pozun başlangıç işareti
            if line == "Poz No" and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                    break

            # Malzeme/İşçilik başlıklarını tespit et
            line_lower = line.lower()
            is_type_header = (line in ["Malzeme", "İşçilik", "MALZEME", "İŞÇİLİK"] or
                             line_lower in ["malzeme", "işçilik"] or
                             line_lower.startswith("malz") or
                             line_lower.startswith("isç") or
                             line_lower == "iscilik" or
                             (len(line) < 15 and line_lower.startswith("is") and len(line) > 4))

            if is_type_header and line.strip():
                current_type = line
                i += 1
                # Başlık altındaki açıklamalar/boş satırları atla
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

                # ANA POZ KONTROLÜ
                is_main_poz = False
                for prev_idx in range(max(0, i - 3), i):
                    if lines[prev_idx].strip() == "Poz No":
                        is_main_poz = True
                        break

                if is_main_poz:
                    i += 1
                    continue

                name = ""
                unit = ""
                qty_str = ""
                price_str = ""

                # Sonraki satırlardan veri topla
                j = i + 1
                name_lines = []
                max_name_lines = 10

                while j < len(lines) and len(name_lines) < max_name_lines:
                    current = lines[j].strip()

                    # Boş satırı geç
                    if not current:
                        j += 1
                        continue

                    # AÇIKLAMA SATIRI TESPİTİ
                    is_pure_number = current.replace(',', '').replace('.', '').replace('-', '').replace('+', '').isdigit()
                    if is_pure_number and len(current) < 20:
                        j += 1
                        continue

                    # Birim satırı bulundu
                    known_units = ["Sa", "Kg", "m³", "m", "m²", "L", "dk", "Saat", "kg", "ha", "gün",
                                  "ton", "Ton", "mL", "cm", "mm", "km", "t", "hm"]
                    is_unit = current in known_units

                    # Veya çok kısa alfanumerik
                    if not is_unit:
                        cleaned = current.replace('³', '').replace('²', '')
                        is_unit = (len(current) <= 3 and
                                  all(c.isalpha() or c in '³²' for c in current) and
                                  current not in ["Su", "Yal", "Bez", "Cam", "Yer", "Yol"])

                    if is_unit:
                        unit = current
                        # Birim buldu, sonra miktar ve fiyat gelecek
                        qty_str = lines[j + 1].strip() if j + 1 < len(lines) else ""
                        price_str = lines[j + 2].strip() if j + 2 < len(lines) else ""
                        break
                    else:
                        # Ad'ın devamı, topla
                        name_lines.append(current)

                    j += 1

                name = " ".join(name_lines)

                # Veri kontrolü ve dönüştürme
                if name and unit and qty_str and price_str:
                    try:
                        # Türkçe number format dönüştür
                        qty = float(qty_str.replace(',', '.'))
                        # Fiyat binler ayırıcısı ile olabilir
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
                    except Exception as e:
                        pass

            i += 1

        return sub_analyses

    def _extract_summary(self, lines, start_idx):
        """Özet bilgileri çıkar (Malzeme+İşçilik, Yüklenici kârı, Fiyat)"""
        summary = {'subtotal': '', 'overhead': '', 'unit_price': ''}

        for i in range(start_idx, min(start_idx + 50, len(lines))):
            line = lines[i].strip()

            if "Malzeme + İşçilik" in line or "Malzeme+İşçilik" in line:
                if i + 1 < len(lines):
                    summary['subtotal'] = lines[i + 1].strip()

            elif "25 %" in line or "%25" in line:
                if i + 1 < len(lines):
                    summary['overhead'] = lines[i + 1].strip()

            elif "1 m" in line and "Fiyatı" in line:
                if i + 1 < len(lines):
                    summary['unit_price'] = lines[i + 1].strip()

        return summary


class CSVLoaderThread(QThread):
    """CSV ve PDF dosyalarını arka planda yükleyen thread (Cache destekli)"""
    finished = pyqtSignal(dict, int, list) # data, count, loaded_files
    error = pyqtSignal(str)
    progress = pyqtSignal(str) # Progress mesajı

    def __init__(self, csv_folder):
        super().__init__()
        self.csv_folder = csv_folder
        self._stop_requested = False
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_file = self.cache_dir / "poz_data_cache.json"

    def stop(self):
        self._stop_requested = True

    def get_file_hash(self, file_path):
        """Dosya hash'i hesapla"""
        try:
            stat = file_path.stat()
            hash_string = f"{file_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_string.encode()).hexdigest()
        except Exception:
            return None

    def load_cache(self):
        """Cache'den poz verilerini yükle"""
        try:
            if not self.cache_file.exists():
                return None, None, None

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Dosya hash'lerini kontrol et
            file_hashes = cache_data.get('file_hashes', {})

            # Mevcut dosyaları al
            current_files = {}
            if self.csv_folder.exists():
                for f in self.csv_folder.glob("*.csv"):
                    current_files[f.name] = self.get_file_hash(f)
                for f in self.csv_folder.glob("*.pdf"):
                    current_files[f.name] = self.get_file_hash(f)

            # Dosya değişikliği kontrolü
            cached_files = set(file_hashes.keys())
            current_file_names = set(current_files.keys())

            # Yeni dosya var mı?
            if current_file_names - cached_files:
                return None, None, None

            # Silinen dosya var mı?
            if cached_files - current_file_names:
                return None, None, None

            # Hash değişmiş mi?
            for fname, fhash in current_files.items():
                if file_hashes.get(fname) != fhash:
                    return None, None, None

            # Cache geçerli
            return (
                cache_data.get('poz_data', {}),
                cache_data.get('loaded_files', []),
                cache_data.get('timestamp', '')
            )

        except Exception as e:
            print(f"Cache yükleme hatası: {e}")
            return None, None, None

    def save_cache(self, poz_data, loaded_files):
        """Poz verilerini cache'e kaydet"""
        try:
            self.cache_dir.mkdir(exist_ok=True)

            # Dosya hash'lerini hesapla
            file_hashes = {}
            if self.csv_folder.exists():
                for f in self.csv_folder.glob("*.csv"):
                    file_hashes[f.name] = self.get_file_hash(f)
                for f in self.csv_folder.glob("*.pdf"):
                    file_hashes[f.name] = self.get_file_hash(f)

            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'poz_data': poz_data,
                'loaded_files': loaded_files,
                'file_hashes': file_hashes
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"Poz cache kaydedildi: {len(poz_data)} poz, {len(loaded_files)} dosya")
            return True
        except Exception as e:
            print(f"Cache kaydetme hatası: {e}")
            return False

    def run(self):
        try:
            # Önce cache'i kontrol et
            self.progress.emit("Cache kontrol ediliyor...")
            cached_data, cached_files, cache_time = self.load_cache()

            if cached_data is not None:
                self.progress.emit(f"Cache'den yüklendi ({len(cached_data)} poz)")
                self.finished.emit(cached_data, len(cached_data), cached_files)
                return

            poz_data = {}
            loaded_files = []

            if not self.csv_folder.exists():
                self.error.emit(f"PDF klasörü bulunamadı: {self.csv_folder}")
                return

            # CSV dosyalarını yükle
            csv_files = list(self.csv_folder.glob("*.csv"))
            self.progress.emit(f"CSV dosyaları taranıyor... ({len(csv_files)} dosya)")

            for csv_path in csv_files:
                if self._stop_requested:
                    break
                try:
                    df = pd.read_csv(csv_path, encoding='utf-8-sig')

                    # Sütun kontrolü
                    required_columns = ['Poz No', 'Açıklama', 'Kurum']
                    missing_columns = [col for col in required_columns if col not in df.columns]

                    if missing_columns:
                        continue

                    csv_poz_count = 0
                    for idx, row in df.iterrows():
                        poz_no = str(row['Poz No']).strip()

                        poz_info = {
                            'poz_no': poz_no,
                            'description': str(row.get('Açıklama', '')).strip(),
                            'unit': str(row.get('Birim', '')).strip(),
                            'quantity': str(row.get('Miktar', '')).strip(),
                            'institution': str(row.get('Kurum', '')).strip(),
                            'source_file': csv_path.name
                        }

                        # Fiyat parse
                        price_cols = ['Birim Fiyatı (TL)', 'Birim Fiyatı', 'Birim Fiyat', 'Fiyat', 'Fiyatı', '2024 Birim Fiyatı', '2025 Birim Fiyatı']
                        for col in price_cols:
                            if col in row:
                                val = str(row.get(col, '')).strip()
                                if val and val.lower() != 'nan':
                                    poz_info['unit_price'] = val
                                    break

                        if 'unit_price' not in poz_info:
                             poz_info['unit_price'] = '0,00'

                        poz_data[poz_no] = poz_info
                        csv_poz_count += 1

                    loaded_files.append({
                        'name': csv_path.name,
                        'type': 'CSV',
                        'poz_count': csv_poz_count
                    })

                except Exception as e:
                    print(f"CSV Okuma hatası {csv_path}: {e}")

            # PDF dosyalarını yükle
            pdf_files = list(self.csv_folder.glob("*.pdf"))
            self.progress.emit(f"PDF dosyaları taranıyor... ({len(pdf_files)} dosya)")

            for pdf_path in pdf_files:
                if self._stop_requested:
                    break
                try:
                    self.progress.emit(f"PDF yükleniyor: {pdf_path.name}")
                    pdf_poz_count = self.extract_pozlar_from_pdf(pdf_path, poz_data)

                    if pdf_poz_count > 0:
                        loaded_files.append({
                            'name': pdf_path.name,
                            'type': 'PDF',
                            'poz_count': pdf_poz_count
                        })

                except Exception as e:
                    print(f"PDF Okuma hatası {pdf_path}: {e}")

            # Cache'e kaydet
            self.save_cache(poz_data, loaded_files)

            self.finished.emit(poz_data, len(poz_data), loaded_files)

        except Exception as e:
            self.error.emit(str(e))

    def extract_pozlar_from_pdf(self, pdf_path, poz_data):
        """PDF dosyasından pozları çıkar"""
        try:
            doc = fitz.open(pdf_path)
            poz_count = 0

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
                    # Örnek: 10.110.1003, 02.017, Y.15.140/01, MSB.700
                    poz_patterns = [
                        r'^(\d{2}\.\d{3}\.\d{4})',  # 10.110.1003
                        r'^(\d{2}\.\d{3})',  # 02.017
                        r'^([A-Z]{1,3}\.\d{2,3}\.\d{3})',  # Y.15.140
                        r'^([A-Z]{2,3}\.\d{3})',  # MSB.700
                    ]

                    poz_no = None
                    for pattern in poz_patterns:
                        match = re.match(pattern, line)
                        if match:
                            poz_no = match.group(1)
                            break

                    if poz_no and poz_no not in poz_data:
                        # Açıklama ve fiyat çıkar
                        remaining = line[len(poz_no):].strip()

                        # Fiyat bulmaya çalış (sayısal değer)
                        price_match = re.search(r'([\d.,]+)\s*(?:TL)?$', remaining)
                        unit_price = '0,00'
                        description = remaining

                        if price_match:
                            try:
                                price_str = price_match.group(1).replace('.', '').replace(',', '.')
                                float(price_str)  # Geçerli sayı mı?
                                unit_price = price_match.group(1)
                                description = remaining[:price_match.start()].strip()
                            except ValueError:
                                pass

                        # Birim bulmaya çalış
                        unit = ''
                        unit_patterns = ['m³', 'm²', 'm2', 'm3', 'ton', 'kg', 'adet', 'lt', 'sa', 'gün', 'ay']
                        for u in unit_patterns:
                            if u in description.lower():
                                unit = u
                                break

                        poz_info = {
                            'poz_no': poz_no,
                            'description': description[:200] if description else f"PDF Poz: {poz_no}",
                            'unit': unit,
                            'quantity': '',
                            'institution': 'PDF',
                            'unit_price': unit_price,
                            'source_file': pdf_path.name
                        }

                        poz_data[poz_no] = poz_info
                        poz_count += 1

            doc.close()
            return poz_count

        except Exception as e:
            print(f"PDF poz çıkarma hatası {pdf_path}: {e}")
            return 0

class ExtractorWorkerThread(QThread):
    """PDF → CSV çıkartma işlemini thread'de çalıştır"""

    progress = pyqtSignal(str, int)  # message, progress
    finished = pyqtSignal(str)  # result_text
    error = pyqtSignal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.pdf_folder = Path(__file__).parent / "PDF"
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        try:
            from poz_extractor_app import PDFPozExtractor

            # PDF dosyalarını bul
            pdf_files = list(self.pdf_folder.glob("*.pdf"))
            if not pdf_files:
                self.error.emit("PDF klasöründe dosya bulunamadı!")
                return

            self.progress.emit(f"Bulunan PDF dosyaları: {len(pdf_files)}", 10)

            # Pozları çıkart
            extractor = PDFPozExtractor()
            all_results = []
            total_files = len(pdf_files)

            for idx, pdf_file in enumerate(pdf_files):
                if self._stop_requested:
                    break
                try:
                    self.progress.emit(f"İşleniyor: {pdf_file.name}", int(20 + (70 * idx / total_files)))

                    results = extractor.extract_poz_from_pdf(str(pdf_file))
                    all_results.extend(results)

                except Exception as e:
                    self.error.emit(f"Hata - {pdf_file.name}: {str(e)}")

            self.progress.emit(f"Toplam {len(all_results)} poz çıkartıldı", 90)

            # CSV'ye kaydet
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_file = self.pdf_folder / f"pozlar_{timestamp}.csv"

            if extractor.export_to_csv(str(csv_file), all_results):
                self.progress.emit(f"CSV kaydedildi: {csv_file.name}", 100)
                self.finished.emit("CSV dosyası başarıyla oluşturuldu!")
            else:
                self.error.emit("CSV kaydedilemedi!")

        except Exception as e:
            self.error.emit(f"Genel hata: {str(e)}")


class BackgroundExtractorThread(QThread):
    """PDF → CSV çıkartma işlemini arka planda sessizce çalıştır (UI göstermez)"""

    finished = pyqtSignal(str)  # result_message
    error = pyqtSignal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.pdf_folder = Path(__file__).parent / "PDF"
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        try:
            from poz_extractor_app import PDFPozExtractor

            # PDF dosyalarını bul
            pdf_files = list(self.pdf_folder.glob("*.pdf"))
            if not pdf_files:
                self.error.emit("PDF klasöründe dosya bulunamadı!")
                return

            # Pozları çıkart
            extractor = PDFPozExtractor()
            all_results = []
            total_files = len(pdf_files)

            for pdf_file in pdf_files:
                if self._stop_requested:
                    break
                try:
                    results = extractor.extract_poz_from_pdf(str(pdf_file))
                    all_results.extend(results)

                except Exception as e:
                    # Sessizce devam et, hata sayılmaz
                    pass

            # CSV'ye kaydet
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_file = self.pdf_folder / f"pozlar_{timestamp}.csv"

            if extractor.export_to_csv(str(csv_file), all_results):
                result_msg = f"CSV başarıyla güncellendi ({len(all_results)} poz)"
                self.finished.emit(result_msg)
            else:
                self.error.emit("CSV kaydedilemedi!")

        except Exception as e:
            self.error.emit(f"Çıkartma hatası: {str(e)}")


class PozViewerWidget(QWidget):
    """Poz Analiz Viewer - ANALIZ klasöründen PDF'leri okuyarak pozları gösterir"""

    def __init__(self):
        super().__init__()
        self.poz_analyses = {}
        self.analiz_folder = Path(__file__).parent / "ANALIZ"
        self.parent_app = None  # Ana uygulamaya referans
        self.current_selected_poz = None  # Şu anda seçili poz
        self.analyzer = None  # Thread referansı
        self.setup_ui()
        self.load_analyses()

    def setup_ui(self):
        """UI kurulumu"""
        main_layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Hazır")
        main_layout.addWidget(self.status_label)

        # 2 Panel Layout
        splitter = QSplitter(Qt.Horizontal)

        # ===== SOL PANEL: Ana Pozlar =====
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        left_group = QGroupBox("Ana Pozlar")
        left_group_layout = QVBoxLayout()

        # Arama çubuğu
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Poz No veya Açıklama ara...")
        self.search_input.textChanged.connect(self.on_search_changed)
        left_group_layout.addWidget(self.search_input)

        self.poz_list = QListWidget()
        self.poz_list.itemClicked.connect(self.on_poz_selected)
        left_group_layout.addWidget(self.poz_list)

        left_group.setLayout(left_group_layout)
        left_layout.addWidget(left_group)
        left_panel.setLayout(left_layout)

        # ===== SAĞ PANEL: Analiz Detayları =====
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: white;")  # Kağıt görünümü
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20, 20, 20, 20)

        # 1. Başlık (Mevzuat Formatı)
        header_frame = QFrame()
        header_frame.setStyleSheet("border: 2px solid black; margin-bottom: 10px;")
        header_layout = QVBoxLayout()
        
        title_lbl = QLabel("T.C.\nÇEVRE VE ŞEHİRCİLİK BAKANLIĞI\nBİRİM FİYAT ANALİZİ")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14pt; color: block;")
        header_layout.addWidget(title_lbl)
        
        # Poz Bilgileri Grid
        info_grid = QFormLayout()
        info_grid.setLabelAlignment(Qt.AlignRight)
        
        self.poz_no_label = QLabel("-")
        self.poz_no_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        
        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 11pt;")
        
        self.unit_label = QLabel("-")
        self.unit_label.setStyleSheet("font-weight: bold;")
        
        info_grid.addRow(QLabel("Poz No:"), self.poz_no_label)
        info_grid.addRow(QLabel("Tanımı:"), self.description_label)
        info_grid.addRow(QLabel("Ölçü Birimi:"), self.unit_label)
        
        header_layout.addLayout(info_grid)
        header_frame.setLayout(header_layout)
        right_layout.addWidget(header_frame)

        # 2. Analiz Tablosu
        self.analyses_table = QTableWidget()
        self.analyses_table.setColumnCount(7)
        self.analyses_table.setHorizontalHeaderLabels([
            'Grup', 'Rayiç No', 'Açıklama', 'Birim', 'Miktar', 'Birim Fiyat', 'Tutar'
        ])
        
        # Tablo stili
        self.analyses_table.setStyleSheet("""
            QTableWidget { border: 1px solid black; gridline-color: black; }
            QHeaderView::section { background-color: #E0E0E0; font-weight: bold; border: 1px solid black; }
        """)
        self.analyses_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Açıklama esnek
        self.analyses_table.verticalHeader().setVisible(False)
        
        right_layout.addWidget(self.analyses_table, 1)

        # 3. Alt Toplamlar (Resmi Format)
        summary_frame = QFrame()
        summary_frame.setStyleSheet("border: 2px solid black; margin-top: 10px;")
        summary_layout = QFormLayout()
        summary_layout.setLabelAlignment(Qt.AlignRight)
        
        self.subtotal_label = QLabel("0,00 TL")
        self.overhead_label = QLabel("0,00 TL")
        self.total_price_label = QLabel("0,00 TL")
        self.unit_price_label = QLabel("0,00 TL") # for unit price extraction check
        
        font_bold = QFont()
        font_bold.setBold(True)
        font_bold.setPointSize(10)
        
        self.subtotal_label.setFont(font_bold)
        self.overhead_label.setFont(font_bold)
        
        font_total = QFont()
        font_total.setBold(True)
        font_total.setPointSize(12)
        self.total_price_label.setFont(font_total)
        self.total_price_label.setStyleSheet("color: #D32F2F;") # Kırmızı
        
        summary_layout.addRow("Malzeme + İşçilik + Makine Toplamı:", self.subtotal_label)
        summary_layout.addRow("%25 Yüklenici Kârı ve Genel Giderler:", self.overhead_label)
        summary_layout.addRow("GENEL TOPLAM (Birim Fiyat):", self.total_price_label)
        
        summary_frame.setLayout(summary_layout)
        right_layout.addWidget(summary_frame)

        right_panel.setLayout(right_layout)

        # Splitter'a panelleri ekle (Değişmedi)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 950])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter, 1)

        # Alt butonlar
        buttons_layout = QHBoxLayout()

        self.export_btn = QPushButton("📤 Analiz İçin Aktar")
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.export_btn.clicked.connect(self.export_to_analysis_tab)
        buttons_layout.addWidget(self.export_btn)

        # Maliyet Hesabına Ekle Butonu (YENİ)
        self.add_cost_btn = QPushButton("💰 Projeye Ekle")
        self.add_cost_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        self.add_cost_btn.clicked.connect(self.add_to_project)
        buttons_layout.addWidget(self.add_cost_btn)

        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.refresh_btn.clicked.connect(self.load_analyses)
        buttons_layout.addWidget(self.refresh_btn)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def load_analyses(self):
        """PDF'lerden analizleri yükle"""
        # Önceki analyzer thread'i varsa durdur
        if self.analyzer and self.analyzer.isRunning():
            self.analyzer.stop()
            self.analyzer.wait(1000)

        self.progress_bar.setVisible(True)
        self.status_label.setText("PDF'ler analiz ediliyor...")
        self.poz_list.clear()

        self.analyzer = PozAnalyzer(self.analiz_folder)
        self.analyzer.progress.connect(self.on_progress)
        self.analyzer.finished.connect(self.on_analyses_loaded)
        self.analyzer.start()

        # Ana uygulamaya thread'i kaydet (closeEvent için)
        if self.parent_app and hasattr(self.parent_app, '_active_threads'):
            self.parent_app._active_threads.append(self.analyzer)

    def on_progress(self, message):
        """İlerleme mesajı"""
        self.status_label.setText(message)

    def on_analyses_loaded(self, analyses):
        """Analizler yüklendi"""
        self.poz_analyses = analyses
        self.progress_bar.setVisible(False)

        if not analyses:
            QMessageBox.warning(self, "Hata", "Poz analizi bulunamadı!")
            self.status_label.setText("Poz analizi bulunamadı")
            return

        # Listete poz'ları ekle
        for poz_no, data in sorted(analyses.items()):
            item = QListWidgetItem(f"{poz_no} - {data['description'][:50]}")
            item.setData(Qt.UserRole, poz_no)
            self.poz_list.addItem(item)

        self.status_label.setText(f"Toplam {len(analyses)} poz analizi yüklendi")

        # İlk pozı seç
        if self.poz_list.count() > 0:
            self.poz_list.setCurrentRow(0)
            self.on_poz_selected(self.poz_list.item(0))

    def on_poz_selected(self, item):
        """Poz seçildi"""
        poz_no = item.data(Qt.UserRole)

        if poz_no not in self.poz_analyses:
            return

        # Şu anda seçili pozunu kaydet (Aktar butonu için)
        self.current_selected_poz = poz_no

        data = self.poz_analyses[poz_no]

        # Başlık bilgilerini güncelle
        self.poz_no_label.setText(f"Poz No: {data['poz_no']}")
        self.description_label.setText(f"Açıklama: {data['description']}")
        self.unit_label.setText(f"Birim: {data['unit']}")

        # Alt analizler tablosunu doldur
        self.analyses_table.setRowCount(0)

        total_amount = 0.0

        for row_idx, analysis in enumerate(data['sub_analyses']):
            self.analyses_table.insertRow(row_idx)

            # Tür sütunu (Malzeme/İşçilik)
            self.analyses_table.setItem(row_idx, 0, QTableWidgetItem(analysis.get('type', '')))
            # Poz No
            self.analyses_table.setItem(row_idx, 1, QTableWidgetItem(analysis['code']))
            # Tanımı
            self.analyses_table.setItem(row_idx, 2, QTableWidgetItem(analysis['name']))
            # Ölçü Birimi
            self.analyses_table.setItem(row_idx, 3, QTableWidgetItem(analysis['unit']))
            # Miktarı
            self.analyses_table.setItem(row_idx, 4, QTableWidgetItem(analysis['quantity']))
            # Birim Fiyatı
            self.analyses_table.setItem(row_idx, 5, QTableWidgetItem(analysis['unit_price']))
            # Tutarı
            self.analyses_table.setItem(row_idx, 6, QTableWidgetItem(analysis['total']))

            # Toplam tutarı hesapla (Turkish format: 1.234,56 → 1234.56)
            try:
                total_str = analysis['total'].replace('.', '').replace(',', '.')
                total_amount += float(total_str)
            except (ValueError, KeyError):
                pass

        # Özet bilgileri güncelle
        summary = data['summary']

        # Alt analizlerin toplamı = Malzeme + İşçilik
        subtotal_formatted = f"{total_amount:,.2f}".replace(',', '@').replace('.', ',').replace('@', '.')
        self.subtotal_label.setText(f"{subtotal_formatted} TL")

        # 25% Yüklenici Kârı hesapla
        overhead_amount = total_amount * 0.25
        overhead_formatted = f"{overhead_amount:,.2f}".replace(',', '@').replace('.', ',').replace('@', '.')
        self.overhead_label.setText(f"{overhead_formatted} TL")

        # Toplam Tutarı = Malzeme+İşçilik + 25% Kârı
        final_total = total_amount + overhead_amount
        formatted_final_total = f"{final_total:,.2f}".replace(',', '@').replace('.', ',').replace('@', '.')

        self.total_price_label.setText(f"{formatted_final_total} TL")
        #self.unit_price_label.setText(f"1 {data['unit']} Fiyatı: {summary.get('unit_price', '-')} TL")

        self.status_label.setText(f"Poz '{poz_no}' - {len(data['sub_analyses'])} alt analiz")

    def on_search_changed(self, text):
        """Poz arama filtresi"""
        search_text = text.strip().lower()

        # Listeyi temizle ve filtrele
        self.poz_list.clear()

        if not search_text:
            # Arama boşsa tümünü göster
            for poz_no, data in sorted(self.poz_analyses.items()):
                item = QListWidgetItem(f"{poz_no} - {data['description'][:50]}")
                item.setData(Qt.UserRole, poz_no)
                self.poz_list.addItem(item)
        else:
            # Filtreleme yap
            for poz_no, data in sorted(self.poz_analyses.items()):
                if (search_text in poz_no.lower() or
                    search_text in data['description'].lower()):
                    item = QListWidgetItem(f"{poz_no} - {data['description'][:50]}")
                    item.setData(Qt.UserRole, poz_no)
                    self.poz_list.addItem(item)

            # Bulunan sayısı status label'a yaz
            self.status_label.setText(f"Arama sonucu: {self.poz_list.count()} poz bulundu")

    def export_to_analysis_tab(self):
        """Seçili pozun detaylarını Poz Analizi sekmesine aktar"""
        try:
            if not self.current_selected_poz:
                QMessageBox.warning(self, "Uyarı", "Lütfen aktar etmek için bir poz seçiniz!")
                return

            if not self.parent_app:
                QMessageBox.warning(self, "Uyarı", "Ana uygulamaya erişim sağlanamadı!")
                return

            # Seçili pozun verilerini al
            poz_no = self.current_selected_poz
            poz_data = self.poz_analyses[poz_no]

            # Poz Analizi sekmesine erişim
            analysis_tab = self.parent_app.analysis_tab
            if not analysis_tab:
                QMessageBox.warning(self, "Uyarı", "Poz Analizi sekmesine erişim sağlanamadı!")
                return

            # Analiz sekmesinin load_analysis metodunu çağır
            # PozAnalyzer'dan gelen verileri AnalysisTableWidget formatına dönüştür
            analysis_data = {
                'poz_no': poz_data['poz_no'],
                'description': poz_data['description'],
                'unit': poz_data['unit'],
                'materials': [],
                'labor': []
            }

            # Alt analizleri malzeme/işçilik kategorilerine göre ayır
            for analysis in poz_data['sub_analyses']:
                item = {
                    'poz_no': analysis.get('code', ''),
                    'description': analysis.get('name', ''),
                    'unit': analysis.get('unit', ''),
                    'quantity': analysis.get('quantity', '0'),
                    'unit_price': analysis.get('unit_price', '0'),
                    'total': analysis.get('total', '0')
                }

                # Kategoriye göre ayır
                if 'Malzeme' in analysis.get('type', ''):
                    analysis_data['materials'].append(item)
            # Analiz sekmesine yükle
            if self.parent_app and hasattr(self.parent_app, 'analysis_tab'):
                 self.parent_app.analysis_tab.load_analysis(analysis_data)
                 self.parent_app.tab_widget.setCurrentWidget(self.parent_app.analysis_tab)
            else:
                 QMessageBox.warning(self, "Hata", "Analiz sekmesi bulunamadı.")
        
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Aktarım sırasında hata oluştu: {str(e)}")

    def add_to_project(self):
        """Seçili pozu aktif projeye ekle"""
        if not self.current_selected_poz:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir poz seçiniz!")
            return

        if not self.parent_app:
            return

        # Poz bilgilerini al
        poz_no = self.current_selected_poz
        data = self.poz_analyses[poz_no]
        
        # Fiyatı al (Sonuç etiketinden parse et)
        total_text = self.total_price_label.text()
        # "1.234,56 TL" -> 1234.56
        price_val = 0.0
        try:
             clean_text = total_text.replace(' TL', '').strip()
             # Turkish format check
             if ',' in clean_text and '.' in clean_text:
                 if clean_text.find('.') < clean_text.find(','):
                      # 1.234,56 -> US: 1234.56
                      price_val = float(clean_text.replace('.', '').replace(',', '.'))
                 else:
                      # 1,234.56 -> US: 1234.56
                      price_val = float(clean_text.replace(',', ''))
             elif ',' in clean_text:
                 # 123,45 -> 123.45
                 price_val = float(clean_text.replace(',', '.'))
             else:
                 price_val = float(clean_text)
        except:
             price_val = 0.0

        # CostEstimator sekmesine eriş
        cost_tab = self.parent_app.cost_tab
        if cost_tab:
            success = cost_tab.add_item_from_external(
                poz_no,
                data['description'],
                data['unit'],
                price_val
            )
            if success:
                QMessageBox.information(self, "Başarılı", f"{poz_no} projeye eklendi!")
                # Sekmeyi değiştir isteğe bağlı
                # self.parent_app.tab_widget.setCurrentWidget(cost_tab)



class AnalysisTableWidget(QWidget):
    """Düzenlenebilir Poz Analiz Tablosu"""

    def __init__(self):
        super().__init__()
        self.current_analysis = None
        self.parent_app = None  # Ana uygulama referansı
        self.search_engine = None  # Search engine referansı
        self.setup_ui()
        # CSV tablosu kaldırıldı - Poz Viewer sekmesinden aktar

    def setup_ui(self):
        """Analiz tablosu UI kurulumu - 2 Sütunlu Tasarım"""
        main_layout = QVBoxLayout()

        # ===== SOL PANEL: CSV Pozları ve Rayiçleri =====
        # SAĞ PANEL: Analiz Tabloları

        # Üst kısım - Başlık ve kontroller (her iki panel'i kapsayan)
        header_group = QGroupBox("Analiz Bilgileri")
        header_layout = QGridLayout()

        header_layout.addWidget(QLabel("Poz No:"), 0, 0)
        self.poz_no_label = QLabel("-")
        header_layout.addWidget(self.poz_no_label, 0, 1)

        header_layout.addWidget(QLabel("Analizin Adı:"), 0, 2)
        self.description_edit = QLineEdit()
        header_layout.addWidget(self.description_edit, 0, 3)

        header_layout.addWidget(QLabel("Ölçü Birimi:"), 1, 0)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(['m²', 'm³', 'm', 'kg', 'ton', 'adet', 'lt', 'Sa'])
        header_layout.addWidget(self.unit_combo, 1, 1)

        # Analiz çek bölümü
        self.poz_input = QLineEdit()
        self.poz_input.setPlaceholderText("Poz No girin (ör: 15.490.1003)")
        header_layout.addWidget(QLabel("Poz Analizi:"), 1, 2)
        header_layout.addWidget(self.poz_input, 1, 3)

        self.extract_analysis_btn = QPushButton("📊 Analiz Çek")
        self.extract_analysis_btn.clicked.connect(self.extract_analysis_from_input)
        self.extract_analysis_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        header_layout.addWidget(self.extract_analysis_btn, 2, 0, 1, 2)

        # Rayiç çekme bölümü
        self.extract_prices_btn = QPushButton("📋 Rayiç Çek")
        self.extract_prices_btn.clicked.connect(self.extract_unit_prices)
        self.extract_prices_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        header_layout.addWidget(self.extract_prices_btn, 2, 2, 1, 2)

        header_group.setLayout(header_layout)
        main_layout.addWidget(header_group)

        # ===== İÇERİK BÖLÜMÜ: SADECE SAĞ SÜTUN (ANALIZ TABLOLARI) =====
        content_layout = QHBoxLayout()

        # ===== ANALIZ TABLOLARI =====
        right_panel = QWidget()
        right_layout = QVBoxLayout()

        # Malzeme tablosu
        materials_group = QGroupBox("Malzeme")
        materials_layout = QVBoxLayout()

        # Malzeme butonları
        materials_buttons = QHBoxLayout()
        self.add_material_btn = QPushButton("+ Malzeme Ekle")
        self.add_material_btn.clicked.connect(self.add_material)
        self.remove_material_btn = QPushButton("- Seçili Malzemeyi Sil")
        self.remove_material_btn.clicked.connect(self.remove_material)

        materials_buttons.addWidget(self.add_material_btn)
        materials_buttons.addWidget(self.remove_material_btn)
        materials_buttons.addStretch()
        materials_layout.addLayout(materials_buttons)

        # Malzeme tablosu
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(6)
        self.materials_table.setHorizontalHeaderLabels([
            'Poz No', 'Tanımı', 'Ölçü Birimi', 'Miktarı', 'Birim Fiyatı', 'Tutarı (TL)'
        ])
        self.materials_table.horizontalHeader().setStretchLastSection(True)
        materials_layout.addWidget(self.materials_table)

        materials_group.setLayout(materials_layout)
        right_layout.addWidget(materials_group, 1)

        # İşçilik tablosu
        labor_group = QGroupBox("İşçilik")
        labor_layout = QVBoxLayout()

        # İşçilik butonları
        labor_buttons = QHBoxLayout()
        self.add_labor_btn = QPushButton("+ İşçilik Ekle")
        self.add_labor_btn.clicked.connect(self.add_labor)
        self.remove_labor_btn = QPushButton("- Seçili İşçiliği Sil")
        self.remove_labor_btn.clicked.connect(self.remove_labor)

        labor_buttons.addWidget(self.add_labor_btn)
        labor_buttons.addWidget(self.remove_labor_btn)
        labor_buttons.addStretch()
        labor_layout.addLayout(labor_buttons)

        # İşçilik tablosu
        self.labor_table = QTableWidget()
        self.labor_table.setColumnCount(6)
        self.labor_table.setHorizontalHeaderLabels([
            'Poz No', 'Tanımı', 'Ölçü Birimi', 'Miktarı', 'Birim Fiyatı', 'Tutarı (TL)'
        ])
        self.labor_table.horizontalHeader().setStretchLastSection(True)
        labor_layout.addWidget(self.labor_table)

        labor_group.setLayout(labor_layout)
        right_layout.addWidget(labor_group, 1)

        # Toplam hesaplamalar
        totals_group = QGroupBox("Hesaplamalar")
        totals_layout = QGridLayout()

        totals_layout.addWidget(QLabel("Malzeme + İşçilik Tutarı:"), 0, 0)
        self.subtotal_label = QLabel("0,00 TL")
        totals_layout.addWidget(self.subtotal_label, 0, 1)

        totals_layout.addWidget(QLabel("25% Yüklenici Kârı:"), 1, 0)
        self.overhead_label = QLabel("0,00 TL")
        totals_layout.addWidget(self.overhead_label, 1, 1)

        totals_layout.addWidget(QLabel("1 m² Fiyatı:"), 2, 0)
        self.unit_price_label = QLabel("0,00 TL")
        self.unit_price_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        totals_layout.addWidget(self.unit_price_label, 2, 1)

        # Yeniden hesapla butonu
        self.calculate_btn = QPushButton("Yeniden Hesapla")
        self.calculate_btn.clicked.connect(self.calculate_totals)
        totals_layout.addWidget(self.calculate_btn, 3, 0, 1, 2)

        totals_group.setLayout(totals_layout)
        right_layout.addWidget(totals_group)

        right_panel.setLayout(right_layout)
        content_layout.addWidget(right_panel, 1)  # Tam genişlik

        main_layout.addLayout(content_layout, 1)

        # Alt butonlar
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("Analizi Kaydet")
        self.save_btn.clicked.connect(self.save_analysis)

        self.export_btn = QPushButton("Excel'e Aktar")
        self.export_btn.clicked.connect(self.export_analysis)

        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.clicked.connect(self.clear_analysis)

        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addStretch()

        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def load_analysis(self, analysis_data):
        """Analiz verilerini tabloya yükle"""
        self.current_analysis = analysis_data

        # Başlık bilgilerini doldur
        self.poz_no_label.setText(analysis_data.get('poz_no', '-'))
        self.description_edit.setText(analysis_data.get('description', ''))

        unit = analysis_data.get('unit', 'm²')
        index = self.unit_combo.findText(unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

        # Malzeme tablosunu doldur
        materials = analysis_data.get('materials', [])
        self.materials_table.setRowCount(len(materials))
        for row, material in enumerate(materials):
            self.materials_table.setItem(row, 0, QTableWidgetItem(material.get('poz_no', '')))
            self.materials_table.setItem(row, 1, QTableWidgetItem(material.get('description', '')))
            self.materials_table.setItem(row, 2, QTableWidgetItem(material.get('unit', '')))
            self.materials_table.setItem(row, 3, QTableWidgetItem(material.get('quantity', '')))
            self.materials_table.setItem(row, 4, QTableWidgetItem(material.get('unit_price', '')))
            self.materials_table.setItem(row, 5, QTableWidgetItem(material.get('total', '')))

        # İşçilik tablosunu doldur
        labor = analysis_data.get('labor', [])
        self.labor_table.setRowCount(len(labor))
        for row, work in enumerate(labor):
            self.labor_table.setItem(row, 0, QTableWidgetItem(work.get('poz_no', '')))
            self.labor_table.setItem(row, 1, QTableWidgetItem(work.get('description', '')))
            self.labor_table.setItem(row, 2, QTableWidgetItem(work.get('unit', '')))
            self.labor_table.setItem(row, 3, QTableWidgetItem(work.get('quantity', '')))
            self.labor_table.setItem(row, 4, QTableWidgetItem(work.get('unit_price', '')))
            self.labor_table.setItem(row, 5, QTableWidgetItem(work.get('total', '')))

        # Toplamları hesapla
        self.calculate_totals()

    def add_material(self):
        """Yeni malzeme satırı ekle"""
        row = self.materials_table.rowCount()
        self.materials_table.insertRow(row)

        # Varsayılan değerler
        self.materials_table.setItem(row, 0, QTableWidgetItem(""))
        self.materials_table.setItem(row, 1, QTableWidgetItem(""))
        self.materials_table.setItem(row, 2, QTableWidgetItem("m²"))
        self.materials_table.setItem(row, 3, QTableWidgetItem("1,0"))
        self.materials_table.setItem(row, 4, QTableWidgetItem("0,00"))
        self.materials_table.setItem(row, 5, QTableWidgetItem("0,00"))

    def remove_material(self):
        """Seçili malzeme satırını sil"""
        current_row = self.materials_table.currentRow()
        if current_row >= 0:
            self.materials_table.removeRow(current_row)
            self.calculate_totals()

    def add_labor(self):
        """Yeni işçilik satırı ekle"""
        row = self.labor_table.rowCount()
        self.labor_table.insertRow(row)

        # Varsayılan değerler
        self.labor_table.setItem(row, 0, QTableWidgetItem(""))
        self.labor_table.setItem(row, 1, QTableWidgetItem(""))
        self.labor_table.setItem(row, 2, QTableWidgetItem("Sa"))
        self.labor_table.setItem(row, 3, QTableWidgetItem("0,1"))
        self.labor_table.setItem(row, 4, QTableWidgetItem("0,00"))
        self.labor_table.setItem(row, 5, QTableWidgetItem("0,00"))

    def remove_labor(self):
        """Seçili işçilik satırını sil"""
        current_row = self.labor_table.currentRow()
        if current_row >= 0:
            self.labor_table.removeRow(current_row)
            self.calculate_totals()

    def calculate_totals(self):
        """Toplamları hesapla"""
        try:
            # Malzeme toplamı
            material_total = 0
            for row in range(self.materials_table.rowCount()):
                total_item = self.materials_table.item(row, 5)
                if total_item:
                    value = total_item.text().replace(',', '.').replace(' TL', '')
                    try:
                        material_total += float(value)
                    except:
                        pass

            # İşçilik toplamı
            labor_total = 0
            for row in range(self.labor_table.rowCount()):
                total_item = self.labor_table.item(row, 5)
                if total_item:
                    value = total_item.text().replace(',', '.').replace(' TL', '')
                    try:
                        labor_total += float(value)
                    except:
                        pass

            # Toplam
            subtotal = material_total + labor_total
            overhead = subtotal * 0.25  # %25 yüklenici kârı
            total_with_overhead = subtotal + overhead

            # Türkçe sayı formatı: 1.234,56
            def format_turkish(value):
                formatted = f"{value:,.2f}"  # US: 1,234.56
                # US formatını Türkçeye çevir
                return formatted.replace(',', '@').replace('.', ',').replace('@', '.')  # TR: 1.234,56

            # Güncelle
            self.subtotal_label.setText(f"Malzeme + İşçilik Tutarı: {format_turkish(subtotal)} TL")
            self.overhead_label.setText(f"25% Yüklenici Kârı: {format_turkish(overhead)} TL")
            self.unit_price_label.setText(f"Toplam Tutarı: {format_turkish(total_with_overhead)} TL")

        except Exception as e:
            print(f"Hesaplama hatası: {e}")

    def save_analysis(self):
        """Analizi kaydet"""
        # TODO: Veritabanına kaydetme işlemi
        print("Analiz kaydedildi!")

    def export_analysis(self):
        """Analizi Excel'e aktar"""
        # TODO: Excel export işlemi
        print("Excel'e aktarılacak!")

    def clear_analysis(self):
        """Analizi temizle"""
        self.poz_no_label.setText("-")
        self.description_edit.clear()
        self.unit_combo.setCurrentIndex(0)
        self.materials_table.setRowCount(0)
        self.labor_table.setRowCount(0)
        self.subtotal_label.setText("0,00 TL")
        self.overhead_label.setText("0,00 TL")
        self.unit_price_label.setText("0,00 TL")
        self.current_analysis = None

    def load_csv_data(self):
        """CSV'den pozları ve rayiçleri yükle"""
        try:
            if not hasattr(self, 'parent_app') or not self.parent_app:
                return

            csv_manager = self.parent_app.csv_manager
            if not csv_manager or not csv_manager.poz_data:
                return

            # CSV tablosunu temizle
            self.csv_table.setRowCount(0)

            # CSV verilerini tabloya ekle
            row = 0
            for poz_no, data in csv_manager.poz_data.items():
                self.csv_table.insertRow(row)

                # Poz No
                poz_item = QTableWidgetItem(poz_no)
                self.csv_table.setItem(row, 0, poz_item)

                # Açıklama (kurumun adı)
                desc_item = QTableWidgetItem(data.get('institution', ''))
                self.csv_table.setItem(row, 1, desc_item)

                # Birim Fiyatı
                price_item = QTableWidgetItem(data.get('price', '0,00'))
                self.csv_table.setItem(row, 2, price_item)

                row += 1

            print(f"CSV'den {row} poz yüklendi")

        except Exception as e:
            print(f"CSV yükleme hatası: {e}")

    def on_csv_row_selected(self):
        """CSV tablosundan satır seçildiğinde"""
        try:
            selected_rows = self.csv_table.selectionModel().selectedRows()
            if not selected_rows:
                return

            # İlk seçili satırı al
            row = selected_rows[0].row()

            # Satırdan poz No'yu oku
            poz_item = self.csv_table.item(row, 0)
            if poz_item:
                poz_no = poz_item.text().strip()

                # Seçili pozun analiz bilgilerini al
                if hasattr(self, 'parent_app') and self.parent_app:
                    csv_manager = self.parent_app.csv_manager
                    if poz_no in csv_manager.poz_data:
                        data = csv_manager.poz_data[poz_no]

                        # Poz analiz bilgilerini yükle
                        self.poz_input.setText(poz_no)
                        self.description_edit.setText(data.get('institution', ''))
                        self.poz_no_label.setText(poz_no)

                        print(f"Poz '{poz_no}' seçildi")

                        # PozViewerWidget'ten alt pozları (malzeme/işçilik) yükle
                        self.load_sub_analyses_from_poz_viewer(poz_no)

        except Exception as e:
            print(f"Satır seçim hatası: {e}")

    def load_sub_analyses_from_poz_viewer(self, poz_no):
        """PozViewerWidget'ten seçili pozun malzeme/işçilik verilerini yükle"""
        try:
            if not hasattr(self, 'parent_app') or not self.parent_app:
                return

            # PozViewerWidget'e erişim
            poz_viewer = self.parent_app.poz_viewer_tab
            if not poz_viewer or poz_no not in poz_viewer.poz_analyses:
                print(f"Poz '{poz_no}' PozViewerWidget'te bulunamadı")
                return

            # Poz verilerini al
            poz_data = poz_viewer.poz_analyses[poz_no]
            sub_analyses = poz_data.get('sub_analyses', [])

            # Malzeme ve işçilik verilerini ayır
            materials = []
            labor = []

            for analysis in sub_analyses:
                item = {
                    'poz_no': analysis.get('code', ''),
                    'description': analysis.get('name', ''),
                    'unit': analysis.get('unit', ''),
                    'quantity': analysis.get('quantity', '0'),
                    'unit_price': analysis.get('unit_price', '0'),
                    'total': analysis.get('total', '0')
                }

                # Malzeme veya işçilik kategorisine göre ayır
                if 'Malzeme' in analysis.get('type', ''):
                    materials.append(item)
                elif 'İşçilik' in analysis.get('type', '') or 'Isçilik' in analysis.get('type', '') or 'Iscilik' in analysis.get('type', ''):
                    labor.append(item)

            # Tablolara yükle
            self.load_materials_table(materials)
            self.load_labor_table(labor)

            # Toplam hesaplamalar
            self.calculate_totals()

            print(f"Poz '{poz_no}' için {len(materials)} malzeme, {len(labor)} işçilik yüklendi")

        except Exception as e:
            print(f"Alt pozları yükleme hatası: {e}")

    def load_materials_table(self, materials):
        """Malzeme tablosunu doldur"""
        self.materials_table.setRowCount(len(materials))
        for row, material in enumerate(materials):
            self.materials_table.setItem(row, 0, QTableWidgetItem(material.get('poz_no', '')))
            self.materials_table.setItem(row, 1, QTableWidgetItem(material.get('description', '')))
            self.materials_table.setItem(row, 2, QTableWidgetItem(material.get('unit', '')))
            self.materials_table.setItem(row, 3, QTableWidgetItem(material.get('quantity', '')))
            self.materials_table.setItem(row, 4, QTableWidgetItem(material.get('unit_price', '')))
            self.materials_table.setItem(row, 5, QTableWidgetItem(material.get('total', '')))

    def load_labor_table(self, labor):
        """İşçilik tablosunu doldur"""
        self.labor_table.setRowCount(len(labor))
        for row, work in enumerate(labor):
            self.labor_table.setItem(row, 0, QTableWidgetItem(work.get('poz_no', '')))
            self.labor_table.setItem(row, 1, QTableWidgetItem(work.get('description', '')))
            self.labor_table.setItem(row, 2, QTableWidgetItem(work.get('unit', '')))
            self.labor_table.setItem(row, 3, QTableWidgetItem(work.get('quantity', '')))
            self.labor_table.setItem(row, 4, QTableWidgetItem(work.get('unit_price', '')))
            self.labor_table.setItem(row, 5, QTableWidgetItem(work.get('total', '')))

    def extract_unit_prices(self):
        """Tablodaki pozlar için rayiç fiyatları çek"""
        if not hasattr(self, 'search_engine'):
            print("Search engine bulunamadı!")
            return

        search_engine = self.search_engine

        # Malzeme tablosundaki pozlar için fiyat çek
        for row in range(self.materials_table.rowCount()):
            poz_item = self.materials_table.item(row, 0)
            unit_price_item = self.materials_table.item(row, 4)

            if poz_item and poz_item.text().strip():
                poz_no = poz_item.text().strip()

                # Bu poz için rayiç fiyat ara
                unit_price = self.find_unit_price(search_engine, poz_no)

                if unit_price and unit_price_item:
                    unit_price_item.setText(unit_price)

                    # Miktar varsa toplam hesapla
                    quantity_item = self.materials_table.item(row, 3)
                    total_item = self.materials_table.item(row, 5)

                    if quantity_item and total_item:
                        try:
                            qty = float(quantity_item.text().replace(',', '.'))
                            price = float(unit_price.replace(',', '.'))
                            total = qty * price
                            total_item.setText(f"{total:,.2f}".replace('.', ','))
                        except:
                            pass

        # İşçilik tablosundaki pozlar için fiyat çek
        for row in range(self.labor_table.rowCount()):
            poz_item = self.labor_table.item(row, 0)
            unit_price_item = self.labor_table.item(row, 4)

            if poz_item and poz_item.text().strip():
                poz_no = poz_item.text().strip()

                # Bu poz için rayiç fiyat ara
                unit_price = self.find_unit_price(search_engine, poz_no)

                if unit_price and unit_price_item:
                    unit_price_item.setText(unit_price)

                    # Miktar varsa toplam hesapla
                    quantity_item = self.labor_table.item(row, 3)
                    total_item = self.labor_table.item(row, 5)

                    if quantity_item and total_item:
                        try:
                            qty = float(quantity_item.text().replace(',', '.'))
                            price = float(unit_price.replace(',', '.'))
                            total = qty * price
                            total_item.setText(f"{total:,.2f}".replace('.', ','))
                        except:
                            pass

        # Toplamları yeniden hesapla
        self.calculate_totals()

        # Status mesajı
        if hasattr(self, 'parent_app'):
            self.parent_app.file_label.setText("Rayiç fiyatları güncellendi!")

    def find_unit_price(self, search_engine, poz_no):
        """Belirli bir poz için birim fiyat bul"""
        try:
            # PDF'lerde bu pozu ara
            for file_name, lines in search_engine.pdf_data.items():
                for line_data in lines:
                    text = line_data['text']

                    # Poz numarası ve fiyat içeren satırları ara
                    if (poz_no in text and '|' in text):
                        parts = [p.strip() for p in text.split('|')]

                        # Birim fiyat listesi formatı: Poz No | Açıklama | Birim Fiyat
                        if (len(parts) >= 3 and
                            parts[0] == poz_no and
                            re.search(r'\d+(?:[\.,]\d+)*(?:,\d{2})?', parts[-1])):

                            # Son sütundan fiyatı çıkar
                            price_text = parts[-1]
                            price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', price_text)

                            if price_match:
                                return price_match.group(1)

            return None

        except Exception as e:
            print(f"Fiyat arama hatası: {e}")
            return None

    def extract_analysis_from_input(self):
        """Girilen poz numarasından analiz çek"""
        poz_no = self.poz_input.text().strip()

        if not poz_no:
            # Ana uygulamanın file_label'ını güncelle
            if hasattr(self, 'parent_app'):
                self.parent_app.file_label.setText("Poz numarası girin!")
            return

        if not hasattr(self, 'search_engine') or not self.search_engine.loaded_files:
            if hasattr(self, 'parent_app'):
                self.parent_app.file_label.setText("Önce PDF dosyası yükleyin!")
            return

        try:
            # Loading göster
            if hasattr(self, 'parent_app'):
                self.parent_app.show_loading("Analiz çekiliyor...")

            # Debug: PDF verilerini kontrol et
            print(f"PDF dosyaları: {self.search_engine.loaded_files}")
            print(f"PDF veri sayısı: {len(self.search_engine.pdf_data)}")

            # Analiz verilerini çıkar
            analysis_data = self.search_engine.extract_poz_analysis(poz_no)

            if hasattr(self, 'parent_app'):
                self.parent_app.hide_loading()

            # Debug: analiz sonuçlarını kontrol et
            print(f"Analiz verisi - Malzeme: {len(analysis_data.get('materials', []))}")
            print(f"Analiz verisi - İşçilik: {len(analysis_data.get('labor', []))}")
            print(f"Analiz verisi - Açıklama: {analysis_data.get('description', '')}")

            if analysis_data['materials'] or analysis_data['labor'] or analysis_data.get('description'):
                # Analiz verilerini yükle
                self.load_analysis(analysis_data)
                if hasattr(self, 'parent_app'):
                    materials_count = len(analysis_data.get('materials', []))
                    labor_count = len(analysis_data.get('labor', []))
                    self.parent_app.file_label.setText(f"Poz '{poz_no}' analizi yüklendi! ({materials_count} malzeme, {labor_count} işçilik)")
            else:
                if hasattr(self, 'parent_app'):
                    self.parent_app.file_label.setText(f"Poz '{poz_no}' için analiz bulunamadı!")

        except Exception as e:
            print(f"Analiz çekme hatası detayı: {str(e)}")
            import traceback
            traceback.print_exc()
            if hasattr(self, 'parent_app'):
                self.parent_app.hide_loading()
                self.parent_app.file_label.setText(f"Analiz çekme hatası: {str(e)}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setMinimumSize(900, 480)
        from database import DatabaseManager
        self.db = DatabaseManager()
        self.base_dir = Path(__file__).resolve().parent
        self.pdf_folder = self.base_dir / "PDF"
        self.analiz_folder = self.base_dir / "ANALIZ"

        # Klasörlerin var olduğundan emin ol
        self.pdf_folder.mkdir(exist_ok=True)
        self.analiz_folder.mkdir(exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Tab Widget
        self.tabs = QTabWidget()

        # --- Tab 1: API Ayarları ---
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        form = QFormLayout()

        # Default Provider Selection
        self.provider_input = QComboBox()
        self.provider_input.addItems(["OpenRouter", "Google Gemini"])
        current_provider = self.db.get_setting("ai_provider")
        if current_provider:
            self.provider_input.setCurrentText(current_provider)
        form.addRow("Varsayılan AI Sağlayıcı:", self.provider_input)

        # API Key
        self.api_key_input = QLineEdit()
        current_key = self.db.get_setting("openrouter_api_key")
        if current_key:
            self.api_key_input.setText(current_key)
        self.api_key_input.setPlaceholderText("sk-or-...")
        form.addRow("OpenRouter API Key:", self.api_key_input)

        # Model Selector with Refresh Button
        model_layout = QHBoxLayout()
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.setMinimumWidth(350)

        # Önbellekten modelleri yükle veya varsayılanları kullan
        cached_models = self.db.get_setting("openrouter_models_cache")
        if cached_models:
            try:
                models = json.loads(cached_models)
            except:
                models = self._get_default_openrouter_models()
        else:
            models = self._get_default_openrouter_models()

        self.model_input.addItems(models)
        current_model = self.db.get_setting("openrouter_model")
        if current_model:
            self.model_input.setCurrentText(current_model)
        else:
            self.model_input.setCurrentText(models[0] if models else "")
        model_layout.addWidget(self.model_input)

        # Model güncelleme butonu
        self.refresh_or_models_btn = QPushButton("🔄")
        self.refresh_or_models_btn.setToolTip("OpenRouter'dan model listesini güncelle")
        self.refresh_or_models_btn.setFixedWidth(35)
        self.refresh_or_models_btn.clicked.connect(self.fetch_openrouter_models)
        model_layout.addWidget(self.refresh_or_models_btn)

        form.addRow("OpenRouter Model:", model_layout)

        # Base URL (Advanced)
        self.base_url_input = QLineEdit()
        current_url = self.db.get_setting("openrouter_base_url")
        self.base_url_input.setText(current_url if current_url else "https://openrouter.ai/api/v1")
        form.addRow("OpenRouter Base URL:", self.base_url_input)

        # --- Google Gemini Settings ---
        form.addRow(QLabel("<b>Google Gemini Ayarları</b>"))
        
        self.gemini_key_input = QLineEdit()
        gemini_key = self.db.get_setting("gemini_api_key")
        if gemini_key:
            self.gemini_key_input.setText(gemini_key)
        self.gemini_key_input.setPlaceholderText("AIzaSy...")
        form.addRow("Google API Key:", self.gemini_key_input)
        
        # Gemini Model Selector with Refresh Button
        gemini_model_layout = QHBoxLayout()
        self.gemini_model_input = QComboBox()
        self.gemini_model_input.setEditable(True)
        self.gemini_model_input.setMinimumWidth(350)

        # Önbellekten modelleri yükle veya varsayılanları kullan
        cached_gemini_models = self.db.get_setting("gemini_models_cache")
        if cached_gemini_models:
            try:
                gemini_models = json.loads(cached_gemini_models)
            except:
                gemini_models = self._get_default_gemini_models()
        else:
            gemini_models = self._get_default_gemini_models()

        self.gemini_model_input.addItems(gemini_models)
        current_gemini_model = self.db.get_setting("gemini_model")
        if current_gemini_model:
            self.gemini_model_input.setCurrentText(current_gemini_model)
        else:
            self.gemini_model_input.setCurrentText(gemini_models[0] if gemini_models else "")
        gemini_model_layout.addWidget(self.gemini_model_input)

        # Gemini model güncelleme butonu
        self.refresh_gemini_models_btn = QPushButton("🔄")
        self.refresh_gemini_models_btn.setToolTip("Google'dan model listesini güncelle")
        self.refresh_gemini_models_btn.setFixedWidth(35)
        self.refresh_gemini_models_btn.clicked.connect(self.fetch_gemini_models)
        gemini_model_layout.addWidget(self.refresh_gemini_models_btn)

        form.addRow("Google Model:", gemini_model_layout)

        api_layout.addLayout(form)

        info_label = QLabel("Yapay zeka analizleri için seçilen sağlayıcı kullanılır. Hata durumunda diğerine geçiş yapılır.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 9pt; margin: 10px 0;")
        api_layout.addWidget(info_label)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        
        test_or_btn = QPushButton("🔌 OpenRouter Test Et")
        test_or_btn.clicked.connect(self.test_connection)
        btn_layout.addWidget(test_or_btn)
        
        test_gemini_btn = QPushButton("🔌 Gemini Test Et")
        test_gemini_btn.clicked.connect(self.test_gemini_connection)
        btn_layout.addWidget(test_gemini_btn)
        
        api_layout.addLayout(btn_layout)

        api_layout.addStretch()
        self.tabs.addTab(api_tab, "🤖 API Ayarları")

        # --- Tab 2: Veri Kaynakları ---
        sources_tab = QWidget()
        sources_layout = QVBoxLayout(sources_tab)

        # Üst bilgi
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #E3F2FD; border-radius: 5px; padding: 10px;")
        info_frame_layout = QVBoxLayout(info_frame)
        info_title = QLabel("📁 PDF ve Analiz Dosyaları Yönetimi")
        info_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #1565C0;")
        info_frame_layout.addWidget(info_title)

        # Klasör yollarını göster
        paths_label = QLabel(f"PDF Klasörü: {self.pdf_folder}\nAnaliz Klasörü: {self.analiz_folder}")
        paths_label.setStyleSheet("color: #546E7A; font-size: 8pt; font-family: monospace;")
        info_frame_layout.addWidget(paths_label)
        sources_layout.addWidget(info_frame)

        # Dosya ekleme bölümü
        add_frame = QFrame()
        add_frame.setStyleSheet("background-color: #F5F5F5; border-radius: 5px; padding: 8px; margin: 5px 0;")
        add_layout = QHBoxLayout(add_frame)

        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["PDF (Birim Fiyat)", "ANALIZ (Poz Analizi)"])
        self.source_type_combo.setMinimumWidth(160)
        self.source_type_combo.currentIndexChanged.connect(self.load_folder_files)
        add_layout.addWidget(QLabel("Klasör:"))
        add_layout.addWidget(self.source_type_combo)

        add_layout.addStretch()

        add_file_btn = QPushButton("📄 Dosya Ekle")
        add_file_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 12px;")
        add_file_btn.clicked.connect(self.add_file_to_folder)
        add_layout.addWidget(add_file_btn)

        open_folder_btn = QPushButton("📂 Klasörü Aç")
        open_folder_btn.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 6px 12px;")
        open_folder_btn.clicked.connect(self.open_current_folder)
        add_layout.addWidget(open_folder_btn)

        sources_layout.addWidget(add_frame)

        # Dosyalar tablosu
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(['Dosya Adı', 'Boyut', 'Değiştirilme Tarihi', 'Durum'])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: bold;
            }
        """)
        sources_layout.addWidget(self.files_table)

        # Dosya sayısı etiketi
        self.file_count_label = QLabel("0 dosya")
        self.file_count_label.setStyleSheet("color: #666; font-size: 9pt;")
        sources_layout.addWidget(self.file_count_label)

        # Alt butonlar
        bottom_btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        refresh_btn.clicked.connect(self.load_folder_files)
        bottom_btn_layout.addWidget(refresh_btn)

        bottom_btn_layout.addStretch()

        delete_btn = QPushButton("🗑️ Seçili Dosyayı Sil")
        delete_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 8px;")
        delete_btn.clicked.connect(self.delete_selected_file)
        bottom_btn_layout.addWidget(delete_btn)

        sources_layout.addLayout(bottom_btn_layout)

        self.tabs.addTab(sources_tab, "📂 Veri Kaynakları")

        # --- Tab 3: Uygulama Ayarları ---
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)

        # Başlangıç Ayarları Grubu
        startup_group = QGroupBox("🚀 Başlangıç Ayarları")
        startup_layout = QFormLayout()

        # Açılışta ne yapılacak
        self.startup_action_combo = QComboBox()
        self.startup_action_combo.addItems([
            "Son projeyi otomatik aç",
            "Yeni proje dialogu göster",
            "Boş başla (proje seçme)"
        ])
        current_startup = self.db.get_setting("startup_action") or "Son projeyi otomatik aç"
        self.startup_action_combo.setCurrentText(current_startup)
        startup_layout.addRow("Uygulama açıldığında:", self.startup_action_combo)

        # Son projeyi hatırla
        self.remember_project_check = QCheckBox("Kapanırken aktif projeyi hatırla")
        remember_project = self.db.get_setting("remember_last_project")
        self.remember_project_check.setChecked(remember_project != "false")
        startup_layout.addRow("", self.remember_project_check)

        startup_group.setLayout(startup_layout)
        app_layout.addWidget(startup_group)

        # Görünüm Ayarları Grubu
        appearance_group = QGroupBox("🎨 Görünüm Ayarları")
        appearance_layout = QFormLayout()

        # Status bar'da proje bilgisi göster
        self.show_project_statusbar_check = QCheckBox("Status bar'da aktif proje bilgisini göster")
        show_project = self.db.get_setting("show_project_in_statusbar")
        self.show_project_statusbar_check.setChecked(show_project != "false")
        appearance_layout.addRow("", self.show_project_statusbar_check)

        # Pencere boyutunu hatırla
        self.remember_window_size_check = QCheckBox("Pencere boyutunu ve konumunu hatırla")
        remember_size = self.db.get_setting("remember_window_geometry")
        self.remember_window_size_check.setChecked(remember_size == "true")
        appearance_layout.addRow("", self.remember_window_size_check)

        appearance_group.setLayout(appearance_layout)
        app_layout.addWidget(appearance_group)

        # Onay Ayarları Grubu
        confirm_group = QGroupBox("⚠️ Onay Ayarları")
        confirm_layout = QFormLayout()

        # Kapatırken onay sor
        self.confirm_exit_check = QCheckBox("Uygulamayı kapatırken onay iste")
        confirm_exit = self.db.get_setting("confirm_on_exit")
        self.confirm_exit_check.setChecked(confirm_exit == "true")
        confirm_layout.addRow("", self.confirm_exit_check)

        # Proje silmeden önce onay
        self.confirm_delete_check = QCheckBox("Proje/veri silmeden önce onay iste")
        confirm_delete = self.db.get_setting("confirm_on_delete")
        self.confirm_delete_check.setChecked(confirm_delete != "false")
        confirm_layout.addRow("", self.confirm_delete_check)

        confirm_group.setLayout(confirm_layout)
        app_layout.addWidget(confirm_group)

        app_layout.addStretch()
        self.tabs.addTab(app_tab, "⚙️ Uygulama Ayarları")

        # --- Tab 4: Nakliye Ayarları (KGM 2025) ---
        nakliye_tab = QWidget()
        nakliye_layout = QVBoxLayout(nakliye_tab)

        # Bilgi başlığı
        nakliye_info = QFrame()
        nakliye_info.setStyleSheet("background-color: #E3F2FD; border-radius: 5px; padding: 10px;")
        nakliye_info_layout = QVBoxLayout(nakliye_info)
        nakliye_title = QLabel("🚛 KGM 2025 Nakliye Hesabı Parametreleri")
        nakliye_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #1565C0;")
        nakliye_info_layout.addWidget(nakliye_title)
        nakliye_desc = QLabel("Bu parametreler, AI analiz oluştururken nakliye hesabında kullanılır.\nKarayolları Genel Müdürlüğü 2025 Birim Fiyat formülleri esas alınmıştır.")
        nakliye_desc.setStyleSheet("color: #546E7A; font-size: 9pt;")
        nakliye_desc.setWordWrap(True)
        nakliye_info_layout.addWidget(nakliye_desc)
        nakliye_layout.addWidget(nakliye_info)

        # Nakliye Modu Seçimi
        mode_group = QGroupBox("📋 Nakliye Hesaplama Modu")
        mode_layout = QVBoxLayout()

        self.nakliye_mode_combo = QComboBox()
        self.nakliye_mode_combo.addItems([
            "AI'ya Bırak (Varsayılan değerler kullanılır)",
            "Manuel Değerler Kullan (Aşağıdaki ayarları kullan)"
        ])
        current_mode = self.db.get_setting("nakliye_mode") or "AI'ya Bırak (Varsayılan değerler kullanılır)"
        self.nakliye_mode_combo.setCurrentText(current_mode)
        self.nakliye_mode_combo.currentIndexChanged.connect(self.toggle_nakliye_fields)
        mode_layout.addWidget(self.nakliye_mode_combo)

        mode_group.setLayout(mode_layout)
        nakliye_layout.addWidget(mode_group)

        # Temel Parametreler
        params_group = QGroupBox("📐 Temel Parametreler")
        params_form = QFormLayout()

        # Ortalama Taşıma Mesafesi (M)
        self.nakliye_mesafe_input = QSpinBox()
        self.nakliye_mesafe_input.setRange(1, 100000)
        self.nakliye_mesafe_input.setSuffix(" m")
        self.nakliye_mesafe_input.setValue(int(self.db.get_setting("nakliye_mesafe") or 20000))
        params_form.addRow("Ortalama Taşıma Mesafesi (M):", self.nakliye_mesafe_input)

        # Taşıma Katsayısı (K) - Motorlu araç poz 10.110.1003 (eski: 02.017)
        k_layout = QHBoxLayout()
        self.nakliye_k_input = QLineEdit()
        self.nakliye_k_input.setPlaceholderText("Örn: 1750,00")
        saved_k = self.db.get_setting("nakliye_k") or "1,00"
        self.nakliye_k_input.setText(str(saved_k))
        self.nakliye_k_input.setFixedWidth(120)
        k_layout.addWidget(self.nakliye_k_input)

        # PDF'den K değerini çekme butonu
        self.fetch_k_btn = QPushButton("📥 PDF'den Çek")
        self.fetch_k_btn.setToolTip("Poz No: 10.110.1003 (Eski: 02.017)\nHer cins ve tonajda motorlu araç taşıma katsayısı K")
        self.fetch_k_btn.clicked.connect(self.fetch_k_from_pdf)
        self.fetch_k_btn.setFixedWidth(110)
        k_layout.addWidget(self.fetch_k_btn)

        k_widget = QWidget()
        k_widget.setLayout(k_layout)
        params_form.addRow("Taşıma Katsayısı (K):", k_widget)

        # A Katsayısı (Taşıma Şartları)
        self.nakliye_a_input = QDoubleSpinBox()
        self.nakliye_a_input.setRange(0.1, 5.0)
        self.nakliye_a_input.setDecimals(2)
        self.nakliye_a_input.setValue(float(self.db.get_setting("nakliye_a") or 1.0))
        a_info = QLabel("(Zor şartlar: 1-3, Kolay şartlar: <1)")
        a_info.setStyleSheet("color: #666; font-size: 8pt;")
        params_form.addRow("A Katsayısı (Taşıma Şartları):", self.nakliye_a_input)
        params_form.addRow("", a_info)

        params_group.setLayout(params_form)
        nakliye_layout.addWidget(params_group)

        # Malzeme Yoğunlukları
        yogunluk_group = QGroupBox("⚖️ Malzeme Yoğunlukları (Y) - ton/m³")
        yogunluk_form = QFormLayout()

        # Kum, çakıl, stabilize, kırmataş
        self.yogunluk_kum_input = QDoubleSpinBox()
        self.yogunluk_kum_input.setRange(0.5, 5.0)
        self.yogunluk_kum_input.setDecimals(2)
        self.yogunluk_kum_input.setSuffix(" ton/m³")
        self.yogunluk_kum_input.setValue(float(self.db.get_setting("yogunluk_kum") or 1.60))
        yogunluk_form.addRow("Kum, Çakıl, Stabilize, Kırmataş:", self.yogunluk_kum_input)

        # Anroşman, moloz taş
        self.yogunluk_moloz_input = QDoubleSpinBox()
        self.yogunluk_moloz_input.setRange(0.5, 5.0)
        self.yogunluk_moloz_input.setDecimals(2)
        self.yogunluk_moloz_input.setSuffix(" ton/m³")
        self.yogunluk_moloz_input.setValue(float(self.db.get_setting("yogunluk_moloz") or 1.80))
        yogunluk_form.addRow("Anroşman, Moloz Taş:", self.yogunluk_moloz_input)

        # Beton, prefabrik
        self.yogunluk_beton_input = QDoubleSpinBox()
        self.yogunluk_beton_input.setRange(0.5, 5.0)
        self.yogunluk_beton_input.setDecimals(2)
        self.yogunluk_beton_input.setSuffix(" ton/m³")
        self.yogunluk_beton_input.setValue(float(self.db.get_setting("yogunluk_beton") or 2.40))
        yogunluk_form.addRow("Beton, Prefabrik Beton:", self.yogunluk_beton_input)

        # Çimento
        self.yogunluk_cimento_input = QDoubleSpinBox()
        self.yogunluk_cimento_input.setRange(0.5, 5.0)
        self.yogunluk_cimento_input.setDecimals(2)
        self.yogunluk_cimento_input.setSuffix(" ton/m³")
        self.yogunluk_cimento_input.setValue(float(self.db.get_setting("yogunluk_cimento") or 1.50))
        yogunluk_form.addRow("Çimento:", self.yogunluk_cimento_input)

        # Demir
        self.yogunluk_demir_input = QDoubleSpinBox()
        self.yogunluk_demir_input.setRange(0.5, 10.0)
        self.yogunluk_demir_input.setDecimals(2)
        self.yogunluk_demir_input.setSuffix(" ton/m³")
        self.yogunluk_demir_input.setValue(float(self.db.get_setting("yogunluk_demir") or 7.85))
        yogunluk_form.addRow("Betonarme Demiri:", self.yogunluk_demir_input)

        yogunluk_group.setLayout(yogunluk_form)
        nakliye_layout.addWidget(yogunluk_group)

        # KGM Formül Bilgisi
        formula_group = QGroupBox("📖 KGM Nakliye Formülleri (Bilgi)")
        formula_layout = QVBoxLayout()

        formula_text = QLabel("""
<b>07.005/K - 10.000 m'ye kadar:</b><br>
<code>F = 1,25 × 0,00017 × K × M × Y × A</code> (m³ için)<br>
<code>F = 1,25 × 0,00017 × K × M × A</code> (ton için)<br><br>

<b>07.006/K - 10.000 m'den fazla:</b><br>
<code>F = 1,25 × K × (0,0007 × M + 0,01) × Y × A</code> (m³ için)<br>
<code>F = 1,25 × K × (0,0007 × M + 0,01) × A</code> (ton için)
        """)
        formula_text.setStyleSheet("background-color: #FFF8E1; padding: 10px; border-radius: 4px; font-size: 9pt;")
        formula_text.setWordWrap(True)
        formula_layout.addWidget(formula_text)

        formula_group.setLayout(formula_layout)
        nakliye_layout.addWidget(formula_group)

        nakliye_layout.addStretch()
        self.tabs.addTab(nakliye_tab, "🚛 Nakliye Ayarları")

        # Toggle fields based on mode
        self.toggle_nakliye_fields()

        # ===== TAB 5: AI PROMPTLARI =====
        prompt_tab = QWidget()
        prompt_layout = QVBoxLayout()

        prompt_info = QLabel("⚠️ AI promptlarını özelleştirin. Varsayılan değerlere dönmek için 'Varsayılana Sıfırla' butonunu kullanın.")
        prompt_info.setStyleSheet("color: #1565C0; background-color: #E3F2FD; padding: 8px; border-radius: 4px;")
        prompt_info.setWordWrap(True)
        prompt_layout.addWidget(prompt_info)

        # Prompt seçimi
        prompt_select_layout = QHBoxLayout()
        prompt_select_layout.addWidget(QLabel("Prompt Türü:"))
        self.prompt_type_combo = QComboBox()
        self.prompt_type_combo.addItems(["📊 Analiz Promptu (Poz Analizi)", "📐 Metraj Promptu (Metraj Hesabı)"])
        self.prompt_type_combo.currentIndexChanged.connect(self.on_prompt_type_changed)
        prompt_select_layout.addWidget(self.prompt_type_combo)
        prompt_select_layout.addStretch()
        prompt_layout.addLayout(prompt_select_layout)

        # Prompt düzenleme alanı
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("AI promptu buraya yazılacak...")
        self.prompt_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 10pt;")
        self.prompt_edit.setMinimumHeight(250)
        prompt_layout.addWidget(self.prompt_edit)

        # Değişken bilgisi
        var_info = QLabel("""
<b>Kullanılabilir Değişkenler:</b><br>
<code>{description}</code> - Poz/imalat tanımı | <code>{unit}</code> - Birim | <code>{context_data}</code> - Bağlam verisi<br>
<code>{nakliye_mesafe}</code> - Mesafe (m) | <code>{nakliye_k}</code> - K katsayısı | <code>{nakliye_a}</code> - A katsayısı<br>
<code>{yogunluk_kum}</code>, <code>{yogunluk_moloz}</code>, <code>{yogunluk_beton}</code>, <code>{yogunluk_cimento}</code>, <code>{yogunluk_demir}</code> - Yoğunluklar<br>
<code>{nakliye_km}</code> - Mesafe (km) | <code>{text}</code> - Metraj girdi metni
        """)
        var_info.setStyleSheet("background-color: #FFF8E1; padding: 8px; border-radius: 4px; font-size: 9pt;")
        var_info.setWordWrap(True)
        prompt_layout.addWidget(var_info)

        # Butonlar
        prompt_btn_layout = QHBoxLayout()

        reset_prompt_btn = QPushButton("🔄 Varsayılana Sıfırla")
        reset_prompt_btn.clicked.connect(self.reset_current_prompt)
        prompt_btn_layout.addWidget(reset_prompt_btn)

        reset_all_prompts_btn = QPushButton("🔄 Tüm Promptları Sıfırla")
        reset_all_prompts_btn.clicked.connect(self.reset_all_prompts)
        prompt_btn_layout.addWidget(reset_all_prompts_btn)

        prompt_btn_layout.addStretch()
        prompt_layout.addLayout(prompt_btn_layout)

        prompt_tab.setLayout(prompt_layout)
        self.tabs.addTab(prompt_tab, "📝 AI Promptları")

        # İlk prompt'u yükle
        self.load_current_prompt()

        # ===== TAB 6: İMZA SAHİPLERİ =====
        signatory_tab = QWidget()
        signatory_layout = QVBoxLayout()

        sig_info = QLabel("PDF raporlarında görünecek imza sahiplerinin bilgilerini girin.\n"
                          "Bu bilgiler Keşif Özeti, Analiz vb. PDF çıktılarında otomatik olarak kullanılacaktır.")
        sig_info.setWordWrap(True)
        sig_info.setStyleSheet("color: #666; padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        signatory_layout.addWidget(sig_info)

        signatory_layout.addWidget(QLabel(""))  # Spacer

        # İmza sahipleri form alanları
        self.signatory_inputs = {}

        # İşin Adı
        signatory_layout.addWidget(QLabel("<b>🏗️ İşin Adı</b>"))
        self.signatory_inputs['work_name'] = QLineEdit()
        self.signatory_inputs['work_name'].setPlaceholderText("Örn: Okul İnşaatı Yapım İşi")
        signatory_layout.addWidget(self.signatory_inputs['work_name'])
        signatory_layout.addWidget(QLabel(""))  # Spacer

        # Hazırlayan
        signatory_layout.addWidget(QLabel("<b>📋 Hazırlayan</b>"))
        hazirlayan_form = QFormLayout()
        self.signatory_inputs['hazirlayan_title'] = QLineEdit()
        self.signatory_inputs['hazirlayan_title'].setPlaceholderText("Örn: İnş. Müh.")
        hazirlayan_form.addRow("Unvan:", self.signatory_inputs['hazirlayan_title'])
        self.signatory_inputs['hazirlayan_name'] = QLineEdit()
        self.signatory_inputs['hazirlayan_name'].setPlaceholderText("Örn: Ahmet YILMAZ")
        hazirlayan_form.addRow("Ad Soyad:", self.signatory_inputs['hazirlayan_name'])
        self.signatory_inputs['hazirlayan_position'] = QLineEdit()
        self.signatory_inputs['hazirlayan_position'].setPlaceholderText("Örn: Proje Mühendisi")
        hazirlayan_form.addRow("Görev:", self.signatory_inputs['hazirlayan_position'])
        self.signatory_inputs['hazirlayan_date'] = QLineEdit()
        self.signatory_inputs['hazirlayan_date'].setPlaceholderText("Tarih")
        hazirlayan_form.addRow("Tarih:", self.signatory_inputs['hazirlayan_date'])
        signatory_layout.addLayout(hazirlayan_form)

        signatory_layout.addWidget(QLabel(""))  # Spacer

        # Kontrol Edenler (3 adet)
        signatory_layout.addWidget(QLabel("<b>🔍 Kontrol Edenler</b>"))

        kontrol_grid = QGridLayout()
        for i in range(1, 4):
            kontrol_grid.addWidget(QLabel(f"<b>{i}. Kontrol</b>"), 0, i-1)

            self.signatory_inputs[f'kontrol{i}_title'] = QLineEdit()
            self.signatory_inputs[f'kontrol{i}_title'].setPlaceholderText("Unvan")
            kontrol_grid.addWidget(self.signatory_inputs[f'kontrol{i}_title'], 1, i-1)

            self.signatory_inputs[f'kontrol{i}_name'] = QLineEdit()
            self.signatory_inputs[f'kontrol{i}_name'].setPlaceholderText("Ad Soyad")
            kontrol_grid.addWidget(self.signatory_inputs[f'kontrol{i}_name'], 2, i-1)

            self.signatory_inputs[f'kontrol{i}_position'] = QLineEdit()
            self.signatory_inputs[f'kontrol{i}_position'].setPlaceholderText("Görev")
            kontrol_grid.addWidget(self.signatory_inputs[f'kontrol{i}_position'], 3, i-1)

            self.signatory_inputs[f'kontrol{i}_date'] = QLineEdit()
            self.signatory_inputs[f'kontrol{i}_date'].setPlaceholderText("Tarih")
            kontrol_grid.addWidget(self.signatory_inputs[f'kontrol{i}_date'], 4, i-1)

        signatory_layout.addLayout(kontrol_grid)

        signatory_layout.addWidget(QLabel(""))  # Spacer

        # Onaylayan Amir
        signatory_layout.addWidget(QLabel("<b>✅ Onaylayan Amir</b>"))
        onaylayan_form = QFormLayout()
        self.signatory_inputs['onaylayan_title'] = QLineEdit()
        self.signatory_inputs['onaylayan_title'].setPlaceholderText("Örn: Y. İnş. Müh.")
        onaylayan_form.addRow("Unvan:", self.signatory_inputs['onaylayan_title'])
        self.signatory_inputs['onaylayan_name'] = QLineEdit()
        self.signatory_inputs['onaylayan_name'].setPlaceholderText("Örn: Mehmet DEMİR")
        onaylayan_form.addRow("Ad Soyad:", self.signatory_inputs['onaylayan_name'])
        self.signatory_inputs['onaylayan_position'] = QLineEdit()
        self.signatory_inputs['onaylayan_position'].setPlaceholderText("Örn: Şube Müdürü")
        onaylayan_form.addRow("Görev:", self.signatory_inputs['onaylayan_position'])
        self.signatory_inputs['onaylayan_date'] = QLineEdit()
        self.signatory_inputs['onaylayan_date'].setPlaceholderText("Tarih")
        onaylayan_form.addRow("Tarih:", self.signatory_inputs['onaylayan_date'])
        signatory_layout.addLayout(onaylayan_form)

        signatory_layout.addStretch()

        signatory_tab.setLayout(signatory_layout)
        self.tabs.addTab(signatory_tab, "✍️ İmza Sahipleri")

        # İmza sahiplerini yükle
        self.load_signatories()

        layout.addWidget(self.tabs)

        # Kaydet butonu (altta)
        save_btn = QPushButton("💾 Kaydet ve Kapat")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; font-size: 11pt;")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        self.setLayout(layout)

        # Dosyaları yükle
        self.load_folder_files()

    def get_current_folder(self):
        """Seçili klasörü döndür"""
        if self.source_type_combo.currentIndex() == 0:
            return self.pdf_folder
        else:
            return self.analiz_folder

    def load_folder_files(self):
        """Seçili klasördeki dosyaları tabloya yükle"""
        folder = self.get_current_folder()
        self.files_table.setRowCount(0)

        if not folder.exists():
            self.file_count_label.setText("Klasör bulunamadı")
            return

        pdf_files = sorted(folder.glob("*.pdf"), key=lambda x: x.name.lower())

        for i, pdf_file in enumerate(pdf_files):
            self.files_table.insertRow(i)

            # Dosya adı
            name_item = QTableWidgetItem(pdf_file.name)
            name_item.setData(Qt.UserRole, str(pdf_file))  # Tam yolu sakla
            self.files_table.setItem(i, 0, name_item)

            # Boyut
            size_bytes = pdf_file.stat().st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            self.files_table.setItem(i, 1, QTableWidgetItem(size_str))

            # Değiştirilme tarihi
            from datetime import datetime
            mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime)
            self.files_table.setItem(i, 2, QTableWidgetItem(mtime.strftime("%Y-%m-%d %H:%M")))

            # Durum
            status_item = QTableWidgetItem("✓ Mevcut")
            status_item.setBackground(QColor('#E8F5E9'))
            self.files_table.setItem(i, 3, status_item)

        self.file_count_label.setText(f"{len(pdf_files)} dosya")

    def add_file_to_folder(self):
        """Dosya seç ve ilgili klasöre kopyala"""
        import shutil

        folder = self.get_current_folder()
        folder_name = "PDF" if self.source_type_combo.currentIndex() == 0 else "ANALIZ"

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            f"{folder_name} Dosyası Seç",
            "",
            "PDF Dosyaları (*.pdf);;Tüm Dosyalar (*.*)"
        )

        if not file_paths:
            return

        added_count = 0
        skipped_count = 0

        for file_path in file_paths:
            source = Path(file_path)
            dest = folder / source.name

            if dest.exists():
                reply = QMessageBox.question(
                    self, "Dosya Mevcut",
                    f"'{source.name}' zaten mevcut.\nÜzerine yazmak istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )
                if reply == QMessageBox.Cancel:
                    break
                elif reply == QMessageBox.No:
                    skipped_count += 1
                    continue

            try:
                shutil.copy2(str(source), str(dest))
                added_count += 1
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Dosya kopyalanamadı: {source.name}\n{str(e)}")

        self.load_folder_files()

        if added_count > 0:
            QMessageBox.information(self, "Başarılı", f"{added_count} dosya {folder_name} klasörüne eklendi.")

    def delete_selected_file(self):
        """Seçili dosyayı sil"""
        current_row = self.files_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silinecek dosyayı seçin.")
            return

        file_path = self.files_table.item(current_row, 0).data(Qt.UserRole)
        file_name = self.files_table.item(current_row, 0).text()

        reply = QMessageBox.question(
            self, "Dosya Sil",
            f"'{file_name}' dosyasını kalıcı olarak silmek istiyor musunuz?\n\n⚠️ Bu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                Path(file_path).unlink()
                self.load_folder_files()
                QMessageBox.information(self, "Başarılı", f"'{file_name}' silindi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya silinemedi: {str(e)}")

    def open_current_folder(self):
        """Seçili klasörü dosya yöneticisinde aç"""
        import subprocess
        import platform

        folder = self.get_current_folder()

        try:
            if platform.system() == "Windows":
                subprocess.Popen(f'explorer "{folder}"')
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Klasör açılamadı: {str(e)}")

    def test_connection(self):
        """OpenRouter bağlantısını test et"""
        import requests
        key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model = self.model_input.currentText().strip()

        if not key:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce API anahtarı girin.")
            return

        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": "Test."}],
                "max_tokens": 5
            }

            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(self, "Başarılı", "✅ Bağlantı başarılı!")
            elif response.status_code == 429:
                QMessageBox.warning(self, "Rate Limit",
                    "⚠️ Çok fazla istek gönderildi (429)!\n\n"
                    "Olası nedenler:\n"
                    "• Kısa sürede çok fazla test yapıldı\n"
                    "• Ücretsiz API kullanım limitine ulaşıldı\n"
                    "• Model şu an yoğun\n\n"
                    "Birkaç dakika bekleyip tekrar deneyin.")
            elif response.status_code == 401:
                QMessageBox.critical(self, "Yetki Hatası",
                    "❌ API anahtarı geçersiz (401)!\n\n"
                    "Lütfen OpenRouter API anahtarınızı kontrol edin.")
            else:
                QMessageBox.critical(self, "Hata", f"❌ Bağlantı başarısız!\nKod: {response.status_code}\n{response.text[:200]}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"❌ Bağlantı hatası: {str(e)}")

    def test_gemini_connection(self):
        """Google Gemini bağlantısını test et"""
        import requests
        key = self.gemini_key_input.text().strip()
        model = self.gemini_model_input.currentText().strip()

        if not key:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce Google API anahtarı girin.")
            return

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            data = {
                "contents": [{"parts": [{"text": "Test."}]}]
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Başarılı", "✅ Google Gemini bağlantısı başarılı!")
            else:
                QMessageBox.critical(self, "Hata", f"❌ Bağlantı başarısız!\nKod: {response.status_code}\n{response.text}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"❌ Bağlantı hatası: {str(e)}")

    def _get_default_openrouter_models(self):
        """Varsayılan OpenRouter model listesi"""
        return [
            "google/gemini-2.0-flash-exp:free",
            "google/gemini-2.5-pro-exp-03-25:free",
            "mistralai/devstral-2512:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "meta-llama/llama-4-maverick:free",
            "qwen/qwen3-235b-a22b:free",
            "amazon/nova-2-lite-v1:free"
        ]

    def _get_default_gemini_models(self):
        """Varsayılan Gemini model listesi"""
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-pro"
        ]

    def fetch_openrouter_models(self):
        """OpenRouter API'den model listesini çek ve önbelleğe al"""
        import requests

        self.refresh_or_models_btn.setEnabled(False)
        self.refresh_or_models_btn.setText("⏳")
        QApplication.processEvents()

        try:
            # OpenRouter models endpoint
            url = "https://openrouter.ai/api/v1/models"
            headers = {"Content-Type": "application/json"}

            # API key varsa ekle (opsiyonel, bazı modeller için gerekli olabilir)
            api_key = self.api_key_input.text().strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                models_data = data.get('data', [])

                # Model ID'lerini al ve sırala
                model_ids = []
                for model in models_data:
                    model_id = model.get('id', '')
                    if model_id:
                        # Pricing bilgisini kontrol et - ücretsiz olanları öne al
                        pricing = model.get('pricing', {})
                        prompt_price = float(pricing.get('prompt', '1') or '1')
                        completion_price = float(pricing.get('completion', '1') or '1')

                        is_free = prompt_price == 0 and completion_price == 0
                        model_ids.append((model_id, is_free, model.get('name', model_id)))

                # Ücretsiz olanları öne al, sonra isme göre sırala
                model_ids.sort(key=lambda x: (not x[1], x[2].lower()))

                # Sadece model ID'lerini al
                final_models = [m[0] for m in model_ids]

                if final_models:
                    # Mevcut seçimi hatırla
                    current_selection = self.model_input.currentText()

                    # Combobox'ı güncelle
                    self.model_input.clear()
                    self.model_input.addItems(final_models)

                    # Eski seçimi geri yükle
                    if current_selection in final_models:
                        self.model_input.setCurrentText(current_selection)
                    else:
                        self.model_input.setCurrentIndex(0)

                    # Önbelleğe kaydet
                    self.db.set_setting("openrouter_models_cache", json.dumps(final_models))
                    self.db.set_setting("openrouter_models_cache_date", datetime.now().strftime("%Y-%m-%d %H:%M"))

                    QMessageBox.information(self, "Başarılı", f"✅ {len(final_models)} model yüklendi!\n(Ücretsiz modeller listenin başında)")
                else:
                    QMessageBox.warning(self, "Uyarı", "Model listesi boş döndü.")
            elif response.status_code == 429:
                QMessageBox.warning(self, "Rate Limit",
                    "⚠️ Çok fazla istek (429)!\n\n"
                    "Birkaç dakika bekleyip tekrar deneyin.\n"
                    "Mevcut önbellekteki modeller kullanılmaya devam edecek.")
            else:
                QMessageBox.critical(self, "Hata", f"❌ API Hatası: {response.status_code}\n{response.text[:200]}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"❌ Bağlantı hatası: {str(e)}")

        finally:
            self.refresh_or_models_btn.setEnabled(True)
            self.refresh_or_models_btn.setText("🔄")

    def fetch_gemini_models(self):
        """Google Gemini API'den model listesini çek ve önbelleğe al"""
        import requests

        api_key = self.gemini_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Uyarı", "Model listesini çekmek için önce Google API anahtarı girin.")
            return

        self.refresh_gemini_models_btn.setEnabled(False)
        self.refresh_gemini_models_btn.setText("⏳")
        QApplication.processEvents()

        try:
            # Gemini models endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                models_data = data.get('models', [])

                # generateContent destekleyen modelleri filtrele
                model_names = []
                for model in models_data:
                    model_name = model.get('name', '').replace('models/', '')
                    supported_methods = model.get('supportedGenerationMethods', [])

                    # generateContent desteği olan modelleri al
                    if 'generateContent' in supported_methods and model_name:
                        # gemini- ile başlayanları tercih et
                        if model_name.startswith('gemini'):
                            model_names.append(model_name)

                # Sırala (yeni modeller önce)
                model_names.sort(key=lambda x: (
                    '2.0' not in x,  # 2.0 modeller önce
                    '1.5' not in x,  # sonra 1.5
                    'flash' not in x,  # flash modeller önce
                    x
                ))

                if model_names:
                    # Mevcut seçimi hatırla
                    current_selection = self.gemini_model_input.currentText()

                    # Combobox'ı güncelle
                    self.gemini_model_input.clear()
                    self.gemini_model_input.addItems(model_names)

                    # Eski seçimi geri yükle
                    if current_selection in model_names:
                        self.gemini_model_input.setCurrentText(current_selection)
                    else:
                        self.gemini_model_input.setCurrentIndex(0)

                    # Önbelleğe kaydet
                    self.db.set_setting("gemini_models_cache", json.dumps(model_names))
                    self.db.set_setting("gemini_models_cache_date", datetime.now().strftime("%Y-%m-%d %H:%M"))

                    QMessageBox.information(self, "Başarılı", f"✅ {len(model_names)} model yüklendi!")
                else:
                    QMessageBox.warning(self, "Uyarı", "Uygun model bulunamadı.")
            else:
                QMessageBox.critical(self, "Hata", f"❌ API Hatası: {response.status_code}\n{response.text[:200]}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"❌ Bağlantı hatası: {str(e)}")

        finally:
            self.refresh_gemini_models_btn.setEnabled(True)
            self.refresh_gemini_models_btn.setText("🔄")

    def save_settings(self):
        key = self.api_key_input.text().strip()
        model = self.model_input.currentText().strip()
        base_url = self.base_url_input.text().strip()
        provider = self.provider_input.currentText().strip()

        self.db.set_setting("openrouter_api_key", key)
        self.db.set_setting("openrouter_model", model)
        self.db.set_setting("openrouter_base_url", base_url)
        self.db.set_setting("ai_provider", provider)

        # Save Gemini settings
        self.db.set_setting("gemini_api_key", self.gemini_key_input.text().strip())
        self.db.set_setting("gemini_model", self.gemini_model_input.currentText().strip())

        # Save App settings
        self.db.set_setting("startup_action", self.startup_action_combo.currentText())
        self.db.set_setting("remember_last_project", "true" if self.remember_project_check.isChecked() else "false")
        self.db.set_setting("show_project_in_statusbar", "true" if self.show_project_statusbar_check.isChecked() else "false")
        self.db.set_setting("remember_window_geometry", "true" if self.remember_window_size_check.isChecked() else "false")
        self.db.set_setting("confirm_on_exit", "true" if self.confirm_exit_check.isChecked() else "false")
        self.db.set_setting("confirm_on_delete", "true" if self.confirm_delete_check.isChecked() else "false")

        # Save Nakliye settings (KGM 2025)
        self.db.set_setting("nakliye_mode", self.nakliye_mode_combo.currentText())
        self.db.set_setting("nakliye_mesafe", str(self.nakliye_mesafe_input.value()))
        self.db.set_setting("nakliye_k", self.nakliye_k_input.text())
        self.db.set_setting("nakliye_a", str(self.nakliye_a_input.value()))
        self.db.set_setting("yogunluk_kum", str(self.yogunluk_kum_input.value()))
        self.db.set_setting("yogunluk_moloz", str(self.yogunluk_moloz_input.value()))
        self.db.set_setting("yogunluk_beton", str(self.yogunluk_beton_input.value()))
        self.db.set_setting("yogunluk_cimento", str(self.yogunluk_cimento_input.value()))
        self.db.set_setting("yogunluk_demir", str(self.yogunluk_demir_input.value()))

        # Save AI Prompts
        current_prompt = self.prompt_edit.toPlainText()
        prompt_type = self.prompt_type_combo.currentIndex()
        if prompt_type == 0:
            # Varsayılandan farklıysa kaydet
            if current_prompt != self.get_default_analysis_prompt():
                self.db.set_setting("custom_analysis_prompt", current_prompt)
            else:
                self.db.set_setting("custom_analysis_prompt", "")
        else:
            if current_prompt != self.get_default_metraj_prompt():
                self.db.set_setting("custom_metraj_prompt", current_prompt)
            else:
                self.db.set_setting("custom_metraj_prompt", "")

        # Save Signatories (İmza Sahipleri)
        self.save_signatories()

        QMessageBox.information(self, "Başarılı", "Ayarlar kaydedildi.")
        self.accept()

    def fetch_k_from_pdf(self):
        """CSV verilerinden K katsayısını çek (Poz No: 10.110.1003 veya 02.017)"""
        try:
            # Ana uygulama penceresinin csv_manager'ına eriş
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, PDFSearchAppPyQt5):
                    main_window = widget
                    break

            if not main_window or not main_window.csv_manager.poz_data:
                QMessageBox.warning(self, "Uyarı",
                    "CSV poz verileri yüklenmemiş!\n\n"
                    "Önce 'CSV Poz Seçimi' sekmesinden CSV verilerini yükleyin.")
                return

            # K katsayısını bul
            found_value, found_poz, found_desc = self.find_k_coefficient(main_window.csv_manager.poz_data)

            if found_value:
                # Türkçe formatla göster (1750.0 -> 1.750,00)
                formatted_value = f"{found_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                self.nakliye_k_input.setText(formatted_value)
                QMessageBox.information(self, "Başarılı",
                    f"K katsayısı CSV'den çekildi!\n\n"
                    f"Poz No: {found_poz}\n"
                    f"Açıklama: {found_desc[:60]}...\n"
                    f"K Değeri: {formatted_value}")
            else:
                QMessageBox.warning(self, "Bulunamadı",
                    "K katsayısı pozu bulunamadı!\n\n"
                    "Aranan Poz No: 10.110.1003 veya 02.017\n"
                    "(Her cins ve tonajda motorlu araç taşıma katsayısı K)\n\n"
                    "CSV verilerinde bu poz mevcut değil.")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"K katsayısı çekilirken hata oluştu:\n{str(e)}")

    def find_k_coefficient(self, poz_data):
        """Poz verilerinden K katsayısını bul ve döndür"""
        # Öncelikli arama: Tam poz numarası eşleşmesi
        priority_pozlar = ['10.110.1003', '02.017']

        for target_poz in priority_pozlar:
            if target_poz in poz_data:
                poz_info = poz_data[target_poz]
                unit_price = poz_info.get('unit_price', '')
                if unit_price:
                    value = self.parse_turkish_number(unit_price)
                    if value and value > 0:
                        return value, target_poz, poz_info.get('description', '')

        # İkincil arama: Poz numarasında içeren
        for poz_no, poz_info in poz_data.items():
            if any(term in poz_no for term in priority_pozlar):
                unit_price = poz_info.get('unit_price', '')
                if unit_price:
                    value = self.parse_turkish_number(unit_price)
                    if value and value > 0:
                        return value, poz_no, poz_info.get('description', '')

        # Üçüncül arama: Açıklamada "motorlu araç taşıma katsayısı" geçen
        for poz_no, poz_info in poz_data.items():
            desc = poz_info.get('description', '').lower()
            if 'motorlu araç' in desc and 'taşıma katsayısı' in desc:
                unit_price = poz_info.get('unit_price', '')
                if unit_price:
                    value = self.parse_turkish_number(unit_price)
                    if value and value > 0:
                        return value, poz_no, poz_info.get('description', '')

        return None, None, None

    def parse_turkish_number(self, value_str):
        """Türkçe sayı formatını parse et (1.750,00 -> 1750.00)"""
        try:
            if not value_str or str(value_str).lower() == 'nan':
                return None

            # String'e çevir ve temizle
            clean = str(value_str).strip().replace(' ', '').replace('TL', '')

            # Türkçe format: binlik ayraç nokta, ondalık virgül
            # Örnek: 1.750,00 -> 1750.00
            if ',' in clean:
                # Noktaları kaldır (binlik ayraç), virgülü noktaya çevir
                clean = clean.replace('.', '').replace(',', '.')

            return float(clean)
        except (ValueError, TypeError):
            return None

    def get_default_analysis_prompt(self):
        """Varsayılan analiz promptunu döndür"""
        return """Sen uzman bir Türk İnşaat Metraj ve Hakediş Mühendisisin.

Görev: Aşağıdaki poz tanımı için "Çevre ve Şehircilik Bakanlığı" birim fiyat analiz formatına uygun detaylı bir analiz oluştur.

Poz Tanımı: {description}
Poz Birimi: {unit}

EK BAĞLAM (MEVCUT KAYNAKLARDAN BULUNAN İLGİLİ POZLAR):
{context_data}

Kurallar:
1. Analiz şu bileşenleri içermelidir:
   - Malzeme (Örn: Çimento, Kum, Tuğla, vb.)
   - İşçilik (Örn: Usta, Düz işçi)
   - Makine (varsa - vinç, beton pompası, vb.)
   - Nakliye (ZORUNLU - malzeme nakliyesi mutlaka hesaplanmalı)

2. KGM 2025 NAKLİYE HESABI (Karayolları Genel Müdürlüğü Formülleri):
   KULLANILACAK PARAMETRELER:
   - Ortalama Taşıma Mesafesi (M): {nakliye_mesafe} metre ({nakliye_km:.1f} km)
   - Taşıma Katsayısı (K): {nakliye_k}
   - A Katsayısı (Taşıma Şartları): {nakliye_a}

   MALZEME YOĞUNLUKLARI (Y - ton/m³):
   - Kum, Çakıl, Stabilize, Kırmataş: {yogunluk_kum} ton/m³
   - Anroşman, Moloz Taş: {yogunluk_moloz} ton/m³
   - Beton, Prefabrik: {yogunluk_beton} ton/m³
   - Çimento: {yogunluk_cimento} ton/m³
   - Betonarme Demiri: {yogunluk_demir} ton/m³

   NAKLİYE FORMÜLÜ (07.005/K - 10.000 m'ye kadar):
   F = 1,25 × 0,00017 × K × M × Y × A  (m³ için)
   F = 1,25 × 0,00017 × K × M × A      (ton için)

   NAKLİYE FORMÜLÜ (07.006/K - 10.000 m'den fazla):
   F = 1,25 × K × (0,0007 × M + 0,01) × Y × A  (m³ için)
   F = 1,25 × K × (0,0007 × M + 0,01) × A      (ton için)

   ÖNEMLİ:
   - Her ağır malzeme (beton, çimento, demir, kum, çakıl) için nakliye kalemi AYRI SATIR olarak ekle
   - Nakliye birim fiyatını yukarıdaki formüle göre hesapla
   - Nakliye miktarı = Malzeme miktarı × Yoğunluk (ton cinsinden)
   - Nakliye tipi: "type": "Nakliye" olarak belirt
   - Nakliye kodu: "07.005/K" veya "07.006/K" kullan

3. Miktarlar gerçekçi inşaat normlarına (analiz kitaplarına) dayanmalıdır.
4. Birim fiyatlar 2024-2025 yılı ortalama piyasa rayiçleri (TL) olmalıdır.
5. Çıktı SADECE geçerli bir JSON formatında olmalı.
6. Lütfen JSON içindeki metin alanlarında çift tırnak (") kullanmaktan kaçının veya escape edin (\").

JSON Formatı Şablonu:
{{
  "explanation": "Bu analizi oluştururken ... mantığını kullandım. Nakliye hesabını KGM 2025 formülüne göre şu şekilde yaptım: F = 1,25 × K × 0,00017 × M × Y × A = ... TL/ton",
  "components": [
      {{ "type": "Malzeme", "code": "10.xxx", "name": "Malzeme Adı", "unit": "kg/m³/adet", "quantity": 0.0, "unit_price": 0.0 }},
      {{ "type": "İşçilik", "code": "01.xxx", "name": "İşçilik Adı", "unit": "sa", "quantity": 0.0, "unit_price": 0.0 }},
      {{ "type": "Makine", "code": "03.xxx", "name": "Makine Adı", "unit": "sa", "quantity": 0.0, "unit_price": 0.0 }},
      {{ "type": "Nakliye", "code": "07.005/K", "name": "Çimento Nakliyesi", "unit": "ton", "quantity": 0.0, "unit_price": 0.0 }},
      {{ "type": "Nakliye", "code": "07.005/K", "name": "Demir Nakliyesi", "unit": "ton", "quantity": 0.0, "unit_price": 0.0 }}
  ]
}}

Lütfen "explanation" kısmında neden bu malzemeleri ve miktarları seçtiğini, nakliye hesabını hangi formülle yaptığını detaylıca anlat."""

    def get_default_metraj_prompt(self):
        """Varsayılan metraj promptunu döndür"""
        return """Sen uzman bir inşaat metraj mühendisisin.
Görev: Verilen metinden TEK BİR İMALAT GRUBU oluştur ve bu gruba ait TÜM MALZEME METRAJLARINI (Beton, Kalıp, Demir, Kazı, Dolgu vb.) hesapla.

Metin: "{text}"

**ÖNEMLİ KURALLAR:**
1. SADECE TEK BİR GRUP oluştur (örn: "Betonarme U Kanal", "İstinat Duvarı" vb.)
2. Bu grubun altında TÜM malzeme metrajlarını ayrı satırlar olarak listele
3. Her malzeme için: Beton, Kalıp, Demir, Kazı, Dolgu, vb. ayrı satır olacak

**HESAPLAMA KURALLARI:**

**Betonarme U Kanal (iç_genişlik: b, iç_yükseklik: h, duvar_kalınlık: t, taban_kalınlık: t0, uzunluk: L):**
- Taban Betonu (m3): L × (b + 2×t) × t0
- Yan Duvar Betonu (m3): L × t × h × 2
- Toplam Beton (m3): Taban + Yan Duvarlar
- İç Kalıp (m2): L × (b + 2×h) (taban + 2 yan iç yüzey)
- Dış Kalıp (m2): L × 2 × h (2 yan dış yüzey)
- Demir (ton): Toplam Beton × 0.10 (100 kg/m3)
- Kazı (m3): L × (b + 2×t + 0.5) × (h + t0 + 0.3) (çalışma payı dahil)
- Geri Dolgu (m3): Kazı - Beton hacmi

**Betonarme İstinat Duvarı:**
- Gövde Betonu (m3): L × H × t
- Taban Betonu (m3): L × B × t0
- Kalıp (m2): 2 × L × H (ön + arka yüzey)
- Demir (ton): Toplam Beton × 0.10

**Taş Duvar:**
- Duvar Hacmi (m3): L × H × t
- Harpuşta (m3): L × genişlik × kalınlık

**ÇIKTI FORMATI (JSON):**
{{
  "explanation": "Hesaplama detayları ve varsayımlar. Örn: U Kanal için L=1m, iç genişlik=3m, iç yükseklik=2m, duvar kalınlığı=0.3m, taban kalınlığı=0.5m kabul edilmiştir. Taban betonu: 1×(3+0.6)×0.5=1.8m3...",
  "groups": [
      {{
        "group_name": "İmalat Adı (örn: Betonarme U Kanal)",
        "unit": "",
        "items": [
          {{"description": "Taban Betonu", "similar_count": 1, "length": 1.0, "width": 3.6, "height": 0.5, "quantity": 1.8, "unit": "m3", "notes": "L×(b+2t)×t0 = 1×3.6×0.5"}},
          {{"description": "Yan Duvar Betonu", "similar_count": 2, "length": 1.0, "width": 0.3, "height": 2.0, "quantity": 1.2, "unit": "m3", "notes": "L×t×h×2 = 1×0.3×2×2"}},
          {{"description": "İç Kalıp", "similar_count": 1, "length": 1.0, "width": 7.0, "height": 1.0, "quantity": 7.0, "unit": "m2", "notes": "L×(b+2h) = 1×(3+4)"}},
          {{"description": "Dış Kalıp", "similar_count": 2, "length": 1.0, "width": 2.0, "height": 1.0, "quantity": 4.0, "unit": "m2", "notes": "L×h×2 = 1×2×2"}},
          {{"description": "Betonarme Demiri", "similar_count": 1, "length": 1.0, "width": 1.0, "height": 1.0, "quantity": 0.30, "unit": "ton", "notes": "Toplam beton × 0.10"}},
          {{"description": "Kazı", "similar_count": 1, "length": 1.0, "width": 4.1, "height": 2.8, "quantity": 11.48, "unit": "m3", "notes": "Çalışma payı dahil"}},
          {{"description": "Geri Dolgu", "similar_count": 1, "length": 1.0, "width": 1.0, "height": 1.0, "quantity": 8.48, "unit": "m3", "notes": "Kazı - Beton"}}
        ]
      }}
  ]
}}

**DİKKAT:**
- SADECE 1 GRUP olacak, birden fazla grup OLUŞTURMA
- Her malzeme türü (beton, kalıp, demir, kazı, dolgu) ayrı bir satır/item olacak
- Hesaplamaları "notes" alanında göster
- "explanation" alanı ZORUNLU ve detaylı olmalı"""

    def on_prompt_type_changed(self):
        """Prompt türü değiştiğinde ilgili promptu yükle"""
        self.load_current_prompt()

    def load_current_prompt(self):
        """Seçili prompt türünü yükle"""
        prompt_type = self.prompt_type_combo.currentIndex()

        if prompt_type == 0:  # Analiz Promptu
            saved_prompt = self.db.get_setting("custom_analysis_prompt")
            if saved_prompt:
                self.prompt_edit.setPlainText(saved_prompt)
            else:
                self.prompt_edit.setPlainText(self.get_default_analysis_prompt())
        else:  # Metraj Promptu
            saved_prompt = self.db.get_setting("custom_metraj_prompt")
            if saved_prompt:
                self.prompt_edit.setPlainText(saved_prompt)
            else:
                self.prompt_edit.setPlainText(self.get_default_metraj_prompt())

    def reset_current_prompt(self):
        """Mevcut promptu varsayılana sıfırla"""
        prompt_type = self.prompt_type_combo.currentIndex()

        reply = QMessageBox.question(self, "Onay",
            "Bu promptu varsayılan değere sıfırlamak istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if prompt_type == 0:
                self.prompt_edit.setPlainText(self.get_default_analysis_prompt())
                self.db.set_setting("custom_analysis_prompt", "")
            else:
                self.prompt_edit.setPlainText(self.get_default_metraj_prompt())
                self.db.set_setting("custom_metraj_prompt", "")

            QMessageBox.information(self, "Başarılı", "Prompt varsayılan değere sıfırlandı.")

    def reset_all_prompts(self):
        """Tüm promptları varsayılana sıfırla"""
        reply = QMessageBox.question(self, "Onay",
            "TÜM AI promptlarını varsayılan değerlere sıfırlamak istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.db.set_setting("custom_analysis_prompt", "")
            self.db.set_setting("custom_metraj_prompt", "")
            self.load_current_prompt()
            QMessageBox.information(self, "Başarılı", "Tüm promptlar varsayılan değerlere sıfırlandı.")

    def load_signatories(self):
        """Veritabanından imza sahiplerini yükle"""
        signatories = self.db.get_signatories()

        for sig in signatories:
            role = sig['role']
            title = sig.get('title', '')
            full_name = sig.get('full_name', '')
            position = sig.get('position', '')

            # İlgili input alanlarına yükle
            if f'{role}_title' in self.signatory_inputs:
                self.signatory_inputs[f'{role}_title'].setText(title)
            if f'{role}_name' in self.signatory_inputs:
                self.signatory_inputs[f'{role}_name'].setText(full_name)
            if f'{role}_position' in self.signatory_inputs:
                self.signatory_inputs[f'{role}_position'].setText(position)
            if f'{role}_date' in self.signatory_inputs:
                self.signatory_inputs[f'{role}_date'].setText(sig.get('date_text', ''))

        # İşin adını yükle
        work_name = self.db.get_setting("work_name")
        if work_name and 'work_name' in self.signatory_inputs:
            self.signatory_inputs['work_name'].setText(work_name)

    def save_signatories(self):
        """İmza sahiplerini veritabanına kaydet"""
        roles = ['hazirlayan', 'kontrol1', 'kontrol2', 'kontrol3', 'onaylayan']

        for role in roles:
            title = self.signatory_inputs.get(f'{role}_title')
            name = self.signatory_inputs.get(f'{role}_name')
            position = self.signatory_inputs.get(f'{role}_position')
            date_input = self.signatory_inputs.get(f'{role}_date')

            if title and name and position:
                self.db.update_signatory(
                    role,
                    title.text().strip(),
                    name.text().strip(),
                    position.text().strip(),
                    date_input.text().strip() if date_input else ""
                )
        
        # İşin adını kaydet
        if 'work_name' in self.signatory_inputs:
            self.db.set_setting("work_name", self.signatory_inputs['work_name'].text().strip())

    def toggle_nakliye_fields(self):
        """Nakliye modu değiştiğinde alanları aktif/pasif yap"""
        is_manual = self.nakliye_mode_combo.currentIndex() == 1

        self.nakliye_mesafe_input.setEnabled(is_manual)
        self.nakliye_k_input.setEnabled(is_manual)
        self.nakliye_a_input.setEnabled(is_manual)
        self.yogunluk_kum_input.setEnabled(is_manual)
        self.yogunluk_moloz_input.setEnabled(is_manual)
        self.yogunluk_beton_input.setEnabled(is_manual)
        self.yogunluk_cimento_input.setEnabled(is_manual)
        self.yogunluk_demir_input.setEnabled(is_manual)
        self.fetch_k_btn.setEnabled(is_manual)

class PDFSearchAppPyQt5(QMainWindow):
    def __init__(self):
        super().__init__()
        self.search_engine = PDFSearchEngine()
        self.csv_manager = CSVDataManager()  # CSV manager init (empty)
        self.current_results = []
        self.loading_thread = None
        self.csv_loader = None
        self.extractor_thread = None
        self._active_threads = []  # Aktif thread'leri takip et
        self.internal_pdf_dir = Path(__file__).resolve().parent / "PDF"
        self.analiz_dir = Path(__file__).resolve().parent / "ANALIZ"

        # Database manager
        from database import DatabaseManager
        self.db = DatabaseManager()

        # Pencere ikonu ayarla (farklı boyutlarda)
        icon_path = Path(__file__).resolve().parent / "yaklasik_maliyet.png"
        if icon_path.exists():
            icon = QIcon()
            for size in [16, 24, 32, 48, 64, 128, 256]:
                icon.addFile(str(icon_path), QSize(size, size))
            self.setWindowIcon(icon)

        # Loading animasyonu için
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
        self.base_loading_text = ""

        self.csv_selected_pozlar = []  # Initialize selected poz list

        self.current_project_id = None  # Aktif proje ID'si

        # Dosya değişiklik bilgisi
        self.changed_files = []
        self.missing_files = []

        # Async Scan Timer
        self.scan_timer = QTimer()
        self.scan_timer.setSingleShot(True)
        self.scan_timer.timeout.connect(self.start_delayed_loading)

        self.setup_ui()

        # Status Bar Setup
        self.status_bar = self.statusBar()
        
        # Project Label
        self.project_status_label = QLabel("Proje: Seçili Değil")
        self.project_status_label.setStyleSheet("color: #333; margin-right: 20px;")
        self.status_bar.addPermanentWidget(self.project_status_label)

        # AI Model Label
        self.model_status_label = QLabel("AI Model: -")
        self.model_status_label.setStyleSheet("color: #333; font-weight: bold; margin-right: 10px;")
        self.status_bar.addPermanentWidget(self.model_status_label)
        
        # Update status initial
        self.update_ai_status()

        # Uygulama tamamen açıldıktan 500ms sonra yüklemeye başla
        self.scan_timer.start(500)

        # Başlangıç ayarlarına göre proje yükle
        QTimer.singleShot(600, self.handle_startup_project)

    def update_ai_status(self):
        """Update AI Status Bar"""
        provider = self.db.get_setting("ai_provider") or "OpenRouter"

        if provider == "Google Gemini":
            model = self.db.get_setting("gemini_model")
        else:
            model = self.db.get_setting("openrouter_model")

        if not model:
            model = "Seçilmedi"

        self.model_status_label.setText(f"AI: {provider} ({model})")

    def handle_startup_project(self):
        """Başlangıç ayarlarına göre proje yükle"""
        startup_action = self.db.get_setting("startup_action") or "Son projeyi otomatik aç"

        if startup_action == "Son projeyi otomatik aç":
            # Son projeyi yükle
            last_project_id = self.db.get_setting("last_project_id")
            if last_project_id:
                try:
                    project_id = int(last_project_id)
                    project = self.db.get_project(project_id)
                    if project:
                        self.current_project_id = project_id
                        self.update_project_status()
                        self.load_project_data()
                except (ValueError, Exception):
                    pass

        elif startup_action == "Yeni proje dialogu göster":
            # Yeni proje dialogunu göster
            QTimer.singleShot(100, self.show_new_project_dialog)

        # "Boş başla" seçeneği için bir şey yapmıyoruz

    def show_new_project_dialog(self):
        """Yeni proje dialogunu göster"""
        if hasattr(self, 'create_new_project'):
            self.create_new_project()

    def update_project_status(self):
        """Status bar'da proje bilgisini güncelle"""
        # project_status_label henüz oluşturulmamış olabilir
        if not hasattr(self, 'project_status_label'):
            return

        show_project = self.db.get_setting("show_project_in_statusbar")
        if show_project == "false":
            self.project_status_label.setVisible(False)
            return

        self.project_status_label.setVisible(True)

        if self.current_project_id:
            project = self.db.get_project(self.current_project_id)
            if project:
                self.project_status_label.setText(f"📁 Proje: {project['name']}")
                self.project_status_label.setStyleSheet("color: #1565C0; font-weight: bold; margin-right: 20px;")
            else:
                self.project_status_label.setText("Proje: Seçili Değil")
                self.project_status_label.setStyleSheet("color: #333; margin-right: 20px;")
        else:
            self.project_status_label.setText("Proje: Seçili Değil")
            self.project_status_label.setStyleSheet("color: #333; margin-right: 20px;")

    def load_project_data(self):
        """Proje verilerini yükle"""
        # Bu metod projeye özel verileri yüklemek için kullanılır
        # Alt sınıflar veya bileşenler tarafından override edilebilir
        pass

    def closeEvent(self, event):
        """Uygulama kapatılırken tüm thread'leri düzgün sonlandır"""
        # Kapatma onayı kontrolü
        confirm_exit = self.db.get_setting("confirm_on_exit")
        if confirm_exit == "true":
            reply = QMessageBox.question(
                self,
                "Çıkış Onayı",
                "Uygulamayı kapatmak istediğinizden emin misiniz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        # Son projeyi kaydet
        remember_project = self.db.get_setting("remember_last_project")
        if remember_project != "false" and self.current_project_id:
            self.db.set_setting("last_project_id", str(self.current_project_id))

        # Pencere geometrisini kaydet
        remember_geometry = self.db.get_setting("remember_window_geometry")
        if remember_geometry == "true":
            geometry = self.geometry()
            self.db.set_setting("window_x", str(geometry.x()))
            self.db.set_setting("window_y", str(geometry.y()))
            self.db.set_setting("window_width", str(geometry.width()))
            self.db.set_setting("window_height", str(geometry.height()))

        # Çalışan tüm thread'leri durdur
        threads_to_stop = []

        if self.loading_thread and self.loading_thread.isRunning():
            threads_to_stop.append(self.loading_thread)
        if self.csv_loader and self.csv_loader.isRunning():
            threads_to_stop.append(self.csv_loader)
        if self.extractor_thread and self.extractor_thread.isRunning():
            threads_to_stop.append(self.extractor_thread)

        # Aktif thread listesinden de kontrol et
        for thread in self._active_threads:
            if thread and thread.isRunning():
                threads_to_stop.append(thread)

        # Tüm thread'lere stop sinyali gönder
        for thread in threads_to_stop:
            if hasattr(thread, 'stop'):
                thread.stop()

        # Thread'lerin bitmesini bekle (max 2 saniye)
        for thread in threads_to_stop:
            thread.wait(2000)

        # Timer'ları durdur
        if hasattr(self, 'loading_timer') and self.loading_timer.isActive():
            self.loading_timer.stop()
        if hasattr(self, 'scan_timer') and self.scan_timer.isActive():
            self.scan_timer.stop()

        event.accept()

    def start_delayed_loading(self):
        """Ağır yükleme işlemlerini başlat"""
        self.file_label.setText("🚀 CSV ve PDF verileri taranıyor...")
        self.loaded_source_files = []  # Yüklenen dosya listesi

        # Async CSV + PDF Load
        self.csv_loader = CSVLoaderThread(self.csv_manager.csv_folder)
        self.csv_loader.finished.connect(self.on_csv_loaded)
        self.csv_loader.progress.connect(lambda msg: self.file_label.setText(f"🔄 {msg}"))
        self.csv_loader.error.connect(lambda e: self.file_label.setText(f"Hata: {e}"))
        self.csv_loader.start()

    def on_csv_loaded(self, data, count, loaded_files):
        """CSV ve PDF yükleme tamamlandı"""
        self.csv_manager.poz_data = data
        self.loaded_source_files = loaded_files

        # Dosya bilgisi özeti oluştur
        csv_count = sum(1 for f in loaded_files if f['type'] == 'CSV')
        pdf_count = sum(1 for f in loaded_files if f['type'] == 'PDF')
        total_files = len(loaded_files)

        self.file_label.setText(f"✅ Hazır: {count} poz ({csv_count} CSV, {pdf_count} PDF dosyasından)")

        # UI Tablosunu güncelle
        self.csv_poz_data = list(data.values())
        if hasattr(self, 'csv_poz_table'):
            self.display_csv_pozlar(self.csv_poz_data)

        # Yüklenen dosyalar bilgisini güncelle (CSV sekmesinde)
        if hasattr(self, 'loaded_files_label'):
            files_text = self.format_loaded_files_text(loaded_files)
            self.loaded_files_label.setText(files_text)

        # 2. PDF Cache Load (Bundan sonra başlasın)
        QTimer.singleShot(100, self.load_pdfs_with_cache)

    def format_loaded_files_text(self, loaded_files):
        """Yüklenen dosyalar için bilgi metni oluştur"""
        if not loaded_files:
            return "Yüklenen dosya yok"

        csv_files = [f for f in loaded_files if f['type'] == 'CSV']
        pdf_files = [f for f in loaded_files if f['type'] == 'PDF']

        lines = []
        lines.append(f"📁 Toplam {len(loaded_files)} dosya yüklendi:")

        if csv_files:
            lines.append(f"\n📄 CSV ({len(csv_files)} dosya):")
            for f in csv_files[:5]:  # İlk 5 dosya
                lines.append(f"  • {f['name']} ({f['poz_count']} poz)")
            if len(csv_files) > 5:
                lines.append(f"  ... ve {len(csv_files) - 5} dosya daha")

        if pdf_files:
            lines.append(f"\n📕 PDF ({len(pdf_files)} dosya):")
            for f in pdf_files[:5]:  # İlk 5 dosya
                lines.append(f"  • {f['name']} ({f['poz_count']} poz)")
            if len(pdf_files) > 5:
                lines.append(f"  ... ve {len(pdf_files) - 5} dosya daha")

        return "\n".join(lines)

    def setup_ui(self):
        """UI kurulumu"""
        self.setWindowTitle("Yaklaşık Maliyet Pro - Birim Fiyat ve Maliyet Tahmini")

        # Pencere geometrisini geri yükle veya varsayılan kullan
        remember_geometry = self.db.get_setting("remember_window_geometry")
        if remember_geometry == "true":
            try:
                x = int(self.db.get_setting("window_x") or 100)
                y = int(self.db.get_setting("window_y") or 100)
                w = int(self.db.get_setting("window_width") or 1400)
                h = int(self.db.get_setting("window_height") or 900)
                self.setGeometry(x, y, w, h)
            except (ValueError, TypeError):
                self.setGeometry(100, 100, 1400, 900)
                self.showMaximized()
        else:
            self.setGeometry(100, 100, 1400, 900)
            self.showMaximized()

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Ana layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # === GÜNCELLEME BANNER'I (varsayılan gizli) ===
        self.update_banner = QFrame()
        self.update_banner.setStyleSheet("""
            QFrame {
                background-color: #FFF3E0;
                border: 2px solid #FF9800;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        banner_layout = QHBoxLayout(self.update_banner)
        banner_layout.setContentsMargins(10, 5, 10, 5)

        self.update_icon_label = QLabel("⚠️")
        self.update_icon_label.setStyleSheet("font-size: 16pt;")
        banner_layout.addWidget(self.update_icon_label)

        self.update_text_label = QLabel("PDF dosyalarında değişiklik tespit edildi!")
        self.update_text_label.setStyleSheet("font-weight: bold; color: #E65100; font-size: 10pt;")
        banner_layout.addWidget(self.update_text_label)

        banner_layout.addStretch()

        self.update_btn = QPushButton("🔄 Verileri Güncelle")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.update_btn.clicked.connect(self.refresh_all_data)
        banner_layout.addWidget(self.update_btn)

        self.dismiss_btn = QPushButton("✕")
        self.dismiss_btn.setCursor(Qt.PointingHandCursor)
        self.dismiss_btn.setFixedSize(25, 25)
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14pt;
                color: #666;
            }
            QPushButton:hover {
                color: #333;
            }
        """)
        self.dismiss_btn.clicked.connect(self.hide_update_banner)
        banner_layout.addWidget(self.dismiss_btn)

        self.update_banner.setVisible(False)  # Varsayılan gizli
        main_layout.addWidget(self.update_banner)

        # Aktif Proje Bilgisi Header
        self.project_header = QGroupBox("Aktif Proje")
        self.project_header.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #1976D2;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #E3F2FD;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1976D2;
            }
        """)
        header_layout = QHBoxLayout()

        self.project_name_label = QLabel("Proje seçilmedi")
        self.project_name_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1565C0;")
        header_layout.addWidget(self.project_name_label)

        header_layout.addWidget(QLabel(" | "))

        self.project_employer_label = QLabel("İşveren: -")
        header_layout.addWidget(self.project_employer_label)

        self.project_contractor_label = QLabel("Yüklenici: -")
        header_layout.addWidget(self.project_contractor_label)

        self.project_location_label = QLabel("Yer: -")
        header_layout.addWidget(self.project_location_label)

        header_layout.addStretch()

        # Proje Yönetim Butonları (Header)
        self.new_proj_btn = QPushButton("+ Yeni Proje")
        self.new_proj_btn.setCursor(Qt.PointingHandCursor)
        self.new_proj_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.new_proj_btn.clicked.connect(lambda: self.cost_tab.create_new_project())
        header_layout.addWidget(self.new_proj_btn)

        self.manage_proj_btn = QPushButton("📁 Proje Yönetimi")
        self.manage_proj_btn.setCursor(Qt.PointingHandCursor)
        self.manage_proj_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.manage_proj_btn.clicked.connect(lambda: self.cost_tab.open_project_manager())
        header_layout.addWidget(self.manage_proj_btn)

        self.close_proj_btn = QPushButton("🚪 Projeden Çıkış")
        self.close_proj_btn.setCursor(Qt.PointingHandCursor)
        self.close_proj_btn.setVisible(False) # Başlangıçta gizli (proje yok)
        self.close_proj_btn.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.close_proj_btn.clicked.connect(lambda: self.cost_tab.close_current_project())
        header_layout.addWidget(self.close_proj_btn)

        self.project_header.setLayout(header_layout)
        main_layout.addWidget(self.project_header)

        # Durum bölümü - Sadece bilgi göster
        status_group = QGroupBox("Durum")
        status_layout = QHBoxLayout()

        self.file_label = QLabel("CSV'den veri yükleniyor...")
        status_layout.addWidget(self.file_label)

        status_layout.addStretch()

        # PDF → CSV Güncelle butonu
        self.extract_status_btn = QPushButton("📄 PDF → CSV Güncelle")
        self.extract_status_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px 15px;")
        self.extract_status_btn.clicked.connect(self.start_background_extraction)
        status_layout.addWidget(self.extract_status_btn)

        # Ayarlar Butonu
        settings_btn = QPushButton("⚙️ Ayarlar")
        settings_btn.clicked.connect(self.open_settings)
        status_layout.addWidget(settings_btn)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Tab widget oluştur
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Hakkımda sekmesi (Her zaman aktif)
        self.about_tab = QWidget()
        self.tab_widget.addTab(self.about_tab, "ℹ️ Hakkımda")
        self.setup_about_tab()

        # CSV Seçim sekmesi
        self.csv_selection_tab = QWidget()
        self.tab_widget.addTab(self.csv_selection_tab, "✨ CSV Poz Seçim")
        self.setup_csv_selection_tab()

        # Poz Viewer sekmesi
        self.poz_viewer_tab = PozViewerWidget()
        self.poz_viewer_tab.parent_app = self  # Parent app referansı
        self.tab_widget.addTab(self.poz_viewer_tab, "📋 Poz Viewer")

        # Analiz sekmesi
        self.analysis_tab = AnalysisTableWidget()
        self.analysis_tab.search_engine = self.search_engine  # Search engine referansı
        self.analysis_tab.parent_app = self  # Parent app referansı
        self.tab_widget.addTab(self.analysis_tab, "📊 Poz Analizi")

        # Maliyet Hesabı
        self.cost_tab = CostEstimator()
        self.tab_widget.addTab(self.cost_tab, "💰 Maliyet Hesabı")

        # Yeni Analiz & AI
        self.builder_tab = AnalysisBuilder()
        self.builder_tab.parent_app = self # REFERANS EKLENDİ
        self.tab_widget.addTab(self.builder_tab, "🤖 Yeni Analiz Yap")
        
        # Kayıtlı Pozlar ve Analizler (YENİ SEKME)
        self.custom_analysis_tab = CustomAnalysisManager()
        self.custom_analysis_tab.parent_app = self  # Projeye ekleme için referans
        self.tab_widget.addTab(self.custom_analysis_tab, "💾 Kayıtlı Pozlar ve Analizler")

        # Tab: Quantity Takeoff (İmalat Metrajları)
        self.takeoff_tab = QuantityTakeoffManager()
        self.tab_widget.addTab(self.takeoff_tab, "📐 Proje İmalat Metrajı")
        
        # Proje değişikliği sinyalini bağla
        self.cost_tab.project_changed_signal.connect(self.on_project_changed)

        # Başlangıçta aktif bir proje varsa (auto-load) header'ı güncelle
        current_project = self.cost_tab.get_current_project()
        if current_project:
            self.on_project_changed(current_project)

        # Başlangıçta tabları kontrol et
        self.update_tabs_state()

    def setup_about_tab(self):
        """Hakkımda sekmesini oluştur"""
        layout = QVBoxLayout(self.about_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        # Arka plan için container
        container = QWidget()
        container.setStyleSheet("background-color: white;")
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignCenter)

        # Logo veya Başlık
        title = QLabel("Yaklaşık Maliyet Pro")
        title.setStyleSheet("""
            QLabel {
                font-size: 28pt; 
                font-weight: bold; 
                color: #1565C0; 
                margin-bottom: 5px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        # Versiyon
        version = QLabel("v1.0.0")
        version.setStyleSheet("""
            QLabel {
                font-size: 11pt; 
                color: white; 
                background-color: #607D8B; 
                border-radius: 10px; 
                padding: 4px 12px;
            }
        """)
        version.setAlignment(Qt.AlignCenter)
        version_container = QWidget()
        version_layout = QHBoxLayout(version_container)
        version_layout.addStretch()
        version_layout.addWidget(version)
        version_layout.addStretch()
        container_layout.addWidget(version_container)

        container_layout.addSpacing(30)

        # Bilgi Kartı
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #F5F7FA;
                border: 1px solid #E0E0E0;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        card_layout = QVBoxLayout(info_card)

        desc = QLabel()
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setTextFormat(Qt.RichText)
        desc.setOpenExternalLinks(True)
        desc.setStyleSheet("font-size: 11pt; color: #37474F; line-height: 1.5;")
        
        html_content = """
        <p style='margin-bottom: 15px;'>
            <b>Türkiye İnşaat Sektörü</b> için geliştirilmiş, PDF'lerden otomatik veri çıkarma ve 
            birim fiyat analiz yeteneklerine sahip kapsamlı maliyet hesaplama aracı.
        </p>

        <hr style='border: 1px solid #CFD8DC; margin: 15px 0;'>

        <p>
            Developed by <b>Umut Çelik</b>
        </p>

        <p style='margin-top: 20px;'>
            📧 <a href='mailto:umutcelik6230@gmail.com' style='text-decoration: none; color: #1976D2; font-weight: bold;'>umutcelik6230@gmail.com</a>
        </p>
        
        <p>
            🐦 <a href='https://x.com/palamut62' style='text-decoration: none; color: #1DA1F2; font-weight: bold;'>@palamut62</a>
        </p>
        """
        desc.setText(html_content)
        card_layout.addWidget(desc)

        container_layout.addWidget(info_card)
        container_layout.addStretch()
        
        # Footer
        footer = QLabel("© 2025 Yaklaşık Maliyet Pro. Tüm hakları saklıdır.")
        footer.setStyleSheet("color: #90A4AE; font-size: 9pt; margin-top: 20px;")
        footer.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(footer)

        layout.addWidget(container)

    def on_project_changed(self, project_data):
        """Proje değiştiğinde çağrılır"""
        # Proje ID'sini güncelle
        self.current_project_id = project_data.get('id') if project_data else None

        if project_data and project_data.get('name'):
            self.project_name_label.setText(project_data.get('name', 'İsimsiz Proje'))
            self.project_employer_label.setText(f"İşveren: {project_data.get('employer', '-') or '-'}")
            self.project_contractor_label.setText(f"Yüklenici: {project_data.get('contractor', '-') or '-'}")
            self.project_location_label.setText(f"Yer: {project_data.get('location', '-') or '-'}")

            # Pencere başlığını güncelle
            self.setWindowTitle(f"Yaklaşık Maliyet Pro - {project_data.get('name', '')}")
        else:
            self.project_name_label.setText("Proje seçilmedi")
            self.project_employer_label.setText("İşveren: -")
            self.project_contractor_label.setText("Yüklenici: -")
            self.project_location_label.setText("Yer: -")
            self.setWindowTitle("Yaklaşık Maliyet Pro - Birim Fiyat ve Maliyet Tahmini")

        # Tab durumlarını güncelle
        self.update_tabs_state()

    def update_tabs_state(self):
        """Proje durumuna göre tabları aktif/pasif yap"""
        has_project = self.cost_tab.has_active_project()

        # Hakkımda (index 0) her zaman aktif
        # Diğer sekmeler proje varsa aktif
        for i in range(self.tab_widget.count()):
            if i == 0:  # Hakkımda sekmesi
                self.tab_widget.setTabEnabled(i, True)
            else:
                self.tab_widget.setTabEnabled(i, has_project)

        # Buton görünürlüğü
        if hasattr(self, 'close_proj_btn'):
            self.close_proj_btn.setVisible(has_project)
        
        # Status bar'ı güncelle
        self.update_project_status()
        
        # Switch to project tab:
        if not has_project:
             # Eğer proje yoksa Hakkımda sekmesine git
            self.tab_widget.setCurrentIndex(0)

    def open_settings(self):
        """Ayarlar penceresini aç"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_ai_status()
        # Ayarlar kapatıldığında dosya değişikliğini kontrol et
        self.check_file_changes()

    def check_file_changes(self):
        """PDF ve Analiz klasörlerindeki dosya değişikliklerini kontrol et"""
        try:
            self.changed_files = []

            # PDF klasöründeki dosyaları kontrol et
            pdf_files = list(self.internal_pdf_dir.glob("*.pdf")) if self.internal_pdf_dir.exists() else []
            analiz_files = list(self.analiz_dir.glob("*.pdf")) if self.analiz_dir.exists() else []

            # Kayıtlı hash'leri al
            last_pdf_hash = self.db.get_setting("pdf_folder_hash")
            last_analiz_hash = self.db.get_setting("analiz_folder_hash")

            # Mevcut hash'leri hesapla
            current_pdf_hash = self._calculate_folder_hash(pdf_files)
            current_analiz_hash = self._calculate_folder_hash(analiz_files)

            # Değişiklik var mı kontrol et
            pdf_changed = last_pdf_hash != current_pdf_hash if last_pdf_hash else False
            analiz_changed = last_analiz_hash != current_analiz_hash if last_analiz_hash else False

            if pdf_changed or analiz_changed:
                changes = []
                if pdf_changed:
                    changes.append("PDF dosyaları")
                if analiz_changed:
                    changes.append("Analiz dosyaları")

                self.show_update_banner(f"{', '.join(changes)} değişmiş!")
            else:
                # İlk çalıştırmada hash'leri kaydet
                if not last_pdf_hash:
                    self.db.set_setting("pdf_folder_hash", current_pdf_hash)
                if not last_analiz_hash:
                    self.db.set_setting("analiz_folder_hash", current_analiz_hash)

        except Exception as e:
            print(f"Dosya değişiklik kontrolü hatası: {e}")

    def _calculate_folder_hash(self, files):
        """Klasördeki dosyaların birleşik hash'ini hesapla"""
        import hashlib
        hash_data = ""
        for f in sorted(files, key=lambda x: x.name):
            try:
                stat = f.stat()
                hash_data += f"{f.name}_{stat.st_size}_{stat.st_mtime}_"
            except:
                pass
        return hashlib.md5(hash_data.encode()).hexdigest() if hash_data else ""

    def show_update_banner(self, message="PDF dosyalarında değişiklik tespit edildi!"):
        """Güncelleme banner'ını göster"""
        self.update_text_label.setText(f"⚠️ {message}")
        self.update_banner.setVisible(True)

    def hide_update_banner(self):
        """Güncelleme banner'ını gizle"""
        self.update_banner.setVisible(False)

    def refresh_all_data(self):
        """Tüm verileri yenile - cache temizle ve yeniden yükle"""
        self.hide_update_banner()
        self.file_label.setText("🔄 Veriler yenileniyor...")

        # Loading göster
        self.update_btn.setEnabled(False)
        self.update_btn.setText("⏳ Güncelleniyor...")

        # Cache temizle
        try:
            if hasattr(self.search_engine, 'clear_cache'):
                self.search_engine.clear_cache()
        except:
            pass

        # CSV verilerini temizle ve yeniden yükle
        self.csv_manager.poz_data = {}

        # Yeni hash'leri kaydet
        pdf_files = list(self.internal_pdf_dir.glob("*.pdf")) if self.internal_pdf_dir.exists() else []
        analiz_files = list(self.analiz_dir.glob("*.pdf")) if self.analiz_dir.exists() else []
        self.db.set_setting("pdf_folder_hash", self._calculate_folder_hash(pdf_files))
        self.db.set_setting("analiz_folder_hash", self._calculate_folder_hash(analiz_files))

        # Yeniden yüklemeyi başlat
        QTimer.singleShot(500, self._complete_refresh)

    def _complete_refresh(self):
        """Yenileme işlemini tamamla"""
        try:
            # CSV'leri yeniden yükle
            self.csv_loader = CSVLoaderThread(self.csv_manager.csv_folder)
            self.csv_loader.finished.connect(self._on_refresh_complete)
            self.csv_loader.error.connect(lambda e: self._on_refresh_error(e))
            self.csv_loader.start()
        except Exception as e:
            self._on_refresh_error(str(e))

    def _on_refresh_complete(self, data, count, loaded_files):
        """Yenileme tamamlandığında"""
        self.csv_manager.poz_data = data
        self.csv_poz_data = list(data.values())
        self.loaded_source_files = loaded_files

        if hasattr(self, 'csv_poz_table'):
            self.display_csv_pozlar(self.csv_poz_data)

        # Yüklenen dosyalar bilgisini güncelle
        if hasattr(self, 'loaded_files_label'):
            files_text = self.format_loaded_files_text(loaded_files)
            self.loaded_files_label.setText(files_text)

        csv_count = sum(1 for f in loaded_files if f['type'] == 'CSV')
        pdf_count = sum(1 for f in loaded_files if f['type'] == 'PDF')

        self.file_label.setText(f"✅ Veriler güncellendi: {count} poz ({csv_count} CSV, {pdf_count} PDF)")
        self.update_btn.setEnabled(True)
        self.update_btn.setText("🔄 Verileri Güncelle")

        QMessageBox.information(self, "Güncelleme Tamamlandı",
                                f"Veriler başarıyla güncellendi.\n{count} poz yüklendi.\n({csv_count} CSV, {pdf_count} PDF dosyasından)")

    def _on_refresh_error(self, error):
        """Yenileme hatası"""
        self.file_label.setText(f"❌ Güncelleme hatası: {error}")
        self.update_btn.setEnabled(True)
        self.update_btn.setText("🔄 Verileri Güncelle")

    def load_pdf_file(self):
        """Tek PDF dosyası yükle"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF Dosyası Seç", "", "PDF files (*.pdf)"
        )

        if file_path:
            self.show_loading("PDF yükleniyor...")

            # QTimer ile UI güncellemesi için kısa gecikme
            QTimer.singleShot(100, lambda: self.load_single_pdf_delayed(file_path))

    def load_single_pdf_delayed(self, file_path):
        """Tek PDF yükleme - delayed execution"""
        try:
            if self.search_engine.load_pdf(file_path):
                self.file_label.setText(f"Yüklendi: {Path(file_path).name}")
                self.hide_loading()
            else:
                self.file_label.setText("PDF yüklenemedi!")
                self.hide_loading()
        except Exception as e:
            self.file_label.setText(f"Hata: {str(e)}")
            self.hide_loading()

    def load_all_pdfs(self):
        """Klasördeki tüm PDF'leri yükle"""
        folder_path = QFileDialog.getExistingDirectory(self, "PDF Klasörü Seç")

        if folder_path:
            pdf_files = list(Path(folder_path).glob("*.pdf"))

            if not pdf_files:
                self.file_label.setText("Klasörde PDF dosyası bulunamadı!")
                return

            self.show_loading("PDF'ler yükleniyor...")

            # Threading ile yükleme
            self.loading_thread = LoadingThread(self.search_engine, pdf_files)
            self.loading_thread.progress_signal.connect(self.update_loading_progress)
            self.loading_thread.finished_signal.connect(self.loading_finished)
            self.loading_thread.error_signal.connect(self.loading_error)
            self.loading_thread.start()

    def update_loading_progress(self, file_name, current, total):
        """Loading progress güncelle"""
        self.file_label.setText(f"Yükleniyor: {file_name} ({current}/{total})")

    def loading_finished(self, loaded_count):
        """Loading tamamlandı"""
        self.hide_loading()
        total_files = len(self.search_engine.loaded_files)
        # Cache'e kaydet
        if self.search_engine.save_cache():
            self.file_label.setText(f"✅ {total_files} PDF yüklendi ve cache'e kaydedildi")
        else:
            self.file_label.setText(f"✅ {total_files} PDF yüklendi")
        self.list_loaded_pdfs_on_label()

    def loading_error(self, error_msg):
        """Loading hatası"""
        print(error_msg)

    def show_loading(self, message="Yükleniyor..."):
        """Loading göster"""
        self.base_loading_text = message
        self.loading_dots = 0
        self.loading_timer.start(500)  # Her 500ms'de güncelle
        # Yalnızca etiket animasyonu; ilerleme çubuğu kullanılmıyor

    def hide_loading(self):
        """Loading gizle"""
        self.loading_timer.stop()
        if hasattr(self, 'search_engine'):
            loaded_count = len(self.search_engine.loaded_files)
            self.file_label.setText(f"{loaded_count} PDF dosyası yüklü")
            self.list_loaded_pdfs_on_label()

    def list_loaded_pdfs_on_label(self):
        """Yüklü PDF dosyalarını etiket üzerinde listele"""
        try:
            if self.search_engine.loaded_files:
                file_count = len(self.search_engine.loaded_files)
                names = ", ".join(self.search_engine.loaded_files[:5])  # İlk 5 dosya
                if file_count > 5:
                    names += f" ... (+{file_count - 5} dosya daha)"
                cache_time = getattr(self.search_engine, 'cache_timestamp', None)
                if cache_time:
                    self.file_label.setText(f"📂 {file_count} PDF yüklü | {names}")
                else:
                    self.file_label.setText(f"📂 {file_count} PDF yüklü | {names}")
            else:
                self.file_label.setText("Yüklenen dosya yok")
        except Exception:
            pass

    def load_pdfs_with_cache(self):
        """PDF dosyalarını cache'den veya yeniden yükle"""
        try:
            # CSV dosyalarını yükle
            csv_count = len(self.csv_manager.poz_data)
            if csv_count > 0:
                self.file_label.setText(f"CSV'den yüklendi: {csv_count} poz")
                # Dosya değişikliği kontrolü
                QTimer.singleShot(1000, self.check_file_changes)
                return

            # PDF'den cache yükle
            if self.search_engine.load_cache():
                file_count = len(self.search_engine.loaded_files)
                cache_time = getattr(self.search_engine, 'cache_timestamp', 'Bilinmiyor')
                self.file_label.setText(f"✅ Cache'den yüklendi: {file_count} PDF (Son güncelleme: {cache_time})")
                self.list_loaded_pdfs_on_label()
                # Dosya değişikliği kontrolü
                QTimer.singleShot(1000, self.check_file_changes)
                return

            # Cache başarısızsa normal yükleme yap
            self.file_label.setText("📂 PDF klasörü taranıyor...")
            self.scan_internal_pdf_folder()
            # Dosya değişikliği kontrolü
            QTimer.singleShot(2000, self.check_file_changes)

        except Exception as e:
            self.file_label.setText(f"Yükleme hatası: {str(e)}")
            # Hata durumunda PDF yüklemeye geri dön
            self.scan_internal_pdf_folder()

    def clear_cache(self):
        """Cache temizleme"""
        try:
            if self.search_engine.clear_cache():
                self.file_label.setText("Cache temizlendi. PDF'ler yeniden yüklenecek.")
                # Cache temizlendikten sonra PDF'leri yeniden yükle
                QTimer.singleShot(1000, self.scan_internal_pdf_folder)
            else:
                self.file_label.setText("Cache temizleme başarısız!")
        except Exception as e:
            self.file_label.setText(f"Cache temizleme hatası: {str(e)}")

    def scan_internal_pdf_folder(self):
        """Dahili PDF klasörünü tara ve PDF'leri yükle"""
        try:
            if not self.internal_pdf_dir.exists():
                self.file_label.setText("Dahili 'PDF' klasörü bulunamadı")
                return

            pdf_files = list(self.internal_pdf_dir.glob("*.pdf"))

            if not pdf_files:
                self.file_label.setText("Dahili klasörde PDF dosyası yok")
                return

            self.show_loading("Dahili PDF'ler taranıyor...")

            # Thread ile yükle
            # Animation Start
            self.loading_files = [p.name for p in pdf_files]
            self.loading_idx = 0
            
            self.loading_thread = LoadingThread(self.search_engine, pdf_files)
            self.loading_thread.progress_signal.connect(self.update_loading_progress)
            self.loading_thread.finished_signal.connect(self.loading_finished)
            self.loading_thread.error_signal.connect(self.loading_error)
            self.loading_thread.start()
        except Exception as e:
            self.file_label.setText(f"Dahili PDF tarama hatası: {str(e)}")

    def update_loading_progress(self, file_name, current, total):
        """Loading progress güncelle - Animasyonlu"""
        # Show specific file name being loaded to create animation effect
        self.file_label.setText(f"📂 Yükleniyor: {file_name} ({current}/{total})")

    def search_poz(self):
        """Poz numarası ara - CSV'den arayı başlat"""
        poz_no = self.poz_entry.text().strip()

        if not poz_no:
            self.file_label.setText("Poz numarası girin!")
            return

        # Önce CSV'den ara
        csv_result = self.csv_manager.search_poz(poz_no)
        if csv_result:
            # CSV'den bulundu
            results = [csv_result]
            self.file_label.setText(f"CSV'den bulundu: {csv_result['institution']}")
            self.display_results(results, f"Poz '{poz_no}'")
            return

        # CSV'de bulunamazsa PDF'den ara
        if not self.search_engine.loaded_files:
            self.file_label.setText("Poz bulunamadı!")
            return

        results = self.search_engine.search_poz_number(poz_no)
        if results:
            self.display_results(results, f"Poz '{poz_no}' (PDF'den)")
        else:
            self.file_label.setText("Poz bulunamadı!")

    def search_keyword(self):
        """Anahtar kelime ara - CSV'den başlat"""
        keyword = self.keyword_entry.text().strip()

        if not keyword:
            self.file_label.setText("Anahtar kelime girin!")
            return

        # Önce CSV'den ara
        csv_results = self.csv_manager.search_keyword(keyword)
        if csv_results:
            self.file_label.setText(f"CSV'den {len(csv_results)} sonuç bulundu")
            self.display_results(csv_results, f"Kelime '{keyword}'")
            return

        # CSV'de bulunamazsa PDF'den ara
        if not self.search_engine.loaded_files:
            self.file_label.setText("Sonuç bulunamadı!")
            return

        results = self.search_engine.search_keyword(keyword)
        if results:
            self.display_results(results, f"Kelime '{keyword}' (PDF'den)")
        else:
            self.file_label.setText("Sonuç bulunamadı!")

    def display_results(self, results, search_info=""):
        """Sonuçları tabloda göster (CSV ve PDF sonuçları)"""
        self.current_results = results
        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            # CSV sonuçları mı PDF sonuçları mı kontrol et
            if isinstance(result, dict) and 'extracted_data' in result:
                # PDF sonucu
                data = result['extracted_data']
                values = [
                    result['file'],
                    str(result['page']),
                    data['poz_no'] or '',
                    data['description'] or '',
                    data['unit'] or '',
                    data['quantity'] or '',
                    data['unit_price'] or '',
                    data.get('institution', ''),  # Kurum
                    data['total_price'] or ''
                ]
            else:
                # CSV sonucu
                values = [
                    result.get('source_file', 'CSV'),
                    '',  # page
                    result.get('poz_no', ''),
                    result.get('description', ''),
                    result.get('unit', ''),
                    result.get('quantity', ''),
                    result.get('unit_price', ''),
                    result.get('institution', ''),  # Kurum
                    ''  # total_price
                ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.results_table.setItem(row, col, item)

        # Sonuç sayısını file_label'da göster
        if results:
            self.file_label.setText(f"{search_info}: {len(results)} sonuç bulundu")
        else:
            self.file_label.setText(f"{search_info}: Sonuç bulunamadı")

    def export_results(self):
        """Sonuçları Excel'e aktar"""
        if not self.current_results:
            self.file_label.setText("Aktarılacak sonuç yok!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyası Kaydet", "", "Excel files (*.xlsx)"
        )

        if file_path:
            try:
                self.show_loading("Excel'e aktarılıyor...")

                export_data = []
                for result in self.current_results:
                    data = result['extracted_data']
                    row = {
                        'Dosya': result['file'],
                        'Sayfa': result['page'],
                        'Satır': result['line_number'],
                        'Arama Terimi': result['search_term'],
                        'Poz No': data['poz_no'],
                        'Açıklama': data['description'],
                        'Birim': data['unit'],
                        'Miktar': data['quantity'],
                        'Birim Fiyat': data['unit_price'],
                        'Toplam Fiyat': data['total_price'],
                        'Tam Metin': result['full_text']
                    }
                    export_data.append(row)

                df = pd.DataFrame(export_data)
                df.to_excel(file_path, index=False)

                self.hide_loading()
                self.file_label.setText(f"Excel'e aktarıldı: {Path(file_path).name}")

            except Exception as e:
                self.hide_loading()
                self.file_label.setText(f"Excel hatası: {str(e)}")

    def start_background_extraction(self):
        """PDF çıkartma işlemini arka planda başlat (UI göstermez)"""
        try:
            # Butonu geçici olarak devre dışı bırak
            self.extract_status_btn.setEnabled(False)
            self.extract_status_btn.setText("⏳ Arka planda çalışıyor...")

            # Thread'de çalıştır
            self.bg_extract_thread = BackgroundExtractorThread()
            self.bg_extract_thread.finished.connect(self.on_background_extraction_finished)
            self.bg_extract_thread.error.connect(self.on_background_extraction_error)
            self.bg_extract_thread.start()

        except Exception as e:
            self.file_label.setText(f"Hata: {str(e)}")
            self.extract_status_btn.setEnabled(True)
            self.extract_status_btn.setText("📄 PDF → CSV Güncelle")

    def on_background_extraction_finished(self, result_message):
        """Arka planda çalışan çıkartma işlemi tamamlandı"""
        self.extract_status_btn.setEnabled(True)
        self.extract_status_btn.setText("📄 PDF → CSV Güncelle")

        # Bilgilendirme mesajı göster
        self.file_label.setText(f"✅ {result_message}")

        # CSV verilerini otomatik olarak yeniden yükle
        QTimer.singleShot(1500, self.reload_csv_data)

    def on_background_extraction_error(self, error_message):
        """Arka plandaki çıkartma işleminde hata"""
        self.extract_status_btn.setEnabled(True)
        self.extract_status_btn.setText("📄 PDF → CSV Güncelle")

        # Hata mesajı göster
        self.file_label.setText(f"❌ Çıkartma hatası: {error_message}")

    def reload_csv_data(self):
        """CSV verilerini yeniden yükle"""
        try:
            # CSV Manager'ı yenile
            self.csv_manager = CSVDataManager()
            self.load_and_display_csv_pozlar()
            self.file_label.setText("CSV verileri yeniden yüklendi!")
        except Exception as e:
            self.file_label.setText(f"CSV yükleme hatası: {str(e)}")

    def force_reload_poz_data(self):
        """Cache'i temizle ve tüm dosyaları yeniden yükle"""
        try:
            # Cache dosyasını sil
            cache_file = Path(__file__).parent / "cache" / "poz_data_cache.json"
            if cache_file.exists():
                cache_file.unlink()
                self.file_label.setText("🗑️ Cache temizlendi, yeniden yükleniyor...")

            # Yüklenen dosyalar bilgisini sıfırla
            if hasattr(self, 'loaded_files_label'):
                self.loaded_files_label.setText("📁 Dosyalar yeniden yükleniyor...")

            # Yeniden yükle
            self.csv_manager.poz_data = {}
            self.start_delayed_loading()

        except Exception as e:
            self.file_label.setText(f"Yenileme hatası: {str(e)}")

    def clear_results(self):
        """Sonuçları temizle"""
        self.results_table.setRowCount(0)
        self.poz_entry.clear()
        self.keyword_entry.clear()
        self.current_results = []

    def setup_csv_selection_tab(self):
        """CSV Poz Seçim sekmesini oluştur"""
        from PyQt5.QtWidgets import QSplitter

        tab_layout = QVBoxLayout()
        self.csv_selection_tab.setLayout(tab_layout)

        # Üst bilgi bölümü - Yüklenen dosyalar
        info_layout = QHBoxLayout()

        # Yüklenen dosyalar bilgisi (sol)
        self.loaded_files_label = QLabel("📁 Dosyalar yükleniyor...")
        self.loaded_files_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 4px;
                padding: 8px;
                font-size: 9pt;
            }
        """)
        self.loaded_files_label.setWordWrap(True)
        self.loaded_files_label.setMinimumHeight(80)
        info_layout.addWidget(self.loaded_files_label, stretch=2)

        # Yenile butonu (sağ)
        refresh_btn = QPushButton("🔄 Verileri Yenile")
        refresh_btn.setToolTip("PDF klasöründeki tüm dosyaları yeniden tara")
        refresh_btn.clicked.connect(self.force_reload_poz_data)
        refresh_btn.setFixedWidth(130)
        info_layout.addWidget(refresh_btn)

        tab_layout.addLayout(info_layout)

        # Arama bölümü
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Ara:"))
        self.csv_search_input = QLineEdit()
        self.csv_search_input.textChanged.connect(self.filter_csv_pozlar)
        search_layout.addWidget(self.csv_search_input)
        tab_layout.addLayout(search_layout)

        # Splitter ile 2 bölüm
        splitter = QSplitter(Qt.Horizontal)

        # SOL: CSV Pozları
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_label = QLabel("CSV Pozları (Çift Tıkla veya → Seç)")
        left_layout.addWidget(left_label)

        self.csv_poz_table = QTableWidget()
        self.csv_poz_table.setColumnCount(4)
        self.csv_poz_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.csv_poz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.csv_poz_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.csv_poz_table.doubleClicked.connect(self.csv_add_selected_poz)
        left_layout.addWidget(self.csv_poz_table)

        # Ok butonları
        button_layout = QHBoxLayout()
        btn_add = QPushButton("➜ Seç (→)")
        btn_add.clicked.connect(self.csv_add_selected_poz)
        button_layout.addWidget(btn_add)

        btn_add_all = QPushButton("⟹ Tümünü Seç")
        btn_add_all.clicked.connect(self.csv_add_all_pozlar)
        button_layout.addWidget(btn_add_all)
        button_layout.addStretch()
        left_layout.addLayout(button_layout)

        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # SAĞ: Seçili Pozlar
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_label = QLabel("Seçili Pozlar")
        right_layout.addWidget(right_label)

        self.csv_selected_table = QTableWidget()
        self.csv_selected_table.setColumnCount(4)
        self.csv_selected_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.csv_selected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.csv_selected_table.setSelectionBehavior(QTableWidget.SelectRows)
        right_layout.addWidget(self.csv_selected_table)

        # Çıkar butonları
        remove_layout = QHBoxLayout()
        btn_remove = QPushButton("← Çıkar (←)")
        btn_remove.clicked.connect(self.csv_remove_selected_poz)
        remove_layout.addWidget(btn_remove)

        btn_remove_all = QPushButton("⟸ Tümünü Çıkar")
        btn_remove_all.clicked.connect(self.csv_remove_all_pozlar)
        remove_layout.addWidget(btn_remove_all)
        remove_layout.addStretch()
        right_layout.addLayout(remove_layout)

        # Bilgi etiketi
        self.csv_info_label = QLabel("Seçili: 0 poz")
        right_layout.addWidget(self.csv_info_label)

        # Export butonu
        btn_export_csv = QPushButton("💾 Seçili Pozları CSV'ye Kaydet")
        btn_export_csv.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_export_csv.clicked.connect(self.export_csv_selected)
        right_layout.addWidget(btn_export_csv)

        # Maliyete Ekle butonu (YENİ)
        btn_add_to_cost = QPushButton("💰 Seçili Pozları Projeye Ekle")
        btn_add_to_cost.setStyleSheet("background-color: #f57f17; color: white; font-weight: bold; padding: 10px;")
        btn_add_to_cost.clicked.connect(self.csv_add_to_cost_estimator)
        right_layout.addWidget(btn_add_to_cost)

        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        tab_layout.addWidget(splitter)

        # Verileri yükle
        self.load_and_display_csv_pozlar()

    def load_and_display_csv_pozlar(self):
        """CSV pozlarını yükle ve göster"""
        try:
            if len(self.csv_manager.poz_data) == 0:
                return

            all_pozlar = self.csv_manager.get_all_pozlar()
            self.csv_poz_data = all_pozlar
            self.csv_selected_pozlar = []
            self.display_csv_pozlar(all_pozlar)

        except Exception as e:
            QMessageBox.warning(self, "Hata", f"CSV yükleme hatası: {str(e)}")

    def display_csv_pozlar(self, data):
        """CSV pozlarını tabloda göster"""
        self.csv_poz_table.setRowCount(len(data))

        for row, item in enumerate(data):
            self.csv_poz_table.setItem(row, 0, QTableWidgetItem(str(item.get('poz_no', ''))))
            self.csv_poz_table.setItem(row, 1, QTableWidgetItem(str(item.get('description', ''))[:40]))
            self.csv_poz_table.setItem(row, 2, QTableWidgetItem(str(item.get('unit_price', ''))))
            self.csv_poz_table.setItem(row, 3, QTableWidgetItem(str(item.get('institution', ''))))

    def filter_csv_pozlar(self):
        """CSV pozlarını filtrele"""
        search_text = self.csv_search_input.text().lower()
        filtered_data = [
            item for item in self.csv_poz_data
            if search_text in str(item.get('poz_no', '')).lower() or
               search_text in str(item.get('description', '')).lower() or
               search_text in str(item.get('institution', '')).lower()
        ]
        self.display_csv_pozlar(filtered_data)

    def csv_add_selected_poz(self):
        """CSV'den seçili pozı ekle"""
        current_row = self.csv_poz_table.currentRow()
        if current_row < 0:
            return

        poz_no = self.csv_poz_table.item(current_row, 0).text()

        for item in self.csv_selected_pozlar:
            if item.get('poz_no') == poz_no:
                return

        for item in self.csv_poz_data:
            if item.get('poz_no') == poz_no:
                self.csv_selected_pozlar.append(item)
                break

        self.update_csv_selected_table()

    def csv_add_all_pozlar(self):
        """Tüm CSV pozlarını seç"""
        self.csv_selected_pozlar = self.csv_poz_data.copy()
        self.update_csv_selected_table()

    def csv_remove_selected_poz(self):
        """Seçili pozı kaldır"""
        current_row = self.csv_selected_table.currentRow()
        if current_row < 0:
            return

        poz_no = self.csv_selected_table.item(current_row, 0).text()
        self.csv_selected_pozlar = [item for item in self.csv_selected_pozlar if item.get('poz_no') != poz_no]
        self.update_csv_selected_table()

    def csv_remove_all_pozlar(self):
        """Tüm seçili pozları kaldır"""
        self.csv_selected_pozlar = []
        self.update_csv_selected_table()

    def update_csv_selected_table(self):
        """Seçili pozlar tablosunu güncelle"""
        self.csv_selected_table.setRowCount(len(self.csv_selected_pozlar))

        for row, item in enumerate(self.csv_selected_pozlar):
            self.csv_selected_table.setItem(row, 0, QTableWidgetItem(str(item.get('poz_no', ''))))
            self.csv_selected_table.setItem(row, 1, QTableWidgetItem(str(item.get('description', ''))[:40]))
            self.csv_selected_table.setItem(row, 2, QTableWidgetItem(str(item.get('unit_price', ''))))
            self.csv_selected_table.setItem(row, 3, QTableWidgetItem(str(item.get('institution', ''))))

        self.csv_info_label.setText(f"Seçili: {len(self.csv_selected_pozlar)} poz")

    def export_csv_selected(self):
        """Seçili pozları CSV'ye kaydet"""
        if not self.csv_selected_pozlar:
            QMessageBox.warning(self, "Uyarı", "Seçili poz yok!")
            return

        try:
            output_file = self.internal_pdf_dir / "seçili_pozlar.csv"
            df = pd.DataFrame(self.csv_selected_pozlar)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')

            QMessageBox.information(
                self,
                "Başarılı",
                f"{len(self.csv_selected_pozlar)} poz kaydedildi:\n{output_file.name}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

    def csv_add_to_cost_estimator(self):
        """Seçili CSV pozlarını maliyet hesabına aktar"""
        if not self.csv_selected_pozlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce tabloya poz ekleyin!")
            return

        if not self.cost_tab.current_project_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen 'Maliyet Hesabı' sekmesinde bir proje seçin!")
            self.tab_widget.setCurrentWidget(self.cost_tab)
            return

        added_count = 0
        for item in self.csv_selected_pozlar:
            poz_no = item.get('poz_no', '')
            desc = item.get('description', '')
            unit = item.get('unit', '')
            price_str = str(item.get('unit_price', '0'))
            
            # Fiyat parse (1.234,56 veya 1234.56)
            try:
                if ',' in price_str and '.' in price_str:
                     if price_str.find('.') < price_str.find(','):
                          price = float(price_str.replace('.', '').replace(',', '.'))
                     else:
                          price = float(price_str.replace(',', ''))
                elif ',' in price_str:
                     price = float(price_str.replace(',', '.'))
                else:
                     price = float(price_str)
            except:
                price = 0.0

            if self.cost_tab.add_item_from_external(poz_no, desc, unit, price):
                added_count += 1
        
        QMessageBox.information(self, "Başarılı", f"{added_count} adet poz projeye eklendi!")
        # self.tab_widget.setCurrentWidget(self.cost_tab)

    def update_loading_animation(self):
        """Loading animasyonunu güncelle"""
        if hasattr(self, 'file_label') and hasattr(self, 'base_loading_text'):
            dots = "." * (self.loading_dots % 4)
            self.file_label.setText(f"{self.base_loading_text}{dots}")
            self.loading_dots += 1


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern görünüm

    # Uygulama ikonu ayarla (tüm pencereler için)
    icon_path = Path(__file__).resolve().parent / "yaklasik_maliyet.png"
    if icon_path.exists():
        icon = QIcon()
        for size in [16, 24, 32, 48, 64, 128, 256]:
            icon.addFile(str(icon_path), QSize(size, size))
        app.setWindowIcon(icon)

    window = PDFSearchAppPyQt5()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    # Gerekli kütüphaneleri kontrol et
    try:
        import fitz
        import pandas as pd
        from PyQt5.QtWidgets import QApplication
    except ImportError as e:
        print(f"Eksik kütüphane: {e}")
        print("Kurulum için: pip install PyMuPDF pandas PyQt5")
        sys.exit(1)

    main()
