#!/usr/bin/env python3
"""
Otomatik Test Sistemi - Ana Çalıştırma Scripti

Kullanım:
    python run_tests.py                      # Tüm testleri çalıştır
    python run_tests.py --category basit     # Sadece basit testleri çalıştır
    python run_tests.py --report html        # HTML rapor oluştur
    python run_tests.py --help               # Yardım
"""

import sys
import argparse
from pathlib import Path

# tests modülünü import edebilmek için path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_runner import AITestRunner

def main():
    parser = argparse.ArgumentParser(
        description='AI Analiz Sistemi Otomatik Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python run_tests.py
  python run_tests.py --category basit
  python run_tests.py --report html --output test_report.html
  python run_tests.py --api http://localhost:8000
        """
    )
    
    parser.add_argument(
        '--category',
        type=str,
        choices=['basit', 'orta', 'kompleks'],
        help='Test kategorisi filtresi'
    )
    
    parser.add_argument(
        '--report',
        type=str,
        choices=['console', 'json', 'html'],
        default='console',
        help='Rapor formatı (varsayılan: console)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Rapor çıktı dosyası (sadece json/html için)'
    )
    
    parser.add_argument(
        '--api',
        type=str,
        default='http://localhost:8000',
        help='API URL (varsayılan: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Detaylı çıktı'
    )
    
    args = parser.parse_args()
    
    # Test runner'ı başlat
    runner = AITestRunner(api_url=args.api)
    
    try:
        # Testleri çalıştır
        print(f"\n🚀 Testler başlatılıyor...\n")
        runner.run_all_tests(category_filter=args.category)
        
        # Rapor oluştur
        report = runner.generate_report(output_format=args.report)
        
        # Console'a yazdır
        if args.report == 'console' or args.verbose:
            print(report)
        
        # Dosyaya kaydet
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report, encoding='utf-8')
            print(f"\n💾 Rapor kaydedildi: {output_path}")
        
        # Exit code (başarısız test varsa 1)
        total = len(runner.results)
        passed = sum(1 for r in runner.results if r.passed)
        
        if passed < total:
            print(f"\n⚠️  {total - passed} test başarısız oldu!")
            sys.exit(1)
        else:
            print(f"\n✅ Tüm testler başarılı!")
            sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"\n❌ HATA: {e}")
        print("\nℹ️  Golden dataset oluşturmak için şu komutu çalıştırın:")
        print("   python tests/create_golden_dataset.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
