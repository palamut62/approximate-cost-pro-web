from typing import List, Dict, Any
from services.vector_db_service import VectorDBService

class RAGService:
    """
    Retrieval-Augmented Generation sistemi.
    Her analiz için en alakalı referans pozları ve kullanıcı düzeltmelerini getirir.
    """
    
    def __init__(self):
        self.vector_db = VectorDBService()
        
    def retrieve_relevant_context(self, query: str) -> Dict[str, Any]:
        """
        Sorgu için en alakalı context'i getir.
        POZ verileri + kullanıcı feedback'leri birleştirilir.
        """
        
        # 1. POZ araması
        poz_results = self.vector_db.search(query, n_results=5)
        
        # 2. Feedback araması
        feedback_results = self.vector_db.search_feedback(query, n_results=3)
        
        # 3. Context metni oluştur
        context_text = self._build_context_text(poz_results, feedback_results)
        
        return {
            'context_text': context_text,
            'poz_count': len(poz_results),
            'feedback_count': len(feedback_results)
        }
    
    def _build_context_text(self, poz_results: List[Dict], feedback_results: List[Dict]) -> str:
        """Context metnini birleştir"""
        
        context_parts = []
        
        # POZ Referansları
        if poz_results:
            context_parts.append("═══ BENZER POZ ANALİZLERİ (KAYNAK: VERİTABANI) ═══")
            for i, res in enumerate(poz_results, 1):
                context_parts.append(f"""
📌 Referans #{i} (Skor: {1 - res.get('score', 0):.2f})
   Kod: {res.get('code')}
   Tanım: {res.get('description')}
   Birim: {res.get('unit')} | Fiyat: {res.get('unit_price')} TL
""")
        
        # Feedback Referansları
        if feedback_results:
            context_parts.append("\n═══ ÖNCEKİ KULLANICI DÜZELTMELERİ (KAYNAK: HAFIZA) ═══")
            for i, fb in enumerate(feedback_results, 1):
                context_parts.append(f"""
⚠️ Düzeltme #{i}: "{fb.get('original_description', '')}"
   Düzeltme Türü: {fb.get('correction_type')}
   Kullanıcı Notu: {fb.get('user_note')}
   Eklenmesi Gereken: {fb.get('added_items', 'Yok')}
   Çıkarılması Gereken: {fb.get('removed_items', 'Yok')}
""")
                
        return "\n".join(context_parts)
    
    def augmented_prompt(self, description: str, unit: str, base_prompt: str) -> str:
        """RAG ile zenginleştirilmiş prompt oluştur"""
        
        context = self.retrieve_relevant_context(description)
        
        if not context['context_text']:
            return base_prompt
            
        augmented = f"""{base_prompt}

═══════════════════════════════════════════════════════════════
                   RAG CONTEXT (OTOMATİK GETİRİLEN BİLGİLER)
═══════════════════════════════════════════════════════════════

{context['context_text']}

⚠️ Yukarıdaki referansları MUTLAKA dikkate al!
   - Benzer pozların miktar ve fiyatlarını referans/emsal kabul et.
   - Kullanıcı düzeltmelerindeki hataları TEKRARLAMA (Örn: Yalın betona demir koyma denmişse koyma).

═══════════════════════════════════════════════════════════════
                        GÖREV
═══════════════════════════════════════════════════════════════

Aşağıdaki imalat için YENİ birim fiyat analizi oluştur:
📌 TANIM: {description}
📌 BİRİM: {unit}
"""
        return augmented
