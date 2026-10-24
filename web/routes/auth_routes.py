from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from web.auth import (
    authenticate_user,
    create_session,
    delete_session,
    get_current_user,
    require_admin,
    list_users,
    create_or_update_user,
    delete_user,
    change_own_password,
    cookie_scheme,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2)
    name: str = Field(default="")
    password: Optional[str] = None
    role: str = Field(default="operador")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/",
    )


@router.post("/login")
def login(req: LoginRequest, response: Response):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )

    token = create_session(
        username=user["username"],
        role=user["role"],
        name=user["name"],
        days=7,
    )

    _set_session_cookie(response, token)

    return {
        "ok": True,
        "token": token,
        "user": user,
    }


@router.post("/logout")
def logout(response: Response, current_token: Optional[str] = Depends(cookie_scheme)):
    if current_token:
        delete_session(current_token)
    response.delete_cookie(key="session_token", path="/")
    return {"ok": True, "message": "Desconectado com sucesso."}


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return {
        "ok": True,
        "user": {
            "username": user["username"],
            "name": user.get("name", user["username"]),
            "role": user["role"],
        },
    }


@router.get("/users")
def get_users(admin=Depends(require_admin)):
    return {"ok": True, "users": list_users()}


@router.post("/users")
def save_user(req: CreateUserRequest, admin=Depends(require_admin)):
    try:
        create_or_update_user(
            username=req.username,
            name=req.name,
            password=req.password,
            role=req.role,
        )
        return {"ok": True, "message": f"Usuário '{req.username}' salvo com sucesso."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{username}")
def remove_user(username: str, admin=Depends(require_admin)):
    try:
        delete_user(username, current_admin=admin["username"])
        return {"ok": True, "message": f"Usuário '{username}' excluído com sucesso."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    response: Response,
    user=Depends(get_current_user),
    current_token: Optional[str] = Depends(cookie_scheme),
):
    try:
        change_own_password(
            username=user["username"],
            old_password=req.old_password,
            new_password=req.new_password,
        )
        # The password change invalidated every session of this user; issue a fresh one
        if current_token:
            delete_session(current_token)
        token = create_session(username=user["username"], role=user["role"], name=user["name"], days=7)
        _set_session_cookie(response, token)
        return {"ok": True, "message": "Senha alterada com sucesso.", "token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
