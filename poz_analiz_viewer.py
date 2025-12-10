"""
Poz Analiz Görüntüleyici
ANALIZ klasöründeki PDF'lerden tüm poz analizlerini çeken GUI uygulaması
Sol panel: Ana pozlar listesi
Sağ panel: Seçili pozun analiz detayları
"""

import sys
import fitz
import re
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QListWidget,
                             QListWidgetItem, QTableWidget, QTableWidgetItem,
                             QSplitter, QGroupBox, QMessageBox, QHeaderView,
                             QProgressBar, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor


class PozAnalyzer(QThread):
    """PDF'lerden poz analizlerini çeken sınıf"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, analiz_folder):
        super().__init__()
        self.analiz_folder = Path(analiz_folder)
        self.poz_analyses = {}

    def run(self):
        """PDF'leri analiz et"""
        pdf_files = sorted(self.analiz_folder.glob("*.pdf"))

        if not pdf_files:
            self.progress.emit("ANALIZ klasöründe PDF bulunamadı!")
            self.finished.emit({})
            return

        self.progress.emit(f"Bulunan {len(pdf_files)} PDF analiz ediliyor...")

        for pdf_file in pdf_files:
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
        # Ana poz tanısı: "Poz No" + "Analizin Adı" + 15/19.xxx kod
        # Böylece o satırdan sonrası kesinlikle alt-analiz olamaz
        next_poz_idx = len(lines)
        for next_idx in range(start_idx + 1, min(start_idx + 500, len(lines))):
            line_stripped = lines[next_idx].strip()
            if re.match(r'^(15|19)\.\d{3}\.\d{4}$', line_stripped):
                # Bu 15/19.xxx kodu, "Poz No" başlığının hemen sonrasında mı?
                # Eğer evet ise, bu yeni bir ana poz'dur
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
        # Limit: sonraki poz sınırına kadar, veya 500 satır
        i = start_idx + 1  # Başlangıç pozü atla
        while i < min(next_poz_idx, start_idx + 500, len(lines)):
            line = lines[i].strip()

            # Poz'un ÖZET bölümüne ulaştık demek ki daha fazla sub-analiz yok
            # Özet satırlarının belirtileri:
            # 1. "Malzeme + İşçilik" + "Tutar" (Analiz-1 formatı)
            # 2. "Sa Fiyatı" veya "m3 Fiyatı" vb (Analiz-2 formatı)
            line_lower = line.lower()

            # Analiz-1: Malzeme + İşçilik Tutar
            # Encoding sorunları nedeniyle "~" gibi kaçık karakterler olabilir
            # "Malzeme" + "Tutar" + herhangi bir garbled iş-çalışan sözcüğü
            if ("tutar" in line_lower and ("malzeme" in line_lower or "malz" in line_lower) and
                (any(variant in line_lower for variant in ["işçilik", "isçilik", "iscilik", "iş", "~"]) or
                 len(line) > 10 and "+" in line)):  # Fallback: Malzeme + ... pattern
                break

            # Analiz-2: unit + "Fiyatı" pattern (starts with "1 Sa Fiyatı", "1 m3 Fiyatı", etc)
            if ("fiyat" in line_lower and line.startswith("1 ") and
                any(unit in line_lower for unit in ["sa ", "m3 ", "m² ", "m2 ", "ton ", "kg ", "dk ", "gün ", "l ", "lt"])):
                break

            # Yeni pozun başlangıç işareti: "Poz No" başlığı + sonra bir 15/19.xxx kodu
            # Bu şekilde ana poz sınırını belirleyebiliriz
            if line == "Poz No" and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^(15|19)\.\d{3}\.\d{4}$', next_line):
                    # Yeni bir ana poz bulundu, çık
                    break

            # Malzeme/İşçilik başlıklarını tespit et
            # Encoding sorunları olabilir - "Isçilik" "Iscilik" gibi kaçık karakterler gelebilir
            line_lower = line.lower()
            is_type_header = (line in ["Malzeme", "İşçilik", "MALZEME", "İŞÇİLİK"] or  # Exact match
                             line_lower in ["malzeme", "işçilik"] or  # Lowercase
                             line_lower.startswith("malz") or  # Starts with "malz"
                             line_lower.startswith("isç") or  # İşçilik kaçık: "isçilik"
                             line_lower == "iscilik" or  # All kaçık
                             (len(line) < 15 and line_lower.startswith("is") and
                              len(line) > 4))  # "Is" + something

            if is_type_header and line.strip():
                current_type = line
                i += 1
                # Başlık altındaki açıklamalar/boş satırları atla (kod gelene kadar)
                while i < min(start_idx + 500, len(lines)):
                    if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', lines[i].strip()):
                        break  # Kod bulundu
                    i += 1
                continue

            # Alt analiz kodu tespiti (10.xxx, 19.xxx, hatta 15.xxx da olabilir)
            # Parantez içi satırlar (açıklamalar) kod değildir
            if line.startswith("(") or line.startswith(")"):
                i += 1
                continue

            if re.match(r'^(10|19|15)\.\d{3}\.\d{4}$', line):
                code = line

                # ANA POZ KONTROLÜ: Eğer bu kod, "Poz No" başlığının hemen sonrasında gelmişse, ana poz'dur
                # Alt-analiz değildir. Atla.
                # Geriye doğru kontrol et (son 3 satır içinde "Poz No" var mı?)
                is_main_poz = False
                for prev_idx in range(max(0, i - 3), i):
                    if lines[prev_idx].strip() == "Poz No":
                        is_main_poz = True
                        break

                if is_main_poz:
                    # Bu ana poz kodudur, alt analiz değildir
                    i += 1
                    continue

                name = ""
                unit = ""
                qty_str = ""
                price_str = ""

                # Sonraki satırlardan veri topla
                # Ad birden fazla satır olabilir, birim satırına kadar
                j = i + 1
                name_lines = []
                max_name_lines = 10  # Maksimum 10 satır ad olabilir

                while j < len(lines) and len(name_lines) < max_name_lines:
                    current = lines[j].strip()

                    # Boş satırı geç
                    if not current:
                        j += 1
                        continue

                    # AÇIKLAMA SATIRI TESPİTİ: Sadece sayılar ve ondalık nokta içeren satırlar açıklamadır
                    # Örnek: "0,000114" veya "17.000.000,00" - bunlar açıklama/amortisман satirlari
                    is_pure_number = current.replace(',', '').replace('.', '').replace('-', '').replace('+', '').isdigit()
                    if is_pure_number and len(current) < 20:
                        # Bu adın sonudur, birim var mı diye kontrol etme
                        j += 1
                        continue

                    # Birim satırı bulundu (Sa, Kg, m³ vb.)
                    # Bilinen birimler
                    known_units = ["Sa", "Kg", "m³", "m", "m²", "L", "dk", "Saat", "kg", "ha", "gün",
                                  "ton", "Ton", "mL", "cm", "mm", "km", "t", "hm"]
                    is_unit = current in known_units

                    # Veya çok kısa alfanumerik (1-3 harf, m³, m² gibi) - ama "Su", "Yal" isimlerini dışla
                    if not is_unit:
                        cleaned = current.replace('³', '').replace('²', '')
                        # Only if it looks like a unit (not a common Turkish word)
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
                        # Fiyat binler ayırıcısı ile olabilir (1.000,50 → 1000.50)
                        price = float(price_str.replace('.', '').replace(',', '.'))
                        total = qty * price

                        sub_analyses.append({
                            'type': current_type,  # "Malzeme" veya "İşçilik"
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


class PozAnalizViewer(QMainWindow):
    """Poz Analiz Görüntüleyici Uygulaması"""

    def __init__(self):
        super().__init__()
        self.poz_analyses = {}
        self.analiz_folder = Path(__file__).parent / "ANALIZ"
        self.setup_ui()
        self.load_analyses()

    def setup_ui(self):
        """UI kurulumu"""
        self.setWindowTitle("Poz Analiz Görüntüleyici")
        self.setGeometry(100, 100, 1400, 800)
        self.showMaximized()

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Başlık
        title = QLabel("ANALIZ PDF'lerinden Poz Analizleri")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

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
        right_layout = QVBoxLayout()

        # Başlık bilgileri
        header_group = QGroupBox("Poz Bilgileri")
        header_layout = QHBoxLayout()

        self.poz_no_label = QLabel("Poz No: -")
        poz_font = self.poz_no_label.font()
        poz_font.setBold(True)
        poz_font.setPointSize(12)
        self.poz_no_label.setFont(poz_font)
        header_layout.addWidget(self.poz_no_label)

        self.description_label = QLabel("Açıklama: -")
        header_layout.addWidget(self.description_label, 1)

        self.unit_label = QLabel("Birim: -")
        header_layout.addWidget(self.unit_label)

        header_group.setLayout(header_layout)
        right_layout.addWidget(header_group)

        # Alt analizler tablosu
        analyses_group = QGroupBox("Alt Analizler")
        analyses_layout = QVBoxLayout()

        self.analyses_table = QTableWidget()
        self.analyses_table.setColumnCount(7)
        self.analyses_table.setHorizontalHeaderLabels([
            'Tür', 'Poz No', 'Tanımı', 'Ölçü Birimi', 'Miktarı', 'Birim Fiyatı', 'Tutarı (TL)'
        ])
        self.analyses_table.horizontalHeader().setStretchLastSection(True)
        analyses_layout.addWidget(self.analyses_table)

        analyses_group.setLayout(analyses_layout)
        right_layout.addWidget(analyses_group, 1)

        # Özet bilgileri
        summary_group = QGroupBox("Fiyat Özeti")
        summary_layout = QHBoxLayout()

        self.subtotal_label = QLabel("Malzeme + İşçilik: -")
        self.subtotal_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.subtotal_label)

        self.overhead_label = QLabel("25% Yüklenici Kârı: -")
        self.overhead_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.overhead_label)

        self.total_price_label = QLabel("Toplam Tutarı: -")
        self.total_price_label.setStyleSheet("font-weight: bold; color: #388E3C; font-size: 12pt;")
        summary_layout.addWidget(self.total_price_label)

        self.unit_price_label = QLabel("1 m³ Fiyatı: -")
        self.unit_price_label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 13pt;")
        summary_layout.addWidget(self.unit_price_label)

        summary_group.setLayout(summary_layout)
        right_layout.addWidget(summary_group)

        right_panel.setLayout(right_layout)

        # Splitter'a panelleri ekle
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 900])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter, 1)

        # Alt butonlar
        buttons_layout = QHBoxLayout()

        self.export_btn = QPushButton("📊 Tümünü Excel'e Aktar")
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        buttons_layout.addWidget(self.export_btn)

        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.refresh_btn.clicked.connect(self.load_analyses)
        buttons_layout.addWidget(self.refresh_btn)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        central_widget.setLayout(main_layout)

    def load_analyses(self):
        """PDF'lerden analizleri yükle"""
        self.progress_bar.setVisible(True)
        self.status_label.setText("PDF'ler analiz ediliyor...")
        self.poz_list.clear()

        self.analyzer = PozAnalyzer(self.analiz_folder)
        self.analyzer.progress.connect(self.on_progress)
        self.analyzer.finished.connect(self.on_analyses_loaded)
        self.analyzer.start()

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
        subtotal_formatted = f"{total_amount:,.2f}".replace(',', '.')  # US format
        subtotal_formatted = subtotal_formatted.replace('.', '@').replace(',', '.').replace('@', ',')  # Turkish format
        self.subtotal_label.setText(f"Malzeme + İşçilik: {subtotal_formatted} TL")

        # 25% Yüklenici Kârı hesapla
        overhead_amount = total_amount * 0.25
        overhead_formatted = f"{overhead_amount:,.2f}".replace(',', '.')  # US format
        overhead_formatted = overhead_formatted.replace('.', '@').replace(',', '.').replace('@', ',')  # Turkish format
        self.overhead_label.setText(f"25% Yüklenici Kârı: {overhead_formatted} TL")

        # Toplam Tutarı = Malzeme+İşçilik + 25% Kârı
        final_total = total_amount + overhead_amount
        formatted_final_total = f"{final_total:,.2f}".replace(',', '.')  # US format
        formatted_final_total = formatted_final_total.replace('.', '@').replace(',', '.').replace('@', ',')  # Turkish format

        self.total_price_label.setText(f"Toplam Tutarı: {formatted_final_total} TL")
        self.unit_price_label.setText(f"1 {data['unit']} Fiyatı: {summary.get('unit_price', '-')} TL")

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


def main():
    app = QApplication(sys.argv)
    window = PozAnalizViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
