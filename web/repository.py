import csv
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

PLATE_REGEX = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")


def parse_datetime(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def format_expiry_display(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


def format_time_remaining(expires_dt: Optional[datetime]) -> str:
    if not expires_dt:
        return ""
    now = datetime.now()
    if expires_dt > now:
        diff = expires_dt - now
        total_seconds = int(diff.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        mins, _ = divmod(rem, 60)
        if days > 0:
            return f"Restam {days}d {hours}h"
        elif hours > 0:
            return f"Restam {hours}h {mins}m"
        else:
            return f"Restam {mins}m"
    else:
        diff = now - expires_dt
        total_seconds = int(diff.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        mins, _ = divmod(rem, 60)
        if days > 0:
            return f"Expirou há {days}d"
        elif hours > 0:
            return f"Expirou há {hours}h"
        else:
            return f"Expirou há {max(1, mins)}m"


class PlateRepository:
    AUTHORIZED_STATUSES = ["autorizado", "autorizado_patio", "autorizado_temp"]
    STATUS_VALIDOS = [
        "autorizado",
        "não autorizado",
        "para recepção",
        "para entrega",
        "autorizado_patio",
        "autorizado_temp",
    ]

    def __init__(self, delimiter: str = ";"):
        self.delimiter = delimiter
        self.data: Dict[str, List[str]] = {}  # {PLACA: [detalhes, status, timestamp, expires_at]}
        self.current_file_path: Optional[str] = None
        self.history: List[Dict[str, str]] = []  # [{"query": ..., "time": ..., "user": ...}]
        self._lock = threading.Lock()

    def load(self, file_path: str) -> Dict[str, List[str]]:
        with self._lock:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo CSV não encontrado: {file_path}")

            new_data: Dict[str, List[str]] = {}
            with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                for row in reader:
                    if len(row) < 3 or not row[0].strip():
                        continue
                    placa = row[0].strip().upper().replace("-", "")
                    detalhes = row[1].strip() if len(row) > 1 else ""
                    status = row[2].strip() if len(row) > 2 else "não autorizado"
                    ts = row[3].strip() if len(row) > 3 else ""
                    expires_at = row[4].strip() if len(row) > 4 else ""
                    cor = row[5].strip() if len(row) > 5 else ""
                    modelo = row[6].strip() if len(row) > 6 else ""
                    new_data[placa] = [detalhes, status, ts, expires_at, cor, modelo]

            self.data = new_data
            self.current_file_path = file_path
            return self.data

    def save_current(self) -> None:
        if not self.current_file_path:
            raise ValueError("Nenhum caminho de CSV definido.")
        self._atomic_save(self.data, self.current_file_path)

    def _atomic_save(self, data: Dict[str, List[str]], file_path: str) -> None:
        dir_name = os.path.dirname(os.path.abspath(file_path)) or "."
        os.makedirs(dir_name, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="tmp_confere_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=self.delimiter)
                for placa, values in data.items():
                    row = [placa] + list(values)
                    while len(row) < 7:
                        row.append("")
                    writer.writerow(row[:7])
            shutil.move(temp_path, file_path)
            self.current_file_path = file_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError(f"Falha na gravação atômica do CSV: {e}")

    def clean_plate(self, placa: str) -> str:
        return (placa or "").strip().upper().replace("-", "").replace(" ", "")

    def validate_plate(self, placa: str) -> bool:
        return bool(PLATE_REGEX.match(placa))

    def add_or_update(
        self,
        placa: str,
        detalhes: str,
        status: str,
        expires_at: Optional[str] = None,
        cor: str = "",
        modelo: str = "",
    ) -> Dict[str, Any]:
        with self._lock:
            clean = self.clean_plate(placa)
            if not clean:
                raise ValueError("Informe a placa.")
            if not self.validate_plate(clean):
                raise ValueError(
                    f"Formato de placa inválido ({clean})! Use padrão Mercosul (ABC1D23) ou antigo (ABC1234)."
                )
            if status not in self.STATUS_VALIDOS:
                raise ValueError(f"Status '{status}' inválido.")
            if not self.current_file_path:
                raise ValueError("Nenhum arquivo CSV carregado no sistema.")

            iso_ts = datetime.now().isoformat()
            exp_str = (expires_at or "").strip()
            cor_str = (cor or "").strip()
            mod_str = (modelo or "").strip()
            self.data[clean] = [detalhes.strip(), status, iso_ts, exp_str, cor_str, mod_str]
            self.save_current()

            return self.get_plate_record(clean)

    def delete(self, placa: str) -> bool:
        with self._lock:
            clean = self.clean_plate(placa)
            if clean in self.data:
                self.data[clean][1] = "excluido"
                self.data[clean][2] = datetime.now().isoformat()
                self.save_current()
                return True
            return False

    def is_expired(self, status: str, expires_at: str) -> bool:
        if status != "autorizado_temp" or not expires_at:
            return False
        dt = parse_datetime(expires_at)
        if dt is None:
            return False
        return dt < datetime.now()

    def get_plate_record(self, placa: str) -> Optional[Dict[str, Any]]:
        clean = self.clean_plate(placa)
        values = self.data.get(clean)
        if not values or values[1] == "excluido":
            return None
        detalhes = values[0]
        status = values[1]
        ts = values[2] if len(values) > 2 else ""
        expires_at = values[3] if len(values) > 3 else ""
        cor = values[4] if len(values) > 4 else ""
        modelo = values[5] if len(values) > 5 else ""

        exp_dt = parse_datetime(expires_at) if (status == "autorizado_temp" and expires_at) else None
        expired = (exp_dt < datetime.now()) if exp_dt else False

        return {
            "placa": clean,
            "detalhes": detalhes,
            "status": status,
            "timestamp": ts,
            "expires_at": expires_at,
            "expires_display": format_expiry_display(exp_dt),
            "time_remaining": format_time_remaining(exp_dt),
            "expired": expired,
            "is_authorized": status in self.AUTHORIZED_STATUSES and not expired,
            "cor": cor,
            "modelo": modelo,
        }

    def search(
        self,
        query: str = "",
        ignore_case: bool = True,
        authorized_only: bool = False,
        temp_filter: Optional[str] = None,  # 'all', 'active', 'expired', or None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            q = query.strip()
            q_clean = q.upper().replace("-", "").replace(" ", "") if ignore_case else q
            results = []

            for placa, values in self.data.items():
                status = values[1]
                if status == "excluido":
                    continue

                detalhes = values[0]
                ts = values[2] if len(values) > 2 else ""
                expires_at = values[3] if len(values) > 3 else ""
                cor = values[4] if len(values) > 4 else ""
                modelo = values[5] if len(values) > 5 else ""

                exp_dt = parse_datetime(expires_at) if (status == "autorizado_temp" and expires_at) else None
                expired = (exp_dt < datetime.now()) if exp_dt else False
                is_authorized = status in self.AUTHORIZED_STATUSES and not expired

                # Match query
                if q_clean:
                    target = placa if ignore_case else placa
                    q_low = q.lower()
                    in_plate = q_clean in target
                    in_detalhes = q_low in detalhes.lower()
                    in_modelo = q_low in modelo.lower()
                    in_cor = q_low in cor.lower()
                    if not (in_plate or in_detalhes or in_modelo or in_cor):
                        continue

                # Filter authorized
                if authorized_only and not is_authorized:
                    continue

                # Temp filter
                if temp_filter:
                    if status != "autorizado_temp":
                        continue
                    if temp_filter == "active" and expired:
                        continue
                    if temp_filter == "expired" and not expired:
                        continue

                results.append({
                    "placa": placa,
                    "detalhes": detalhes,
                    "status": status,
                    "timestamp": ts,
                    "expires_at": expires_at,
                    "expires_display": format_expiry_display(exp_dt),
                    "time_remaining": format_time_remaining(exp_dt),
                    "expired": expired,
                    "is_authorized": is_authorized,
                    "cor": cor,
                    "modelo": modelo,
                })

            return results

    def add_history(self, query: str, user: str = "") -> None:
        q = query.strip().upper()
        if not q:
            return
        with self._lock:
            # Avoid duplicate consecutive
            if self.history and self.history[0]["query"] == q:
                return
            self.history.insert(0, {
                "query": q,
                "time": datetime.now().strftime("%H:%M:%S"),
                "user": user,
            })
            if len(self.history) > 60:
                self.history.pop()

    def clear_history(self) -> None:
        with self._lock:
            self.history.clear()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = 0
            authorized = 0
            temp_active = 0
            temp_expired = 0
            unauthorized = 0
            now = datetime.now()

            for values in self.data.values():
                status = values[1]
                if status == "excluido":
                    continue
                total += 1
                expires_at = values[3] if len(values) > 3 else ""
                exp_dt = parse_datetime(expires_at) if (status == "autorizado_temp" and expires_at) else None
                expired = (exp_dt < now) if exp_dt else False

                if status == "autorizado_temp":
                    if expired:
                        temp_expired += 1
                    else:
                        temp_active += 1
                        authorized += 1
                elif status in ("autorizado", "autorizado_patio"):
                    authorized += 1
                else:
                    unauthorized += 1

            return {
                "total": total,
                "authorized": authorized,
                "temp_active": temp_active,
                "temp_expired": temp_expired,
                "unauthorized": unauthorized,
                "csv_path": self.current_file_path or "",
                "csv_name": os.path.basename(self.current_file_path) if self.current_file_path else "Nenhum",
            }


# Singleton instance shared across the web app
repository = PlateRepository()
