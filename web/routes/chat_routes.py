from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from web.auth import get_current_user, get_user_from_token, require_admin
from web.chat_manager import chat_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatSendRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


@router.get("/messages")
def get_chat_messages(limit: int = Query(default=50, ge=1, le=100), user=Depends(get_current_user)):
    return {
        "ok": True,
        "messages": chat_manager.get_recent_messages(limit=limit),
    }


@router.post("/messages")
async def send_chat_message(req: ChatSendRequest, user=Depends(get_current_user)):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    msg = await chat_manager.add_chat_message(user, text)
    return {
        "ok": True,
        "message": msg,
    }


@router.get("/online-users")
def get_online_users(user=Depends(get_current_user)):
    users = chat_manager.get_online_users()
    return {
        "ok": True,
        "count": len(users),
        "online_users": users,
    }


@router.delete("/messages")
def clear_chat_history(admin=Depends(require_admin)):
    chat_manager.clear_history()
    return {
        "ok": True,
        "message": "Histórico do chat limpo com sucesso.",
    }


@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    # Authenticate token from query param or session cookie
    auth_token = token
    if not auth_token:
        auth_token = websocket.cookies.get("session_token")

    user = get_user_from_token(auth_token)
    if not user:
        await websocket.close(code=4001, reason="Não autenticado")
        return

    await chat_manager.connect(websocket, user)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "chat_message":
                text = (data.get("text") or "").strip()
                if text:
                    await chat_manager.add_chat_message(user, text)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await chat_manager.disconnect(websocket)
    except Exception:
        await chat_manager.disconnect(websocket)
