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


from core.data_manager import PozAnalyzer
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
