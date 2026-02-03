from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from services.ai_service import AIAnalysisService
from services.consensus_service import ConsensusAnalysisService
from services.self_consistency_service import SelfConsistencyService
from services.cot_service import ChainOfThoughtService
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from database import DatabaseManager
from pathlib import Path
from config import get_analysis_config, get_price_config, get_validation_config
from utils.logger import get_ai_logger, get_price_logger, get_validation_logger
import json
import uuid
import asyncio
from datetime import datetime
import threading
from services.description_parser import extract_included_services, should_exclude_component
from services.density_service import calculate_transport_tonnage

router = APIRouter(prefix="/ai", tags=["AI"])

# Logger instances
logger = get_ai_logger()
price_logger = get_price_logger()
validation_logger = get_validation_logger()

# Config instances
analysis_config = get_analysis_config()
price_config = get_price_config()
validation_config = get_validation_config()

# ============================================
# BACKGROUND JOB STORAGE
# ============================================
# Job'ları saklamak için in-memory storage
# Format: {job_id: {"status": "pending/running/completed/failed", "result": {...}, "error": "...", "created_at": datetime}}
ANALYSIS_JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

# Database for feedback
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))


class AnalysisRequest(BaseModel):
    description: str
    unit: str
    context_data: str = ""
    use_consensus: bool = False
    use_self_consistency: bool = False
    use_cot: bool = False


class RefineRequest(BaseModel):
    text: str


class LearnRuleRequest(BaseModel):
    trigger_keywords: List[str]
    required_item_name: str
    condition_text: str


class AsyncAnalysisRequest(BaseModel):
    description: str
    unit: str
    context_data: str = ""


# ============================================
# ASYNC JOB HELPER FUNCTIONS
# ============================================

def create_job(job_id: str, description: str):
    """Yeni bir job oluştur"""
    with JOBS_LOCK:
        ANALYSIS_JOBS[job_id] = {
            "status": "pending",
            "description": description,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }


def update_job_status(job_id: str, status: str, result: Any = None, error: str = None):
    """Job durumunu güncelle"""
    with JOBS_LOCK:
        if job_id in ANALYSIS_JOBS:
            ANALYSIS_JOBS[job_id]["status"] = status
            if result is not None:
                ANALYSIS_JOBS[job_id]["result"] = result
            if error is not None:
                ANALYSIS_JOBS[job_id]["error"] = error
            if status in ["completed", "failed"]:
                ANALYSIS_JOBS[job_id]["completed_at"] = datetime.now().isoformat()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Job bilgisini getir"""
    with JOBS_LOCK:
        return ANALYSIS_JOBS.get(job_id)


def cleanup_old_jobs(max_age_hours: int = 24):
    """Eski job'ları temizle"""
    with JOBS_LOCK:
        now = datetime.now()
        to_delete = []
        for job_id, job in ANALYSIS_JOBS.items():
            created = datetime.fromisoformat(job["created_at"])
            if (now - created).total_seconds() > max_age_hours * 3600:
                to_delete.append(job_id)
        for job_id in to_delete:
            del ANALYSIS_JOBS[job_id]


def run_analysis_job(job_id: str, description: str, unit: str, context_data: str = ""):
    """
    Arka planda analiz işlemini çalıştır.
    Bu fonksiyon BackgroundTasks tarafından çağrılır.
    """
    try:
        update_job_status(job_id, "running")
        print(f"[JOB {job_id[:8]}] Analiz başladı: {description[:50]}...")

        # Analiz işlemini yap (senkron olarak)
        result = perform_analysis_sync(description, unit, context_data)

        update_job_status(job_id, "completed", result=result)
        print(f"[JOB {job_id[:8]}] ✅ Analiz tamamlandı!")

    except Exception as e:
        error_msg = str(e)
        update_job_status(job_id, "failed", error=error_msg)
        print(f"[JOB {job_id[:8]}] ❌ Analiz hatası: {error_msg}")


def perform_analysis_sync(
    description: str,
    unit: str,
    context_data: str = "",
    use_consensus: bool = False,
    use_self_consistency: bool = False,
    use_cot: bool = False
) -> Dict[str, Any]:
    """
    Senkron analiz işlemi.
    analyze_poz endpoint'inin mantığını içerir.

    Args:
        description: İmalat tanımı
        unit: Birim
        context_data: Ek context verisi
        use_consensus: Çoklu model konsensüs modu
        use_self_consistency: Self-consistency modu
        use_cot: Chain-of-Thought modu
    """
    service = AIAnalysisService()
    training_service = get_training_service()

    # ========================================
    # STEP 1: DIRECT LOOKUP (Tam Eşleşme)
    # ========================================
    if training_service:
        direct_match = training_service.direct_lookup(description, threshold=0.95)
        if direct_match:
            print(f"✅ DIRECT LOOKUP HIT! Similarity: {direct_match['similarity']:.2%}")

            # POZ_DATA'yı al (isim düzeltmeleri için gerekli)
            poz_data = get_poz_data()
            
            training_output = direct_match['output']
            components = []

            # İşçilik
            for item in training_output.get('iscilik', []):
                kod = item.get('kod', '')
                ad = item.get('ad', '')
                
                # DEBUG: ad değerini kontrol et
                print(f"[DEBUG] İşçilik item: kod='{kod}', ad='{ad}', ad_type={type(ad)}, ad_len={len(ad) if ad else 0}")
                
                # Eğer ad boşsa kod üzerinden POZ_DATA'dan al
                is_ad_empty = not ad or len(ad.strip()) == 0
                kod_exists = kod and kod in poz_data
                
                print(f"[DEBUG] Checks: is_ad_empty={is_ad_empty}, kod_exists={kod_exists}")
                
                if is_ad_empty and kod_exists:
                    ad = poz_data[kod].get('description', '')
                    print(f"[TRAINING NAME FIX] İşçilik '{kod}' → '{ad}'")
                
                components.append({
                    'type': 'İşçilik',
                    'code': kod,
                    'name': ad,
                    'unit': item.get('birim', ''),
                    'quantity': item.get('miktar', 1.0),
                    'unit_price': 0.0,
                    'total_price': 0.0,
                    'price_source': 'training_data'
                })

            # Malzeme
            for item in training_output.get('malzeme', []):
                kod = item.get('kod', '')
                ad = item.get('ad', '')
                
                # Eğer ad boşsa kod üzerinden POZ_DATA'dan al
                if (not ad or len(ad.strip()) == 0) and kod and kod in poz_data:
                    ad = poz_data[kod].get('description', '')
                    print(f"[TRAINING NAME FIX] Malzeme '{kod}' → '{ad}'")
                
                components.append({
                    'type': 'Malzeme',
                    'code': kod,
                    'name': ad,
                    'unit': item.get('birim', ''),
                    'quantity': item.get('miktar', 1.0),
                    'unit_price': 0.0,
                    'total_price': 0.0,
                    'price_source': 'training_data'
                })

            # Makine
            for item in training_output.get('makine', []):
                kod = item.get('kod', '')
                ad = item.get('ad', '')
                
                # Eğer ad boşsa kod üzerinden POZ_DATA'dan al
                if (not ad or len(ad.strip()) == 0) and kod and kod in poz_data:
                    ad = poz_data[kod].get('description', '')
                    print(f"[TRAINING NAME FIX] Makine '{kod}' → '{ad}'")
                
                components.append({
                    'type': 'Makine',
                    'code': kod,
                    'name': ad,
                    'unit': item.get('birim', ''),
                    'quantity': item.get('miktar', 1.0),
                    'unit_price': 0.0,
                    'total_price': 0.0,
                    'price_source': 'training_data'
                })

            # Nakliye
            for item in training_output.get('nakliye', []):
                kod = item.get('kod', '')
                ad = item.get('ad', '')
                
                # Eğer ad boşsa kod üzerinden POZ_DATA'dan al
                if (not ad or len(ad.strip()) == 0) and kod and kod in poz_data:
                    ad = poz_data[kod].get('description', '')
                    print(f"[TRAINING NAME FIX] Nakliye '{kod}' → '{ad}'")
                
                components.append({
                    'type': 'Nakliye',
                    'code': kod,
                    'name': ad,
                    'unit': item.get('birim', ''),
                    'quantity': item.get('miktar', 1.0),
                    'unit_price': 0.0,
                    'total_price': 0.0,
                    'price_source': 'training_data'
                })

            result = {
                'suggested_unit': unit,
                'unit': unit,
                'explanation': f"Bu analiz eğitim verisinden direkt eşleşme ile bulundu (Benzerlik: {direct_match['similarity']:.0%}). "
                               f"Orijinal sorgu: \"{direct_match['input']}\". "
                               f"Birim fiyatlar POZ_DATA'dan eşleştirilecektir.",
                'components': components,
                'metadata': {
                    'source': 'direct_lookup',
                    'match_type': direct_match['match_type'],
                    'similarity': direct_match['similarity'],
                    'training_example': direct_match['input']
                }
            }

            # PDF verilerinden birim fiyatları eşleştir
            result = match_prices_from_poz_data(result)
            return result

    # ========================================
    # STEP 2: RAG + LLM
    # ========================================
    poz_data = get_poz_data()
    poz_context = build_poz_context(description, poz_data)
    feedback_context = build_feedback_context(description)

    training_rag_context = ""
    if training_service:
        training_rag_context = training_service.build_rag_context(description, top_k=3)

    # Context'leri birleştir (limit kontrolü ile)
    full_context = merge_contexts(poz_context, feedback_context, training_rag_context)

    # AI analizi al (gelişmiş modlar dahil)
    advanced_metrics = {}

    if use_consensus:
        # Çoklu model konsensüs modu
        try:
            consensus_service = ConsensusAnalysisService(service)
            result = asyncio.run(consensus_service.analyze_with_consensus(
                description, unit, full_context
            ))
            advanced_metrics["consensus_score"] = result.get("consensus_score", 0)
            advanced_metrics["model_count"] = result.get("model_count", 0)
            logger.info(f"Consensus analiz tamamlandı. Skor: {advanced_metrics['consensus_score']:.2f}")
        except Exception as e:
            logger.warning(f"Consensus analiz hatası, standart moda dönülüyor: {e}")
            result = service.generate_analysis(description, unit, full_context)

    elif use_self_consistency:
        # Self-consistency modu
        try:
            consistency_service = SelfConsistencyService(service, n_samples=3)
            result = asyncio.run(consistency_service.analyze_with_consistency(
                description, unit, full_context
            ))
            advanced_metrics["consistency_score"] = result.get("consistency_score", 0)
            advanced_metrics["sample_count"] = result.get("sample_count", 0)
            if result.get("warning"):
                advanced_metrics["consistency_warning"] = result.get("warning")
            logger.info(f"Self-consistency analiz tamamlandı. Skor: {advanced_metrics['consistency_score']:.2f}")
        except Exception as e:
            logger.warning(f"Self-consistency analiz hatası, standart moda dönülüyor: {e}")
            result = service.generate_analysis(description, unit, full_context)

    elif use_cot:
        # Chain-of-Thought modu (prompt genişletme)
        try:
            cot_service = ChainOfThoughtService()
            cot_prompt = cot_service.build_cot_prompt(description, unit, full_context)
            # CoT prompt'u ile standart servis çağır (temperature biraz yüksek)
            result = service.generate_analysis(description, unit, cot_prompt, temperature=0.15)
            advanced_metrics["cot_enabled"] = True
            logger.info("Chain-of-Thought analiz tamamlandı.")
        except Exception as e:
            logger.warning(f"CoT analiz hatası, standart moda dönülüyor: {e}")
            result = service.generate_analysis(description, unit, full_context)

    else:
        # Standart mod
        result = service.generate_analysis(description, unit, full_context)

    # Advanced metrics'i result'a ekle
    if advanced_metrics:
        result["advanced_metrics"] = advanced_metrics

    # Validasyonlar
    exclusions = check_exclusions(description)
    result["components"] = validate_beton_composition(result.get("components", []), description)
    result["components"] = validate_beton_betonarme(result.get("components", []), description)
    result["components"] = auto_add_kalip_if_needed(result.get("components", []), description, exclusions)
    
    # [NEW] Açıklama bazlı filtreleme: "Nakliye dahil" gibi ifadeleri kontrol et
    # Önce ana pozun kendisini kontrol et (eğer eşleşme varsa)
    excluded_services = set()
    
    # 1. Kullanıcı açıklamasından gelen filtreler
    excluded_services.update(extract_included_services(description))
    
    # 2. Seçilen bileşenlerin açıklamalarından gelen filtreler
    # Not: Bu adımda henüz POZ_DATA'dan tam açıklamaları çekmemiş olabiliriz, o yüzden match_prices_from_poz_data sonrası bir tur daha dönebiliriz.
    # Ancak maliyetli olmaması için burada basitçe yapıyoruz, detaylısı aşağıda.

    # Fiyat eşleştirme (Burada pozların gerçek açıklamaları doluyor)
    result = match_prices_from_poz_data(result)
    
    # 3. İkinci Tur Filtreleme: Dolu poz açıklamalarından gelen "dahil" hizmetlere göre neleri atacağımıza karar verelim
    final_components = []
    
    # Sırayla işle: Eğer bir bileşen "X dahil" diyorsa, SONRAKİ listedeki X silinmeli mi? 
    # Veya zaten eklenmiş X'ler silinmeli mi? 
    # Mevcut mantık: Ana kalemler genellikle baştadır. Ana kalem "nakliye dahil" diyorsa, alt kalemdeki nakliye silinir.
    
    current_excluded_services = excluded_services.copy()
    
    # Poz verisine erişim
    full_poz_data = get_poz_data()
    
    for comp in result.get("components", []):
        comp_code = comp.get('code', '')
        comp_name = comp.get('name', '')
        comp_type = comp.get('type', '')
        
        # Bu bileşen yasaklı listesinde mi?
        if should_exclude_component(comp_name, comp_type, current_excluded_services):
            print(f"[FILTER] '{comp_name}' ({comp_type}) filtrelendi. Sebepler: {current_excluded_services}")
            continue
            
        # Değilse listeye ekle
        final_components.append(comp)
        
        # Bu bileşenin kendisi yeni yasaklar getiriyor mu?
        # Poz açıklamasını bul
        item_description = comp_name # Varsayılan
        if comp_code and comp_code in full_poz_data:
            item_description = full_poz_data[comp_code].get('description', comp_name)
            
        new_exclusions = extract_included_services(item_description)
        if new_exclusions:
            print(f"[FILTER UPDATE] '{comp_name}' şunu içeriyor: {new_exclusions}")
            current_excluded_services.update(new_exclusions)
            
        # [NEW] Nakliye Miktar Doğrulaması (Density Check)
        if comp_type == "Nakliye" and comp_name:
            # Nakliyesi yapılan malzemeyi bulmaya çalış (basit sezgisel)
            # Genellikle "Beton nakli", "Kum nakli" gibi yazar.
            # Ana pozun kendisi de olabilir (örn: Hazır beton)
            
            target_material = None
            quantity_to_convert = 0.0
            unit_to_convert = ""
            
            # 1. Ana pozun kendisi mi taşınıyor?
            # E.g. description="Hazır beton", comp="Beton nakli" -> Match "beton"
            if "beton" in description.lower() and "beton" in comp_name.lower():
                target_material = "hazir_beton"
                # Ana poz miktarını bulmak lazım ama burada 'unit' var sadece.
                # AI result içinde 'quantity' yok, çünkü ana pozun miktarı kullanıcıdan (frontend) geliyor olabilir veya 1 birim kabul ediliyor.
                # Varsayım: Analiz 1 birim (1 m3, 1 m2) için yapılıyor.
                quantity_to_convert = 1.0 
                unit_to_convert = result.get("suggested_unit", unit)
                
            # 2. Bileşenin kendi içinde miktar var mı?
            # "0.31 ton çimento nakli" -> zaten ton, gerek yok.
            # "1 m3 beton nakli" -> m3 -> ton çevir.
            
            try:
                current_qty = float(comp.get("quantity", 0))
                current_unit = comp.get("unit", "")
                
                # Eğer birim m3 ise ve nakliye ise, tona çevirmeyi dene
                if current_unit in ["m3", "m³"] and target_material:
                     corrected_tonnage = calculate_transport_tonnage(target_material, current_qty, current_unit)
                     if corrected_tonnage:
                         print(f"[DENSITY FIX] {comp_name}: {current_qty} {current_unit} -> {corrected_tonnage:.3f} ton (Density service)")
                         comp["quantity"] = corrected_tonnage
                         comp["unit"] = "ton"
                         # Fiyatı güncellemek gerekir mi? Nakliye birim fiyatı genelde sabittir (mesafe bazlı).
                         # Tonaja dönünce "1 ton x 25 TL" formülü çalışır.
                         # Ancak AI m3 fiyatı verdiyse (örn: 1 m3=60 tl), biz bunu ton yaptık (2.4 ton).
                         # Fiyatı bölemeyiz çünkü veritabanı fiyatı ton başınadır (15.100.1001).
                         # Bu yüzden birim fiyatı POZ_DATA'dan (ton fiyatı) geliyorsa dokunma.
                         
            except Exception as e:
                print(f"Density fix error: {e}")

    result["components"] = final_components

    # Metadata ekle
    result["metadata"] = result.get("metadata", {})
    result["metadata"]["source"] = "rag_llm"
    result["metadata"]["poz_data_count"] = len(poz_data) if poz_data else 0
    result["metadata"]["context_provided"] = bool(poz_context)
    result["metadata"]["feedback_used"] = bool(feedback_context)
    result["metadata"]["training_rag_used"] = bool(training_rag_context)

    # Fiyat kaynağı istatistikleri
    price_sources = {"exact_code": 0, "similar_code": 0, "description": 0, "ai_generated": 0, "not_found": 0}
    for comp in result.get("components", []):
        src = comp.get("price_source", "not_found")
        if src == "exact_code_validated":
            src = "exact_code"
        if src in price_sources:
            price_sources[src] += 1

    result["metadata"]["price_sources"] = price_sources
    result["metadata"]["input_unit"] = unit
    result["metadata"]["suggested_unit"] = result.get("suggested_unit", unit)

    return result


