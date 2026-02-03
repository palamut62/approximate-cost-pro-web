from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import DatabaseManager
from pathlib import Path

router = APIRouter(prefix="/projects", tags=["Projects"])
db = DatabaseManager(str(Path(__file__).parent.parent.parent / "data.db"))

class ProjectItemSchema(BaseModel):
    poz_no: str
    description: str
    unit: str
    quantity: float
    unit_price: float
    notes: Optional[str] = ""

class ProjectSchema(BaseModel):
    name: str
    description: Optional[str] = ""
    employer: Optional[str] = ""
    contractor: Optional[str] = ""
    location: Optional[str] = ""
    project_code: Optional[str] = ""
    project_date: Optional[str] = ""
    items: List[ProjectItemSchema] = []

class ProjectRenameSchema(BaseModel):
    name: str

@router.get("/")
def get_projects():
    return db.get_projects()

@router.get("/{project_id}")
def get_project(project_id: int):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project['items'] = db.get_project_items(project_id)
    return project

@router.post("/")
def create_project(project: ProjectSchema):
    project_id = db.create_project(
        name=project.name,
        description=project.description,
        employer=project.employer,
        contractor=project.contractor,
        location=project.location,
        project_code=project.project_code,
        project_date=project.project_date
    )
    
    for item in project.items:
        db.add_project_item(
            project_id=project_id,
            poz_no=item.poz_no,
            description=item.description,
            unit=item.unit,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
    
    return {"id": project_id, "message": "Project created successfully"}

@router.put("/{project_id}")
def update_project(project_id: int, project: ProjectSchema):
    success = db.update_project(
        project_id=project_id,
        name=project.name,
        description=project.description,
        employer=project.employer,
        contractor=project.contractor,
        location=project.location,
        project_code=project.project_code,
        project_date=project.project_date
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Simple strategy: clear and re-add items for now
    db.clear_project_items(project_id)
    for item in project.items:
        db.add_project_item(
            project_id=project_id,
            poz_no=item.poz_no,
            description=item.description,
            unit=item.unit,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        
    return {"message": "Project updated successfully"}

@router.delete("/{project_id}")
def delete_project(project_id: int):
    db.delete_project(project_id)
    return {"message": "Project deleted successfully"}


@router.patch("/{project_id}/rename")
def rename_project(project_id: int, project: ProjectRenameSchema):
    success = db.rename_project(project_id, project.name)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project renamed successfully"}
