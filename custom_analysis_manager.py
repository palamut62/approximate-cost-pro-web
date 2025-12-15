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
        """)
        right_layout.addWidget(self.detail_table)
        
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
            # item.setData(Qt.UserRole, analysis['id']) # Store ID
            
            # Text Display
            display_text = f"{analysis['poz_no']} - {analysis['name']}"
            item.setText(display_text)
            item.setToolTip(f"Oluşturulma: {analysis['created_date']}")
            
            # Store full data object or ID
            item.setData(Qt.UserRole, analysis)
            
            self.list_widget.addItem(item)
            
        self.detail_table.setRowCount(0)
        self.delete_btn.setEnabled(False)
        self.current_analysis_id = None
        self.total_price_label.setText("Toplam Analiz Tutarı: 0.00 TL")
        
    def on_poz_selected(self, row):
        if row < 0:
            return
            
        item = self.list_widget.item(row)
        analysis = item.data(Qt.UserRole)
        self.current_analysis_id = analysis['id']
        self.delete_btn.setEnabled(True)
        
        # Load components
        components = self.db.get_analysis_components(self.current_analysis_id)
        
        self.detail_table.setRowCount(0)
        for i, comp in enumerate(components):
            self.detail_table.insertRow(i)
            self.detail_table.setItem(i, 0, QTableWidgetItem(comp['type']))
            self.detail_table.setItem(i, 1, QTableWidgetItem(comp['code']))
            self.detail_table.setItem(i, 2, QTableWidgetItem(comp['name']))
            self.detail_table.setItem(i, 3, QTableWidgetItem(comp['unit']))
            self.detail_table.setItem(i, 4, QTableWidgetItem(str(comp['quantity'])))
            self.detail_table.setItem(i, 5, QTableWidgetItem(str(comp['unit_price'])))
            
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
