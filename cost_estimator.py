from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QInputDialog, QMessageBox, QGroupBox,
                             QFormLayout, QDialog, QDoubleSpinBox, QComboBox,
                             QLineEdit, QTextEdit, QDateEdit, QListWidget,
                             QListWidgetItem, QSplitter, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont
from database import DatabaseManager


class ProjectDialog(QDialog):
    """Proje ekleme/düzenleme dialogu"""

    def __init__(self, parent=None, project_data=None):
        super().__init__(parent)
        self.project_data = project_data
        self.setWindowTitle("Proje Düzenle" if project_data else "Yeni Proje Oluştur")
        self.setMinimumWidth(500)
        self.setup_ui()

        if project_data:
            self.load_project_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Şık bir Form Layout ve GroupBox
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 10px;
            }
            QLineEdit, QTextEdit, QDateEdit {
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
                border: 1px solid #2196F3;
            }
            QLabel {
                font-weight: bold;
                color: #495057;
                font-size: 10pt;
            }
        """)
        container_layout = QVBoxLayout(container)
        
        # Başlık
        header = QLabel("Proje Bilgileri")
        header.setStyleSheet("font-size: 14pt; color: #1976D2; border-bottom: 2px solid #1976D2; padding-bottom: 5px; margin-bottom: 10px;")
        container_layout.addWidget(header)

        # Form Grid Layout (Daha düzenli)
        grid = QGridLayout()
        grid.setSpacing(15)

        # 1. Satır: Proje Adı (Tam genişlik)
        grid.addWidget(QLabel("Proje Adı *:"), 0, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Proje adını girin (Zorunlu)")
        self.name_input.setStyleSheet("font-weight: bold;")
        grid.addWidget(self.name_input, 0, 1, 1, 3)

        # 2. Satır: Kod ve Tarih
        grid.addWidget(QLabel("Proje Kodu:"), 1, 0)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Örn: 2024-001")
        grid.addWidget(self.code_input, 1, 1)

        grid.addWidget(QLabel("Tarih:"), 1, 2)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        grid.addWidget(self.date_input, 1, 3)

        # 3. Satır: İşveren ve Yüklenici
        grid.addWidget(QLabel("İşveren:"), 2, 0)
        self.employer_input = QLineEdit()
        self.employer_input.setPlaceholderText("İdare veya şahıs adı")
        grid.addWidget(self.employer_input, 2, 1)

        grid.addWidget(QLabel("Yüklenici:"), 2, 2)
        self.contractor_input = QLineEdit()
        self.contractor_input.setPlaceholderText("Yüklenici firma adı")
        grid.addWidget(self.contractor_input, 2, 3)

        # 4. Satır: Yer (Tam genişlik)
        grid.addWidget(QLabel("Proje Yeri:"), 3, 0)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Şehir, İlçe veya adres")
        grid.addWidget(self.location_input, 3, 1, 1, 3)

        # 5. Satır: Açıklama
        grid.addWidget(QLabel("Açıklama:"), 4, 0)
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Proje hakkında notlar...")
        self.desc_input.setMaximumHeight(80)
        grid.addWidget(self.desc_input, 4, 1, 1, 3)

        container_layout.addLayout(grid)
        layout.addWidget(container)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 10, 10, 10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("background-color: #e0e0e0; color: #333; font-weight: bold; padding: 8px 20px; border-radius: 5px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Kaydet")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2; 
                color: white; 
                font-weight: bold; 
                padding: 8px 30px; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def load_project_data(self):
        """Mevcut proje verilerini forma yükle"""
        if not self.project_data:
            return

        self.name_input.setText(self.project_data.get('name', ''))
        self.code_input.setText(self.project_data.get('project_code', '') or '')
        self.employer_input.setText(self.project_data.get('employer', '') or '')
        self.contractor_input.setText(self.project_data.get('contractor', '') or '')
        self.location_input.setText(self.project_data.get('location', '') or '')
        self.desc_input.setPlainText(self.project_data.get('description', '') or '')

        # Tarih
        date_str = self.project_data.get('project_date', '')
        if date_str:
            date = QDate.fromString(date_str, "yyyy-MM-dd")
            if date.isValid():
                self.date_input.setDate(date)

    def get_data(self):
        """Form verilerini döndür"""
        return {
            'name': self.name_input.text().strip(),
            'project_code': self.code_input.text().strip(),
            'employer': self.employer_input.text().strip(),
            'contractor': self.contractor_input.text().strip(),
            'location': self.location_input.text().strip(),
            'project_date': self.date_input.date().toString("yyyy-MM-dd"),
            'description': self.desc_input.toPlainText().strip()
        }

    def accept(self):
        """Kaydet butonuna tıklandığında"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Uyarı", "Proje adı zorunludur!")
            return
        super().accept()


