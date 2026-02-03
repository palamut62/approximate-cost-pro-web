
from typing import List, Dict
import asyncio
from collections import Counter

class ConsensusAnalysisService:
    """Çoklu model konsensüs sistemi"""

    def __init__(self, ai_service):
        self.ai_service = ai_service

        # Kullanılacak modeller (farklı perspektifler için)
        self.models = [
            "moonshot/kimi-k2.5",
            "google/gemini-2.0-flash-001",
        ]

    async def analyze_with_consensus(
        self,
        description: str,
        unit: str,
        context_data: str = ""
    ) -> Dict:
        """Çoklu model ile analiz yap ve konsensüs oluştur"""

        # Paralel olarak tüm modellerden sonuç al
        tasks = []
        for model in self.models:
            # ai_service.generate_analysis sync method, asyncio.to_thread ile çağır
            task = asyncio.to_thread(
                self.ai_service.generate_analysis,
                description, unit, context_data, model
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Başarılı sonuçları filtrele
        valid_results = [r for r in results if isinstance(r, dict) and not r.get('error')]
        
        if len(valid_results) < 2:
            # Tek sonuç varsa direkt döndür
            return valid_results[0] if valid_results else {"error": "Tüm modeller başarısız"}
        
        # Konsensüs oluştur
        return self._build_consensus(valid_results, description)
    
    def _build_consensus(self, results: List[Dict], description: str) -> Dict:
        """Sonuçlardan konsensüs oluştur"""
        
        all_components = []
        for result in results:
            for comp in result.get('components', []):
                # Normalize et
                comp_key = self._normalize_component(comp)
                all_components.append(comp_key)
        
        # En sık geçen component'ları say
        component_counts = Counter(all_components)
        
        # Çoğunluk eşiği: en az 2 modelin kabul ettiği veya yarıdan fazlası
        majority_threshold = max(2, len(results) // 2 + 1)
        
        consensus_components = []
        seen_keys = set()
        
        for comp_key, count in component_counts.items():
            if count >= majority_threshold and comp_key not in seen_keys:
                # Orijinal component'ı bul ve ekle (ilk bulduğumuzu alıyoruz)
                found = False
                for result in results:
                    for comp in result.get('components', []):
                        if self._normalize_component(comp) == comp_key:
                            consensus_components.append(comp)
                            seen_keys.add(comp_key)
                            found = True
                            break
                    if found:
                        break
        
        # Eğer hiç konsensüs çıkmadıysa, en iyi (en detaylı) sonucu al
        if not consensus_components:
            return max(results, key=lambda r: len(r.get('components', [])))

        # Miktar ve fiyatları ortala
        consensus_components = self._average_quantities(consensus_components, results)
        
        return {
            "components": consensus_components,
            "consensus_score": len(consensus_components) / max(len(component_counts), 1),
            "model_count": len(results),
            "source": "consensus_ensemble"
        }
    
    def _normalize_component(self, comp: Dict) -> str:
        """Component'ı karşılaştırılabilir key'e dönüştür"""
        name = comp.get('name', '').lower().strip()
        type_ = comp.get('type', '').lower().strip()
        
        # Ana anahtar kelimeleri çıkar
        keywords = []
        # Yaygın inşaat terimleri
        common_terms = ['beton', 'demir', 'kalıp', 'harç', 'çimento', 'kum', 'çakıl', 
                     'nakliye', 'işçi', 'usta', 'makine', 'pompa', 'tuğla', 'seramik']
        
        for word in common_terms:
            if word in name:
                keywords.append(word)
        
        # Hiçbir kelime eşleşmezse ismin kendisini kullan (kısa hali)
        if not keywords:
            keywords = [name[:10]]
            
        return f"{type_}:{':'.join(sorted(keywords))}"
    
    def _average_quantities(self, components: List[Dict], results: List[Dict]) -> List[Dict]:
        """Component miktarlarını optimize et"""
        # Şimdilik direkt componentları dönüyoruz, ileride ortalama alınabilir
        return components
