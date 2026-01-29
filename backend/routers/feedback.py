from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import DatabaseManager
from pathlib import Path

router = APIRouter(prefix="/feedback", tags=["AI Feedback"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))


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

    Bu düzeltme gelecekte benzer sorgularda AI'ya context olarak gönderilecek.

    Düzeltme Tipleri:
    - wrong_method: Yanlış yöntem (örn: elle yapım yerine makine ile yapım)
    - missing_item: Eksik kalem (örn: nakliye eklenmemiş)
    - wrong_price: Yanlış fiyat
    - wrong_quantity: Yanlış miktar
    - other: Diğer
    """
    try:
        components = [comp.dict() for comp in feedback.correct_components]

        feedback_id = db.save_ai_feedback(
            original_prompt=feedback.original_prompt,
            original_unit=feedback.original_unit,
            correction_type=feedback.correction_type,
            correction_description=feedback.correction_description,
            correct_components=components,
            keywords=feedback.keywords
        )

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
