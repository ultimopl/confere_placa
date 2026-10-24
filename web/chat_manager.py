import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket

from web.config import DATA_DIR

CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
MAX_CHAT_HISTORY = 100


class ChatManager:
    def __init__(self):
        # Active websocket connections: ws -> {"username": str, "name": str, "role": str}
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        self.messages: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(CHAT_HISTORY_FILE):
            return []
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self) -> None:
        try:
            temp_file = CHAT_HISTORY_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.messages[-MAX_CHAT_HISTORY:], f, indent=2, ensure_ascii=False)
            os.replace(temp_file, CHAT_HISTORY_FILE)
        except Exception:
            pass

    async def connect(self, websocket: WebSocket, user_info: Dict[str, Any]):
        await websocket.accept()
        self.active_connections[websocket] = user_info
        # Notify all about updated online users and a system join message
        await self.broadcast_users_list()

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            user = self.active_connections.pop(websocket)
            await self.broadcast_users_list()

    def get_online_users(self) -> List[Dict[str, Any]]:
        # Return unique list of online users by username
        seen = set()
        users = []
        for info in self.active_connections.values():
            uname = info.get("username", "")
            if uname and uname not in seen:
                seen.add(uname)
                users.append({
                    "username": uname,
                    "name": info.get("name", uname),
                    "role": info.get("role", "operador"),
                })
        return sorted(users, key=lambda x: (x["role"] != "admin", x["name"]))

    async def broadcast_users_list(self):
        users = self.get_online_users()
        payload = {
            "type": "users_update",
            "online_users": users,
            "count": len(users),
        }
        await self.broadcast(payload)

    async def broadcast(self, message: Dict[str, Any]):
        dead_connections = []
        for ws in list(self.active_connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.active_connections.pop(ws, None)

    async def add_chat_message(self, user_info: Dict[str, Any], text: str) -> Dict[str, Any]:
        msg_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%H:%M:%S")
        date_str = datetime.now().strftime("%d/%m/%Y")
        msg = {
            "id": msg_id,
            "type": "chat_message",
            "username": user_info.get("username", "anônimo"),
            "name": user_info.get("name", user_info.get("username", "anônimo")),
            "role": user_info.get("role", "operador"),
            "text": text.strip(),
            "time": timestamp,
            "date": date_str,
            "system": False,
        }
        self.messages.append(msg)
        if len(self.messages) > MAX_CHAT_HISTORY:
            self.messages = self.messages[-MAX_CHAT_HISTORY:]
        self._save_history()

        await self.broadcast(msg)
        return msg

    async def notify_new_plate(self, plate_record: Dict[str, Any], created_by: Dict[str, Any], loud_alert: bool = False):
        msg_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%H:%M:%S")
        date_str = datetime.now().strftime("%d/%m/%Y")
        payload = {
            "id": msg_id,
            "type": "new_plate_alert",
            "plate": plate_record,
            "created_by": created_by.get("username", ""),
            "creator_name": created_by.get("name", created_by.get("username", "")),
            "loud_alert": loud_alert,
            "time": timestamp,
            "date": date_str,
        }
        await self.broadcast(payload)

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.messages[-limit:]

    def clear_history(self) -> None:
        self.messages = []
        self._save_history()


chat_manager = ChatManager()
