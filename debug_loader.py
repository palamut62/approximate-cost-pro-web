
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = os.path.join(os.getcwd(), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.data_manager import CSVLoader

def test_loading():
    print("Testing data loading...")
    
    # Try PDF folder
    pdf_folder = Path(os.getcwd()) / "PDF"
    print(f"Checking PDF folder: {pdf_folder}")
    if pdf_folder.exists():
        loader = CSVLoader(pdf_folder)
        data, count, files = loader.run()
        print(f"Loaded from PDF: {count} items from {len(files)} files.")
        if count == 0:
            print("  -> PDF extraction failed or no suitable files found.")
    else:
        print("  -> PDF folder does not exist.")
        
    # Try ANALIZ folder
    analiz_folder = Path(os.getcwd()) / "ANALIZ"
    print(f"Checking ANALIZ folder: {analiz_folder}")
    if analiz_folder.exists():
        loader = CSVLoader(analiz_folder)
        data, count, files = loader.run()
        print(f"Loaded from ANALIZ: {count} items from {len(files)} files.")
    else:
        print("  -> ANALIZ folder does not exist.")

if __name__ == "__main__":
    test_loading()
