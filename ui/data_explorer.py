
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget)
from ui.widgets import PozViewerWidget
from ui.csv_widget import CSVSelectionWidget

class DataExplorerWidget(QWidget):
    """Veri Gezgini: PDF ve CSV kaynaklarını tek bir yerde toplar"""
    
    def __init__(self, parent_app=None):
        super().__init__()
        self.parent_app = parent_app
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 1. PDF Gezgini (Poz Viewer)
        self.pdf_viewer = PozViewerWidget()
        self.pdf_viewer.parent_app = self.parent_app
        self.tab_widget.addTab(self.pdf_viewer, "📄 PDF Arama")
        
        # 2. CSV Seçim
        self.csv_selector = CSVSelectionWidget(self.parent_app)
        self.tab_widget.addTab(self.csv_selector, "📊 CSV Listesi")
        
    def load_initial_data(self):
        """Başlangıç verilerini yükle"""
        if hasattr(self.csv_selector, 'load_data'):
            self.csv_selector.load_data()
