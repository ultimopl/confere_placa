from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from web.auth import get_current_user, require_admin
from web.chat_manager import chat_manager
from web.repository import repository, parse_datetime

router = APIRouter(prefix="/api/plates", tags=["plates"])


class PlateCreateRequest(BaseModel):
    placa: str = Field(..., min_length=1)
    detalhes: str = Field(default="")
    status: str = Field(default="autorizado")
    expires_at: Optional[str] = None
    duration_hours: Optional[int] = None
    cor: str = Field(default="")
    modelo: str = Field(default="")
    loud_alert: bool = Field(default=False)


class PlateUpdateRequest(BaseModel):
    detalhes: str = Field(default="")
    status: str = Field(...)
    expires_at: Optional[str] = None
    duration_hours: Optional[int] = None
    cor: str = Field(default="")
    modelo: str = Field(default="")


def resolve_expiry(status: str, expires_at: Optional[str], duration_hours: Optional[int]) -> str:
    if status != "autorizado_temp":
        return ""
    if expires_at and expires_at.strip():
        dt = parse_datetime(expires_at.strip())
        if dt is None:
            raise ValueError("Formato de data de expiração inválido. Use AAAA-MM-DD HH:MM.")
        return dt.isoformat()
    elif duration_hours is not None and duration_hours > 0:
        return (datetime.now() + timedelta(hours=duration_hours)).isoformat()
    else:
        # Default 24 hours for temporary
        return (datetime.now() + timedelta(hours=24)).isoformat()


@router.get("")
def search_plates(
    q: str = Query(default=""),
    ignore_case: bool = Query(default=True),
    authorized_only: bool = Query(default=False),
    temp_filter: Optional[str] = Query(default=None),
    user=Depends(get_current_user),
):
    results = repository.search(
        query=q,
        ignore_case=ignore_case,
        authorized_only=authorized_only,
        temp_filter=temp_filter,
    )
    if q.strip():
        repository.add_history(q, user=user.get("username", ""))

    return {
        "ok": True,
        "count": len(results),
        "results": results,
    }


@router.get("/history")
def get_history(user=Depends(get_current_user)):
    return {
        "ok": True,
        "history": repository.history,
    }


@router.delete("/history")
def clear_history(user=Depends(get_current_user)):
    repository.clear_history()
    return {"ok": True, "message": "Histórico limpo com sucesso."}


@router.get("/{placa}")
def get_plate(placa: str, user=Depends(get_current_user)):
    record = repository.get_plate_record(placa)
    if not record:
        raise HTTPException(status_code=404, detail="Placa não encontrada ou excluída.")
    return {"ok": True, "plate": record}


@router.post("")
async def add_plate(req: PlateCreateRequest, admin=Depends(require_admin)):
    try:
        final_expires = resolve_expiry(req.status, req.expires_at, req.duration_hours)
        record = repository.add_or_update(
            placa=req.placa,
            detalhes=req.detalhes,
            status=req.status,
            expires_at=final_expires,
            cor=req.cor,
            modelo=req.modelo,
        )
        # Broadcast alert to all connected users
        await chat_manager.notify_new_plate(record, admin, loud_alert=req.loud_alert)
        return {
            "ok": True,
            "message": f"Placa {record['placa']} cadastrada com sucesso.",
            "plate": record,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@router.put("/{placa}")
def update_plate(placa: str, req: PlateUpdateRequest, admin=Depends(require_admin)):
    try:
        clean = repository.clean_plate(placa)
        if clean not in repository.data or repository.data[clean][1] == "excluido":
            raise HTTPException(status_code=404, detail="Placa não encontrada para edição.")

        final_expires = resolve_expiry(req.status, req.expires_at, req.duration_hours)
        record = repository.add_or_update(
            placa=clean,
            detalhes=req.detalhes,
            status=req.status,
            expires_at=final_expires,
            cor=req.cor,
            modelo=req.modelo,
        )
        return {
            "ok": True,
            "message": f"Placa {record['placa']} atualizada com sucesso.",
            "plate": record,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@router.delete("/{placa}")
def delete_plate(placa: str, admin=Depends(require_admin)):
    ok = repository.delete(placa)
    if not ok:
        raise HTTPException(status_code=404, detail="Placa não encontrada.")
    return {
        "ok": True,
        "message": f"Placa {repository.clean_plate(placa)} excluída com sucesso.",
    }
