"""
CSV Poz Arama ve Seçim Uygulaması
Sol: CSV poz listesi, Sağ: Seçili poz detayları
"""

import sys
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QSplitter,
    QTextEdit, QLineEdit, QMessageBox, QGroupBox, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer


class CSVPozSearchApp(QMainWindow):
    """CSV Poz Seçim Uygulaması"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poz Seçim Uygulaması - CSV")
        self.setGeometry(100, 100, 1600, 900)
        self.showMaximized()

        self.csv_data = []
        self.selected_pozlar = []
        self.pdf_folder = Path(__file__).parent / "PDF"

        self.init_ui()
        self.load_csv_data()

    def init_ui(self):
        """Arayüzü oluştur"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()

        # Başlık
        title = QLabel("CSV Poz Seçim Uygulaması")
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Arama bölümü
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Ara:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_pozlar)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Splitter ile 2 bölüm
        splitter = QSplitter(Qt.Horizontal)

        # SOL: Poz Listesi
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        left_label = QLabel("CSV Pozları (Çift Tıkla veya Ok → Seç)")
        left_layout.addWidget(left_label)

        self.poz_table = QTableWidget()
        self.poz_table.setColumnCount(4)
        self.poz_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.poz_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.poz_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.poz_table.setSelectionMode(QTableWidget.SingleSelection)
        self.poz_table.doubleClicked.connect(self.on_poz_double_click)
        left_layout.addWidget(self.poz_table)

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

        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)

        # SAĞ: Seçili Pozlar
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        right_label = QLabel("Seçili Pozlar")
        right_layout.addWidget(right_label)

        self.selected_table = QTableWidget()
        self.selected_table.setColumnCount(4)
        self.selected_table.setHorizontalHeaderLabels(["Poz No", "Açıklama", "Birim Fiyat", "Kurum"])
        self.selected_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.selected_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.selected_table.setSelectionMode(QTableWidget.SingleSelection)
        right_layout.addWidget(self.selected_table)

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
        self.info_label = QLabel("Seçili: 0 poz")
        right_layout.addWidget(self.info_label)

        # Export butonu
        btn_export = QPushButton("💾 Seçili Pozları CSV'ye Kaydet")
        btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_export.clicked.connect(self.export_selected)
        right_layout.addWidget(btn_export)

        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        # Splitter'ı ortaya koy
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)

    def load_csv_data(self):
        """CSV dosyasını yükle"""
        try:
            csv_files = list(self.pdf_folder.glob("*.csv"))
            if not csv_files:
                QMessageBox.warning(self, "Uyarı", "CSV dosyası bulunamadı!")
                return

            # En yeni CSV dosyasını al
            csv_file = sorted(csv_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]

            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            self.csv_data = df.to_dict('records')

            self.display_pozlar(self.csv_data)
            self.setWindowTitle(f"Poz Seçim - {csv_file.name}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"CSV yüklenirken hata: {str(e)}")

    def display_pozlar(self, data):
        """Pozları tabloda göster"""
        self.poz_table.setRowCount(len(data))

        for row, item in enumerate(data):
            self.poz_table.setItem(row, 0, QTableWidgetItem(str(item.get('Poz No', ''))))
            self.poz_table.setItem(row, 1, QTableWidgetItem(str(item.get('Açıklama', ''))[:40]))
            self.poz_table.setItem(row, 2, QTableWidgetItem(str(item.get('Birim Fiyatı (TL)', ''))))
            self.poz_table.setItem(row, 3, QTableWidgetItem(str(item.get('Kurum', ''))))

    def filter_pozlar(self):
        """Ara kutusuna göre filtrele"""
        search_text = self.search_input.text().lower()
        filtered_data = [
            item for item in self.csv_data
            if search_text in str(item.get('Poz No', '')).lower() or
               search_text in str(item.get('Açıklama', '')).lower() or
               search_text in str(item.get('Kurum', '')).lower()
        ]
        self.display_pozlar(filtered_data)

    def on_poz_double_click(self):
        """Poz çift tıklandığında seç"""
        self.add_selected_poz()

    def add_selected_poz(self):
        """Seçili pozı sağ tarafa ekle"""
        current_row = self.poz_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Bir poz seçin!")
            return

        # Tablodan veriyi al
        poz_no = self.poz_table.item(current_row, 0).text()
        aciklama = self.poz_table.item(current_row, 1).text()
        fiyat = self.poz_table.item(current_row, 2).text()
        kurum = self.poz_table.item(current_row, 3).text()

        # Zaten seçilmişse ekle
        for item in self.selected_pozlar:
            if item.get('Poz No') == poz_no:
                QMessageBox.info(self, "Bilgi", "Bu poz zaten seçilmiş!")
                return

        # Ekle
        self.selected_pozlar.append({
            'Poz No': poz_no,
            'Açıklama': aciklama,
            'Birim Fiyatı (TL)': fiyat,
            'Kurum': kurum
        })

        self.update_selected_table()

    def add_all_pozlar(self):
        """Tüm pozları seç"""
        self.selected_pozlar = self.csv_data.copy()
        self.update_selected_table()

    def remove_selected_poz(self):
        """Seçili pozı kaldır"""
        current_row = self.selected_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Uyarı", "Bir poz seçin!")
            return

        poz_no = self.selected_table.item(current_row, 0).text()
        self.selected_pozlar = [item for item in self.selected_pozlar if item.get('Poz No') != poz_no]
        self.update_selected_table()

    def remove_all_pozlar(self):
        """Tüm pozları kaldır"""
        self.selected_pozlar = []
        self.update_selected_table()

    def update_selected_table(self):
        """Seçili pozlar tablosunu güncelle"""
        self.selected_table.setRowCount(len(self.selected_pozlar))

        for row, item in enumerate(self.selected_pozlar):
            self.selected_table.setItem(row, 0, QTableWidgetItem(str(item.get('Poz No', ''))))
            self.selected_table.setItem(row, 1, QTableWidgetItem(str(item.get('Açıklama', ''))[:40]))
            self.selected_table.setItem(row, 2, QTableWidgetItem(str(item.get('Birim Fiyatı (TL)', ''))))
            self.selected_table.setItem(row, 3, QTableWidgetItem(str(item.get('Kurum', ''))))

        self.info_label.setText(f"Seçili: {len(self.selected_pozlar)} poz")

    def export_selected(self):
        """Seçili pozları CSV'ye kaydet"""
        if not self.selected_pozlar:
            QMessageBox.warning(self, "Uyarı", "Seçili poz yok!")
            return

        try:
            output_file = self.pdf_folder / "seçili_pozlar.csv"
            df = pd.DataFrame(self.selected_pozlar)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')

            QMessageBox.information(
                self,
                "Başarılı",
                f"{len(self.selected_pozlar)} poz kaydedildi:\n{output_file.name}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = CSVPozSearchApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
