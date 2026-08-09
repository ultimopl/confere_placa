import json
import os
import re
from datetime import datetime

from repository import Repository
from ui import UI

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_PATH = os.path.join(APP_DIR, "..", "app.conf")


def _parse_dt(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


class App:
    APP_NAME = "Confere Placa"
    VERSION = "3.0"
    AUTHORIZED_STATUSES = ["autorizado", "autorizado_patio", "autorizado_temp"]
    STATUS_VALIDOS = [
        "autorizado", "não autorizado", "para recepção",
        "para entrega", "autorizado_patio", "autorizado_temp",
    ]

    def __init__(self):
        self.repository = Repository(delimiter=";")
        self.csv_path = None
        self.history_list = []  # [(placa, time_str), ...]
        self.credits = "{}\nVersão {}\nArquitetura em abas".format(self.APP_NAME, self.VERSION)

        self.conf_path = os.path.normpath(CONF_PATH)
        self.config = self._load_config()

        self.ui = UI(self)

    def run(self):
        last_csv = self.config.get("last_csv", "")
        if last_csv and os.path.exists(last_csv):
            self._load_csv(last_csv)
        self.ui.mainloop()

    # --- CSV ---

    def on_open_csv_requested(self, path):
        try:
            self._load_csv(path)
        except Exception as e:
            self.ui.show_error("Erro", "Falha ao carregar: {}".format(e))

    def _load_csv(self, path):
        self.repository.load(path)
        self.csv_path = path
        self.config["last_csv"] = path
        self._save_config()

    def csv_label(self):
        if self.csv_path:
            return os.path.basename(self.csv_path)
        return "nenhum arquivo"

    # --- Search ---

    def search(self, query, ignore_case=True, authorized_only=False):
        raw = self.repository.find_by_query(
            query,
            ignore_case=ignore_case,
            authorized_only=authorized_only,
            authorized_statuses=self.AUTHORIZED_STATUSES,
        )
        results = []
        for placa, detalhes, status in raw:
            record = self.repository.data[placa]
            expires_at = record[3] if len(record) > 3 else ""
            expired = self._is_expired(status, expires_at)
            expires_display = self._format_expiry(expires_at) if status == "autorizado_temp" else ""
            results.append((placa, detalhes, status, expired, expires_display))
        return results

    def _is_expired(self, status, expires_at):
        if status != "autorizado_temp" or not expires_at:
            return False
        dt = _parse_dt(expires_at)
        if dt is None:
            return False
        return dt < datetime.now()

    def _format_expiry(self, expires_at):
        if not expires_at:
            return ""
        dt = _parse_dt(expires_at)
        if dt is None:
            return expires_at
        return dt.strftime("%d/%m/%Y %H:%M")

    # --- Save / Delete ---

    def save_entry(self, placa, detalhes, status, expires_at=None):
        placa_clean = (placa or "").strip().upper().replace("-", "")
        if not placa_clean:
            self.ui.show_error("Erro", "Informe a placa.")
            return False
        if not re.match(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$", placa_clean):
            self.ui.show_error("Erro", "Formato de placa inválido!\nEx: ABC1234 ou ABC1D23")
            return False
        if status not in self.STATUS_VALIDOS:
            self.ui.show_error("Erro", "Status inválido.")
            return False
        if not self.csv_path:
            self.ui.show_error("Erro", "Abra um arquivo CSV primeiro (aba Configurações).")
            return False
        try:
            self.repository.add_or_update(placa_clean, (detalhes or "").strip(), status,
                                          expires_at or "")
            self.repository.save(self.repository.get_all(), self.csv_path)
            return True
        except Exception as e:
            self.ui.show_error("Erro", "Falha ao salvar: {}".format(e))
            return False

    def delete_entry(self, placa):
        try:
            self.repository.delete(placa)
            self.repository.save(self.repository.get_all(), self.csv_path)
        except Exception as e:
            self.ui.show_error("Erro", "Falha ao excluir: {}".format(e))

    # --- History ---

    def add_history(self, placa):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.history_list.append((placa, time_str))

    # --- Config ---

    def _load_config(self):
        try:
            with open(self.conf_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self):
        try:
            with open(self.conf_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
