import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyCookie, HTTPBearer, HTTPAuthorizationCredentials

from web.config import USERS_FILE, SESSIONS_FILE

cookie_scheme = APIKeyCookie(name="session_token", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

# In-memory sessions cache: {token: {"username": ..., "role": ..., "expires_at": ...}}
_sessions: Dict[str, Dict[str, Any]] = {}


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()


def load_users() -> Dict[str, Any]:
    if not os.path.exists(USERS_FILE):
        return {}
    # Never treat an unreadable file as "no users": callers that save afterwards
    # would overwrite every account (and init_default_admin would recreate admin)
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except (OSError, ValueError) as e:
        raise RuntimeError(
            f"Não foi possível ler {USERS_FILE}: {e}. "
            "Corrija ou restaure o arquivo; ele não será sobrescrito."
        ) from e
    if not isinstance(users, dict):
        raise RuntimeError(f"Formato inválido em {USERS_FILE}: esperado um objeto JSON.")
    return users


def save_users(users: Dict[str, Any]) -> None:
    temp_file = USERS_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    os.replace(temp_file, USERS_FILE)


LEGACY_DEFAULT_PASSWORD = "admin123"


def init_default_admin() -> None:
    """Create the first admin (only when there are no users) or rotate the legacy
    hardcoded 'admin123' password. The password comes from CONFERE_ADMIN_PASSWORD
    or is generated randomly and printed once to the server console."""
    users = load_users()
    admin = users.get("admin")
    legacy = admin is not None and secrets.compare_digest(
        _hash_password(LEGACY_DEFAULT_PASSWORD, admin["salt"]), admin["password_hash"]
    )
    if users and not legacy:
        return

    env_password = os.environ.get("CONFERE_ADMIN_PASSWORD", "")
    password = env_password or secrets.token_urlsafe(9)
    salt = secrets.token_hex(16)
    if legacy:
        admin["salt"] = salt
        admin["password_hash"] = _hash_password(password, salt)
    else:
        users["admin"] = {
            "username": "admin",
            "name": "Administrador",
            "password_hash": _hash_password(password, salt),
            "salt": salt,
            "role": "admin",
            "created_at": datetime.now().isoformat(),
        }
    save_users(users)

    motivo = "substituída (senha padrão antiga)" if legacy else "criada"
    if env_password:
        print(f"[OK] Senha do usuário 'admin' {motivo} a partir de CONFERE_ADMIN_PASSWORD.")
    else:
        print(f"[!] Senha do usuário 'admin' {motivo}: {password}")
        print("[!] Anote-a e altere-a após o primeiro login. Ela não será exibida novamente.")


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    users = load_users()
    u = users.get(username.strip().lower())
    if not u:
        return None
    test_hash = _hash_password(password, u["salt"])
    if secrets.compare_digest(test_hash, u["password_hash"]):
        return {
            "username": u["username"],
            "name": u.get("name", u["username"]),
            "role": u.get("role", "operador"),
        }
    return None


def create_session(username: str, role: str, name: str, days: int = 7) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    _sessions[token] = {
        "username": username,
        "name": name,
        "role": role,
        "expires_at": expires,
        # Salt changes on every password change, invalidating older sessions
        "salt": load_users().get(username, {}).get("salt", ""),
    }
    return token


def delete_session(token: str) -> None:
    _sessions.pop(token, None)


def get_user_from_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate a session against users.json on every call, so deleted users,
    role changes and password changes take effect immediately."""
    if not token:
        return None
    session = _sessions.get(token)
    if not session:
        return None
    try:
        expired = datetime.now() > datetime.fromisoformat(session["expires_at"])
    except Exception:
        expired = True
    u = load_users().get(session["username"])
    if expired or not u or u.get("salt") != session.get("salt"):
        _sessions.pop(token, None)
        return None
    session["role"] = u.get("role", "operador")
    session["name"] = u.get("name", u["username"])
    return session


def get_current_user(
    request: Request,
    token_cookie: Optional[str] = Depends(cookie_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    token = token_cookie or (bearer.credentials if bearer else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Por favor, faça login.",
        )

    session = get_user_from_token(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    return session


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Ação permitida apenas para administradores.",
        )
    return user


def list_users() -> list:
    users = load_users()
    res = []
    for u in users.values():
        res.append({
            "username": u["username"],
            "name": u.get("name", u["username"]),
            "role": u.get("role", "operador"),
            "created_at": u.get("created_at", ""),
        })
    return sorted(res, key=lambda x: (x["role"] != "admin", x["username"]))


def create_or_update_user(username: str, name: str, password: Optional[str], role: str) -> None:
    username = username.strip().lower()
    if not username:
        raise ValueError("Nome de usuário obrigatório.")
    if role not in ("admin", "operador"):
        raise ValueError("Papel inválido. Deve ser 'admin' ou 'operador'.")

    users = load_users()
    existing = users.get(username)

    if existing:
        existing["name"] = name.strip() or existing["name"]
        existing["role"] = role
        if password:
            salt = secrets.token_hex(16)
            existing["salt"] = salt
            existing["password_hash"] = _hash_password(password, salt)
        users[username] = existing
    else:
        if not password:
            raise ValueError("Senha obrigatória para novo usuário.")
        salt = secrets.token_hex(16)
        users[username] = {
            "username": username,
            "name": name.strip() or username,
            "password_hash": _hash_password(password, salt),
            "salt": salt,
            "role": role,
            "created_at": datetime.now().isoformat(),
        }

    save_users(users)


def delete_user(username: str, current_admin: str) -> None:
    username = username.strip().lower()
    if username == current_admin.lower():
        raise ValueError("Você não pode excluir seu próprio usuário.")
    users = load_users()
    if username not in users:
        raise ValueError("Usuário não encontrado.")
    del users[username]
    save_users(users)


def change_own_password(username: str, old_password: str, new_password: str) -> None:
    users = load_users()
    u = users.get(username.strip().lower())
    if not u:
        raise ValueError("Usuário não encontrado.")
    test_hash = _hash_password(old_password, u["salt"])
    if not secrets.compare_digest(test_hash, u["password_hash"]):
        raise ValueError("Senha atual incorreta.")
    if len(new_password) < 4:
        raise ValueError("A nova senha deve ter no mínimo 4 caracteres.")
    salt = secrets.token_hex(16)
    u["salt"] = salt
    u["password_hash"] = _hash_password(new_password, salt)
    users[username] = u
    save_users(users)
