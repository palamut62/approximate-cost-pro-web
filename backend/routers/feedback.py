from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import DatabaseManager
from pathlib import Path
import logging

router = APIRouter(prefix="/feedback", tags=["AI Feedback"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))
logger = logging.getLogger("feedback")

# Kategori bazlı zorunlu bileşen kuralları (otomatik çıkarım için)
CATEGORY_TRIGGERS = {
    "taş duvar":      {"triggers": ["taş", "duvar"], "items": ["iskele", "barbakan", "harç", "nakliye"]},
    "betonarme":      {"triggers": ["betonarme"],     "items": ["demir", "kalıp", "paspayı", "nakliye"]},
    "tuğla duvar":    {"triggers": ["tuğla", "duvar"], "items": ["iskele", "harç", "nakliye"]},
    "sıva":           {"triggers": ["sıva"],           "items": ["iskele", "çimento", "kum", "nakliye"]},
    "boya":           {"triggers": ["boya"],           "items": ["astar", "iskele", "nakliye"]},
    "kazı":           {"triggers": ["kazı"],           "items": ["nakliye"]},
    "boru döşeme":    {"triggers": ["boru"],           "items": ["yatak", "nakliye"]},
}


def _extract_rule_from_feedback(original_prompt: str, correction_type: str, correct_components: list) -> Optional[dict]:
    """
    missing_item feedback'inden otomatik kural çıkar.
    Örnek: "taş duvar" + missing "iskele" → rule: taş+duvar → iskele zorunlu
    """
    if correction_type != "missing_item":
        return None

    prompt_lower = original_prompt.lower()

    # Hangi kategoriye ait bu feedback?
    for category, cat_info in CATEGORY_TRIGGERS.items():
        triggers = cat_info["triggers"]
        if all(t in prompt_lower for t in triggers):
            # Missing item: correct_components'tan, CATEGORY_TRIGGERS'deki zorunlu listede olmayan yeni items bul
            # Feedback'in düzelttiği item: correct_components'ta olan ama
            # CATEGORY_TRIGGERS'deki zorunlu listede olmayan yeni kalemler
            new_required = []
            for comp in correct_components:
                comp_name = comp.get("name", "").lower()
                already_known = any(item in comp_name for item in cat_info["items"])
                if not already_known and comp.get("type", "").lower() == "malzeme":
                    new_required.append({"name": comp.get("name", ""), "type": "Malzeme"})

            # Eğer yeni zorunlu kalem bulunamadıysa, mevcut zorunlu listesi üzerinden kural yaz
            if not new_required:
                new_required = [{"name": item.capitalize(), "type": "Malzeme"} for item in cat_info["items"]]

            display_names = [item["name"] for item in new_required]
            return {
                "trigger_keywords": triggers,
                "required_items": new_required,
                "condition_text": f"{category} imalatında zorunlu: {', '.join(display_names)}"
            }

    return None


class ComponentSchema(BaseModel):
    type: str
    code: str
    name: str
    unit: str
    quantity: float
    unit_price: float


class FeedbackCreateSchema(BaseModel):
    original_prompt: str
    original_unit: str
    correction_type: str  # 'wrong_method', 'missing_item', 'wrong_price', 'wrong_quantity', 'other'
    correction_description: str
    correct_components: List[ComponentSchema]
    keywords: Optional[List[str]] = None


class FeedbackResponse(BaseModel):
    id: int
    message: str


@router.post("/", response_model=FeedbackResponse)
def create_feedback(feedback: FeedbackCreateSchema):
    """
    Kullanıcının AI düzeltmesini kaydet.
    SQLite'a kaydet → Vector DB'ye index'le → Otomatik kural çıkar.
    """
    try:
        components = [comp.dict() for comp in feedback.correct_components]

        # 1. SQLite'a kaydet
        feedback_id = db.save_ai_feedback(
            original_prompt=feedback.original_prompt,
            original_unit=feedback.original_unit,
            correction_type=feedback.correction_type,
            correction_description=feedback.correction_description,
            correct_components=components,
            keywords=feedback.keywords
        )

        # 2. Vector DB'ye semantic index ekle (async-safe, hata durumunda sil mi)
        try:
            from services.vector_db_service import VectorDBService
            vector_service = VectorDBService()
            vector_service.index_feedback({
                "id": str(feedback_id),
                "original_description": feedback.original_prompt,
                "correction_type": feedback.correction_type,
                "user_note": feedback.correction_description
            })
            logger.info(f"[FEEDBACK] Vector DB'ye indexlendi: feedback_id={feedback_id}")
        except Exception as ve:
            logger.warning(f"[FEEDBACK] Vector DB indexleme hatası (non-fatal): {ve}")

        # 3. Otomatik kural çıkarımı (missing_item feedback'lerden)
        rule_data = _extract_rule_from_feedback(
            feedback.original_prompt,
            feedback.correction_type,
            components
        )
        if rule_data:
            try:
                rule_id = db.save_user_rule(
                    trigger_keywords=rule_data["trigger_keywords"],
                    required_items=rule_data["required_items"],
                    condition_text=rule_data["condition_text"]
                )
                logger.info(f"[FEEDBACK] Otomatik kural oluşturuldu: rule_id={rule_id} — {rule_data['condition_text']}")
            except Exception as re_err:
                logger.warning(f"[FEEDBACK] Kural kaydetme hatası (non-fatal): {re_err}")

        return FeedbackResponse(
            id=feedback_id,
            message="Düzeltme kaydedildi. AI bundan sonraki benzer sorgularda bu bilgiyi kullanacak."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_all_feedback():
    """Tüm AI düzeltmelerini listele"""
    feedback_list = db.get_all_feedback()

    # JSON string'leri parse et
    import json
    for fb in feedback_list:
        try:
            fb['correct_components'] = json.loads(fb.get('correct_components', '[]'))
            fb['keywords'] = json.loads(fb.get('keywords', '[]'))
        except:
            fb['correct_components'] = []
            fb['keywords'] = []

    return feedback_list


@router.get("/relevant")
def get_relevant_feedback(prompt: str, unit: str = ""):
    """Verilen prompt için ilgili düzeltmeleri getir"""
    import json

    feedback_list = db.get_relevant_feedback(prompt, unit)

    for fb in feedback_list:
        try:
            fb['correct_components'] = json.loads(fb.get('correct_components', '[]'))
            fb['keywords'] = json.loads(fb.get('keywords', '[]'))
        except:
            fb['correct_components'] = []
            fb['keywords'] = []

    return feedback_list


@router.delete("/{feedback_id}")
def delete_feedback(feedback_id: int):
    """Bir düzeltmeyi sil"""
    db.delete_feedback(feedback_id)
    return {"message": "Düzeltme silindi"}


@router.put("/{feedback_id}/toggle")
def toggle_feedback(feedback_id: int, is_active: bool = True):
    """Düzeltmenin aktif/pasif durumunu değiştir"""
    db.toggle_feedback_active(feedback_id, is_active)
    return {"message": f"Düzeltme {'aktif' if is_active else 'pasif'} yapıldı"}