class ProjectManagerDialog(QDialog):
    """Proje yönetim dialogu - Liste ve düzenleme"""

    project_changed = pyqtSignal(int)  # Proje seçildiğinde sinyal

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db or DatabaseManager()
        self.selected_project_id = None
        self.setWindowTitle("Proje Yönetimi")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.load_projects()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #333;
            }
        """)

        # Üst başlık (Header)
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-bottom: 2px solid #BBDEFB;
                border-radius: 5px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        title_lbl = QLabel("📁 Proje Yönetimi")
        title_lbl.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1565C0;")
        header_layout.addWidget(title_lbl)
        
        subtitle_lbl = QLabel("Projelerinizi oluşturun, düzenleyin veya aktif çalışmak için seçin.")
        subtitle_lbl.setStyleSheet("color: #546E7A; font-size: 10pt;")
        header_layout.addStretch()
        header_layout.addWidget(subtitle_lbl)
        
        layout.addWidget(header_frame)

        # Splitter - Sol liste, sağ detay
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E0E0E0;
            }
        """)

        # Sol Panel - Proje Listesi
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 10, 10, 10)

        list_label = QLabel("Kayıtlı Projeler")
        list_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #455A64;")
        left_layout.addWidget(list_label)

        self.project_list = QListWidget()
        self.project_list.setFocusPolicy(Qt.NoFocus)
        self.project_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CFD8DC;
                border-radius: 4px;
                background-color: #FAFAFA;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #EEEEEE;
                color: #37474F;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
                border-left: 3px solid #1976D2;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
        """)
        self.project_list.currentRowChanged.connect(self.on_project_selected)
        left_layout.addWidget(self.project_list)

        # Liste butonları (CRUD)
        list_btn_layout = QHBoxLayout()
        list_btn_layout.setSpacing(10)

        add_btn = QPushButton("+ Yeni Proje")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; border-radius: 4px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #43A047; }
        """)
        add_btn.clicked.connect(self.add_project)
        list_btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("✎ Düzenle")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white; border-radius: 4px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1E88E5; }
        """)
        edit_btn.clicked.connect(self.edit_project)
        list_btn_layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Sil")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF5350; color: white; border-radius: 4px; padding: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #E53935; }
        """)
        del_btn.clicked.connect(self.delete_project)
        list_btn_layout.addWidget(del_btn)

        left_layout.addLayout(list_btn_layout)

        splitter.addWidget(left_widget)

        # Sağ Panel - Proje Detayı
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 0, 10)

        detail_label = QLabel("Proje Önizleme")
        detail_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #455A64;")
        right_layout.addWidget(detail_label)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background-color: white; 
                border: 1px solid #E0E0E0; 
                border-radius: 4px;
                padding: 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
                line-height: 1.5;
            }
        """)
        right_layout.addWidget(self.detail_text)

        splitter.addWidget(right_widget)
        
        # Splitter oranı
        splitter.setSizes([280, 420])
        
        layout.addWidget(splitter)
        
        # Alt Aksiyon Barı (Seç ve Kapat)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("padding: 8px 15px; border: 1px solid #ccc; border-radius: 4px; background-color: #fff;")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        self.select_btn = QPushButton("✅ Seç ve Çalışmaya Başla")
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7; 
                color: white; 
                font-weight: bold; 
                font-size: 11pt;
                padding: 10px 25px; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #5E35B1; }
        """)
        self.select_btn.clicked.connect(self.select_project)
        bottom_layout.addWidget(self.select_btn)
        
        layout.addLayout(bottom_layout)

    def load_projects(self):
        """Projeleri listele"""
        self.project_list.clear()
        projects = self.db.get_projects()

        for p in projects:
            item = QListWidgetItem(f"{p['name']}")
            item.setData(Qt.UserRole, p['id'])
            self.project_list.addItem(item)

        if projects:
            self.project_list.setCurrentRow(0)

    def on_project_selected(self, row):
        """Proje seçildiğinde detayları göster"""
        if row < 0:
            self.detail_text.clear()
            self.selected_project_id = None
            return

        item = self.project_list.item(row)
        project_id = item.data(Qt.UserRole)
        self.selected_project_id = project_id

        project = self.db.get_project(project_id)
        if project:
            details = f"""
<h2>{project.get('name', 'İsimsiz Proje')}</h2>
<hr>
<table style="width: 100%;">
<tr><td><b>Proje Kodu:</b></td><td>{project.get('project_code', '-') or '-'}</td></tr>
<tr><td><b>İşveren:</b></td><td>{project.get('employer', '-') or '-'}</td></tr>
<tr><td><b>Yüklenici:</b></td><td>{project.get('contractor', '-') or '-'}</td></tr>
<tr><td><b>Yer:</b></td><td>{project.get('location', '-') or '-'}</td></tr>
<tr><td><b>Proje Tarihi:</b></td><td>{project.get('project_date', '-') or '-'}</td></tr>
<tr><td><b>Oluşturulma:</b></td><td>{project.get('created_date', '-') or '-'}</td></tr>
<tr><td><b>Güncelleme:</b></td><td>{project.get('updated_date', '-') or '-'}</td></tr>
</table>
<br>
<b>Açıklama:</b><br>
{project.get('description', '-') or '-'}
"""
            self.detail_text.setHtml(details)

    def add_project(self):
        """Yeni proje ekle"""
        dialog = ProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.db.create_project(
                name=data['name'],
                description=data['description'],
                employer=data['employer'],
                contractor=data['contractor'],
                location=data['location'],
                project_code=data['project_code'],
                project_date=data['project_date']
            )
            self.load_projects()
            # Son eklenen projeyi seç
            self.project_list.setCurrentRow(0)

    def edit_project(self):
        """Seçili projeyi düzenle"""
        if self.selected_project_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir proje seçin!")
            return

        project = self.db.get_project(self.selected_project_id)
        dialog = ProjectDialog(self, project)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.db.update_project(
                self.selected_project_id,
                name=data['name'],
                description=data['description'],
                employer=data['employer'],
                contractor=data['contractor'],
                location=data['location'],
                project_code=data['project_code'],
                project_date=data['project_date']
            )
            self.load_projects()
            # Aynı projeyi seç
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.UserRole) == self.selected_project_id:
                    self.project_list.setCurrentRow(i)
                    break

    def delete_project(self):
        """Seçili projeyi sil"""
        if self.selected_project_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir proje seçin!")
            return

        reply = QMessageBox.question(
            self, 'Proje Silme',
            'Bu projeyi ve tüm kalemlerini silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db.delete_project(self.selected_project_id)
            self.selected_project_id = None
            self.load_projects()

    def select_and_close(self):
        """Projeyi seç ve dialogu kapat"""
        if self.selected_project_id is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir proje seçin!")
            return

        self.project_changed.emit(self.selected_project_id)
        self.accept()


class CostEstimator(QWidget):
    # Proje değişikliği için sinyal
    project_changed_signal = pyqtSignal(dict)  # Proje bilgisi dict olarak

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_project_id = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # --- Proje Bilgi Özeti (En üstte) ---

        # --- Proje Bilgi Özeti ---
        self.project_info_group = QGroupBox("Proje Bilgileri")
        info_layout = QHBoxLayout()

        self.info_labels = {
            'employer': QLabel("-"),
            'contractor': QLabel("-"),
            'location': QLabel("-"),
            'date': QLabel("-")
        }

        info_layout.addWidget(QLabel("İşveren:"))
        info_layout.addWidget(self.info_labels['employer'])
        info_layout.addWidget(QLabel(" | Yüklenici:"))
        info_layout.addWidget(self.info_labels['contractor'])
        info_layout.addWidget(QLabel(" | Yer:"))
        info_layout.addWidget(self.info_labels['location'])
        info_layout.addWidget(QLabel(" | Tarih:"))
        info_layout.addWidget(self.info_labels['date'])
        info_layout.addStretch()

        self.project_info_group.setLayout(info_layout)
        layout.addWidget(self.project_info_group)

        # --- Middle Section: Cost Table ---
        table_group = QGroupBox("Keşif Özeti / Metraj")
        table_layout = QVBoxLayout()

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels([
            'ID', 'Poz No', 'Açıklama', 'Birim', 'Miktar', 'Birim Fiyat', 'Tutar'
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.items_table.hideColumn(0)  # Hide ID
        self.items_table.itemChanged.connect(self.on_item_edited)
        table_layout.addWidget(self.items_table)

        # Total Summary
        summary_layout = QHBoxLayout()
        self.total_label = QLabel("Toplam Tutar: 0.00 TL")
        self.total_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #388E3C;")
        summary_layout.addStretch()
        summary_layout.addWidget(self.total_label)
        table_layout.addLayout(summary_layout)

        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # --- Bottom section: Actions ---
        actions_layout = QHBoxLayout()

        add_manual_btn = QPushButton("Manuel Kalem Ekle")
        add_manual_btn.clicked.connect(self.add_manual_item)
        actions_layout.addWidget(add_manual_btn)

        remove_item_btn = QPushButton("Seçili Kalemi Sil")
        remove_item_btn.clicked.connect(self.delete_selected_item)
        actions_layout.addWidget(remove_item_btn)

        actions_layout.addStretch()

        # Yaklaşık Maliyeti Sıfırla butonu
        reset_btn = QPushButton("⚠️ Maliyeti Sıfırla")
        reset_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; padding: 8px;")
        reset_btn.clicked.connect(self.reset_cost)
        actions_layout.addWidget(reset_btn)

        layout.addLayout(actions_layout)

        self.setLayout(layout)

        # Initial Load
        self.refresh_projects()

        # Son projeyi kontrol et ve yükle
        last_proj_id = self.db.get_setting("last_active_project_id")
        if last_proj_id:
            try:
                self.select_project_by_id(int(last_proj_id))
            except:
                pass

    def open_project_manager(self):
        """Proje yönetim penceresini aç"""
        dialog = ProjectManagerDialog(self, self.db)
        dialog.project_changed.connect(self.select_project_by_id)
        dialog.exec_()
        self.refresh_projects()

    def refresh_projects(self):
        """Projeleri veritabanından kontrol et"""
        # Combo box kaldırıldı, sadece mevcut projenin hala geçerli olup olmadığını kontrol edebiliriz
        if self.current_project_id:
            project = self.db.get_project(self.current_project_id)
            if not project:
                # Proje silinmişse çıkış yap
                self.close_current_project()
            else:
                # Bilgileri güncelle
                self.update_project_info()
                self.emit_project_changed()
        else:
             self.emit_project_changed()

    def create_new_project(self):
        dialog = ProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            project_id = self.db.create_project(
                name=data['name'],
                description=data['description'],
                employer=data['employer'],
                contractor=data['contractor'],
                location=data['location'],
                project_code=data['project_code'],
                project_date=data['project_date']
            )
            self.refresh_projects()
            # Yeni projeyi seç
            self.select_project_by_id(project_id)

    def delete_current_project(self):
        if not self.current_project_id:
            return

        reply = QMessageBox.question(self, 'Onay', 'Bu projeyi silmek istediğinize emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_project(self.current_project_id)
            self.refresh_projects()

    def close_current_project(self):
        """Aktif projeden çıkış yap"""
        self.current_project_id = None
        
        # Ayarı temizle
        self.db.set_setting("last_active_project_id", "")

        # Arayüzü temizle
        self.items_table.setRowCount(0)
        self.total_label.setText("Toplam Tutar: 0.00 TL")
        self.clear_project_info()
        
        # Sinyal gönder (Boş dict) -> Ana pencere sekmeleri kapatacak
        self.emit_project_changed()
        
        QMessageBox.information(self, "Bilgi", "Projeden çıkış yapıldı.")

    def select_project_by_id(self, project_id):
        """ID ile projeyi seç"""
        self.current_project_id = project_id
        # Ayarı kaydet
        self.db.set_setting("last_active_project_id", str(project_id))
        
        self.load_project_items()
        self.update_project_info()
        self.emit_project_changed()

    def update_project_info(self):
        """Proje bilgilerini güncelle"""
        if not self.current_project_id:
            self.clear_project_info()
            return

        project = self.db.get_project(self.current_project_id)
        if project:
            self.info_labels['employer'].setText(project.get('employer', '-') or '-')
            self.info_labels['contractor'].setText(project.get('contractor', '-') or '-')
            self.info_labels['location'].setText(project.get('location', '-') or '-')
            self.info_labels['date'].setText(project.get('project_date', '-') or '-')

    def clear_project_info(self):
        """Proje bilgilerini temizle"""
        for label in self.info_labels.values():
            label.setText("-")

    def emit_project_changed(self):
        """Proje değişikliği sinyali gönder"""
        if self.current_project_id:
            project = self.db.get_project(self.current_project_id)
            self.project_changed_signal.emit(project if project else {})
        else:
            self.project_changed_signal.emit({})

    def parse_tr_float(self, text):
        """Türkçe sayı formatını float'a çevir (1.234,56 -> 1234.56)"""
        if not text:
            return 0.0
        try:
            # Önce temizle
            text = str(text).strip()
            # 1.234,56 -> 1234.56
            if ',' in text and '.' in text:
                text = text.replace('.', '').replace(',', '.')
            elif ',' in text:
                text = text.replace(',', '.')
            return float(text)
        except ValueError:
            return 0.0

    def load_project_items(self):
        if not self.current_project_id:
            return

        items = self.db.get_project_items(self.current_project_id)
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(0)

        total_project_cost = 0

        for row, item in enumerate(items):
            self.items_table.insertRow(row)
            self.items_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(item.get('poz_no', ''))))
            self.items_table.setItem(row, 2, QTableWidgetItem(str(item.get('description', ''))))
            self.items_table.setItem(row, 3, QTableWidgetItem(str(item.get('unit', ''))))

            # Numeric items
            qty_item = QTableWidgetItem(f"{item.get('quantity', 0)}")
            price_item = QTableWidgetItem(f"{item.get('unit_price', 0)}")

            self.items_table.setItem(row, 4, qty_item)
            self.items_table.setItem(row, 5, price_item)

            total = item.get('total_price', 0)
            total_project_cost += total

            total_item = QTableWidgetItem(f"{total:.2f}")
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)  # Read only
            self.items_table.setItem(row, 6, total_item)

        self.items_table.blockSignals(False)
        self.total_label.setText(f"Toplam Tutar: {total_project_cost:,.2f} TL")

    def on_item_edited(self, item):
        row = item.row()
        col = item.column()

        # Only handle Quantity (4) or Unit Price (5) changes
        if col not in [4, 5]:
            return

        try:
            item_id = int(self.items_table.item(row, 0).text())
            qty = self.parse_tr_float(self.items_table.item(row, 4).text())
            price = self.parse_tr_float(self.items_table.item(row, 5).text())

            # Update DB
            self.db.update_project_item(item_id, quantity=qty, unit_price=price)

            # Update UI Total column
            total = qty * price
            self.items_table.blockSignals(True)
            self.items_table.item(row, 6).setText(f"{total:.2f}")
            self.items_table.blockSignals(False)

            # Recalculate Project Total
            self.recalc_total()

        except ValueError:
            pass

    def recalc_total(self):
        total = 0
        for i in range(self.items_table.rowCount()):
            try:
                val = self.parse_tr_float(self.items_table.item(i, 6).text())
                total += val
            except:
                pass
        self.total_label.setText(f"Toplam Tutar: {total:,.2f} TL")

    def add_manual_item(self):
        if not self.current_project_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir proje seçin!")
            return

        # Dialog for manual entry
        dialog = QDialog(self)
        dialog.setWindowTitle("Kalem Ekle")
        form = QFormLayout(dialog)

        # Inputs
        fields = {}

        fields['poz'] = QLineEdit()
        fields['desc'] = QLineEdit()
        fields['unit'] = QLineEdit("adet")
        fields['qty'] = QDoubleSpinBox()
        fields['qty'].setMaximum(9999999)
        fields['price'] = QDoubleSpinBox()
        fields['price'].setMaximum(9999999)

        form.addRow("Poz No:", fields['poz'])
        form.addRow("Açıklama:", fields['desc'])
        form.addRow("Birim:", fields['unit'])
        form.addRow("Miktar:", fields['qty'])
        form.addRow("Birim Fiyat:", fields['price'])

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Ekle")
        ok_btn.clicked.connect(dialog.accept)
        buttons.addWidget(ok_btn)
        form.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            self.db.add_project_item(
                self.current_project_id,
                fields['poz'].text(),
                fields['desc'].text(),
                fields['unit'].text(),
                fields['qty'].value(),
                fields['price'].value()
            )
            self.load_project_items()

    def add_item_from_external(self, poz_no, desc, unit, price):
        """Called from other modules (Search/Analysis) to add item to calculated cost"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen 'Maliyet Hesabı' sekmesinden bir proje seçin veya oluşturun!")
            return False

        try:
            # Price parsing if string
            if isinstance(price, str):
                price = float(price.replace('.', '').replace(',', '.'))

            self.db.add_project_item(
                self.current_project_id,
                poz_no,
                desc,
                unit,
                1.0,  # Default Quantity
                price
            )
            self.load_project_items()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ekleme hatası: {str(e)}")
            return False

    def delete_selected_item(self):
        row = self.items_table.currentRow()
        if row < 0:
            return

        item_id = int(self.items_table.item(row, 0).text())
        self.db.delete_project_item(item_id)
        self.items_table.removeRow(row)
        self.recalc_total()

    def reset_cost(self):
        """Yaklaşık maliyeti sıfırla - Tüm kalemleri sil"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Uyarı", "Aktif bir proje yok!")
            return

        reply = QMessageBox.question(
            self, 'Yaklaşık Maliyeti Sıfırla',
            'Bu projedeki TÜM kalemleri silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db.clear_project_items(self.current_project_id)
            self.load_project_items()
            QMessageBox.information(self, "Bilgi", "Yaklaşık maliyet sıfırlandı.")

    def get_current_project(self):
        """Mevcut proje bilgilerini döndür"""
        if self.current_project_id:
            return self.db.get_project(self.current_project_id)
        return None

    def has_active_project(self):
        """Aktif proje var mı?"""
        return self.current_project_id is not None
