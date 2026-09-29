import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from web.auth import get_current_user, require_admin
from web.config import set_active_csv_path, DATA_DIR
from web.repository import repository

router = APIRouter(prefix="/api/config", tags=["config"])


class CsvPathRequest(BaseModel):
    path: str = Field(..., min_length=1)


@router.get("")
def get_config_info(user=Depends(get_current_user)):
    return {
        "ok": True,
        "stats": repository.get_stats(),
    }


@router.post("/csv-path")
def set_csv_path(req: CsvPathRequest, admin=Depends(require_admin)):
    target_path = os.path.normpath(req.path.strip())
    if not os.path.exists(target_path):
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado: {target_path}",
        )
    try:
        repository.load(target_path)
        set_active_csv_path(target_path)
        return {
            "ok": True,
            "message": f"CSV carregado com sucesso: {os.path.basename(target_path)}",
            "stats": repository.get_stats(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao carregar CSV: {e}")


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), admin=Depends(require_admin)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="O arquivo enviado deve ser do tipo .csv")

    upload_dir = os.path.join(DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    target_path = os.path.join(upload_dir, file.filename)

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        repository.load(target_path)
        set_active_csv_path(target_path)

        return {
            "ok": True,
            "message": f"Arquivo '{file.filename}' enviado e ativado com sucesso!",
            "stats": repository.get_stats(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar upload: {e}")
