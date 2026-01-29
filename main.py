
import sys
import os
from PyQt5.QtWidgets import QApplication

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import PDFSearchAppPyQt5

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = PDFSearchAppPyQt5()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