# ============================================
# ASYNC ANALYSIS ENDPOINTS
# ============================================

@router.post("/analyze/async")
async def start_async_analysis(request: AsyncAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Asenkron AI analizi başlat.

    Sayfa değişse bile analiz arka planda devam eder.
    Job ID ile durumu ve sonucu sorgulayabilirsiniz.

    Returns:
        job_id: Analiz job'ının ID'si
    """
    job_id = str(uuid.uuid4())

    # Job'ı oluştur
    create_job(job_id, request.description)

    # Arka planda analizi başlat
    background_tasks.add_task(
        run_analysis_job,
        job_id,
        request.description,
        request.unit,
        request.context_data
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Analiz başlatıldı. Sayfa değişse bile işlem devam edecek.",
        "check_url": f"/api/ai/analyze/status/{job_id}",
        "result_url": f"/api/ai/analyze/result/{job_id}"
    }


@router.get("/analyze/status/{job_id}")
async def get_analysis_status(job_id: str):
    """
    Analiz job'ının durumunu sorgula.

    Status değerleri:
    - pending: Bekliyor
    - running: Çalışıyor
    - completed: Tamamlandı
    - failed: Hata oluştu
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadı")

    return {
        "job_id": job_id,
        "status": job["status"],
        "description": job["description"],
        "created_at": job["created_at"],
        "completed_at": job["completed_at"],
        "has_result": job["result"] is not None,
        "has_error": job["error"] is not None
    }


@router.get("/analyze/result/{job_id}")
async def get_analysis_result(job_id: str):
    """
    Tamamlanmış analiz sonucunu al.
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job bulunamadı")

    if job["status"] == "pending":
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Analiz henüz başlamadı"
        }

    if job["status"] == "running":
        return {
            "job_id": job_id,
            "status": "running",
            "message": "Analiz devam ediyor..."
        }

    if job["status"] == "failed":
        return {
            "job_id": job_id,
            "status": "failed",
            "error": job["error"]
        }

    # completed
    return {
        "job_id": job_id,
        "status": "completed",
        "result": job["result"]
    }


@router.get("/analyze/jobs")
async def list_analysis_jobs():
    """
    Aktif analiz job'larını listele.
    """
    # Eski job'ları temizle
    cleanup_old_jobs(24)

    with JOBS_LOCK:
        jobs = []
        for job_id, job in ANALYSIS_JOBS.items():
            jobs.append({
                "job_id": job_id,
                "status": job["status"],
                "description": job["description"][:50] + "..." if len(job["description"]) > 50 else job["description"],
                "created_at": job["created_at"]
            })

    return {"jobs": jobs, "total": len(jobs)}


@router.post("/refine-feedback")
async def refine_feedback(request: RefineRequest):
    """Kullanıcı geri bildirim açıklamasını iyileştir"""
    service = AIAnalysisService()
    try:
        refined_text = service.refine_feedback_description(request.text)
        return {"refined_text": refined_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine-request")
async def refine_request(request: RefineRequest):
    """Kullanıcının basit talebini profesyonel bir poz analiz talebine dönüştür"""
    service = AIAnalysisService()
    try:
        refined_text = service.refine_construction_request(request.text)
        return {"refined_text": refined_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReviewAnalysisRequest(BaseModel):
    description: str
    components: List[Dict[str, Any]]
    totals: Dict[str, Any]
    unit: str


@router.post("/review-analysis")
async def review_analysis(request: ReviewAnalysisRequest):
    """
    Mevcut bir analizi AI ile incele, eksiklikleri ve hataları tespit et.
    Eleştirmen AI: Mantık kontrolü, eksik kalem tespiti, fiyat anomalileri.
    """
    from services.critic_service import CriticService
    
    try:
        critic = CriticService()
        
        # Prepare analysis data for critic
        analysis_data = {
            "description": request.description,
            "unit": request.unit,
            "components": request.components,
            "totals": request.totals
        }
        
        # Run critic review (returns CriticReview dataclass)
        critic_review = critic.review_analysis(analysis_data, request.description)
        
        # Convert dataclass to dict
        critic_result = {
            "status": critic_review.status,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "suggestion": issue.suggestion
                }
                for issue in critic_review.issues
            ],
            "suggestions": critic_review.suggestions
        }
        
        # Calculate updated score based on issues
        issue_count = len(critic_result["issues"])
        critical_count = sum(1 for i in critic_result["issues"] if i["severity"] == "critical")
        
        base_score = 85
        score_penalty = (critical_count * 15) + ((issue_count - critical_count) * 5)
        updated_score = max(20, base_score - score_penalty)
        
        # Extract new warnings from issues
        new_warnings = [
            f"[{issue['category']}] {issue['message']}"
            for issue in critic_result["issues"][:3]  # Top 3 as warnings
        ]
        
        return {
            "critic_review": critic_result,
            "updated_score": updated_score,
            "new_warnings": new_warnings
        }
        
    except Exception as e:
        print(f"[AI REVIEW ERROR] {e}")
        # Fallback: return basic review
        return {
            "critic_review": {
                "status": "warning",
                "issues": [{
                    "severity": "warning",
                    "category": "Sistem",
                    "message": f"Analiz incelemesi tamamlanamadı: {str(e)}",
                    "suggestion": "Analizi manuel olarak kontrol edin."
                }],
                "suggestions": []
            },
            "updated_score": 60,
            "new_warnings": ["AI incelemesi tamamlanamadı, lütfen manuel kontrol yapın."]
        }



@router.post("/learn-rule")
def learn_rule(request: LearnRuleRequest):
    """
    Kullanıcının AI önerisini kalıcı bir kurala çevirmesini sağlar.
    """
    from services.rule_service import RuleService
    
    try:
        service = RuleService()
        
        # Basit bir required item yapısı oluştur
        required_items = [{
            "name": request.required_item_name,
            "type": "Malzeme" # Varsayılan olarak malzeme kabul ediyoruz, ileride geliştirilebilir
        }]
        
        rule_id = service.add_rule(
            trigger_keywords=request.trigger_keywords,
            required_items=required_items,
            condition_text=request.condition_text
        )
        
        return {"id": rule_id, "message": "Kural başarıyla öğrenildi."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# POZ DATA ERİŞİM FONKSİYONLARI
# ============================================

def get_poz_data() -> Dict[str, Any]:
    """main.py'den POZ_DATA'ya erişim - sys.modules üzerinden güncel referans"""
    import sys
    try:
        # Önce app.state'e erişmeyi dene (en güncel)
        if 'backend.main' in sys.modules:
            main_module = sys.modules['backend.main']
            if hasattr(main_module, 'app'):
                app_state = getattr(main_module.app, 'state', None)
                if app_state and hasattr(app_state, 'poz_data'):
                    return app_state.poz_data

        # Sys.modules üzerinden güncel modüle eriş (fallback)
        if 'main' in sys.modules:
            return sys.modules['main'].__dict__.get('POZ_DATA', {})
        elif 'backend.main' in sys.modules:
            return sys.modules['backend.main'].__dict__.get('POZ_DATA', {})
        else:
            # Modül henüz yüklenmemiş, import et ve eriş
            import backend.main as main_module
            return main_module.__dict__.get('POZ_DATA', {})
    except Exception as e:
        print(f"POZ_DATA erişim hatası: {e}")
        return {}


def get_training_service():
    """main.py'den TRAINING_DATA_SERVICE'e erişim"""
    import sys
    try:
        # Önce app.state'e erişmeyi dene (en güncel)
        if 'backend.main' in sys.modules:
            main_module = sys.modules['backend.main']
            if hasattr(main_module, 'app'):
                app_state = getattr(main_module.app, 'state', None)
                if app_state and hasattr(app_state, 'training_data_service'):
                    return app_state.training_data_service

        # Sys.modules üzerinden güncel modüle eriş (fallback)
        if 'main' in sys.modules:
            return sys.modules['main'].__dict__.get('TRAINING_DATA_SERVICE')
        elif 'backend.main' in sys.modules:
            return sys.modules['backend.main'].__dict__.get('TRAINING_DATA_SERVICE')
        else:
            # Modül henüz yüklenmemiş, import et ve eriş
            import backend.main as main_module
            return main_module.__dict__.get('TRAINING_DATA_SERVICE')
    except Exception as e:
        print(f"TRAINING_DATA_SERVICE erişim hatası: {e}")
        return None


def parse_price(price_str: str) -> float:
    """Türkçe formatlı fiyatı float'a çevir (1.234,56 -> 1234.56)"""
    if not price_str:
        return 0.0
    try:
        cleaned = str(price_str).replace('.', '').replace(',', '.')
        return float(cleaned)
    except:
        return 0.0


# ============================================
# CONTEXT OLUŞTURMA (AI'ya gönderilecek veri)
# ============================================

def calculate_similarity(text1: str, text2: str) -> float:
    """İki metin arasındaki benzerlik oranını hesapla (0-1)"""
    if not text1 or not text2:
        return 0.0
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    return SequenceMatcher(None, text1, text2).ratio()


def extract_keywords(description: str) -> List[str]:
    """Açıklamadan anahtar kelimeleri çıkar"""
    # Türkçe stop words
    stop_words = {'ve', 'ile', 'için', 'bir', 'bu', 'de', 'da', 'den', 'dan', 'nin', 'nın', 'ın', 'in'}

    words = description.lower().replace('/', ' ').replace('-', ' ').split()
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
    return keywords


# ============================================
# SEMANTİK ETİKET SİSTEMİ
# ============================================

# Malzeme ve imalat türleri için semantik etiket mapping
SEMANTIC_TAGS = {
    # BETON TİPLERİ (EN YÜKSEK ÖNCELİK!)
    'hazir_beton': [
        'santral', 'santrali', 'santraldan', 'santralle', 'hazır beton',
        'dökme', 'pompa', 'pompala', 'mikserde', 'mikserli', 'beton döküm',
        'beton dökülmesi', 'dökülen', 'betonu', 'hazır', 'betonarme beton'
    ],
    'beton_harci': [
        'harcı', 'karım', 'karışım', 'karıştır', 'elle', 'şantiye',
        'torbadan', 'torba', 'çimento karışım', 'şantiye betonu'
    ],

    # BETON SINIFLARI
    'c20': ['c20', 'c20/25', 'c 20', 'c-20'],
    'c25': ['c25', 'c25/30', 'c 25', 'c-25'],
    'c30': ['c30', 'c30/37', 'c 30', 'c-30'],
    'c35': ['c35', 'c35/45', 'c 35', 'c-35'],

    # BETON ÇEŞİTLERİ
    'betonarme': ['betonarme', 'donatılı', 'donatı', 'hasır', 'armatürlü', 'nervürlü', 'çelik'],
    'yalin_beton': ['yalın', 'düz', 'donatısız', 'armatürsüz'],

    # DEMİR/ÇELİK
    'demir': ['demir', 'nervürlü', 's420', 's400', 'betonarme çeliği', 'donatı çeliği'],

    # KALIP TÜRLERİ
    'kalip_ahsap': ['ahşap kalıp', 'tahta kalıp', 'kereste'],
    'kalip_metal': ['metal kalıp', 'çelik kalıp', 'profil'],

    # DUVAR MALZEMELERİ
    'tugla': ['tuğla', 'yatay delikli', 'düşey delikli', 'briket'],
    'gazbeton': ['gazbeton', 'ytong', 'siporeks', 'bims'],

    # AGREGA
    'kum': ['kum', 'ince agrega', '0-5'],
    'cakil': ['çakıl', 'iri agrega', '5-15', '15-30'],

    # İŞÇİLİK TÜRLERİ
    'usta': ['usta', 'ustası', 'kalfa'],
    'yardimci': ['yardımcı', 'amele', 'işçi'],

    # İMALAT YÖNTEMLERİ
    'makine': ['makine', 'mekanik', 'vinç', 'ekskavatör', 'kazıcı', 'kepçe'],
    'elle': ['elle', 'el', 'manuel', 'insan gücü'],

    # İMALAT TİPLERİ
    'kazi': ['kazı', 'hafriyat', 'kazma', 'temel kazı'],
    'dolgu': ['dolgu', 'doldurma', 'iksa'],
    'orgu': ['örgü', 'örme', 'duvar'],
    'kaplama': ['kaplama', 'kaplı', 'döşeme'],
    'siva': ['sıva', 'sıvama', 'harç'],
    'boya': ['boya', 'boyama', 'badana'],

    # NAKLİYE
    'nakliye': ['nakliye', 'taşıma', 'taşınması', 'sevk'],

    # KANAL/BORU TİPLERİ
    'trapez_kanal': ['trapez', 'trapeze', 'kanal'],
    'boru': ['boru', 'borulu', 'pvc', 'hdpe', 'pprc'],
}


def extract_semantic_tags(text: str) -> List[str]:
    """
    Metinden semantik etiketler çıkar.
    Örnek: "beton santrali ile dökülen c25" -> ['hazir_beton', 'c25', 'betonarme']
    """
    if not text:
        return []

    text_lower = text.lower()
    found_tags = []

    for tag, keywords in SEMANTIC_TAGS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_tags.append(tag)
                break  # Aynı tag'i birden fazla ekleme

    return found_tags


def calculate_tag_match_score(user_tags: List[str], poz_tags: List[str]) -> float:
    """
    İki etiket listesi arasındaki eşleşme skorunu hesapla.
    """
    if not user_tags or not poz_tags:
        return 0.0

    # Kesişim / Birleşim oranı (Jaccard similarity)
    intersection = len(set(user_tags) & set(poz_tags))
    union = len(set(user_tags) | set(poz_tags))

    if union == 0:
        return 0.0

    return intersection / union


def truncate_context(context: str, max_chars: int, label: str = "context") -> str:
    """
    Context'i belirtilen karakter limitine göre kırp.
    Kırpma yapılırsa log'a yazar.
    """
    if not context or len(context) <= max_chars:
        return context

    truncated = context[:max_chars]
    # Son satırı tamamla (kesilmiş satır kalmasın)
    last_newline = truncated.rfind('\n')
    if last_newline > max_chars * 0.8:  # Son %20'de bir newline varsa oradan kes
        truncated = truncated[:last_newline]

    logger.warning(f"{label} kırpıldı: {len(context)} -> {len(truncated)} karakter")
    return truncated + "\n[... kırpıldı ...]"


def merge_contexts(poz_context: str, feedback_context: str, training_context: str) -> str:
    """
    Tüm context'leri birleştir ve toplam limiti aşmamayı garanti et.
    """
    # Her context'i kendi limitine göre kırp
    poz_ctx = truncate_context(poz_context, analysis_config.MAX_POZ_CONTEXT_CHARS, "POZ context")
    feedback_ctx = truncate_context(feedback_context, analysis_config.MAX_FEEDBACK_CONTEXT_CHARS, "Feedback context")
    training_ctx = truncate_context(training_context, analysis_config.MAX_TRAINING_RAG_CONTEXT_CHARS, "Training RAG context")

    # Birleştir
    parts = [p for p in [poz_ctx, feedback_ctx, training_ctx] if p]
    merged = "\n\n".join(parts)

    # Toplam limiti kontrol et
    if len(merged) > analysis_config.MAX_TOTAL_CONTEXT_CHARS:
        merged = truncate_context(merged, analysis_config.MAX_TOTAL_CONTEXT_CHARS, "Toplam context")

    return merged


def build_context_from_poz_data(description: str, unit: str, max_results: int = 15) -> str:
    """
    Poz tanımına göre POZ_DATA'dan benzer pozları bul ve AI için context oluştur.
    Semantik etiket sistemi ile daha akıllı eşleştirme yapar.
    """
    poz_data = get_poz_data()
    if not poz_data:
        return ""

    keywords = extract_keywords(description)
    user_tags = extract_semantic_tags(description)
    matches = []

    # ---------------------------------------------------------
    # HİBRİT ARAMA: Vector DB -> Semantic Re-ranking
    # ---------------------------------------------------------
    from services.vector_db_service import VectorDBService
    vector_service = VectorDBService()

    # Lazy ingestion: İlk kullanımda arka planda veri yükle
    if not vector_service.is_ready() and not vector_service._ingestion_started:
        import sys
        if 'backend.main' in sys.modules:
            main_module = sys.modules['backend.main']
            if hasattr(main_module, 'app'):
                app_state = getattr(main_module.app, 'state', None)
                if app_state and hasattr(app_state, 'poz_data_for_vector'):
                    vector_service.lazy_ingest(app_state.poz_data_for_vector)

    # 1. Aday Havuzu Oluştur (Vector Search)
    candidates = []

    # Vector DB'den adayları çek (limit config'den)
    vector_results = vector_service.search(description, n_results=analysis_config.VECTOR_SEARCH_LIMIT)

    if vector_results:
        logger.info(f"Vector DB'den {len(vector_results)} aday bulundu")
        for res in vector_results:
            if res['code'] in poz_data:
                candidates.append(poz_data[res['code']])
    else:
        logger.warning("Vector DB boş, tam tarama yapılıyor (yavaş)")
        candidates = list(poz_data.values())

    # 2. Adayları Puanla (Semantic Re-ranking)
    for poz_info in candidates:
        poz_no = poz_info.get('poz_no', '')
        poz_desc = poz_info.get('description', '')
        poz_unit = poz_info.get('unit', '')
        poz_tags = extract_semantic_tags(poz_desc)

        # Benzerlik puanı hesapla (ağırlıklı sistem)
        score = 0

        # ... (Existing scoring logic below)
        
        # 1. SEMANTİK ETİKET EŞLEŞMESİ (EN ÖNEMLİ!)
        tag_match_score = calculate_tag_match_score(user_tags, poz_tags)
        score += tag_match_score * 100  # En yüksek ağırlık

        # 2. Açıklama benzerliği
        # Eğer vector search'ten geldiyse zaten benzerdir, ama yine de hesapla
        desc_similarity = calculate_similarity(description, poz_desc)
        score += desc_similarity * 40

        # 3. Anahtar kelime eşleşmesi
        poz_desc_lower = poz_desc.lower()
        keyword_matches = sum(1 for kw in keywords if kw in poz_desc_lower)
        score += keyword_matches * 8

        # 4. Birim eşleşmesi
        if unit and unit.lower() != "otomatik" and unit.lower() == poz_unit.lower():
            score += 15

        # 5. Kritik etiket bonusları (özel durumlar)
        # ... (Existing tag logic) ...
        # Eğer kullanıcı "hazır beton" arıyorsa ve poz da "hazır beton" içeriyorsa
        if 'hazir_beton' in user_tags and 'hazir_beton' in poz_tags:
            score += 50

        # Eğer kullanıcı "beton harcı" arıyorsa ama poz "hazır beton" ise ceza ver (ters eşleşme)
        if 'beton_harci' in user_tags and 'hazir_beton' in poz_tags:
            score -= 40

        # Tam tersi: Kullanıcı "hazır beton" arıyorsa ama poz "beton harcı" ise ceza ver
        if 'hazir_beton' in user_tags and 'beton_harci' in poz_tags:
            score -= 40

        # Trapez kanal araması için bonus
        if 'trapez_kanal' in user_tags and 'trapez_kanal' in poz_tags:
            score += 40

        # Beton sınıfı eşleşmeleri için bonus
        for concrete_class in ['c20', 'c25', 'c30', 'c35']:
            if concrete_class in user_tags and concrete_class in poz_tags:
                score += 30

        # Betonarme vs yalın beton ayrımı
        if 'betonarme' in user_tags and 'betonarme' in poz_tags:
            score += 35
        if 'yalin_beton' in user_tags and 'yalin_beton' in poz_tags:
            score += 35

        # Kalıp tipi eşleşmeleri
        if 'kalip_ahsap' in user_tags and 'kalip_ahsap' in poz_tags:
            score += 25
        if 'kalip_metal' in user_tags and 'kalip_metal' in poz_tags:
            score += 25

        # İmalat yöntemi eşleşmeleri
        if 'makine' in user_tags and 'makine' in poz_tags:
            score += 20
        if 'elle' in user_tags and 'elle' in poz_tags:
            score += 20

        if score > 5:  # Minimum eşik
            matches.append({
                'poz_no': poz_no,
                'description': poz_desc,
                'unit': poz_unit,
                'unit_price': poz_info.get('unit_price', '0'),
                'score': score,
                'tags': poz_tags  # Debug için
            })

    # En yüksek puanlıları al
    matches.sort(key=lambda x: x['score'], reverse=True)
    top_matches = matches[:max_results]

    if not top_matches:
        return ""

    # Context string oluştur
    context_lines = ["MEVCUT VERİTABANINDAN BULUNAN BENZER POZLAR:"]
    context_lines.append("=" * 60)

    # Kullanıcının aradığı etiketleri göster
    if user_tags:
        context_lines.append(f"\n🏷️ ARANAN ÖZELLİKLER: {', '.join(user_tags)}")
        context_lines.append("")

    # Kategorilere ayır
    materials = []
    labor = []
    transport = []
    other = []

    for m in top_matches:
        poz_no = m['poz_no']
        if poz_no.startswith('10.') or poz_no.startswith('15.') or poz_no.startswith('04.'):
            materials.append(m)
        elif poz_no.startswith('01.') or poz_no.startswith('02.'):
            labor.append(m)
        elif poz_no.startswith('07.'):
            transport.append(m)
        else:
            other.append(m)

    if materials:
        context_lines.append("\n📦 MALZEMELER:")
        for m in materials[:5]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if labor:
        context_lines.append("\n👷 İŞÇİLİKLER:")
        for m in labor[:4]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if transport:
        context_lines.append("\n🚚 NAKLİYE:")
        for m in transport[:3]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    if other:
        context_lines.append("\n📋 DİĞER İLGİLİ POZLAR:")
        for m in other[:3]:
            price = parse_price(m['unit_price'])
            context_lines.append(f"  • {m['poz_no']}: {m['description'][:50]} = {price:,.2f} TL/{m['unit']}")

    context_lines.append("\n" + "=" * 60)
    context_lines.append("NOT: Yukarıdaki fiyatlar 2025 yılı Çevre ve Şehircilik Bakanlığı rayiçleridir.")
    context_lines.append("Analiz oluştururken bu fiyatları referans alın.")

    return "\n".join(context_lines)


# ============================================
# FEEDBACK CONTEXT (Kullanıcı Düzeltmelerinden Öğrenme)
# ============================================

def build_feedback_context(description: str, unit: str) -> str:
    """
    Benzer sorgular için geçmiş kullanıcı düzeltmelerini context olarak hazırla.
    Bu sayede AI, daha önce yapılan hatalardan öğrenir.
    """
    feedback_list = db.get_relevant_feedback(description, unit, limit=3)

    if not feedback_list:
        return ""

    context_lines = [
        "\n" + "=" * 60,
        "⚠️ ÖNCEKİ KULLANICI DÜZELTMELERİ (ÖNEMLİ!):",
        "=" * 60,
        "Aşağıdaki düzeltmeler benzer sorgular için yapılmıştır.",
        "Bu bilgileri DİKKATE AL ve aynı hataları TEKRARLAMA!\n"
    ]

    for i, fb in enumerate(feedback_list, 1):
        try:
            components = fb.get('correct_components', [])
            if isinstance(components, str):
                components = json.loads(components)
        except:
            components = []

        context_lines.append(f"📝 Düzeltme #{i}:")
        context_lines.append(f"   Orijinal sorgu: \"{fb.get('original_prompt', '')}\"")
        context_lines.append(f"   Sorun: {fb.get('correction_description', '')}")

        if components:
            context_lines.append(f"   Doğru bileşenler:")
            for comp in components[:5]:  # Max 5 bileşen göster
                context_lines.append(
                    f"     • {comp.get('type', '')}: {comp.get('name', '')} "
                    f"({comp.get('quantity', 0)} {comp.get('unit', '')}) = {comp.get('unit_price', 0)} TL"
                )

        context_lines.append("")

        # Kullanım sayısını artır
        if fb.get('id'):
            try:
                db.increment_feedback_use_count(fb['id'])
            except:
                pass

    context_lines.append("=" * 60)
    context_lines.append("YUKARIDAKİ DÜZELTMELERİ DİKKATE AL!")
    context_lines.append("=" * 60)

    return "\n".join(context_lines)


# ============================================
# FİYAT EŞLEŞTİRME FONKSİYONLARI
# ============================================

def find_price_by_code(code: str, poz_data: Dict) -> Optional[float]:
    """Poz koduna göre doğrudan fiyat bul"""
    if code in poz_data:
        return parse_price(poz_data[code].get('unit_price', '0'))
    return None


def find_price_by_similar_code(code: str, poz_data: Dict) -> Optional[float]:
    """Benzer poz koduna göre fiyat bul (örn: 15.150.1001 için 15.150.* ara)"""
    if not code:
        return None

    parts = code.split('.')
    best_match = None
    best_score = 0

    for poz_no, poz_info in poz_data.items():
        poz_parts = poz_no.split('.')

        score = 0
        for i, part in enumerate(parts):
            if i < len(poz_parts) and poz_parts[i] == part:
                score += 1
            else:
                break

        if score >= 2 and score > best_score:
            best_match = poz_info
            best_score = score

    if best_match:
        return parse_price(best_match.get('unit_price', '0'))
    return None


def normalize_for_search(text: str) -> str:
    """Arama için metni normalize et (boşlukları sil, küçük harf yap)"""
    if not text:
        return ""
    return text.lower().replace(" ", "").replace("\t", "")

def find_price_by_description(name: str, unit: str, poz_data: Dict) -> Optional[float]:
    """Açıklama benzerliğine göre fiyat bul"""
    if not name:
        return None

    best_match = None
    best_score = 0.0

    keywords = extract_keywords(name)
    name_norm = normalize_for_search(name)

    for poz_no, poz_info in poz_data.items():
        poz_desc = poz_info.get('description', '')
        poz_unit = poz_info.get('unit', '')

        # 1. Normalize edilmiş tam eşleşme (boşluksuz)
        # Örn: "C 25/30" vs "C25/30"
        desc_norm = normalize_for_search(poz_desc)
        if name_norm in desc_norm or desc_norm in name_norm:
            # Birim de tutuyorsa bu çok güçlü bir eşleşmedir
            if unit.lower() == poz_unit.lower():
                return parse_price(poz_info.get('unit_price', '0'))

        # 2. Benzerlik hesapla
        similarity = calculate_similarity(name, poz_desc)

        # Anahtar kelime bonusu
        poz_desc_lower = poz_desc.lower()
        keyword_bonus = sum(0.1 for kw in keywords if kw in poz_desc_lower)

        # Birim bonusu
        unit_bonus = 0.15 if unit.lower() == poz_unit.lower() else 0

        total_score = similarity + keyword_bonus + unit_bonus

        # --- FİYAT KAYNAĞI FİLTRESİ ---

        # 1. MAKİNE ALIM FİYATLARI (10.120.xxxx) SADECE "SATIN", "MAKİNE", "ALIMI" GİBİ İFADELER VARSA KULLANILSIN
        if poz_no.startswith('10.120.'):
            is_machine_requested = any(kw in name.lower() for kw in ['makine', 'vinç', 'kamyon', 'satın', 'alım'])
            if not is_machine_requested:
                total_score -= 2.0  # Ceza artırıldı (0.8 → 2.0)

        # 1a. NAKLİYE İÇİN MAKİNE ALIM KODLARI ASLA KULLANILMASIN!
        if 'nakliye' in name.lower() or 'taşıma' in name.lower():
            if poz_no.startswith('10.120.'):
                total_score -= 10.0  # Kesin engelle

        # 2. NAKLİYE İÇİN KOD BONUSU
        # UYARI: Sadece POZ açıklamasında da nakliye/taşıma geçiyorsa bonus ver!
        if "nakliye" in name.lower() or "taşıma" in name.lower():
            # POZ açıklamasında da nakliye varsa bonus ver
            if any(kw in poz_desc_lower for kw in ['nakliye', 'taşıma', 'nakil', 'yükleme', 'boşaltma']):
                if poz_no.startswith('15.') or poz_no.startswith('07.'):
                    total_score += 0.4
            elif poz_no.startswith('10.120.'):
                total_score -= 1.0 

        # 3. İŞÇİLİK İÇİN KOD BONUSU
        if "işçi" in name.lower() or "usta" in name.lower():
            if poz_no.startswith('10.100.') or poz_no.startswith('01.'):
                total_score += 0.3

        # Fiyat 0 olan pozları atla
        poz_price = parse_price(poz_info.get('unit_price', '0'))
        if poz_price == 0:
            continue

        if total_score > best_score and total_score > 0.4:  # Minimum eşik
            best_match = poz_info
            best_score = total_score

    if best_match:
        matched_price = parse_price(best_match.get('unit_price', '0'))
        price_logger.info(f"'{name}' → {best_match.get('poz_no', 'N/A')} = {matched_price} TL (score: {best_score:.2f})")
        return {
            'price': matched_price,
            'code': best_match.get('poz_no'),
            'description': best_match.get('description')
        }
    return None


def find_price_by_similar_code(code: str, poz_data: Dict) -> Optional[Dict]:
    """Kod benzerliğine göre fiyat ve bilgi bul"""
    # 1. Tam kod (noktalarla)
    if code in poz_data:
        info = poz_data[code]
        return {
            'price': parse_price(info.get('unit_price', '0')),
            'code': code,
            'description': info.get('description')
        }
        
    # 2. Noktaları kaldırıp dene
    code_clean = code.replace('.', '')
    for p_code, info in poz_data.items():
        if p_code.replace('.', '') == code_clean:
             return {
                'price': parse_price(info.get('unit_price', '0')),
                'code': p_code,
                'description': info.get('description')
            }
            
    return None

# Eski fonksiyonu sarmala (geriye uyumluluk)
def find_price_by_description(name: str, unit: str, poz_data: Dict) -> float:
    res = find_price_and_info_by_description(name, unit, poz_data)
    return res['price'] if res else 0.0

def find_price_and_info_by_description(name: str, unit: str, poz_data: Dict, comp_type: str = '') -> Optional[Dict]:
    """
    Açıklama benzerliğine göre fiyat ve bilgi bul.
    find_price_by_description'ın güncel versiyonu - kod ve açıklama da döndürür.
    """
    if not name:
        return None

    best_match = None
    best_score = 0.0

    keywords = extract_keywords(name)
    name_norm = normalize_for_search(name)

    for poz_no, poz_info in poz_data.items():
        poz_desc = poz_info.get('description', '')
        poz_unit = poz_info.get('unit', '')

        # 1. Normalize edilmiş tam eşleşme
        desc_norm = normalize_for_search(poz_desc)
        if name_norm in desc_norm or desc_norm in name_norm:
            if unit.lower() == poz_unit.lower():
                return {
                    'price': parse_price(poz_info.get('unit_price', '0')),
                    'code': poz_no,
                    'description': poz_desc
                }

        # 2. Benzerlik hesapla
        similarity = calculate_similarity(name, poz_desc)

        # Anahtar kelime bonusu
        poz_desc_lower = poz_desc.lower()
        keyword_bonus = sum(0.1 for kw in keywords if kw in poz_desc_lower)

        # Birim bonusu
        unit_bonus = 0.15 if unit.lower() == poz_unit.lower() else 0

        total_score = similarity + keyword_bonus + unit_bonus

        # Fiyat kaynak filtreleri
        if poz_no.startswith('10.120.'):
            is_machine_requested = any(kw in name.lower() for kw in ['makine', 'vinç', 'kamyon', 'satın', 'alım'])
            if not is_machine_requested:
                total_score -= 2.0

        if 'nakliye' in name.lower() or 'taşıma' in name.lower():
            if poz_no.startswith('10.120.'):
                total_score -= 10.0

        if "nakliye" in name.lower() or "taşıma" in name.lower():
            if any(kw in poz_desc_lower for kw in ['nakliye', 'taşıma', 'nakil', 'yükleme', 'boşaltma']):
                if poz_no.startswith('15.') or poz_no.startswith('07.'):
                    total_score += 0.4
            elif poz_no.startswith('10.120.'):
                total_score -= 1.0

        if "işçi" in name.lower() or "usta" in name.lower():
            if poz_no.startswith('10.100.') or poz_no.startswith('01.'):
                total_score += 0.3

        poz_price = parse_price(poz_info.get('unit_price', '0'))
        if poz_price == 0:
            continue

        if total_score > best_score and total_score > 0.4:
            best_match = poz_info
            best_score = total_score

    if best_match:
        matched_price = parse_price(best_match.get('unit_price', '0'))
        price_logger.info(f"'{name}' → {best_match.get('poz_no', 'N/A')} = {matched_price} TL (score: {best_score:.2f})")
        return {
            'price': matched_price,
            'code': best_match.get('poz_no'),
            'description': best_match.get('description')
        }
    return None


def match_prices_from_poz_data(result: Dict) -> Dict:
    """
    AI analiz sonuçlarındaki bileşenler için POZ_DATA'dan birim fiyatları eşleştir.
    Çoklu strateji kullanır: kod eşleşmesi -> benzer kod -> açıklama benzerliği
    """
    poz_data = get_poz_data()

    if not poz_data or "components" not in result:
        return result

    for comp in result["components"]:
        code = comp.get("code", "")
        name = comp.get("name", "")
        unit = comp.get("unit", "")
        current_price = float(comp.get("unit_price", 0))

        matched_price = None
        match_method = None
        
        # Strateji 0: Var olan kodu DOĞRULA
        # Eğer kod varsa ama açıklaması tamamen alakasızsa, bu kodu reddet!
        is_code_valid = False
        if code in poz_data:
            db_desc = poz_data[code].get('description', '')
            # Basit benzerlik kontrolü
            sim = calculate_similarity(name, db_desc)
            
            # Özel Durum: Beton sınıfları (C25/30 vb) için daha esnek ol
            if "beton" in name.lower() and "beton" in db_desc.lower():
                # Beton sınıfı kontrolü
                name_norm = normalize_for_search(name)
                db_norm = normalize_for_search(db_desc)
                if "c20" in name_norm and "c20" in db_norm: sim = 1.0
                elif "c25" in name_norm and "c25" in db_norm: sim = 1.0
                elif "c30" in name_norm and "c30" in db_norm: sim = 1.0
            
            # Keyif Kaçıran Kelime Kontrolü (Keyword Mismatch)
            # Eğer DB açıklamasında kritik kelimeler var ama aranan isimde yoksa ceza ver
            critical_keywords = ['demir', 'kalıp', 'beton', 'iskele', 'duvar', 'alçı', 'boya', 'seramik', 'tesisat']
            name_lower = name.lower()
            db_desc_lower = db_desc.lower()
            
            for k in critical_keywords:
                if k in db_desc_lower and k not in name_lower:
                    # Kritik kelime uyumsuzluğu (örn: Demirci kodu ama Kalıpçı aranıyor)
                    sim -= 0.3 # Ciddi ceza
            
            if sim > 0.45: # Eşik değer artırıldı (0.3 -> 0.45)
                is_code_valid = True
            else:
                print(f"[AI VALIDATION] Kod reddedildi: {code} ({name}) != DB: {db_desc} (Sim: {sim:.2f})")
                code = "" # Kodu sil ki aşağıda açıklama ile arasın

        # Strateji 1: Doğrudan kod eşleşmesi (Validasyondan geçtiyse)
        if is_code_valid:
            matched_price = parse_price(poz_data[code].get('unit_price', '0'))
            # Eğer AI, "Açıklama girin" dediyse veya isim çok kısaysa, veritabanından TAM ismini al
            if 'description' in poz_data[code]:
                db_name = poz_data[code]['description']
                # Nakliye kalemlerinde açıklama özel olabilir (formül vs.), dokunma
                if comp.get('type') != 'Nakliye':
                    # Geliştirilmiş kontrol: Boş, kısa veya genel isimler
                    name_lower = name.lower() if name else ""
                    is_invalid_name = (
                        not name or  # Boş
                        len(name) < 5 or  # Çok kısa
                        name == "Açıklama girin" or  # Tam eşleşme
                        "açıklama" in name_lower or  # İçeriyor
                        "girin" in name_lower or  # "girin" kelimesi
                        name_lower.strip() == "" or  # Sadece boşluk
                        name == "N/A" or  # Placeholder
                        name == "-"  # Tire
                    )
                    
                    if is_invalid_name:
                        comp["name"] = db_name
                        print(f"[NAME FIX] '{name}' → '{db_name}'")

            if matched_price > 0:
                match_method = "exact_code_validated"

        # Strateji 2: Benzer kod eşleşmesi
        if (not matched_price or matched_price == 0) and code:
            matched_code_info = find_price_by_similar_code(code, poz_data)
            if matched_code_info:
                matched_price = matched_code_info.get('price', 0)
                # Kodu da güncelle
                if matched_code_info.get('code'):
                    comp["code"] = matched_code_info.get('code')
                    # Eğer isim eksikse ismi de güncelle
                    if not name or name in ["Açıklama girin", ""] or "açıklama" in name.lower():
                        comp["name"] = matched_code_info.get('description', name)
                
                if matched_price and matched_price > 0:
                    match_method = "similar_code"

        # Strateji 3: Açıklama benzerliği
        if not matched_price or matched_price == 0:
            match_result = find_price_and_info_by_description(name, unit, poz_data, comp.get('type', ''))
            if match_result:
                matched_price = match_result.get('price', 0)
                if matched_price and matched_price > 0:
                    match_method = "description"
                    # Kod ve ismi de güncelle
                    comp["code"] = match_result.get('code', comp.get('code'))
                    # Nakliye değilse ismi güncelle (Nakliye açıklaması özel oluyor genelde)
                    if not comp.get('type') == 'Nakliye' and (not name or name in ["Açıklama girin", ""] or "açıklama" in name.lower()):
                         comp["name"] = match_result.get('description', name)

        # Fiyatı güncelle
        if matched_price and matched_price > 0:
            comp["unit_price"] = matched_price
            comp["price_source"] = match_method
        elif current_price > 0:
            comp["price_source"] = "ai_generated"
        else:
            comp["price_source"] = "not_found"

        # Tutarı hesapla
        quantity = float(comp.get("quantity", 0))
        unit_price = float(comp.get("unit_price", 0))
        comp["total_price"] = round(quantity * unit_price, 2)

    return result


# ============================================
# ANA API ENDPOINT
# ============================================


# ============================================
# VALIDATION LOGIC (Beton/Betonarme Kontrolü)
# ============================================

def check_exclusions(description: str) -> Dict[str, bool]:
    """
    Poz tanımında 'hariç' olan kalemleri tespit et.

    Args:
        description: Poz tanımı metni

    Returns:
        Dict with exclusion flags for kalip, demir, kazi

    Examples:
        "beton döküm (kalıp hariç)" → {'kalip_haric': True, 'demir_haric': False, ...}
    """
    desc_lower = description.lower()

    return {
        'kalip_haric': any(pattern in desc_lower for pattern in [
            'kalıp hariç',
            'kalıp bedeli hariç',
            'kalıp dahil değil',
            'kalıpsız',
            'kalıp ve',  # "kalıp ve demir hariç" gibi
            'kalıp,',    # "kalıp, demir hariç" gibi
        ]) and 'hariç' in desc_lower,

        'demir_haric': (
            any(pattern in desc_lower for pattern in [
                'demir hariç',
                'demir bedeli hariç',
                'donatı hariç',
                'donatısız',
                'demir donatı hariç',
                'armatür hariç',
            ]) or
            # Virgül veya "ve" ile ayrılmış liste kontrolü
            (('demir' in desc_lower or 'donatı' in desc_lower) and
             ('hariç' in desc_lower or 'dahil değil' in desc_lower))
        ) and 'hariç' in desc_lower,

        'kazi_haric': any(pattern in desc_lower for pattern in [
            'kazı hariç',
            'kazı bedeli hariç',
            'hafriyat hariç',
            'kazı ve',
            'kazı,',
        ]) and 'hariç' in desc_lower
    }


def validate_formwork_duplication(components: List[Dict], description: str) -> List[Dict]:
    """
    Eğer özel kalıp pozu varsa (Trapez vb.), genel ahşap/çelik kalıp pozunu kaldır.
    """
    if not components: return components

    # Özel kalıp var mı? (Kanal, Tünel, Perde, Kolon POZLARI)
    # Genelde ismi '... kalıbı' şeklinde biten ama 'ahşap/çelik/plastik kalıp' olmayanlar.
    special_formwork = False
    for comp in components:
        name_lower = comp.get('name', '').lower()
        # 'kanal kalıbı', 'tünel kalıbı', 'perde kalıbı' vb.
        if 'kalıp' in name_lower and any(x in name_lower for x in ['kanal', 'tünel', 'perde', 'kolon', 'kiriş']) and 'işçilik' not in comp.get('type', '').lower():
            # Ahşap/Çelik kelimesi GEÇMİYORSA veya "Trapez Kesitli" gibi özel bir ifade varsa
            if 'trapez' in name_lower or 'tünel' in name_lower:
                special_formwork = True
                break
            
    if special_formwork:
        # Genel kalıpları sil (Ahşap Kalıp, Çelik Kalıp)
        new_components = []
        for comp in components:
            name_lower = comp.get('name', '').lower()
            code = comp.get('code', '')
            
            # Silinecek genel kalıplar
            if name_lower.strip() in ['ahşap kalıp', 'saç kalıp', 'çelik kalıp', 'plastik kalıp', 'kontrplak kalıp'] or \
               code in ['15.180.1001', '15.180.1002']:
                validation_logger.info(f"Mükerrer kalıp kaldırıldı: {comp['name']} ({code})")
                continue
                
            new_components.append(comp)
            
        return new_components
        
    return components


def validate_beton_composition(components: List[Dict], description: str) -> List[Dict]:
    """
    Beton kompozisyon kontrolü ve düzeltme.

    SORUNLAR:
    1. Hazır beton + Çimento/Kum/Çakıl birlikte olmamalı
    2. Grobeton ayrı bir malzeme olarak eklenmeli
    3. Kalıp miktarı 0 olmamalı
    """
    if not components:
        return components

    desc_lower = description.lower()

    # 1. HAZIR BETON KONTROLÜ
    has_hazir_beton = any(
        'hazır beton' in comp.get('name', '').lower() or
        'hazir beton' in comp.get('name', '').lower() or
        comp.get('code', '').startswith('15.150.')
        for comp in components if comp.get('type', '').lower() == 'malzeme'
    )

    if has_hazir_beton:
        validation_logger.debug("Hazır beton tespit edildi")

        # Çimento, kum, çakıl varsa KALDIR
        original_count = len(components)
        components = [
            comp for comp in components
            if not (comp.get('type', '').lower() == 'malzeme' and
                   comp.get('code', '') in ['10.130.1202', '10.130.1004', '10.130.1001'])
        ]

        if len(components) < original_count:
            removed = original_count - len(components)
            validation_logger.info(f"{removed} gereksiz malzeme kaldırıldı (çimento/kum/çakıl - hazır beton kullanılıyor)")

    # 2. GROBETON KONTROLÜ
    has_grobeton_keyword = any(kw in desc_lower for kw in ['grobeton', 'düşük kaliteli beton', 'taban betonu'])

    if has_grobeton_keyword:
        validation_logger.debug("Grobeton kelimesi tespit edildi")

        # Grobeton malzemesi var mı kontrol et
        has_grobeton_material = any(
            'grobeton' in comp.get('name', '').lower() or
            ('c15' in comp.get('name', '').lower() or 'c20' in comp.get('name', '').lower())
            for comp in components if comp.get('type', '').lower() == 'malzeme'
        )

        if not has_grobeton_material:
            validation_logger.warning("Grobeton malzemesi eksik - AI ayrı malzeme eklemeyi unutmuş olabilir")

    # 3. KALIP MİKTARI KONTROLÜ VE DÜZELTME
    kalip_components = [comp for comp in components if 'kalıp' in comp.get('name', '').lower()]

    # Önce beton miktarını bul
    beton_qty = 0.0
    for comp in components:
        if 'beton' in comp.get('name', '').lower() and comp.get('type', '').lower() == 'malzeme':
            beton_qty = comp.get('quantity', 0.0)
            break

    for kalip in kalip_components:
        if kalip.get('quantity', 0) == 0 and beton_qty > 0:
            # Kalıp miktarını beton miktarına göre hesapla
            # 1 m³ beton için yaklaşık 6 m² kalıp
            calculated_qty = round(beton_qty * 6.0, 2)
            kalip['quantity'] = calculated_qty
            kalip['total_price'] = round(calculated_qty * kalip.get('unit_price', 0), 2)
            kalip['notes'] = kalip.get('notes', '') + f' [MİKTAR DÜZELTME: {beton_qty:.2f} m³ beton × 6 m²/m³]'
            validation_logger.info(f"Kalıp miktarı düzeltildi: 0 → {calculated_qty} m² ({kalip.get('name', '')})")
        elif kalip.get('quantity', 0) == 0:
            validation_logger.warning(f"Kalıp miktarı 0: {kalip.get('name', '')} (beton miktarı da 0)")

    return components


def validate_beton_betonarme(components: List[Dict], description: str) -> List[Dict]:
    """
    Beton ve betonarme ayrımını kontrol et ve gerekirse düzelt.

    YENİ: "Hariç" kelime kontrolü eklendi!
    Eğer kullanıcı "kalıp hariç" veya "demir hariç" derse, bunları otomatik ekleme.

    Desktop uygulamasındaki mantığın aynısı + Exclusion kontrolü
    """
    if not components:
        return components

    desc_lower = description.lower()

    # 1. Hariç olan kalemleri tespit et
    exclusions = check_exclusions(description)

    # 2. Beton mu betonarme mi tespit et
    is_betonarme = any(keyword in desc_lower for keyword in [
        'betonarme', 'betonarm', 'donatı', 'donatılı', 'hasır', 'armatüre',
        'armature', 'reinforced', 'demir', 'nervürlü'
    ])

    # 3. "hariç" kelimeleri betonarme tespitini geçersiz kılar
    # Örnek: "beton kanal (demir hariç)" → Demir olmasın
    if exclusions['demir_haric']:
        is_betonarme = False  # Demir hariç denilmişse betonarme sayma

    is_beton = any(keyword in desc_lower for keyword in [
        'beton', 'concrete'
    ])

    # BETON (donatısız) ise
    if is_beton and not is_betonarme:
        # Demir varsa KALDIR
        original_count = len(components)
        components = [
            comp for comp in components
            if not any(kw in comp.get('name', '').lower() for kw in [
                'demir', 'donatı', 'nervürlü', 'hasır', 'çelik', 'armatür'
            ])
        ]

        if len(components) < original_count:
            validation_logger.info(f"{original_count - len(components)} demir kalemi kaldırıldı (beton donatısız)")

        # Kalıp var mı kontrol et
        has_kalip = any('kalıp' in comp.get('name', '').lower() for comp in components)
        has_beton = any('beton' in comp.get('name', '').lower() for comp in components if comp.get('type', '').lower() == 'malzeme')

        # Kalıp ekle (SADECE "kalıp hariç" denilmemişse)
        if has_beton and not has_kalip and not exclusions['kalip_haric']:
            # Beton miktarını bul ve kalıp miktarını hesapla
            beton_qty = 0.0
            for comp in components:
                if 'beton' in comp.get('name', '').lower() and comp.get('type', '').lower() == 'malzeme':
                    beton_qty = comp.get('quantity', 0.0)
                    break

            # Kalıp miktarı hesabı: 1 m³ beton için yaklaşık 6-8 m² kalıp
            # Kanal/trapez için 1 m uzunluk başına ~1.5-2 m² kalıp
            kalip_qty = beton_qty * 6.0 if beton_qty > 0 else 1.0  # m³ beton × 6 m²/m³

            components.append({
                'type': 'Malzeme',
                'code': '04.001.1001',
                'name': 'Ahşap Kalıp',
                'unit': 'm²',
                'quantity': round(kalip_qty, 2),
                'unit_price': 50.0,
                'total_price': round(kalip_qty * 50.0, 2),
                'price_source': 'validation_rule',
                'notes': f'[OTOMATIK EKLENDI] Beton için kalıp zorunludur ({beton_qty:.2f} m³ beton × 6 m²/m³)'
            })
            validation_logger.info(f"Kalıp otomatik eklendi: {kalip_qty:.2f} m² (beton için zorunlu)")
        elif has_beton and not has_kalip and exclusions['kalip_haric']:
            validation_logger.debug("Kalıp eklenmedi - kullanıcı 'kalıp hariç' belirtti")

    # BETONARME ise
    elif is_betonarme:
        # Zorunlu malzemeler kontrolü
        has_beton = any('beton' in comp.get('name', '').lower() for comp in components if comp.get('type', '').lower() == 'malzeme')
        has_demir = any(kw in comp.get('name', '').lower() for kw in ['demir', 'donatı', 'nervürlü', 'hasır', 'çelik'] for comp in components if comp.get('type', '').lower() == 'malzeme')
        has_kalip = any('kalıp' in comp.get('name', '').lower() for comp in components)

        # Demir ekle (SADECE "demir hariç" denilmemişse)
        if has_beton and not has_demir and not exclusions['demir_haric']:
            components.append({
                'type': 'Malzeme',
                'code': '10.140.1001',
                'name': 'Nervürlü Betonarme Çeliği S420',
                'unit': 'ton',
                'quantity': 0.0,
                'unit_price': 25000.0,
                'total_price': 0.0,
                'price_source': 'validation_rule',
                'notes': '[OTOMATIK EKLENDI] Betonarme için demir zorunludur'
            })
            validation_logger.info("Demir otomatik eklendi (betonarme için zorunlu)")
        elif has_beton and not has_demir and exclusions['demir_haric']:
            validation_logger.debug("Demir eklenmedi - kullanıcı 'demir hariç' belirtti")

        # Kalıp ekle (SADECE "kalıp hariç" denilmemişse)
        if has_beton and not has_kalip and not exclusions['kalip_haric']:
            # Beton miktarını bul ve kalıp miktarını hesapla
            beton_qty = 0.0
            for comp in components:
                if 'beton' in comp.get('name', '').lower() and comp.get('type', '').lower() == 'malzeme':
                    beton_qty = comp.get('quantity', 0.0)
                    break

            # Kalıp miktarı: 1 m³ beton için yaklaşık 6-8 m² kalıp (betonarme için biraz daha fazla)
            kalip_qty = beton_qty * 7.0 if beton_qty > 0 else 1.0

            components.append({
                'type': 'Malzeme',
                'code': '04.001.1001',
                'name': 'Ahşap Kalıp',
                'unit': 'm²',
                'quantity': round(kalip_qty, 2),
                'unit_price': 50.0,
                'total_price': round(kalip_qty * 50.0, 2),
                'price_source': 'validation_rule',
                'notes': f'[OTOMATIK EKLENDI] Betonarme için kalıp zorunludur ({beton_qty:.2f} m³ beton × 7 m²/m³)'
            })
            validation_logger.info(f"Kalıp otomatik eklendi: {kalip_qty:.2f} m² (betonarme için zorunlu)")
        elif has_beton and not has_kalip and exclusions['kalip_haric']:
            validation_logger.debug("Kalıp eklenmedi - kullanıcı 'kalıp hariç' belirtti")

    return components


def validate_general_construction_rules(components: List[Dict], description: str) -> List[Dict]:
    """
    Genel inşaat mantığı kurallarını kontrol et ve eksikleri tamamla.
    
    Kurallar:
    - Kazı varsa nakliye de olmalı
    - Duvar varsa harç olmalı
    - Seramik/Fayans varsa yapıştırıcı olmalı
    """
    if not components:
        return components
    
    desc_lower = description.lower()
    
    # Mevcut bileşenleri analiz et
    has_excavation = any('kazı' in comp.get('name', '').lower() for comp in components)
    has_transport = any('nakliye' in comp.get('name', '').lower() or 'taşıma' in comp.get('name', '').lower() 
                       for comp in components)
    
    has_wall = any('duvar' in comp.get('name', '').lower() or 'tuğla' in comp.get('name', '').lower() 
                  for comp in components)
    has_mortar = any('harç' in comp.get('name', '').lower() or 'çimento' in comp.get('name', '').lower() 
                    for comp in components)
    
    has_tile = any('seramik' in comp.get('name', '').lower() or 'fayans' in comp.get('name', '').lower() 
                  for comp in components)
    has_adhesive = any('yapıştırıcı' in comp.get('name', '').lower() or 'derz' in comp.get('name', '').lower() 
                      for comp in components)
    
    # Kural 1: Kazı varsa nakliye de olmalı
    if has_excavation and not has_transport and 'nakliye hariç' not in desc_lower:
        components.append({
            'type': 'Nakliye',
            'code': '15.100.1003',
            'name': 'Kazı malzemesi nakliyesi',
            'unit': 'm³',
            'quantity': 0.0,
            'unit_price': 43.44,
            'total_price': 0.0,
            'price_source': 'validation_rule',
            'notes': '[OTOMATIK EKLENDI] Kazı yapıldığında toprak nakliyesi gereklidir'
        })
    
    # Kural 2: Duvar varsa harç olmalı
    if has_wall and not has_mortar and 'harç hariç' not in desc_lower:
        components.append({
            'type': 'Malzeme',
            'code': '10.130.1008',
            'name': 'Hazır kireç harcı',
            'unit': 'm³',
            'quantity': 0.0,
            'unit_price': 1850.0,
            'total_price': 0.0,
            'price_source': 'validation_rule',
            'notes': '[OTOMATIK EKLENDI] Duvar örülmesi için harç gereklidir'
        })
    
    # Kural 3: Seramik/Fayans varsa yapıştırıcı olmalı
    if has_tile and not has_adhesive and 'yapıştırıcı hariç' not in desc_lower:
        components.append({
            'type': 'Malzeme',
            'code': '10.160.1044',
            'name': 'Seramik yapıştırıcı',
            'unit': 'kg',
            'quantity': 0.0,
            'unit_price': 12.5,
            'total_price': 0.0,
            'price_source': 'validation_rule',
            'notes': '[OTOMATIK EKLENDI] Seramik/Fayans için yapıştırıcı gereklidir'
        })
    
    return components


def calculate_confidence_score(components: List[Dict], description: str) -> int:
    """
    Analiz sonucunun güven skorunu hesapla (0-100).
    
    Puanlama:
    - Tam kod eşleşmesi: +30
    - Benzer kod eşleşmesi: +20
    - Açıklama benzerliği: +15
    - AI tahmini: +10
    - Fiyat bulunamadı: 0
    """
    if not components:
        return 0
    
    total_score = 0
    component_count = len(components)
    
    for comp in components:
        source = comp.get('price_source', 'not_found')
        
        if source == 'exact_code_validated':
            total_score += 30
        elif source == 'similar_code':
            total_score += 20
        elif source == 'description':
            total_score += 15
        elif source == 'ai_generated':
            total_score += 10
        elif source == 'validation_rule':
            total_score += 25  # Kural bazlı eklemeler güvenilir
        elif source == 'training_data':
            total_score += 35  # Eğitim verisinden gelen en güvenilir
        else:  # not_found
            total_score += 0
    
    # Ortalama skoru hesapla
    if component_count > 0:
        avg_score = total_score / component_count
    else:
        avg_score = 0
    
    # Eksik veriler için ceza
    missing_prices = sum(1 for c in components if c.get('unit_price', 0) == 0)
    if missing_prices > 0:
        penalty = (missing_prices / component_count) * 20
        avg_score -= penalty
    
    # 0-100 aralığına sınırla
    score = max(0, min(100, int(avg_score)))
    
    # Güven seviyesi belirle
    if score >= 85:
        level = "High"
    elif score >= 60:
        level = "Medium"
    else:
        level = "Low"
    
    return {
        "score": score,
        "level": level
    }


@router.post("/analyze")
async def analyze_poz(request: AnalysisRequest):
    """
    AI analizi yap ve birim fiyatları PDF verilerinden eşleştir.

    HİBRİT YAKLAŞIM:
    1. Direct Lookup: Eğitim verisinde tam eşleşme varsa direkt döndür
    2. RAG: Benzer örnekleri bulup AI'ya context olarak gönder
    3. LLM: Zenginleştirilmiş context ile AI analizini al

    Ek İyileştirmeler:
    - POZ_DATA'dan benzer pozları bulup AI'ya context olarak gönderir
    - Geçmiş kullanıcı düzeltmelerini context'e ekler (feedback learning)
    - AI yanıtındaki fiyatları PDF verileriyle eşleştirir (kod + açıklama benzerliği)
    - Daha detaylı ve Türkiye'ye özel prompt kullanır
    """
    service = AIAnalysisService()
    training_service = get_training_service()

    try:
        # ========================================
        # STEP 1: DIRECT LOOKUP (Tam Eşleşme)
        # ========================================
        if training_service:
            direct_match = training_service.direct_lookup(request.description, threshold=0.95)
            
            # --- YENİ: Kritik Kelime Kontrolü (Concrete Class Check) ---
            if direct_match:
                import re
                try:
                    user_concrete = re.search(r'C\s*(\d+/\d+)', request.description, re.IGNORECASE)
                    matched_concrete = re.search(r'C\s*(\d+/\d+)', direct_match['input'], re.IGNORECASE)

                    if user_concrete and matched_concrete:
                        if user_concrete.group(1) != matched_concrete.group(1):
                            print(f"❌ DIRECT LOOKUP REFUSED: Beton sınıfı uyuşmazlığı ({user_concrete.group(1)} != {matched_concrete.group(1)})")
                            direct_match = None # Eşleşmeyi iptal et
                except Exception as e:
                    print(f"Error in concrete check: {e}")

            if direct_match:
                print(f"✅ DIRECT LOOKUP HIT! Similarity: {direct_match['similarity']:.2%}")
                print(f"   Input: {direct_match['input']}")

                # POZ_DATA'yı al (isim düzeltmeleri için)
                poz_data = get_poz_data()
                
                training_output = direct_match['output']
                components = []

                # Helper function for components
                def add_components(source_list, type_name):
                    for item in source_list:
                        kod = item.get('kod', '')
                        ad = item.get('ad', '')
                        
                        # İsim boşsa POZ_DATA'dan doldur
                        if (not ad or len(str(ad).strip()) < 2) and kod and kod in poz_data:
                            ad = poz_data[kod].get('description', '')
                            print(f"[NAME FIX] {type_name} '{kod}' → '{ad}'")
                        
                        components.append({
                            'type': type_name,
                            'code': kod,
                            'name': ad,
                            'unit': item.get('birim', ''),
                            'quantity': item.get('miktar', 1.0),
                            'unit_price': 0.0,
                            'total_price': 0.0,
                            'price_source': 'training_data'
                        })

                # Bileşenleri ekle
                add_components(training_output.get('iscilik', []), 'İşçilik')
                add_components(training_output.get('malzeme', []), 'Malzeme')
                add_components(training_output.get('makine', []), 'Makine')
                add_components(training_output.get('nakliye', []), 'Nakliye')

                match_metadata = direct_match.get('metadata', {})
                poz_no = match_metadata.get('ana_poz_no', 'N/A')
                
                from services.local_pdf_service import get_local_pdf_service
                pdf_service = get_local_pdf_service()
                technical_description = pdf_service.get_description(poz_no, return_structured=False) if poz_no != 'N/A' else ""
                analysis_data = pdf_service.get_description(poz_no, return_structured=True) if poz_no != 'N/A' else {}

                result = {
                    'suggested_unit': request.unit,
                    'unit': request.unit,
                    'explanation': f"Bu analiz ÇŞB (Çevre ve Şehircilik Bakanlığı) resmi analizlerinden eşleştirilmiştir (Referans Poz: {poz_no}).\n"
                                   f"Benzerlik: {direct_match['similarity']:.0%}\n"
                                   f"Birim fiyatlar POZ_DATA'dan güncellenmiştir.",
                    'components': components,
                    'technical_description': technical_description,
                    'analysis_data': analysis_data,
                    'metadata': {
                        'source': 'direct_lookup',
                        'match_type': direct_match['match_type'],
                        'similarity': direct_match['similarity'],
                        'training_example': direct_match['input'],
                        'reference_poz': poz_no,
                        'reference_source': match_metadata.get('source')
                    }
                }

                # PDF verilerinden birim fiyatları eşleştir
                result = match_prices_from_poz_data(result)

                # Özet bilgi ekle
                result["metadata"]["poz_data_count"] = len(get_poz_data())
                result["metadata"]["price_sources"] = summarize_price_sources(result)

                return result

        # ========================================
        # STEP 2: RAG + LLM (Benzer örneklerle)
        # ========================================

        # 2.1. POZ_DATA context oluştur
        poz_context = build_context_from_poz_data(request.description, request.unit)

        # 2.2. Feedback context oluştur
        feedback_context = build_feedback_context(request.description, request.unit)

        # 2.3. Training Data RAG context oluştur (Benzer örnekleri ekle)
        training_rag_context = ""
        if training_service:
            training_rag_context = training_service.build_rag_context(request.description, top_k=3)

        # 2.4. Tüm context'leri birleştir (limit kontrolü ile)
        full_context = merge_contexts(poz_context, feedback_context, training_rag_context)

        # WEB SCRAPER INTEGRATION - Poz numarası varsa teknik tarif ekle
        import re
        ref_poz_no = None

        # 1. Kullanıcı açıklamasında poz no var mı?
        match_user = re.search(r'(\d{2}\.\d{3}\.\d{4})', request.description)
        if match_user:
            ref_poz_no = match_user.group(1)

        # 2. RAG içeriğinde var mı? (İlk eşleşen)
        if not ref_poz_no and training_rag_context:
            match_rag = re.search(r'(\d{2}\.\d{3}\.\d{4})', training_rag_context)
            if match_rag:
                ref_poz_no = match_rag.group(1)
            
            # Scraper çağır ve context'e ekle
            technical_desc_found = ""
            analysis_data_found = {}
            if ref_poz_no:
                try:
                    # 1. ÖNCE YEREL PDF ARA (En Hızlı ve Güvenilir)
                    from services.local_pdf_service import get_local_pdf_service
                    local_service = get_local_pdf_service()
                    local_desc = local_service.get_description(ref_poz_no, return_structured=False)
                    local_data = local_service.get_description(ref_poz_no, return_structured=True)
                    
                    if local_desc:
                        print(f"✅ Yerel PDF tarifi bulundu: {ref_poz_no} ({len(local_desc)} karakter)")
                        full_context += f"\n\n[{ref_poz_no} POZUNUN ANALİZ PDF'İNDEN ALINAN RESMİ TARİFİ]:\n{local_desc}\n\nÖNEMLİ: Bu resmi tarife göre fiyata DAHİL olan kalemleri tekrar maliyetlendirme!\n"
                        technical_desc_found = local_desc
                        analysis_data_found = local_data
                    
                    else:
                        # 2. BULUNAMAZSA WEB ARA (Fallback)
                        from services.web_scraper_service import get_scraper_service
                        scraper = get_scraper_service()
                        web_desc = scraper.get_description(ref_poz_no)
                        
                        if web_desc:
                            print(f"✅ Web tarifi eklendi: {ref_poz_no} ({len(web_desc)} karakter)")
                            full_context += f"\n\n[{ref_poz_no} POZUNUN WEB TARİFİ]:\n{web_desc}\n\nÖNEMLİ: Bu tarife göre fiyata DAHİL olanları tekrar ekleme!\n"
                            technical_desc_found = web_desc
                            
                except Exception as e:
                    print(f"⚠️ Tarif Çekme Hatası: {e}")

        if request.context_data:
            full_context += "\n\nKULLANICI EK BİLGİLERİ:\n" + request.context_data

        # 2.5. AI analizini al (zenginleştirilmiş context ile, gelişmiş modlar dahil)
        advanced_metrics = {}

        if request.use_consensus:
            # Çoklu model konsensüs modu
            try:
                consensus_service = ConsensusAnalysisService(service)
                result = asyncio.get_event_loop().run_until_complete(
                    consensus_service.analyze_with_consensus(
                        request.description, request.unit, full_context
                    )
                )
                advanced_metrics["consensus_score"] = result.get("consensus_score", 0)
                advanced_metrics["model_count"] = result.get("model_count", 0)
                logger.info(f"Consensus analiz tamamlandı. Skor: {advanced_metrics.get('consensus_score', 0):.2f}")
            except Exception as e:
                logger.warning(f"Consensus analiz hatası, standart moda dönülüyor: {e}")
                result = await run_in_threadpool(
                    service.generate_analysis,
                    description=request.description,
                    unit=request.unit,
                    context_data=full_context
                )

        elif request.use_self_consistency:
            # Self-consistency modu
            try:
                consistency_service = SelfConsistencyService(service, n_samples=3)
                result = asyncio.get_event_loop().run_until_complete(
                    consistency_service.analyze_with_consistency(
                        request.description, request.unit, full_context
                    )
                )
                advanced_metrics["consistency_score"] = result.get("consistency_score", 0)
                advanced_metrics["sample_count"] = result.get("sample_count", 0)
                if result.get("warning"):
                    advanced_metrics["consistency_warning"] = result.get("warning")
                logger.info(f"Self-consistency analiz tamamlandı. Skor: {advanced_metrics.get('consistency_score', 0):.2f}")
            except Exception as e:
                logger.warning(f"Self-consistency analiz hatası, standart moda dönülüyor: {e}")
                result = await run_in_threadpool(
                    service.generate_analysis,
                    description=request.description,
                    unit=request.unit,
                    context_data=full_context
                )

        elif request.use_cot:
            # Chain-of-Thought modu
            try:
                cot_service = ChainOfThoughtService()
                cot_prompt = cot_service.build_cot_prompt(request.description, request.unit, full_context)
                result = await run_in_threadpool(
                    service.generate_analysis,
                    description=request.description,
                    unit=request.unit,
                    context_data=cot_prompt,
                    temperature=0.15
                )
                advanced_metrics["cot_enabled"] = True
                logger.info("Chain-of-Thought analiz tamamlandı.")
            except Exception as e:
                logger.warning(f"CoT analiz hatası, standart moda dönülüyor: {e}")
                result = await run_in_threadpool(
                    service.generate_analysis,
                    description=request.description,
                    unit=request.unit,
                    context_data=full_context
                )

        else:
            # Standart mod
            result = await run_in_threadpool(
                service.generate_analysis,
                description=request.description,
                unit=request.unit,
                context_data=full_context
            )

        # Advanced metrics'i result'a ekle
        if advanced_metrics:
            result["advanced_metrics"] = advanced_metrics

        # 2.6. Validasyon (Çoklu katman)
        if "components" in result:
            # Kalıp mükerrerlik kontrolü (Özel kalıp varsa genel kalıbı sil)
            result["components"] = validate_formwork_duplication(result["components"], request.description)
            
            # Önce kompozisyon kontrolü (hazır beton vs çimento/kum/çakıl)
            result["components"] = validate_beton_composition(result["components"], request.description)
            # Sonra beton/betonarme ayrımı
            result["components"] = validate_beton_betonarme(result["components"], request.description)

        # 2.7. PDF verilerinden birim fiyatları eşleştir
        result = match_prices_from_poz_data(result)

        # ========================================
        # STEP 3: EK VALIDASYONLAR VE PUANLAMA (YENİ)
        # ========================================
        
        # 3.1. Genel İnşaat Kuralları Validasyonu (Kazı->Nakliye, Duvar->Harç vb.)
        result["components"] = validate_general_construction_rules(result["components"], request.description)

        # 3.2. Güven Skoru Hesaplama
        confidence_data = calculate_confidence_score(result["components"], request.description)

        # 2.8. AI'dan önerilen birimi kullan (giriş birimi yerine)
        suggested_unit = result.get("suggested_unit", request.unit)
        result["unit"] = suggested_unit
        
        # 2.8.5. Teknik Tarifi ekle (eğer Step 1'de eklenmediyse)
        if "technical_description" not in result and 'technical_desc_found' in locals():
            result["technical_description"] = technical_desc_found
            result["analysis_data"] = analysis_data_found

        # 2.9. Özet bilgi ekle
        result["metadata"] = {
            "source": "rag_llm",
            "poz_data_count": len(get_poz_data()),
            "context_provided": bool(full_context),
            "feedback_used": bool(feedback_context),
            "training_rag_used": bool(training_rag_context),
            "price_sources": summarize_price_sources(result),
            "analysis_score": confidence_data["score"],
            "confidence_level": confidence_data["level"],
            "warnings": [],  # Critic review sonrasında doldurulacak
            "input_unit": request.unit,
            "suggested_unit": suggested_unit
        }


        # ========================================
        # CRITIC REVIEW: Eleştirmen AI Kontrolü
        # ========================================
        from services.critic_service import get_critic_service

        critic = get_critic_service()
        critic_review = await run_in_threadpool(critic.review_analysis, result, request.description)

        # Critic sonuçlarını result'a ekle
        result["critic_review"] = {
            "status": critic_review.status,
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "message": issue.message,
                    "suggestion": issue.suggestion
                }
                for issue in critic_review.issues
            ],
            "suggestions": critic_review.suggestions
        }

        # Tüm critic issue'larını warnings'a ekle (severity'ye göre formatla)
        for issue in critic_review.issues:
            if issue.severity == "critical":
                result["metadata"]["warnings"].append(f"🔴 KRİTİK: {issue.message}")
            elif issue.severity == "warning":
                result["metadata"]["warnings"].append(f"⚠️ {issue.message}")

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def summarize_price_sources(result: Dict) -> Dict[str, int]:
    """Fiyat kaynaklarının özetini çıkar"""
    sources = {"exact_code": 0, "similar_code": 0, "description": 0, "ai_generated": 0, "not_found": 0}

    for comp in result.get("components", []):
        source = comp.get("price_source", "not_found")
        if source in sources:
            sources[source] += 1

    return sources
