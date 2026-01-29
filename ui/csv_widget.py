
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLineEdit, QSplitter, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import pandas as pd
from pathlib import Path

class CSVSelectionWidget(QWidget):
    """CSV Poz Seçim ve Yönetim Widget'ı"""
    
    def __init__(self, parent_app=None):
        super().__init__()
        self.parent_app = parent_app
        self.csv_poz_data = []
        self.csv_selected_pozlar = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Üst bilgi bölümü
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
        self.loaded_files_label.setMinimumHeight(60)
        info_layout.addWidget(self.loaded_files_label, stretch=2)
        
        # Yenile butonu (sağ)
        refresh_btn = QPushButton("🔄 Verileri Yenile")
        refresh_btn.setToolTip("PDF klasöründeki tüm dosyaları yeniden tara")
        refresh_btn.clicked.connect(self.force_reload_poz_data)
        refresh_btn.setFixedWidth(130)
        info_layout.addWidget(refresh_btn)
        
        layout.addLayout(info_layout)
        
        # Arama bölümü
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Ara:"))
        self.csv_search_input = QLineEdit()
        self.csv_search_input.setPlaceholderText("Poz No, Açıklama veya Kurum ara...")
        self.csv_search_input.textChanged.connect(self.filter_csv_pozlar)
        search_layout.addWidget(self.csv_search_input)
        layout.addLayout(search_layout)
        
        # Splitter ile 2 bölüm
        splitter = QSplitter(Qt.Horizontal)
        
        # SOL: CSV Pozları
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("CSV Pozları (Çift Tıkla veya → Seç)"))
        
        self.csv_poz_table = QTableWidget()
        self.csv_poz_table.setColumnCount(4)
        self.csv_poz_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.csv_poz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.csv_poz_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.csv_poz_table.doubleClicked.connect(self.add_selected_poz)
        left_layout.addWidget(self.csv_poz_table)
        
        # Ok butonları
        button_layout = QHBoxLayout()
        btn_add = QPushButton("➜ Seç (→)")
        btn_add.clicked.connect(self.add_selected_poz)
        button_layout.addWidget(btn_add)
        
        btn_add_all = QPushButton("⟹ Tümünü Seç")
        btn_add_all.clicked.connect(self.add_all_pozlar)
        button_layout.addWidget(btn_add_all)
        button_layout.addStretch()
        left_layout.addLayout(button_layout)
        
        splitter.addWidget(left_widget)
        
        # SAĞ: Seçili Pozlar
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Seçili Pozlar"))
        
        self.csv_selected_table = QTableWidget()
        self.csv_selected_table.setColumnCount(4)
        self.csv_selected_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.csv_selected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.csv_selected_table.setSelectionBehavior(QTableWidget.SelectRows)
        right_layout.addWidget(self.csv_selected_table)
        
        # Çıkar butonları
        remove_layout = QHBoxLayout()
        btn_remove = QPushButton("← Çıkar (←)")
        btn_remove.clicked.connect(self.remove_selected_poz)
        remove_layout.addWidget(btn_remove)
        
        btn_remove_all = QPushButton("⟸ Tümünü Çıkar")
        btn_remove_all.clicked.connect(self.remove_all_pozlar)
        remove_layout.addWidget(btn_remove_all)
        remove_layout.addStretch()
        right_layout.addLayout(remove_layout)
        
        # Bilgi etiketi
        self.csv_info_label = QLabel("Seçili: 0 poz")
        right_layout.addWidget(self.csv_info_label)
        
        # Export butonu
        btn_export_csv = QPushButton("💾 Seçili Pozları CSV'ye Kaydet")
        btn_export_csv.clicked.connect(self.export_csv_selected)
        right_layout.addWidget(btn_export_csv)
        
        # Maliyete Ekle butonu
        btn_add_to_cost = QPushButton("💰 Seçili Pozları Projeye Ekle")
        btn_add_to_cost.setStyleSheet("background-color: #f57f17; color: white; font-weight: bold; padding: 10px;")
        btn_add_to_cost.clicked.connect(self.add_to_cost_estimator)
        right_layout.addWidget(btn_add_to_cost)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
    def load_data(self):
        """CSV pozlarını yükle ve göster"""
        if not self.parent_app or not hasattr(self.parent_app, 'csv_manager'):
            return
            
        try:
            if len(self.parent_app.csv_manager.poz_data) == 0:
                return

            all_pozlar = self.parent_app.csv_manager.get_all_pozlar()
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

    def add_selected_poz(self):
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

        self.update_selected_table()

    def add_all_pozlar(self):
        """Tüm CSV pozlarını seç"""
        self.csv_selected_pozlar = self.csv_poz_data.copy()
        self.update_selected_table()

    def remove_selected_poz(self):
        """Seçili pozı kaldır"""
        current_row = self.csv_selected_table.currentRow()
        if current_row < 0:
            return

        poz_no = self.csv_selected_table.item(current_row, 0).text()
        self.csv_selected_pozlar = [item for item in self.csv_selected_pozlar if item.get('poz_no') != poz_no]
        self.update_selected_table()

    def remove_all_pozlar(self):
        """Tüm seçili pozları kaldır"""
        self.csv_selected_pozlar = []
        self.update_selected_table()

    def update_selected_table(self):
        """Seçili pozlar tablosunu güncelle"""
        self.csv_selected_table.setRowCount(len(self.csv_selected_pozlar))
        for row, item in enumerate(self.csv_selected_pozlar):
            self.csv_selected_table.setItem(row, 0, QTableWidgetItem(str(item.get('poz_no', ''))))
            self.csv_selected_table.setItem(row, 1, QTableWidgetItem(str(item.get('description', ''))[:40]))
            self.csv_selected_table.setItem(row, 2, QTableWidgetItem(str(item.get('unit_price', ''))))
            self.csv_selected_table.setItem(row, 3, QTableWidgetItem(str(item.get('institution', ''))))

        self.csv_info_label.setText(f"Seçili: {len(self.csv_selected_pozlar)} poz")

    def force_reload_poz_data(self):
        """Ana uygulamadaki force_reload_poz_data metodunu çağırır"""
        if self.parent_app and hasattr(self.parent_app, 'force_reload_poz_data'):
            self.parent_app.force_reload_poz_data()
            
    def export_csv_selected(self):
        if not self.csv_selected_pozlar:
            QMessageBox.warning(self, "Uyarı", "Seçili poz yok!")
            return

        try:
            if self.parent_app and hasattr(self.parent_app, 'internal_pdf_dir'):
                output_file = self.parent_app.internal_pdf_dir / "seçili_pozlar.csv"
                df = pd.DataFrame(self.csv_selected_pozlar)
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Başarılı", f"{len(self.csv_selected_pozlar)} poz kaydedildi:\n{output_file.name}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

    def add_to_cost_estimator(self):
        """Seçili CSV pozlarını maliyet hesabına aktar"""
        if not self.parent_app:
            return
            
        if not self.csv_selected_pozlar:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce tabloya poz ekleyin!")
            return

        if not self.parent_app.cost_tab.current_project_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen 'Maliyet Hesabı' sekmesinde bir proje seçin!")
            self.parent_app.tab_widget.setCurrentWidget(self.parent_app.cost_tab)
            return

        added_count = 0
        for item in self.csv_selected_pozlar:
            poz_no = item.get('poz_no', '')
            desc = item.get('description', '')
            unit = item.get('unit', '')
            price_str = str(item.get('unit_price', '0'))
            
            # Fiyat parse
            try:
                if ',' in price_str:
                    price_val = float(price_str.replace('.', '').replace(',', '.'))
                else:
                    price_val = float(price_str)
            except:
                price_val = 0.0

            if self.parent_app.cost_tab.add_item_from_external(poz_no, desc, unit, price_val):
                added_count += 1
                
        QMessageBox.information(self, "Başarılı", f"{added_count} poz projeye eklendi!")
