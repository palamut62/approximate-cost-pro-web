from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import DatabaseManager
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/analyses", tags=["Analyses"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))


class AnalysisComponentSchema(BaseModel):
    type: str
    code: str
    name: str
    unit: str
    quantity: float
    unit_price: float


class AnalysisSchema(BaseModel):
    name: str
    description: str
    unit: str
    explanation: Optional[str] = ""
    components: List[AnalysisComponentSchema] = []


@router.get("/")
def get_analyses():
    """Tüm kayıtlı analizleri listele"""
    analyses = db.get_custom_analyses()
    return analyses


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int):
    """Tek bir analizin detayını getir"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM custom_analyses WHERE id = ?', (analysis_id,))
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı")

    analysis = dict(zip(columns, row))
    analysis['components'] = db.get_analysis_components(analysis_id)
    return analysis


@router.post("/")
def create_analysis(analysis: AnalysisSchema):
    """Yeni analiz kaydet"""
    # Benzersiz poz numarası oluştur
    poz_no = f"AI.{datetime.now().strftime('%Y%m%d.%H%M%S')}"

    # Component'ları hazırla
    components = []
    for comp in analysis.components:
        total_price = comp.quantity * comp.unit_price
        components.append({
            'type': comp.type,
            'code': comp.code,
            'name': comp.name,
            'unit': comp.unit,
            'quantity': comp.quantity,
            'unit_price': comp.unit_price,
            'total_price': total_price
        })

    # Kaydet
    success = db.save_analysis(
        poz_no=poz_no,
        name=analysis.name,
        unit=analysis.unit,
        components=components,
        is_ai=True
    )

    if not success:
        raise HTTPException(status_code=500, detail="Analiz kaydedilemedi")

    # AI açıklamasını kaydet
    analyses = db.get_custom_analyses()
    if analyses:
        latest = analyses[0]
        db.update_analysis_ai_data(latest['id'], analysis.explanation, analysis.description)

    return {"message": "Analiz başarıyla kaydedildi", "poz_no": poz_no}


@router.put("/{analysis_id}")
def update_analysis(analysis_id: int, analysis: AnalysisSchema):
    """Mevcut analizi güncelle"""
    # Önce mevcut analizi kontrol et
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM custom_analyses WHERE id = ?', (analysis_id,))
    existing = cursor.fetchone()
    conn.close()

    if not existing:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı")

    # Bileşenleri temizle ve yeniden ekle
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM analysis_components WHERE analysis_id = ?', (analysis_id,))
    conn.commit()
    conn.close()

    # Yeni bileşenleri ekle
    total = 0
    for comp in analysis.components:
        total_price = comp.quantity * comp.unit_price
        total += total_price
        db.add_analysis_component(
            analysis_id=analysis_id,
            comp_type=comp.type,
            code=comp.code,
            name=comp.name,
            unit=comp.unit,
            quantity=comp.quantity,
            unit_price=comp.unit_price
        )

    # Toplam tutarı güncelle
    db.update_analysis_total(analysis_id)

    # AI açıklamasını güncelle
    db.update_analysis_ai_data(analysis_id, analysis.explanation, analysis.description)

    return {"message": "Analiz başarıyla güncellendi"}


@router.delete("/{analysis_id}")
def delete_analysis(analysis_id: int):
    """Analizi sil"""
    db.delete_analysis(analysis_id)
    return {"message": "Analiz başarıyla silindi"}
