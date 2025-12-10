from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QInputDialog, QMessageBox, QGroupBox,
                             QFormLayout, QDialog, QDoubleSpinBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from database import DatabaseManager

class CostEstimator(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_project_id = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # --- Top Section: Project Selection ---
        project_group = QGroupBox("Proje Yönetimi")
        proj_layout = QHBoxLayout()
        
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        proj_layout.addWidget(QLabel("Aktif Proje:"))
        proj_layout.addWidget(self.project_combo, 1)
        
        new_proj_btn = QPushButton("+ Yeni Proje")
        new_proj_btn.clicked.connect(self.create_new_project)
        new_proj_btn.setStyleSheet("background-color: #2196F3; color: white;")
        proj_layout.addWidget(new_proj_btn)
        
        del_proj_btn = QPushButton("Sil")
        del_proj_btn.clicked.connect(self.delete_current_project)
        del_proj_btn.setStyleSheet("background-color: #f44336; color: white;")
        proj_layout.addWidget(del_proj_btn)
        
        project_group.setLayout(proj_layout)
        layout.addWidget(project_group)
        
        # --- Middle Section: Cost Table ---
        table_group = QGroupBox("Keşif Özeti / Metraj")
        table_layout = QVBoxLayout()
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels([
            'ID', 'Poz No', 'Açıklama', 'Birim', 'Miktar', 'Birim Fiyat', 'Tutar'
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.items_table.hideColumn(0) # Hide ID
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
        
        layout.addLayout(actions_layout)
        
        self.setLayout(layout)
        
        # Initial Load
        self.refresh_projects()

    def refresh_projects(self):
        projects = self.db.get_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p['name'], p['id'])
        self.project_combo.blockSignals(False)
        
        if projects:
            self.current_project_id = projects[0]['id']
            self.load_project_items()
        else:
            self.current_project_id = None
            self.items_table.setRowCount(0)
            self.total_label.setText("Toplam Tutar: 0.00 TL")

    def create_new_project(self):
        name, ok = QInputDialog.getText(self, "Yeni Proje", "Proje Adı:")
        if ok and name:
            self.db.create_project(name)
            self.refresh_projects()

    def delete_current_project(self):
        if not self.current_project_id:
            return
            
        reply = QMessageBox.question(self, 'Onay', 'Bu projeyi silmek istediğinize emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_project(self.current_project_id)
            self.refresh_projects()

    def on_project_changed(self, index):
        self.current_project_id = self.project_combo.itemData(index)
        self.load_project_items()

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
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable) # Read only
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
            qty = float(self.items_table.item(row, 4).text())
            price = float(self.items_table.item(row, 5).text())
            
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
                val = float(self.items_table.item(i, 6).text())
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
        poz_input = QInputDialog() # Helper
        fields = {}
        
        from PyQt5.QtWidgets import QLineEdit
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
                1.0, # Default Quantity
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
