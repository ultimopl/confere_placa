import csv
import os
import shutil
import tempfile
from datetime import datetime


class Repository:
    # data: {placa: [detalhes, status, timestamp, expires_at]}

    def __init__(self, delimiter=";"):
        self.delimiter = delimiter
        self.data = {}
        self.current_file_path = None

    def load(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError("O arquivo {} não existe.".format(file_path))
        new_data = {}
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                for row in reader:
                    if len(row) < 3 or not row[0].strip():
                        continue
                    placa = row[0].strip().upper()
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
        except Exception as e:
            raise IOError("Erro ao carregar CSV: {}".format(e))

    def save(self, data, file_path):
        if not file_path:
            raise ValueError("Caminho do arquivo não fornecido.")
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path), prefix="tmp_")
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
            self.data = data.copy()
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError("Erro ao salvar CSV (escrita atômica falhou): {}".format(e))

    def find_by_query(self, query, ignore_case=True, authorized_only=False,
                      authorized_statuses=None):
        if authorized_statuses is None:
            authorized_statuses = []
        results = []
        query_clean = query.strip().upper()
        for placa, values in self.data.items():
            status = values[1]
            detalhes = values[0]
            if status == "excluido":
                continue
            if not query_clean:
                match = True
            elif ignore_case:
                match = query_clean in placa
            else:
                match = query_clean == placa
            if not match:
                continue
            if authorized_only and status not in authorized_statuses:
                continue
            results.append((placa, detalhes, status))
        return results

    def add_or_update(self, placa, detalhes, status, expires_at=""):
        self.data[placa] = [detalhes, status, datetime.now().isoformat(), expires_at]

    def delete(self, placa):
        if placa in self.data:
            self.data[placa][1] = "excluido"
            self.data[placa][2] = datetime.now().isoformat()
            return True
        return False

    def get_all(self):
        return self.data
