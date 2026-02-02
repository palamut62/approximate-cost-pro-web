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
# Removed PyQt5 and UI imports for backend compatibility
from services.pdf_engine import PDFSearchEngine
class CSVDataManager:
    """PDF klasöründeki CSV dosyalarından pozları yönetir"""

    def __init__(self):
        # Path pointing to approximate_cost/ANALIZ
        self.csv_folder = Path(__file__).parent.parent.parent / "ANALIZ"
        if not self.csv_folder.exists():
            # Fallback to backend/PDF just in case
             self.csv_folder = Path(__file__).parent.parent / "PDF"
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


class LoadingManager:
    """PDF ve CSV yükleme işlemlerini yöneten sınıf (Sync/Async wrapper)"""
    def __init__(self, search_engine, files):
        self.search_engine = search_engine
        self.files = files
        self._stop_requested = False
    
    def stop(self):
        self._stop_requested = True
    
    def run(self, progress_callback=None):
        loaded_count = 0
        for i, file_path in enumerate(self.files):
            if self._stop_requested:
                break
            try:
                file_name = Path(file_path).name
                if progress_callback:
                    progress_callback(file_name, i + 1, len(self.files))

                if self.search_engine.load_pdf(str(file_path)):
                    loaded_count += 1

            except Exception as e:
                print(f"Hata - {file_name}: {str(e)}")
        
        return loaded_count

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


class PozAnalyzer:
    """PDF'lerden poz analizlerini çeken sınıf"""

    def __init__(self, analiz_folder):
        self.analiz_folder = Path(analiz_folder)
        self.poz_analyses = {}
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self, progress_callback=None):
        """PDF'leri analiz et"""
        pdf_files = sorted(self.analiz_folder.glob("*.pdf"))

        if not pdf_files:
            print("ANALIZ klasöründe PDF bulunamadı!")
            return {}

        print(f"Bulunan {len(pdf_files)} PDF analiz ediliyor...")

        for i, pdf_file in enumerate(pdf_files):
            if self._stop_requested:
                break
            if progress_callback:
                progress_callback(f"İşleniyor: {pdf_file.name}", i+1, len(pdf_files))
            
            self._extract_from_pdf(str(pdf_file))

        print(f"Toplam {len(self.poz_analyses)} poz analizi bulundu")
        return self.poz_analyses

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


