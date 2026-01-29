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


from core.pdf_engine import PDFSearchEngine
from core.data_manager import CSVDataManager, LoadingThread, BackgroundExtractorThread, ExtractorWorkerThread, CSVLoaderThread
from ui.widgets import PozViewerWidget, AnalysisTableWidget
from ui.csv_widget import CSVSelectionWidget
from ui.data_explorer import DataExplorerWidget
from ui.dialogs import SettingsDialog

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

        # Data Explorer'ı güncelle
        if hasattr(self, 'data_explorer'):
             self.data_explorer.load_initial_data()

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

        # Veri Gezgini (CSV + PDF)
        self.data_explorer = DataExplorerWidget(self)
        self.tab_widget.addTab(self.data_explorer, "🗂️ Veri Kaynakları")
        
        # Uyumluluk için referanslar (Diğer widget'lar parent_app üzerinden erişiyor)
        self.poz_viewer_tab = self.data_explorer.pdf_viewer
        self.csv_widget = self.data_explorer.csv_selector
        
        # İlk yükleme
        QTimer.singleShot(1000, self.data_explorer.load_initial_data)

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


    def update_loading_animation(self):
        """Loading animasyonunu güncelle"""
        if hasattr(self, 'file_label') and hasattr(self, 'base_loading_text'):
            dots = "." * (self.loading_dots % 4)
            self.file_label.setText(f"{self.base_loading_text}{dots}")
            self.loading_dots += 1
