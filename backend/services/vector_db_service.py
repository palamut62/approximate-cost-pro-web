
import chromadb
from sentence_transformers import SentenceTransformer
import os
from typing import List, Dict, Any, Optional
import threading
from utils.logger import get_vector_logger

logger = get_vector_logger()
base_logger = logger # Alias for consistency if needed

class VectorDBService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorDBService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("[VECTOR_DB] Servis başlatılıyor (lazy mode)...")

        # CUDA hatasını önlemek için CPU kullanımını zorla satırını kaldırıyoruz
        # os.environ['CUDA_VISIBLE_DEVICES'] = ''

        self.persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
        self.model = None
        self.client = None
        self.collection = None
        self.collection_name = "poz_data_collection"

        # Lazy loading state
        self._model_loaded = False
        self._ingestion_started = False
        self._ingestion_complete = False
        self._pending_data: Optional[List[Dict]] = None

        self._initialized = True
        logger.info("[VECTOR_DB] Servis hazır (model henüz yüklenmedi).")

    def _ensure_client_connected(self):
        """ChromaDB client'a bağlan (model olmadan). Status kontrolü için yeterli."""
        if self.client is not None:
            return True

        with self._lock:
            if self.client is not None:
                return True
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.feedback_collection = self.client.get_or_create_collection(
                    name="user_feedbacks",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"[VECTOR_DB] Client bağlandı. Mevcut belge sayısı: {self.collection.count()}")
                return True
            except Exception as e:
                logger.error(f"[VECTOR_DB] Client bağlantı hatası: {e}")
                return False

    def _ensure_model_loaded(self):
        """Embedding modeli lazy olarak yükle (search/ingest için gerekli)."""
        if self._model_loaded:
            return True

        with self._lock:
            if self._model_loaded:
                return True

            # Önce client bağlantısını sağla
            self._ensure_client_connected()

            try:
                import torch
                device = "cpu"  # GTX 850M incompatibility
            except ImportError:
                device = "cpu"

            logger.info(f"[VECTOR_DB] Embedding modeli yükleniyor ({device.upper()} modunda)...")
            try:
                self.model = SentenceTransformer('emrecan/bert-base-turkish-cased-mean-nli-stsb-tr', device=device)
                self._model_loaded = True
                logger.info(f"[VECTOR_DB] Model yüklendi. Mevcut belge: {self.collection.count()}")
                return True
            except Exception as e:
                logger.error(f"[VECTOR_DB] Model yüklenemedi: {e}")
                return False

    @property
    def is_ready(self) -> bool:
        """Vector DB'nin sorgulamaya hazır olup olmadığını kontrol eder (model olmadan)."""
        self._ensure_client_connected()
        if not self.collection:
            return False
        try:
            return self.collection.count() > 0
        except:
            return False

    def lazy_ingest(self, poz_data: List[Dict[str, Any]]):
        """Arka planda veri yüklemeyi başlat"""
        if self._ingestion_started:
            return
        
        self._ingestion_started = True
        logger.info("[VECTOR_DB] Lazy ingestion tetiklendi...")
        
        # Arka planda çalıştır
        thread = threading.Thread(target=self._ingest_worker, args=(poz_data,))
        thread.daemon = True
        thread.start()

    def _ingest_worker(self, poz_data: List[Dict]):
        """Arka plan thread'i"""
        try:
            self._ensure_model_loaded()
            self.ingest_data(poz_data)
            self._ingestion_complete = True
        except Exception as e:
            logger.error(f"[VECTOR_DB] Arka plan yükleme hatası: {e}")

    def ingest_data(self, poz_data: List[Dict[str, Any]]):
        """
        Poz verilerini vektör veritabanına ekler.
        Zaten varsa atlar (basit kontrol).
        """
        if not self.model:
            logger.warning("[VECTOR_DB] Model yüklü değil, ingestion iptal.")
            return

        current_count = self.collection.count()
        if current_count >= len(poz_data) * 0.9:
            logger.info(f"[VECTOR_DB] Veri zaten yüklü görünüyor ({current_count} belge). İşlem atlandı.")
            return

        logger.info(f"[VECTOR_DB] {len(poz_data)} poz için ingestion başlıyor...")
        
        # Cihaz kapasitesine göre batch size ayarla
        try:
            device = self.model.device.type
        except:
            device = 'cpu'
            
        batch_size = 500 if device == 'cuda' else 100
        total_batches = (len(poz_data) + batch_size - 1) // batch_size
        
        ids = []
        documents = []
        metadatas = []
        
        for idx, poz in enumerate(poz_data):
            # Poz ID (Code)
            code = poz.get('poz_no') or poz.get('code')
            if not code: continue
            
            # İçerik: "Kod - Açıklama" formatında
            desc = poz.get('description') or poz.get('name') or ""
            doc_text = f"{code} {desc}"
            
            # Metadata
            meta = {
                "code": code,
                "unit": poz.get('unit', ''),
                "price": str(poz.get('unit_price', '0')),
                "description": desc
            }
            
            ids.append(code)
            documents.append(doc_text)
            metadatas.append(meta)
            
            # Batch Process
            if len(ids) >= batch_size or idx == len(poz_data) - 1:
                try:
                    # Embeddings (Model otomatik yapabilir ama manuel kontrol daha iyi)
                    embeddings = self.model.encode(documents).tolist()
                    
                    self.collection.upsert(
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas
                    )
                    logger.info(f"[VECTOR_DB] Batch {idx // batch_size + 1}/{total_batches} tamamlandı.")
                except Exception as e:
                    logger.error(f"[VECTOR_DB] Batch hatası: {e}")
                
                ids = []
                documents = []
                metadatas = []

        logger.info("[VECTOR_DB] Ingestion tamamlandı.")

    def search(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Sorguya en yakın pozları getirir (lazy loading ile).
        """
        # Lazy model loading
        if not self._ensure_model_loaded():
            return []

        # Veri yoksa boş dön
        if self.collection.count() == 0:
            logger.warning("[VECTOR_DB] Koleksiyon boş, arama yapılamıyor.")
            return []

        try:
            query_embedding = self.model.encode([query_text]).tolist()

            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )

            # Sonuçları formatla
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        "code": doc_id,
                        "description": results['metadatas'][0][i]['description'],
                        "unit": results['metadatas'][0][i]['unit'],
                        "unit_price": results['metadatas'][0][i]['price'],
                        "score": results['distances'][0][i] if 'distances' in results else 0
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"[VECTOR_DB] Arama hatası: {e}")
            return []

    def index_feedback(self, feedback_data: Dict[str, Any]):
        """Kullanıcı geri bildirimini vektör veritabanına ekle"""
        if not self._ensure_model_loaded():
            return

        try:
            # ID ve Metin
            doc_id = feedback_data.get('id') or f"fb_{len(feedback_data)}"
            doc_text = f"{feedback_data.get('original_description')} -> {feedback_data.get('correction_type')} : {feedback_data.get('user_note')}"
            
            # Embed
            embeddings = self.model.encode([doc_text]).tolist()
            
            self.feedback_collection.upsert(
                ids=[str(doc_id)],
                embeddings=embeddings,
                documents=[doc_text],
                metadatas=[feedback_data]
            )
            logger.info(f"[VECTOR_DB] Feedback eklendi: {doc_id}")
            
        except Exception as e:
            logger.error(f"[VECTOR_DB] Feedback ekleme hatası: {e}")

    def search_feedback(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Benzer geri bildirimleri ara"""
        if not self._ensure_model_loaded():
            return []
            
        if self.feedback_collection.count() == 0:
            return []
            
        try:
            query_embedding = self.model.encode([query_text]).tolist()
            
            results = self.feedback_collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )
            
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    formatted_results.append(metadata)
                    
            return formatted_results
            
        except Exception as e:
            logger.error(f"[VECTOR_DB] Feedback arama hatası: {e}")
            return []

    def get_count(self) -> int:
        """Koleksiyondaki belge sayısını döndür"""
        if self.collection is None:
            return 0
        return self.collection.count()

    def get_status(self) -> Dict[str, Any]:
        """Servis durumunu döndürür (model olmadan çalışır)."""
        self._ensure_client_connected()
        doc_count = 0
        feedback_count = 0
        if self.collection:
            doc_count = self.collection.count()
        if self.feedback_collection:
            feedback_count = self.feedback_collection.count()

        return {
            "initialized": self._model_loaded,
            "document_count": doc_count,
            "feedback_count": feedback_count,
            "model_loaded": self._model_loaded,
            "device": str(self.model.device) if self.model else "cpu"
        }
