"""
Poz Birim Fiyat Çıkarıcı Uygulaması - PyQt5 Versiyonu
Çevre Şehircilik ve diğer kurumlara ait birim fiyat PDF'lerinden
poz numarası, açıklama ve birim fiyatları çıkartır.
"""

import sys
import fitz  # PyMuPDF
import re
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QProgressBar, QGroupBox, QHeaderView, QSplitter,
    QTabWidget, QSpinBox, QCheckBox, QComboBox, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor


class PDFPozExtractor:
    """PDF dosyalarından poz bilgilerini çıkartır"""

    def __init__(self):
        self.extracted_data = []

    def extract_poz_from_pdf(self, pdf_path: str, institution: str = "") -> List[Dict]:
        """PDF'den poz bilgilerini çıkart"""
        try:
            doc = fitz.open(pdf_path)
            results = []

            # Eğer kurum adı belirtilmemişse PDF dosya adından al
            if not institution:
                institution = self._extract_institution_name(pdf_path)

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
                                        'font_size': span['size']
                                    })

                # Y koordinatına göre sırala (satırlar)
                text_items.sort(key=lambda x: x['y'])

                # Satırları grupla (aynı Y koordinatındakiler)
                rows = []
                current_row = []
                current_y = None
                tolerance = 3

                for item in text_items:
                    if current_y is None or abs(item['y'] - current_y) <= tolerance:
                        current_row.append(item)
                        current_y = item['y'] if current_y is None else current_y
                    else:
                        if current_row:
                            current_row.sort(key=lambda x: x['x'])
                            rows.append(current_row)
                        current_row = [item]
                        current_y = item['y']

                if current_row:
                    current_row.sort(key=lambda x: x['x'])
                    rows.append(current_row)

                # Satırları analiz et ve poz bilgilerini çıkart
                for row in rows:
                    poz_info = self._parse_poz_row(row, page_num + 1, institution)
                    if poz_info:
                        results.append(poz_info)

            doc.close()
            self.extracted_data = results
            return results

        except Exception as e:
            print(f"PDF çıkarma hatası: {str(e)}")
            return []

    def _extract_institution_name(self, pdf_path: str) -> str:
        """PDF dosyasının başlığından kurum adını çıkart"""
        try:
            doc = fitz.open(pdf_path)

            # İlk sayfa başlığını ara (üst kısım)
            for page_num in range(min(3, len(doc))):  # İlk 3 sayfada ara
                page = doc[page_num]
                text = page.get_text()
                lines = text.split('\n')

                # İlk 10 satırda başlık ara
                for line in lines[:10]:
                    line = line.strip()
                    if len(line) > 3:  # Çok kısa satırları atla
                        # Başlık gibi görünen satırları bul
                        # Genellikle büyük harfler, Türkçe karakterler içerir
                        if any(ord(c) > 127 for c in line) or (len(line) > 5 and line.isupper()):
                            # Kurum adı olabilecek metni temizle
                            institution = self._clean_institution_name(line)
                            if institution and len(institution) > 3:
                                doc.close()
                                return institution

            doc.close()

            # Başlık bulunamazsa dosya adından çıkart
            return self._extract_from_filename(pdf_path)

        except Exception as e:
            print(f"PDF başlığı çıkarma hatası: {str(e)}")
            return self._extract_from_filename(pdf_path)

    def _clean_institution_name(self, text: str) -> str:
        """Kuruma adını temizle"""
        # Boşlukları normalleştir
        text = re.sub(r'\s+', ' ', text).strip()

        # Yaygın gereksiz kelimeleri kaldır
        text = re.sub(r'(Birim Fiyat|Analiz|PDF|Ver|Sürüm|v\d+\.?\d*)', '', text, flags=re.IGNORECASE)

        # Satır sonu karakterlerini kaldır
        text = text.replace('\n', ' ').replace('\r', ' ')

        # Boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()

        return text if text else ""

    def _extract_from_filename(self, pdf_path: str) -> str:
        """PDF dosya adından kurum adını çıkart"""
        file_name = Path(pdf_path).stem  # Uzantı olmadan dosya adı

        # Dosya adından temizle
        institution = file_name.replace('_', ' ').replace('-', ' ')

        # Yaygın pattern'leri temizle
        institution = re.sub(r'[\d\s]+$', '', institution).strip()

        return institution if institution else "Bilinmiyor"

    def _parse_poz_row(self, row: List[Dict], page_num: int, institution: str = "") -> Dict or None:
        """Satırdan poz bilgisini çıkart"""
        if len(row) < 2:
            return None

        # Sütunları metin olarak birleştir
        columns = [item['text'] for item in row]

        # Poz numarası pattermleri
        poz_patterns = [
            r'(\d{2}\.\d{3}\.\d{4})',  # 15.490.1003
            r'(\d{2}\.\d{3})',         # 15.490
            r'(\d{1,2}\.\d{1,3}\.\d{1,4})'
        ]

        # İlk sütundan poz numarası bul
        poz_no = None
        first_col = columns[0] if columns else ""

        for pattern in poz_patterns:
            match = re.search(pattern, first_col)
            if match:
                poz_no = match.group(1)
                break

        if not poz_no:
            return None

        # İkinci sütundan açıklama al
        description = columns[1] if len(columns) > 1 else ""

        # Birim fiyat bul (genellikle son sütunlar)
        unit_price = None
        unit = None
        quantity = None

        # Tüm sütunlarda arama yap
        for col in columns[2:]:
            col = col.strip()

            # Birim kontrolü
            if not unit:
                unit_match = re.search(r'\b(m³|m²|m|kg|ton|adet|lt|da|gr|cm|mm|Sa|saat)\b', col, re.IGNORECASE)
                if unit_match:
                    unit = unit_match.group(1)
                    continue

            # Sayısal değer
            if re.search(r'\d+(?:[.,]\d+)?', col):
                # Fiyat ve miktar ayrıştır
                number_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)', col)
                if number_match:
                    number_str = number_match.group(1)

                    try:
                        # Türk sayı formatını normalize et
                        normalized = number_str.replace('.', '').replace(',', '.')
                        num_val = float(normalized)

                        # Değere göre sınıflandır
                        if num_val < 100 and not quantity:
                            quantity = number_str
                        elif not unit_price:
                            unit_price = number_str
                    except ValueError:
                        if not unit_price:
                            unit_price = number_str

        # En az poz no ve açıklama olmalı
        if poz_no and description:
            return {
                'poz_no': poz_no,
                'description': description.strip(),
                'unit': unit or '',
                'quantity': quantity or '',
                'unit_price': unit_price or '',
                'page': page_num,
                'institution': institution
            }

        return None

    def export_to_csv(self, output_path: str, data: List[Dict] = None) -> bool:
        """Çıkartılan verileri CSV'ye kaydet"""
        try:
            if data is None:
                data = self.extracted_data

            if not data:
                return False

            df = pd.DataFrame(data)

            # Sütun sırasını belirle (Kurum ilk sütun)
            columns = ['institution', 'poz_no', 'description', 'unit', 'quantity', 'unit_price', 'page']
            available_columns = [col for col in columns if col in df.columns]

            df = df[available_columns]

            # Türkçe başlıklar
            column_names = {
                'institution': 'Kurum',
                'poz_no': 'Poz No',
                'description': 'Açıklama',
                'unit': 'Birim',
                'quantity': 'Miktar',
                'unit_price': 'Birim Fiyatı (TL)',
                'page': 'Sayfa'
            }

            df = df.rename(columns=column_names)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')

            return True
        except Exception as e:
            print(f"CSV kaydetme hatası: {str(e)}")
            return False


