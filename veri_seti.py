import pdfplumber
import pandas as pd
import re
import os

# Bu scripti PDF dosyalarının olduğu klasörde çalıştır

def pdf_to_csv():
    files = [f for f in os.listdir() if f.endswith('.pdf')]
    all_data = []

    for file in files:
        print(f"İşleniyor: {file}...")
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        for line in text.split('\n'):
                            # Basit Poz Yakalama Mantığı
                            if re.search(r'\d{2}\.\d{3}', line):
                                all_data.append([line])
        except Exception as e:
            print(f"Hata: {e}")

    df = pd.DataFrame(all_data, columns=["Ham Veri"])
    df.to_csv("TUM_INSAAT_VERISI.csv", index=False)
    print("Bitti! 'TUM_INSAAT_VERISI.csv' dosyası oluşturuldu.")

if __name__ == "__main__":
    pdf_to_csv()