class CSVLoader:
    """CSV ve PDF dosyalarını yükleyen sınıf (Cache destekli)"""
    
    def __init__(self, csv_folder):
        self.csv_folder = csv_folder
        self._stop_requested = False
        self.cache_dir = Path(__file__).parent / "cache"
        
        # Unique cache file per folder to avoid collisions
        folder_name = csv_folder.name if hasattr(csv_folder, 'name') else 'default'
        folder_hash = hashlib.md5(str(csv_folder).encode()).hexdigest()[:8]
        self.cache_file = self.cache_dir / f"poz_data_cache_{folder_name}_{folder_hash}.json"

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

    def run(self, progress_callback=None):
        try:
            # Önce cache'i kontrol et
            if progress_callback: progress_callback("Cache kontrol ediliyor...")
            cached_data, cached_files, cache_time = self.load_cache()

            if cached_data is not None:
                if progress_callback: progress_callback(f"Cache'den yüklendi ({len(cached_data)} poz)")
                return cached_data, len(cached_data), cached_files

            poz_data = {}
            loaded_files = []

            if not self.csv_folder.exists():
                print(f"PDF klasörü bulunamadı: {self.csv_folder}")
                return {}, 0, []

            # CSV dosyalarını yükle
            csv_files = list(self.csv_folder.glob("*.csv"))
            if progress_callback: progress_callback(f"CSV dosyaları taranıyor... ({len(csv_files)} dosya)")

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
            if progress_callback: progress_callback(f"PDF dosyaları taranıyor... ({len(pdf_files)} dosya)")

            for pdf_path in pdf_files:
                if self._stop_requested:
                    break
                try:
                    if progress_callback: progress_callback(f"PDF yükleniyor: {pdf_path.name}")
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

            return poz_data, len(poz_data), loaded_files

        except Exception as e:
            print(f"Hata: {str(e)}")
            return {}, 0, []

    def extract_pozlar_from_pdf(self, pdf_path, poz_data):
        """PDF dosyasından pozları çıkar - Koordinat tabanlı satır birleştirme ile"""
        try:
            doc = fitz.open(pdf_path)
            poz_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Koordinat tabanlı metin çıkarma ("dict")
                blocks = page.get_text("dict")
                
                # Tüm metin parçalarını düz bir listede topla
                text_items = []
                for block in blocks["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span['text'].strip()
                                if text:
                                    text_items.append({
                                        'text': text,
                                        'y': span['bbox'][1], # Y koordinatı (üst)
                                        'x': span['bbox'][0], # X koordinatı (sol)
                                        'height': span['bbox'][3] - span['bbox'][1]
                                    })

                # Y koordinatına göre sırala
                text_items.sort(key=lambda item: item['y'])

                # Satırları oluştur (Y toleransına göre grupla)
                rows = []
                if text_items:
                    current_row = [text_items[0]]
                    current_y = text_items[0]['y']
                    # Yüksekliğin yarısı kadar tolerans
                    tolerance = text_items[0]['height'] / 2 if text_items[0]['height'] > 0 else 5
                    
                    for item in text_items[1:]:
                        if abs(item['y'] - current_y) <= tolerance:
                            current_row.append(item)
                        else:
                            # Satırı X'e göre sırala ve birleştir
                            current_row.sort(key=lambda i: i['x'])
                            rows.append(" ".join([i['text'] for i in current_row]))
                            
                            current_row = [item]
                            current_y = item['y']
                            tolerance = item['height'] / 2 if item['height'] > 0 else 5
                    
                    # Son satırı ekle
                    if current_row:
                        current_row.sort(key=lambda i: i['x'])
                        rows.append(" ".join([i['text'] for i in current_row]))

                # Oluşturulan satırları işle
                for line in rows:
                    if not line:
                        continue

                    # Poz numarası pattern'leri
                    poz_patterns = [
                        r'^(\d{2}\.\d{3}\.\d{4})',  # 10.110.1003
                        r'^(\d{2}\.\d{3})',         # 02.017
                        r'^([A-Z]{1,3}\.\d{2,3}\.\d{3})',  # Y.15.140
                        r'^([A-Z]{2,3}\.\d{3})',  # MSB.700
                        r'^(\d{3}-\d{3})', # KGM: 715-104
                        r'^([A-Z0-9/]+\.\d+)', # Genel: KGM/123.456
                        r'(\d{2}\.\d{3}\.\d{4})',  # match anywhere
                        r'(\d{3}-\d{3})',  # match anywhere
                    ]

                    poz_no = None
                    for pattern in poz_patterns:
                        match = re.search(pattern, line.strip()) # Use search instead of match for robustness
                        if match:
                            poz_no = match.group(1)
                            break

                            break

                    if poz_no:
                        # Existing poz check with "Better Description" strategy
                        if poz_no in poz_data:
                            existing_desc = poz_data[poz_no].get('description', '')
                            # If we are about to parse a line, we don't know the description yet.
                            # We must parse it first, THEN decide to update.
                            pass
                        
                        # ÇŞB formatında ise aynı satırda veya alt satırda olur.
                        
                        description_lines = []
                        unit = ""
                        unit_price = "0,00"
                        
                        # Pozun olduğu satırdan kalan kısmı al
                        try:
                            start_idx = line.find(poz_no)
                            if start_idx != -1:
                                same_line_remaining = line[start_idx + len(poz_no):].strip()
                            else:
                                same_line_remaining = line.replace(poz_no, "").strip()
                        except:
                            same_line_remaining = line.replace(poz_no, "").strip()
                            
                        # Eğer kalan kısımda "Analizin Adı" gibi başlıklar varsa temizle
                        same_line_remaining = re.sub(r'Analizin Adı', '', same_line_remaining, flags=re.IGNORECASE).strip()
                        
                        if same_line_remaining:
                             description_lines.append(same_line_remaining)

                        # Alt satırları tara (ÇŞB'de açıklama alt satırlara iner)
                        current_idx = rows.index(line)
                        price_found = False
                        
                        # Sonraki 15 satıra bak
                        for k in range(1, 15):
                            if current_idx + k >= len(rows):
                                break
                            
                            next_line = rows[current_idx + k].strip()
                            
                            # Yeni bir poz no başladıysa dur
                            is_new_poz = False
                            for pat in poz_patterns:
                                if re.search(pat, next_line):
                                    is_new_poz = True
                                    break
                            if is_new_poz:
                                break
                            
                            # Tanımı, Ölçü Birimi gibi başlıkları atla/durdur
                            if "Tanımı" in next_line or "Ölçü Birimi" in next_line and len(next_line) < 20:
                                continue
                                
                            # Fiyat satırı mı?
                            price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|$)', next_line)
                            # ÇŞB analizlerinde fiyat satırı altında "Malzeme:" yazar, oraya gelmeden fiyatı buluruz.
                            if "Malzeme:" in next_line or "İşçilik:" in next_line:
                                # Analiz detayına girdik, açıklamayı bitir.
                                break
                                
                            # Bu satır açıklamanın devamı mı?
                            # "(Nakliye dahil)" gibi kritik bilgiler burada olabilir.
                            description_lines.append(next_line)
                            
                        full_description = " ".join(description_lines)
                        
                        # Temizlik
                        # Fiyatı ve gereksiz headerları temizle
                        clean_desc = full_description
                        # ... cleaning logic can be added here if needed
                        
                        description = clean_desc

                        unit = ""
                        unit_price = "0,00"
                        
                        # Mevcut satırı kontrol et (ÇŞB Formatı)
                        try:
                            start_idx = line.find(poz_no)
                            if start_idx != -1:
                                same_line_remaining = line[start_idx + len(poz_no):].strip()
                            else:
                                same_line_remaining = line.replace(poz_no, "").strip()
                        except:
                            same_line_remaining = line.replace(poz_no, "").strip()

                        # Fiyat kontrolü (Aynı satırda)
                        price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:TL|₺|$)', same_line_remaining)
                        
                        if price_match and len(same_line_remaining) > 10:
                            # ÇŞB Formatı (Aynı satırda veri var)
                            # Fiyatı al
                            unit_price = price_match.group(1)
                            # Açıklamayı al (fiyattan öncesi)
                            description = same_line_remaining[:price_match.start()].strip()
                            
                            # Birimi bul
                            unit_patterns = ['m³', 'm²', 'm2', 'm3', 'ton', 'kg', 'adet', 'lt', 'sa', 'gün', 'ay', 'ad', 'km']
                            for u in unit_patterns:
                                # Safe units for partial match (symbols)
                                safe_to_partial = u in ['m³', 'm²', 'm2', 'm3']
                                
                                pattern = r'\b' + re.escape(u) + r'\b'
                                if safe_to_partial:
                                    pattern = re.escape(u) # Relaxed for symbols
                                    
                                if re.search(pattern, description, re.IGNORECASE):
                                    unit = u
                                    break
                                    
                            # Eğer stringler yapışık ise (örn: ...m³Depoda...)
                            # Açıklamayı temizlerken birimi de ayırabiliriz
                            if unit and unit in description:
                                # unit'in bitişinden sonra boşluk yoksa ekle (Görüntüleme için)
                                pass # Şimdilik elleme, sadece metadata düzelsin yeter
                        else:
                            # KGM Formatı (Alt satırlara bak)
                            desc_lines = []
                            found_price = False
                            
                            # Sonraki 10 satıra bak
                            current_idx = rows.index(line)
                            for k in range(1, 10):
                                if current_idx + k >= len(rows):
                                    break
                                
                                next_line = rows[current_idx + k].strip()
                                
                                # Yeni bir poz no başladıysa dur
                                is_new_poz = False
                                for pattern in poz_patterns:
                                    if re.match(pattern, next_line):
                                        is_new_poz = True
                                        break
                                if is_new_poz:
                                    break

                                # Fiyat ve Birim Satırı mı? (Örn: "ad 543,24")
                                price_candidates = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))', next_line)
                                if price_candidates:
                                    # Sayısal doğrulama
                                    try:
                                        p_val = float(price_candidates[-1].replace('.', '').replace(',', '.'))
                                        if p_val > 0 and (len(next_line.strip()) < 20 or next_line.strip().endswith(price_candidates[-1])):
                                            # Evet bu fiyat satırı
                                            unit_price = price_candidates[-1]
                                            found_price = True
                                            
                                            # Bu satırda birim var mı?
                                            remaining_in_price_line = next_line.replace(unit_price, "").strip()
                                            if remaining_in_price_line:
                                                unit = remaining_in_price_line
                                            break
                                    except:
                                        pass
                                
                                # Sadece Birim Satırı mı? (Örn: "ad", "Sa")
                                if len(next_line) < 10 and not found_price:
                                    known_units = ['m³', 'm²', 'm2', 'm3', 'ton', 'kg', 'adet', 'lt', 'sa', 'gün', 'ay', 'ad', 'km', 'saat']
                                    if next_line.lower() in known_units:
                                        unit = next_line
                                        continue # Sonraki satır fiyat olabilir

                                # Açıklama parçası
                                desc_lines.append(next_line)

                            description = " ".join(desc_lines) if desc_lines else same_line_remaining

                        # Kurum Tahmini
                        institution = 'ÇŞB'
                        if poz_no.startswith('10.') or poz_no.startswith('15.') or poz_no.startswith('25.'):
                             institution = 'ÇŞB'
                        elif poz_no.startswith('MSB'):
                             institution = 'MSB'
                        elif poz_no.startswith('KGM') or '-' in poz_no:
                             institution = 'KGM'
                        elif poz_no.startswith('İLLER'):
                             institution = 'İLLER'

                        # Karar verme: Güncelle veya Atla
                        should_update = True
                        if poz_no in poz_data:
                            old_desc = poz_data[poz_no].get('description', '')
                            # Eğer yeni açıklama çok daha uzunsa (Main Definition ise) güncelle
                            if len(description) > len(old_desc) + 20:
                                should_update = True
                            # Eğer mevcut açıklama zaten uzunsa (Definition ise) ve yeni gelen kısaysa (Reference), güncelleme
                            elif len(old_desc) > len(description) + 20:
                                should_update = False
                            # Benzer uzunlukta? İlk gelen kalsın (First match wins for similar)
                            else:
                                should_update = False
                                
                        if should_update:
                             poz_info = {
                                 'poz_no': poz_no,
                                 'description': description,
                                 'unit': unit,
                                 'unit_price': unit_price,
                                 'institution': institution, # Use the determined institution
                                 'source_file': pdf_path.name
                             }
                             poz_data[poz_no] = poz_info
                        poz_count += 1

            doc.close()
            return poz_count

        except Exception as e:
            print(f"PDF poz çıkarma hatası {pdf_path}: {e}")
            return 0

# Removed ExtractorWorkerThread and BackgroundExtractorThread as they depend on PyQt5.
# Data extraction logic is handled by CSVLoader and PDFSearchEngine.

