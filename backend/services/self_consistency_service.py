
import asyncio
from typing import List, Dict
import statistics

class SelfConsistencyService:
    """Self-consistency ile analiz doğruluğunu artır"""

    def __init__(self, ai_service, n_samples: int = 3):
        self.ai_service = ai_service
        self.n_samples = n_samples

    async def analyze_with_consistency(
        self,
        description: str,
        unit: str,
        context_data: str = ""
    ) -> Dict:
        """Birden fazla örnek alıp tutarlılık kontrolü yap"""

        # N adet sonuç al (farklı temperature ile)
        tasks = []
        temperatures = [0.1, 0.2, 0.3][:self.n_samples]

        for temp in temperatures:
            # ai_service.generate_analysis sync method, asyncio.to_thread ile çağır
            task = asyncio.to_thread(
                self.ai_service.generate_analysis,
                description, unit, context_data, None, temp
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [r for r in results if isinstance(r, dict) and not r.get('error')]
        
        if len(valid_results) < 2:
            return valid_results[0] if valid_results else {"error": "Tutarlı sonuç üretilemedi"}
        
        # Tutarlılık skoru hesapla
        consistency_score = self._calculate_consistency(valid_results)
        
        # En tutarlı sonucu seç
        best_result = self._select_best_result(valid_results)
        best_result['consistency_score'] = consistency_score
        best_result['sample_count'] = len(valid_results)
        if consistency_score < 0.5:
             best_result['warning'] = "Düşük tutarlılık skoru. Sonucu kontrol edin."
        
        return best_result
    
    def _calculate_consistency(self, results: List[Dict]) -> float:
        """Sonuçlar arası tutarlılık skoru"""
        
        # Component sayıları
        counts = [len(r.get('components', [])) for r in results]
        if not counts:
            return 0.0
        
        # Standart sapma / ortalama = varyasyon katsayısı
        mean = statistics.mean(counts)
        if mean == 0:
            return 0.0
        
        stdev = statistics.stdev(counts) if len(counts) > 1 else 0
        cv = stdev / mean
        
        # CV düşükse tutarlılık yüksek
        consistency = max(0, 1 - cv)
        
        # Component isim benzerliği (basit set overlap)
        all_names = []
        for r in results:
            names = set(c.get('name', '').lower()[:15] for c in r.get('components', []))
            all_names.append(names)
        
        # Ortalama Jaccard similarity
        jaccard_scores = []
        if len(all_names) >= 2:
            for i in range(len(all_names)):
                for j in range(i + 1, len(all_names)):
                     intersection = len(all_names[i] & all_names[j])
                     union = len(all_names[i] | all_names[j])
                     if union > 0:
                         jaccard_scores.append(intersection / union)
            
            avg_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0
            consistency = (consistency + avg_jaccard) / 2
        
        return round(consistency, 3)
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """En iyi sonucu seç (medyan component sayısına en yakın)"""
        counts = [len(r.get('components', [])) for r in results]
        median = statistics.median(counts)
        
        # Medyana en yakın sonucu seç
        best_idx = min(range(len(results)), 
                       key=lambda i: abs(counts[i] - median))
        
        return results[best_idx]
