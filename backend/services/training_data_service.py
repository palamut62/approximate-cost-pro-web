from pathlib import Path
from utils.logger import get_training_logger

logger = get_training_logger()


class TrainingDataService:
    """
    Eğitim verisini yönetir (egitim_verisi_FINAL_READY.jsonl).

    Özellikler:
    - Direct Lookup: Tam eşleşme kontrolü
    - RAG: Benzer örnekleri bulma
    - Semantic Search: Anahtar kelime tabanlı arama
    """

    def __init__(self, jsonl_path: str):
        self.jsonl_path = jsonl_path
        self.training_data: List[Dict[str, Any]] = []
        self.load_training_data()

    def load_training_data(self):
        """JSONL dosyasını yükle"""
        try:
            path = Path(self.jsonl_path)
            if not path.exists():
                logger.warning(f"⚠️ Training data file not found: {self.jsonl_path}")
                return

            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self.training_data.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON parse error at line {line_num}: {e}")

            logger.info(f"✅ Loaded {len(self.training_data)} training examples from {self.jsonl_path}")

        except Exception as e:
            logger.error(f"❌ Error loading training data: {e}")
            self.training_data = []

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """İki metin arasındaki benzerlik oranı (0-1)"""
        if not text1 or not text2:
            return 0.0
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        return SequenceMatcher(None, text1, text2).ratio()

    def normalize_text(self, text: str) -> str:
        """Metni normalize et (küçük harf, boşlukları düzenle)"""
        if not text:
            return ""
        return " ".join(text.lower().strip().split())

    def extract_keywords(self, text: str) -> List[str]:
        """Metinden anahtar kelimeleri çıkar"""
        stop_words = {'ve', 'ile', 'için', 'bir', 'bu', 'de', 'da', 'den', 'dan', 'nin', 'nın', 'ın', 'in', 'her', 'beher'}
        words = text.lower().replace('/', ' ').replace('-', ' ').split()
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords

    def direct_lookup(self, user_input: str, threshold: float = 0.95) -> Optional[Dict[str, Any]]:
        """
        Tam eşleşme kontrolü (Direct Lookup).

        Args:
            user_input: Kullanıcının girdiği imalat tanımı
            threshold: Minimum benzerlik oranı (0.95 = %95)

        Returns:
            Eşleşen örnek varsa output'u döner, yoksa None
        """
        if not self.training_data:
            return None

        user_norm = self.normalize_text(user_input)

        for example in self.training_data:
            example_input = example.get('input', '')
            example_norm = self.normalize_text(example_input)

            # Tam eşleşme
            if user_norm == example_norm:
                return {
                    'input': example_input,
                    'output': example['output'],
                    'metadata': example.get('metadata', {}),
                    'match_type': 'exact',
                    'similarity': 1.0
                }

            # Çok yüksek benzerlik
            similarity = self.calculate_similarity(user_norm, example_norm)
            if similarity >= threshold:
                return {
                    'input': example_input,
                    'output': example['output'],
                    'metadata': example.get('metadata', {}),
                    'match_type': 'high_similarity',
                    'similarity': similarity
                }

        return None

    def find_similar_examples(self, user_input: str, top_k: int = 5, min_similarity: float = 0.4) -> List[Dict[str, Any]]:
        """
        Benzer örnekleri bul (RAG için).

        Args:
            user_input: Kullanıcının girdiği imalat tanımı
            top_k: Kaç örnek döndürülecek
            min_similarity: Minimum benzerlik oranı

        Returns:
            Benzerlik skoruna göre sıralı örnek listesi
        """
        if not self.training_data:
            return []

        user_norm = self.normalize_text(user_input)
        user_keywords = set(self.extract_keywords(user_input))

        matches = []

        for example in self.training_data:
            example_input = example.get('input', '')
            example_norm = self.normalize_text(example_input)
            example_keywords = set(self.extract_keywords(example_input))

            # Benzerlik skoru hesapla (ağırlıklı sistem)
            score = 0.0

            # 1. Metin benzerliği (60% ağırlık)
            text_similarity = self.calculate_similarity(user_norm, example_norm)
            score += text_similarity * 0.6

            # 2. Anahtar kelime eşleşmesi (40% ağırlık)
            if user_keywords and example_keywords:
                keyword_intersection = len(user_keywords & example_keywords)
                keyword_union = len(user_keywords | example_keywords)
                keyword_similarity = keyword_intersection / keyword_union if keyword_union > 0 else 0
                score += keyword_similarity * 0.4

            if score >= min_similarity:
                matches.append({
                    'input': example_input,
                    'output': example['output'],
                    'similarity': score,
                    'text_similarity': text_similarity,
                    'common_keywords': list(user_keywords & example_keywords)
                })

        # Skorlara göre sırala ve top_k al
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:top_k]

    def build_rag_context(self, user_input: str, top_k: int = 3) -> str:
        """
        RAG için context string'i oluştur.
        LLM'e gönderilecek benzer örnekleri formatla.

        Args:
            user_input: Kullanıcı girdisi
            top_k: Kaç örnek gösterilecek

        Returns:
            Formatlanmış context metni
        """
        similar_examples = self.find_similar_examples(user_input, top_k=top_k)

        if not similar_examples:
            return ""

        lines = [
            "\n" + "=" * 70,
            "📚 BENZER ÖRNEKLER (EĞİTİM VERİSİNDEN)",
            "=" * 70,
            "Aşağıdaki benzer sorguların doğru analizlerini referans alabilirsin:\n"
        ]

        for i, example in enumerate(similar_examples, 1):
            lines.append(f"📝 ÖRNEK {i} (Benzerlik: {example['similarity']:.0%}):")
            lines.append(f"   İmalat Tanımı: \"{example['input']}\"")
            lines.append(f"   Bileşenler:")

            output = example['output']

            # İşçilik
            if output.get('iscilik'):
                lines.append("   🔹 İşçilik:")
                for item in output['iscilik'][:3]:  # Max 3 göster
                    lines.append(f"      • {item.get('kod', '')} - {item.get('ad', '')} ({item.get('birim', '')})")

            # Malzeme
            if output.get('malzeme'):
                lines.append("   🔹 Malzeme:")
                for item in output['malzeme'][:3]:
                    lines.append(f"      • {item.get('kod', '')} - {item.get('ad', '')} ({item.get('birim', '')})")

            # Makine
            if output.get('makine'):
                lines.append("   🔹 Makine:")
                for item in output['makine'][:3]:
                    lines.append(f"      • {item.get('kod', '')} - {item.get('ad', '')} ({item.get('birim', '')})")

            # Nakliye
            if output.get('nakliye'):
                lines.append("   🔹 Nakliye:")
                for item in output['nakliye'][:3]:
                    lines.append(f"      • {item.get('kod', '')} - {item.get('ad', '')} ({item.get('birim', '')})")

            lines.append("")

        lines.append("=" * 70)
        lines.append("⚠️ ÖNEMLİ: Yukarıdaki örnekleri referans al ama aynen kopyalama!")
        lines.append("Kullanıcının talebine göre miktar ve detayları UYARLA.")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """İstatistik bilgilerini döndür"""
        if not self.training_data:
            return {
                'total_examples': 0,
                'loaded': False
            }

        # Kategori sayıları
        has_iscilik = sum(1 for ex in self.training_data if ex.get('output', {}).get('iscilik'))
        has_malzeme = sum(1 for ex in self.training_data if ex.get('output', {}).get('malzeme'))
        has_makine = sum(1 for ex in self.training_data if ex.get('output', {}).get('makine'))
        has_nakliye = sum(1 for ex in self.training_data if ex.get('output', {}).get('nakliye'))

        return {
            'total_examples': len(self.training_data),
            'loaded': True,
            'categories': {
                'with_iscilik': has_iscilik,
                'with_malzeme': has_malzeme,
                'with_makine': has_makine,
                'with_nakliye': has_nakliye
            }
        }
