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


from database import DatabaseManager
from ui.widgets import AnalysisTableWidget
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
