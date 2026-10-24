import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF_PATH = os.path.join(BASE_DIR, "app.conf")
DATA_DIR = os.path.join(BASE_DIR, "web_data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_app_config() -> dict:
    try:
        if os.path.exists(CONF_PATH):
            with open(CONF_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_app_config(cfg: dict) -> None:
    try:
        with open(CONF_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_active_csv_path() -> str:
    cfg = load_app_config()
    last = cfg.get("last_csv", "")
    if last and os.path.exists(last):
        return last
    default_fake = os.path.join(BASE_DIR, "fake_data.csv")
    if os.path.exists(default_fake):
        return default_fake
    return ""


def set_active_csv_path(path: str) -> None:
    cfg = load_app_config()
    cfg["last_csv"] = path
    save_app_config(cfg)
