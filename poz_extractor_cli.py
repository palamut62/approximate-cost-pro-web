"""
Poz Birim Fiyat Çıkarıcı - CLI Versiyonu
Komut satırından kullanılabilir, otomatik işlem yapabilir
"""

import sys
import argparse
from pathlib import Path
from poz_extractor_app import PDFPozExtractor
import json
from datetime import datetime


class PozExtractorCLI:
    """CLI tabanlı poz çıkarıcı"""

    def __init__(self):
        self.extractor = PDFPozExtractor()

    def process_files(self, pdf_files: list, output_csv: str = None, output_json: str = None):
        """PDF dosyalarını işle ve sonuçları kaydet"""
        print(f"\n{'='*60}")
        print(f"POZ ÇIKARICI - CLI MODU")
        print(f"{'='*60}\n")

        all_results = []
        total_files = len(pdf_files)

        for idx, pdf_file in enumerate(pdf_files, 1):
            pdf_path = Path(pdf_file)

            if not pdf_path.exists():
                print(f"⚠️  {pdf_path.name}: Dosya bulunamadı")
                continue

            print(f"[{idx}/{total_files}] İşleniyor: {pdf_path.name}")

            try:
                results = self.extractor.extract_poz_from_pdf(str(pdf_path))
                all_results.extend(results)
                print(f"    [OK] {len(results)} poz çıkartıldı")
            except Exception as e:
                print(f"    [ERROR] Hata: {str(e)}")

        print(f"\n{'='*60}")
        print(f"TOPLAM: {len(all_results)} poz çıkartıldı")
        print(f"{'='*60}\n")

        # CSV Kaydet
        if output_csv:
            csv_path = Path(output_csv)
            if self.extractor.export_to_csv(str(csv_path), all_results):
                print(f"[OK] CSV kaydedildi: {csv_path.absolute()}")
            else:
                print(f"[ERROR] CSV kaydedilemedi")

        # JSON Kaydet
        if output_json:
            json_path = Path(output_json)
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=2)
                print(f"[OK] JSON kaydedildi: {json_path.absolute()}")
            except Exception as e:
                print(f"[ERROR] JSON kaydedilemedi: {str(e)}")

        return all_results

    def process_directory(self, directory: str, output_csv: str = None, output_json: str = None):
        """Dizindeki tüm PDF'leri işle"""
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"[ERROR] Dizin bulunamadı: {directory}")
            return

        pdf_files = sorted(list(dir_path.glob("*.pdf")))

        if not pdf_files:
            print(f"[WARNING] {directory} dizininde PDF dosyası bulunamadı")
            return

        print(f"Bulunan PDF dosyaları: {len(pdf_files)}")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file.name}")

        self.process_files([str(f) for f in pdf_files], output_csv, output_json)

    def show_results_sample(self, data: list, limit: int = 5):
        """Sonuçlardan örnek göster"""
        if not data:
            print("Sonuç yok")
            return

        print(f"\n{'='*90}")
        print(f"İlk {min(limit, len(data))} sonuç:")
        print(f"{'='*90}\n")

        for idx, item in enumerate(data[:limit], 1):
            print(f"{idx}. Kurum: {item.get('institution', 'N/A')}")
            print(f"   Poz: {item['poz_no']}")
            print(f"   Açıklama: {item['description'][:60]}")
            print(f"   Birim: {item['unit']}")
            print(f"   Birim Fiyatı: {item['unit_price']} TL")
            print(f"   Sayfa: {item['page']}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Poz Birim Fiyat Çıkarıcı - Çevre Şehircilik ve diğer kurumlara ait PDF'lerden poz bilgilerini çıkart"
    )

    parser.add_argument(
        "input",
        help="PDF dosyası veya dizin"
    )

    parser.add_argument(
        "-o", "--output",
        help="Çıktı CSV dosyası (varsayılan: pozlar_YYYYMMDD_HHMMSS.csv)"
    )

    parser.add_argument(
        "-j", "--json",
        help="JSON formatında çıktı dosyası"
    )

    parser.add_argument(
        "-s", "--sample",
        type=int,
        default=5,
        help="Sonuçlardan kaç örnek gösterilsin (varsayılan: 5)"
    )

    parser.add_argument(
        "-d", "--directory",
        action="store_true",
        help="Giriş olarak dizin kullan"
    )

    args = parser.parse_args()

    cli = PozExtractorCLI()

    # Çıktı dosya adı belirle - PDF klasöründe kaydet
    pdf_folder = Path(__file__).parent / "PDF"
    if not args.output:
        args.output = str(pdf_folder / f"pozlar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    else:
        # Eğer sadece dosya adı verilmişse PDF klasöründe kaydet
        if not Path(args.output).is_absolute():
            args.output = str(pdf_folder / args.output)

    if args.directory:
        cli.process_directory(args.input, args.output, args.json)
    else:
        if Path(args.input).is_dir():
            cli.process_directory(args.input, args.output, args.json)
        else:
            results = cli.process_files([args.input], args.output, args.json)
            cli.show_results_sample(results, args.sample)


if __name__ == "__main__":
    main()
