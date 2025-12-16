from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QListWidget, QListWidgetItem, 
                             QSplitter, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from database import DatabaseManager

class CustomAnalysisManager(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_analysis_id = None
        self.component_ids = []  # Her satırın component ID'sini tutan liste
        self.original_component_ids = [] # Veritabanındaki orijinal ID'leri tut
        self.is_loading = False  # Veri yüklenirken cellChanged sinyalini engelle
        self.has_unsaved_changes = False
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet("""
            QWidget { background-color: white; }
            QLabel { color: #333; }
        """)
        
        # --- Header Frame ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #E3F2FD;
                border-bottom: 2px solid #BBDEFB;
                border-radius: 5px;
            }
        """)
        header_frame.setFixedHeight(60) # Yüksekliği sabitle
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5) # Marginleri küçült
        
        main_header = QLabel("🗂️ Kayıtlı Pozlar ve Analizler")
        main_header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1565C0;")
        header_layout.addWidget(main_header)
        
        sub_header = QLabel("Yapay zeka veya manuel oluşturduğunuz özel pozları buradan yönetebilirsiniz.")
        sub_header.setStyleSheet("color: #546E7A; font-size: 9pt;")
        header_layout.addStretch()
        header_layout.addWidget(sub_header)
        
        layout.addWidget(header_frame)
        
        # --- Splitter (Left: List, Right: Detail) ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E0E0E0;
            }
        """)
        
        # --- LEFT PANEL (List) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 10, 10, 0)
        
        list_label = QLabel("📋 Poz Listesi")
        list_label.setStyleSheet("font-weight: bold; color: #455A64; font-size: 10pt; margin-bottom: 5px;")
        left_layout.addWidget(list_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #CFD8DC;
                border-radius: 4px;
                background-color: #FAFAFA;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
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
        self.list_widget.currentRowChanged.connect(self.on_poz_selected)
        left_layout.addWidget(self.list_widget)
        
        refresh_btn = QPushButton("🔄 Listeyi Yenile")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B; 
                color: white; 
                border-radius: 4px; 
                padding: 8px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #546E7A; }
        """)
        refresh_btn.clicked.connect(self.refresh_list)
        left_layout.addWidget(refresh_btn)
        
        splitter.addWidget(left_widget)
        
        # --- RIGHT PANEL (Detail) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 0, 0)
        
        detail_label = QLabel("📊 Analiz Detayları")
        detail_label.setStyleSheet("font-weight: bold; color: #455A64; font-size: 10pt; margin-bottom: 5px;")
        right_layout.addWidget(detail_label)
        
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(6)
        self.detail_table.setHorizontalHeaderLabels([
            'Tür', 'Kod', 'Ad', 'Birim', 'Miktar', 'Birim Fiyat'
        ])
        self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #F5F5F5;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: bold;
                color: #555;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
            }
        """)
        self.detail_table.cellChanged.connect(self.on_cell_changed)
        right_layout.addWidget(self.detail_table)

        # --- Table Edit Buttons ---
        table_btn_layout = QHBoxLayout()
        table_btn_layout.setContentsMargins(0, 5, 0, 0)

        self.add_row_btn = QPushButton("➕ Satır Ekle")
        self.add_row_btn.setCursor(Qt.PointingHandCursor)
        self.add_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #43A047;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:disabled { background-color: #C8E6C9; color: #81C784; }
        """)
        self.add_row_btn.setEnabled(False)
        self.add_row_btn.clicked.connect(self.add_table_row)
        table_btn_layout.addWidget(self.add_row_btn)

        self.delete_row_btn = QPushButton("➖ Satır Sil")
        self.delete_row_btn.setCursor(Qt.PointingHandCursor)
        self.delete_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF7043;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #F4511E; }
            QPushButton:disabled { background-color: #FFCCBC; color: #FF8A65; }
        """)
        self.delete_row_btn.setEnabled(False)
        self.delete_row_btn.clicked.connect(self.delete_table_row)
        table_btn_layout.addWidget(self.delete_row_btn)

        self.clear_all_btn = QPushButton("🗑️ Tümünü Temizle")
        self.clear_all_btn.setCursor(Qt.PointingHandCursor)
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5252;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #FF1744; }
            QPushButton:disabled { background-color: #FFCCBC; color: #FF8A65; }
        """)
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.clicked.connect(self.clear_all_rows)
        table_btn_layout.addWidget(self.clear_all_btn)

        table_btn_layout.addStretch()

        self.save_changes_btn = QPushButton("💾 Değişiklikleri Kaydet")
        self.save_changes_btn.setCursor(Qt.PointingHandCursor)
        self.save_changes_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #1565C0; }
            QPushButton:disabled { background-color: #BBDEFB; color: #64B5F6; }
        """)
        self.save_changes_btn.setEnabled(False)
        self.save_changes_btn.clicked.connect(self.save_table_changes)
        table_btn_layout.addWidget(self.save_changes_btn)

        right_layout.addLayout(table_btn_layout)
        
        # --- Total Price Label ---
        self.total_price_label = QLabel("Toplam Analiz Tutarı: 0.00 TL")
        self.total_price_label.setAlignment(Qt.AlignRight)
        self.total_price_label.setStyleSheet("""
            font-size: 12pt; 
            font-weight: bold; 
            color: #2E7D32; 
            padding: 5px;
            background-color: #E8F5E9;
            border-radius: 4px;
        """)
        right_layout.addWidget(self.total_price_label)
        
        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 5, 0, 0)
        
        self.delete_btn = QPushButton("🗑️ Seçili Pozu Sil")
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF5350; 
                color: white; 
                font-weight: bold; 
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover { background-color: #E53935; }
            QPushButton:disabled { background-color: #FFCDD2; color: #EF9A9A; }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_poz)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.delete_btn)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([280, 520])
        
        layout.addWidget(splitter)
        
    def refresh_list(self):
        self.list_widget.clear()
        analyses = self.db.get_custom_analyses()

        for analysis in analyses:
            item = QListWidgetItem()

            # Text Display
            display_text = f"{analysis['poz_no']} - {analysis['name']}"
            item.setText(display_text)
            item.setToolTip(f"Oluşturulma: {analysis['created_date']}")

            # Store full data object or ID
            item.setData(Qt.UserRole, analysis)

            self.list_widget.addItem(item)

        self.detail_table.setRowCount(0)
        self.delete_btn.setEnabled(False)
        self.add_row_btn.setEnabled(False)
        self.delete_row_btn.setEnabled(False)
        self.clear_all_btn.setEnabled(False)
        self.save_changes_btn.setEnabled(False)
        self.current_analysis_id = None
        self.component_ids = []
        self.original_component_ids = []
        self.has_unsaved_changes = False
        self.total_price_label.setText("Toplam Analiz Tutarı: 0.00 TL")
        
    def on_poz_selected(self, row):
        if row < 0:
            return

        # Kaydedilmemiş değişiklik varsa uyar
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Kaydedilmemiş Değişiklikler",
                "Kaydedilmemiş değişiklikler var. Kaydetmeden devam etmek istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        item = self.list_widget.item(row)
        analysis = item.data(Qt.UserRole)
        self.current_analysis_id = analysis['id']
        self.delete_btn.setEnabled(True)
        self.add_row_btn.setEnabled(True)
        self.delete_row_btn.setEnabled(True)
        self.clear_all_btn.setEnabled(True)

        # Load components
        self.is_loading = True
        components = self.db.get_analysis_components(self.current_analysis_id)

        self.detail_table.setRowCount(0)
        self.component_ids = []

        for i, comp in enumerate(components):
            self.detail_table.insertRow(i)
            self.detail_table.setItem(i, 0, QTableWidgetItem(comp['type']))
            self.detail_table.setItem(i, 1, QTableWidgetItem(comp['code']))
            self.detail_table.setItem(i, 2, QTableWidgetItem(comp['name']))
            self.detail_table.setItem(i, 3, QTableWidgetItem(comp['unit']))
            self.detail_table.setItem(i, 4, QTableWidgetItem(str(comp['quantity'])))
            self.detail_table.setItem(i, 5, QTableWidgetItem(str(comp['unit_price'])))
            self.component_ids.append(comp['id'])

        self.original_component_ids = list(self.component_ids) # Kopyasını sakla

        self.is_loading = False
        self.has_unsaved_changes = False
        self.save_changes_btn.setEnabled(False)

        # Update Total Price Label
        total_price = analysis.get('total_price', 0.0)
        self.total_price_label.setText(f"Toplam Analiz Tutarı (Kârlı): {total_price:,.2f} TL")
            
    def delete_selected_poz(self):
        if not self.current_analysis_id:
            return
            
        reply = QMessageBox.question(
            self, "Sil", 
            "Bu pozu ve tüm analizini silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.delete_analysis(self.current_analysis_id)
            self.refresh_list()
            QMessageBox.information(self, "Bilgi", "Poz silindi.")

    def calculate_ui_total(self):
        """Tablodaki verilerden toplam tutarı hesapla"""
        total = 0.0
        for row in range(self.detail_table.rowCount()):
            try:
                quantity_text = self.detail_table.item(row, 4).text() if self.detail_table.item(row, 4) else "0"
                price_text = self.detail_table.item(row, 5).text() if self.detail_table.item(row, 5) else "0"
                quantity = float(quantity_text.replace(',', '.'))
                unit_price = float(price_text.replace(',', '.'))
                total += quantity * unit_price
            except:
                continue
        
        # %25 Kar ekle
        total_with_profit = total * 1.25
        return total_with_profit

    def on_cell_changed(self, row, column):
        """Hücre değiştiğinde çağrılır"""
        if self.is_loading:
            return

        self.has_unsaved_changes = True
        self.save_changes_btn.setEnabled(True)
        
        # Toplam tutarı güncelle (UI üzerinden)
        new_total = self.calculate_ui_total()
        self.total_price_label.setText(f"Toplam Analiz Tutarı (Kârlı): {new_total:,.2f} TL (Kaydedilmedi)")

    def add_table_row(self):
        """Tabloya yeni satır ekle"""
        if not self.current_analysis_id:
            return

        self.is_loading = True

        row_count = self.detail_table.rowCount()
        self.detail_table.insertRow(row_count)

        # Varsayılan değerler
        self.detail_table.setItem(row_count, 0, QTableWidgetItem("Malzeme"))
        self.detail_table.setItem(row_count, 1, QTableWidgetItem(""))
        self.detail_table.setItem(row_count, 2, QTableWidgetItem("Yeni Kalem"))
        self.detail_table.setItem(row_count, 3, QTableWidgetItem("Adet"))
        self.detail_table.setItem(row_count, 4, QTableWidgetItem("1"))
        self.detail_table.setItem(row_count, 5, QTableWidgetItem("0"))

        # Yeni satır için henüz veritabanında ID yok, None ile işaretle
        self.component_ids.append(None)

        self.is_loading = False
        self.has_unsaved_changes = True
        self.save_changes_btn.setEnabled(True)

        # Yeni satıra odaklan
        self.detail_table.selectRow(row_count)
        self.detail_table.scrollToItem(self.detail_table.item(row_count, 0))

    def delete_table_row(self):
        """Seçili satırı tablodan sil"""
        if not self.current_analysis_id:
            return

        current_row = self.detail_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek istediğiniz satırı seçin.")
            return

        reply = QMessageBox.question(
            self, "Satır Sil",
            "Bu satırı silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Sadece UI'dan ve listeden kaldır (Soft delete)
            # Veritabanından silme işlemi "Kaydet" butonuna basılınca yapılacak

            # Tablodan satırı kaldır
            self.detail_table.removeRow(current_row)

            # Component ID listesinden kaldır
            if current_row < len(self.component_ids):
                self.component_ids.pop(current_row)

            # UI güncellemeleri
            self.has_unsaved_changes = True
            self.save_changes_btn.setEnabled(True)
            
            # Toplam fiyatı güncelle
            new_total = self.calculate_ui_total()
            self.total_price_label.setText(f"Toplam Analiz Tutarı (Kârlı): {new_total:,.2f} TL (Kaydedilmedi)")

    def clear_all_rows(self):
        """Bu analizdeki tüm satırları sil (Soft Delete)"""
        if not self.current_analysis_id:
            return

        if self.detail_table.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self, "Tümünü Sil",
            "Bu analizdeki TÜM satırları silmek istediğinize emin misiniz?\n(Değişiklikleri kaydetmediğiniz sürece geri alabilirsiniz)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Sadece UI'ı temizle (Soft delete)
            self.detail_table.setRowCount(0)
            self.component_ids = []
            
            # UI güncellemeleri
            self.has_unsaved_changes = True
            self.save_changes_btn.setEnabled(True)
            
            # Toplam tutarı güncelle (0 olacak)
            self.total_price_label.setText(f"Toplam Analiz Tutarı (Kârlı): 0.00 TL (Kaydedilmedi)")

    def save_table_changes(self):
        """Tablodaki değişiklikleri veritabanına kaydet (Silinenler ve eklenenler dahil)"""
        if not self.current_analysis_id:
            return

        try:
            # 1. Silinenleri Bul ve Veritabanından Sil
            # Orijinal listede olup yeni listede olmayanlar silinmiştir
            current_valid_ids = set(filter(None, self.component_ids))
            for original_id in self.original_component_ids:
                if original_id not in current_valid_ids:
                    self.db.delete_analysis_component(original_id)

            # 2. Mevcut ve Yeni Satırları Kaydet/Güncelle
            row_count = self.detail_table.rowCount()

            for row in range(row_count):
                # Hücre değerlerini al
                comp_type = self.detail_table.item(row, 0).text() if self.detail_table.item(row, 0) else "Malzeme"
                code = self.detail_table.item(row, 1).text() if self.detail_table.item(row, 1) else ""
                name = self.detail_table.item(row, 2).text() if self.detail_table.item(row, 2) else ""
                unit = self.detail_table.item(row, 3).text() if self.detail_table.item(row, 3) else ""

                # Sayısal değerleri güvenli şekilde çevir
                try:
                    quantity_text = self.detail_table.item(row, 4).text() if self.detail_table.item(row, 4) else "0"
                    quantity = float(quantity_text.replace(',', '.'))
                except (ValueError, AttributeError):
                    quantity = 0.0

                try:
                    price_text = self.detail_table.item(row, 5).text() if self.detail_table.item(row, 5) else "0"
                    unit_price = float(price_text.replace(',', '.'))
                except (ValueError, AttributeError):
                    unit_price = 0.0

                component_id = self.component_ids[row] if row < len(self.component_ids) else None

                if component_id is None:
                    # Yeni satır, veritabanına ekle
                    new_id = self.db.add_analysis_component(
                        self.current_analysis_id, comp_type, code, name, unit, quantity, unit_price
                    )
                    if row < len(self.component_ids):
                        self.component_ids[row] = new_id
                    else:
                        self.component_ids.append(new_id)
                else:
                    # Mevcut satır, güncelle
                    self.db.update_analysis_component(
                        component_id, comp_type, code, name, unit, quantity, unit_price
                    )

            # Toplam tutarı güncelle
            new_total = self.db.update_analysis_total(self.current_analysis_id)
            self.total_price_label.setText(f"Toplam Analiz Tutarı (Kârlı): {new_total:,.2f} TL")

            # Sol listedeki fiyatı güncelle
            self.update_list_item_price(new_total)

            # Listeleri senkronize et
            self.original_component_ids = list(filter(None, self.component_ids))
            
            self.has_unsaved_changes = False
            self.save_changes_btn.setEnabled(False)

            QMessageBox.information(self, "Başarılı", "Tüm değişiklikler (silinenler dahil) kaydedildi.")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

    def update_list_item_price(self, new_total):
        """Sol listedeki seçili öğenin fiyatını güncelle"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            item = self.list_widget.item(current_row)
            analysis = item.data(Qt.UserRole)
            analysis['total_price'] = new_total
            item.setData(Qt.UserRole, analysis)
