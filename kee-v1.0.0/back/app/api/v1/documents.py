from fastapi import APIRouter, UploadFile, File, Form
from app.services.documents import document_service
router=APIRouter(prefix="/documents",tags=["documents"])
@router.post("/upload")
async def upload(file:UploadFile=File(...),domain:str=Form("general")):
 return await document_service.ingest(file,domain)
