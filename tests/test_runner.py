"""
Test Runner - Golden Dataset'teki senaryoları test eder

Bu script:
1. golden_dataset.json'dan senaryoları okur
2. Her senaryo için API'ye istek gönderir
3. Sonuçları beklenen değerlerle karşılaştırır
4. Rapor oluşturur
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class TestResult:
    def __init__(self, scenario_id: str, passed: bool, details: str = ""):
        self.scenario_id = scenario_id
        self.passed = passed
        self.details = details
        self.timestamp = datetime.now().isoformat()

class AITestRunner:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.dataset_path = Path(__file__).parent / "golden_dataset.json"
        self.results: List[TestResult] = []
        
    def load_dataset(self) -> List[Dict]:
        """Golden dataset'i yükle"""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Golden dataset bulunamadı: {self.dataset_path}")
        
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('scenarios', [])
    
    def call_api(self, description: str) -> Dict:
        """AI analiz API'sini çağır"""
        try:
            response = requests.post(
                f"{self.api_url}/api/ai/analyze",
                json={"description": description, "unit": "otomatik"},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API hatası: {str(e)}")
    
    def validate_component_exists(self, actual_components: List[Dict], 
                                   expected: Dict) -> Tuple[bool, str]:
        """Beklenen bileşenin mevcut olup olmadığını kontrol et"""
        exp_type = expected.get('type', '').lower()
        exp_name = expected.get('name', '').lower()
        
        for comp in actual_components:
            comp_type = comp.get('type', '').lower()
            comp_name = comp.get('name', '').lower()
            
            # Tip ve isim eşleşmesi (kısmi eşleşme kabul et)
            if exp_type in comp_type and exp_name in comp_name:
                # Miktar kontrolü (varsa)
                if 'min_quantity' in expected:
                    quantity = comp.get('quantity', 0)
                    if not (expected['min_quantity'] <= quantity <= expected['max_quantity']):
                        return False, f"Miktar aralık dışı: {quantity} (beklenen: {expected['min_quantity']}-{expected['max_quantity']})"
                
                return True, "OK"
        
        return False, f"Bileşen bulunamadı: {expected['type']} - {expected['name']}"
    
    def validate_rules(self, actual_components: List[Dict], 
                       rules: Dict) -> Tuple[bool, List[str]]:
        """Validasyon kurallarını kontrol et"""
        issues = []
        
        # Harç kontrolü
        if rules.get('must_have_mortar', False):
            has_mortar = any('harç' in comp.get('name', '').lower() or 
                            'çimento' in comp.get('name', '').lower() 
                            for comp in actual_components)
            if not has_mortar:
                issues.append("Harç bulunamadı (zorunlu)")
        
        # İşçilik kontrolü
        if rules.get('must_have_labor', False):
            has_labor = any(comp.get('type', '').lower() == 'işçilik' 
                           for comp in actual_components)
            if not has_labor:
                issues.append("İşçilik bulunamadı (zorunlu)")
        
        # Nakliye kontrolü
        if rules.get('must_have_transport', False):
            has_transport = any('nakliye' in comp.get('name', '').lower() or 
                               comp.get('type', '').lower() == 'nakliye'
                               for comp in actual_components)
            if not has_transport:
                issues.append("Nakliye bulunamadı (zorunlu)")
        
        # Fiyat aralığı kontrolü
        if 'price_range' in rules:
            total_price = sum(comp.get('total_price', 0) for comp in actual_components)
            min_price = rules['price_range']['min']
            max_price = rules['price_range']['max']
            
            if not (min_price <= total_price <= max_price):
                issues.append(f"Toplam fiyat aralık dışı: {total_price:.2f} TL (beklenen: {min_price}-{max_price} TL)")
        
        return len(issues) == 0, issues
    
    def test_scenario(self, scenario: Dict) -> TestResult:
        """Tek bir senaryoyu test et"""
        scenario_id = scenario['id']
        description = scenario['description']
        
        print(f"\n🧪 Test: {scenario_id}")
        print(f"   Tanım: {description}")
        
        try:
            # API çağrısı
            print("   ⏳ API çağrılıyor...")
            result = self.call_api(description)
            
            # Bileşenleri al
            actual_components = result.get('components', [])
            expected_components = scenario.get('expected_components', [])
            
            # Her beklenen bileşeni kontrol et
            component_issues = []
            for expected in expected_components:
                passed, msg = self.validate_component_exists(actual_components, expected)
                if not passed:
                    component_issues.append(msg)
            
            # Validasyon kurallarını kontrol et
            rules = scenario.get('validation_rules', {})
            rules_passed, rule_issues = self.validate_rules(actual_components, rules)
            
            # Toplam sonuç
            all_issues = component_issues + rule_issues
            
            if len(all_issues) == 0:
                print("   ✅ BAŞARILI")
                return TestResult(scenario_id, True, "Tüm kontroller geçti")
            else:
                print("   ❌ BAŞARISIZ")
                for issue in all_issues:
                    print(f"      - {issue}")
                return TestResult(scenario_id, False, "; ".join(all_issues))
                
        except Exception as e:
            print(f"   ❌ HATA: {str(e)}")
            return TestResult(scenario_id, False, f"Test hatası: {str(e)}")
    
    def run_all_tests(self, category_filter: str = None) -> List[TestResult]:
        """Tüm testleri çalıştır"""
        scenarios = self.load_dataset()
        
        if category_filter:
            scenarios = [s for s in scenarios if s.get('category') == category_filter]
        
        print(f"\n{'='*60}")
        print(f"🧪 AI ANALİZ TEST SUITE")
        print(f"{'='*60}")
        print(f"Toplam senaryo: {len(scenarios)}")
        if category_filter:
            print(f"Kategori filtresi: {category_filter}")
        print(f"API URL: {self.api_url}")
        
        results = []
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}]", end=' ')
            result = self.test_scenario(scenario)
            results.append(result)
            time.sleep(0.5)  # API'yi çok yüklememek için
        
        self.results = results
        return results
    
    def generate_report(self, output_format: str = "console") -> str:
        """Test raporu oluştur"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        if output_format == "console":
            report = f"\n{'='*60}\n"
            report += f"📊 TEST RAPORU\n"
            report += f"{'='*60}\n"
            report += f"Toplam Test: {total}\n"
            report += f"✅ Başarılı: {passed}\n"
            report += f"❌ Başarısız: {failed}\n"
            report += f"📈 Başarı Oranı: %{success_rate:.1f}\n"
            report += f"{'='*60}\n"
            
            if failed > 0:
                report += f"\n❌ BAŞARISIZ TESTLER:\n"
                for result in self.results:
                    if not result.passed:
                        report += f"\n  • {result.scenario_id}\n"
                        report += f"    Detay: {result.details}\n"
            
            return report
        
        elif output_format == "json":
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": success_rate
                },
                "results": [
                    {
                        "scenario_id": r.scenario_id,
                        "passed": r.passed,
                        "details": r.details,
                        "timestamp": r.timestamp
                    }
                    for r in self.results
                ]
            }
            return json.dumps(report_data, indent=2, ensure_ascii=False)
        
        elif output_format == "html":
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Test Raporu</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .stat {{ background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 32px; font-weight: bold; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
        .results {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .test-item {{ padding: 10px; margin: 10px 0; border-left: 4px solid #3498db; background: #ecf0f1; }}
        .test-item.failed {{ border-left-color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 AI Analiz Test Raporu</h1>
        <p>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <div class="stat">
            <div class="stat-value">{total}</div>
            <div class="stat-label">Toplam Test</div>
        </div>
        <div class="stat">
            <div class="stat-value pass">{passed}</div>
            <div class="stat-label">Başarılı</div>
        </div>
        <div class="stat">
            <div class="stat-value fail">{failed}</div>
            <div class="stat-label">Başarısız</div>
        </div>
        <div class="stat">
            <div class="stat-value">{success_rate:.1f}%</div>
            <div class="stat-label">Başarı Oranı</div>
        </div>
    </div>
    
    <div class="results">
        <h2>Test Detayları</h2>
"""
            
            for result in self.results:
                status_class = "failed" if not result.passed else ""
                status_icon = "❌" if not result.passed else "✅"
                html += f"""
        <div class="test-item {status_class}">
            <strong>{status_icon} {result.scenario_id}</strong><br>
            <small>{result.details}</small>
        </div>
"""
            
            html += """
    </div>
</body>
</html>
"""
            return html
        
        return "Geçersiz format"

if __name__ == "__main__":
    runner = AITestRunner()
    runner.run_all_tests()
    print(runner.generate_report("console"))