class ExtractorThread(QThread):
    """PDF çıkarma işlemini ayrı thread'de çalıştır"""

    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, pdf_files: List[str]):
        super().__init__()
        self.pdf_files = pdf_files
        self.extractor = PDFPozExtractor()

    def run(self):
        try:
            all_results = []
            total_files = len(self.pdf_files)

            for idx, pdf_file in enumerate(self.pdf_files):
                try:
                    file_name = Path(pdf_file).name
                    self.status_update.emit(f"İşleniyor: {file_name}")

                    results = self.extractor.extract_poz_from_pdf(pdf_file)
                    all_results.extend(results)

                    progress = int((idx + 1) / total_files * 100)
                    self.progress.emit(progress)

                except Exception as e:
                    self.error.emit(f"Hata - {Path(pdf_file).name}: {str(e)}")

            self.finished.emit(all_results)
        except Exception as e:
            self.error.emit(f"Genel hata: {str(e)}")


class PozExtractorUI(QMainWindow):
    """Poz Çıkarıcı Uygulaması Ana Penceresi"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poz Birim Fiyat Çıkarıcı")
        self.setGeometry(100, 100, 1200, 700)

        self.pdf_files = []
        self.extracted_data = []
        self.extractor_thread = None
        self.pdf_folder = Path(__file__).parent / "PDF"
        self.current_csv_file = None

        self.init_ui()
        self.auto_load_pdf_folder()

        # Otomatik başla
        QTimer.singleShot(500, self.auto_extract_and_save)

    def init_ui(self):
        """UI bileşenlerini oluştur"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()

        # Başlık
        title = QLabel("PDF Poz Çıkarıcı - Birim Fiyat Yayınları")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Kontrol Paneli
        control_layout = QHBoxLayout()

        self.btn_open_csv = QPushButton("📂 CSV Dosyasını Aç")
        self.btn_open_csv.clicked.connect(self.open_csv_file)
        self.btn_open_csv.setEnabled(False)
        self.btn_open_csv.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:!disabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        control_layout.addWidget(self.btn_open_csv)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Seçili dosyalar
        files_group = QGroupBox("Seçili PDF Dosyaları")
        files_layout = QVBoxLayout()

        self.files_text = QTextEdit()
        self.files_text.setReadOnly(True)
        self.files_text.setMaximumHeight(80)
        files_layout.addWidget(self.files_text)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Sonuç Tablosu
        table_group = QGroupBox("Çıkartılan Pozlar")
        table_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Kurum', 'Poz No', 'Açıklama', 'Birim', 'Miktar', 'Birim Fiyatı (TL)', 'Sayfa'
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # Durum Bilgisi
        self.status_label = QLabel("Hazır")
        layout.addWidget(self.status_label)

        main_widget.setLayout(layout)

    def auto_load_pdf_folder(self):
        """PDF klasöründeki tüm PDF dosyalarını otomatik yükle"""
        if self.pdf_folder.exists():
            pdf_files = list(self.pdf_folder.glob("*.pdf"))
            if pdf_files:
                self.pdf_files = [str(f) for f in pdf_files]
                self.update_files_display()
                self.status_label.setText(f"✓ {len(pdf_files)} PDF dosyası otomatik yüklendi")

    def auto_extract_and_save(self):
        """Otomatik olarak pozları çıkart ve CSV'ye kaydet"""
        if not self.pdf_files:
            self.status_label.setText("❌ PDF dosyası bulunamadı")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Otomatik işlem başlıyor...")

        self.extractor_thread = ExtractorThread(self.pdf_files)
        self.extractor_thread.progress.connect(self.update_progress)
        self.extractor_thread.finished.connect(self.on_auto_extraction_finished)
        self.extractor_thread.error.connect(self.on_extraction_error)
        self.extractor_thread.status_update.connect(self.update_status)
        self.extractor_thread.start()

    def on_auto_extraction_finished(self, data):
        """Otomatik çıkarma tamamlandı, CSV'ye kaydet"""
        self.extracted_data = data
        self.display_results(data)

        # CSV dosyasını PDF klasöründe kaydet
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = self.pdf_folder / f"pozlar_{timestamp}.csv"

        extractor = PDFPozExtractor()
        if extractor.export_to_csv(str(csv_file), self.extracted_data):
            self.current_csv_file = csv_file
            self.btn_open_csv.setEnabled(True)

            self.progress_bar.setVisible(False)
            self.status_label.setText(
                f"✅ İşlem Tamamlandı! {len(data)} poz çıkartıldı.\n"
                f"CSV kaydedildi: {csv_file.name}"
            )

            # Başarı mesajı göster
            QMessageBox.information(
                self,
                "İşlem Başarılı",
                f"{len(data)} poz başarıyla çıkartıldı ve kaydedildi.\n\n"
                f"Dosya: {csv_file.name}\n"
                f"Konum: {csv_file.parent}\n\n"
                f"'CSV Dosyasını Aç' butonuna tıkla"
            )
        else:
            self.progress_bar.setVisible(False)
            self.status_label.setText("❌ CSV kaydedilemedi")
            QMessageBox.critical(self, "Hata", "CSV kaydedilemedi")

    def update_files_display(self):
        """Seçili dosyaları göster"""
        text = "\n".join([Path(f).name for f in self.pdf_files])
        self.files_text.setText(text)

    def update_progress(self, value):
        """Progress bar güncelle"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """Status mesajını güncelle"""
        self.status_label.setText(message)

    def on_extraction_error(self, error_msg):
        """Çıkarma sırasında hata"""
        QMessageBox.warning(self, "Hata", error_msg)

    def display_results(self, data: List[Dict]):
        """Sonuçları tabloda göster"""
        self.table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            items = [
                str(row_data.get('institution', '')),
                str(row_data.get('poz_no', '')),
                str(row_data.get('description', ''))[:50],
                str(row_data.get('unit', '')),
                str(row_data.get('quantity', '')),
                str(row_data.get('unit_price', '')),
                str(row_data.get('page', ''))
            ]

            for col_idx, item in enumerate(items):
                widget = QTableWidgetItem(item)
                self.table.setItem(row_idx, col_idx, widget)

    def open_csv_file(self):
        """CSV dosyasını Excel veya varsayılan uygulamada aç"""
        if not self.current_csv_file or not self.current_csv_file.exists():
            QMessageBox.warning(self, "Uyarı", "CSV dosyası bulunamadı")
            return

        try:
            import subprocess
            import platform

            if platform.system() == "Windows":
                # Windows'ta varsayılan programla aç
                subprocess.Popen(f'explorer /select,"{self.current_csv_file}"')
            elif platform.system() == "Darwin":
                # macOS'te Finder'da aç
                subprocess.Popen(["open", "-R", str(self.current_csv_file)])
            else:
                # Linux'te dosya yöneticisinde aç
                subprocess.Popen(["xdg-open", str(self.current_csv_file.parent)])

            self.status_label.setText(f"📂 CSV dosyası açılıyor: {self.current_csv_file.name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı: {str(e)}")


def main():
    app = QApplication(sys.argv)

    # Stil
    app.setStyle('Fusion')

    window = PozExtractorUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
