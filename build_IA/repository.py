import csv
import os
import shutil
import tempfile
from datetime import datetime

class Repository:
    """
    Handles data persistence using CSV with atomic writes.
    """

    def __init__(self, delimiter=";"):
        self.delimiter = delimiter
        self.data = {}  # {placa: [detalhes, status, timestamp]}
        self.current_file_path = None

    def load(self, file_path):
        """
        Loads data from a CSV file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"O arquivo {file_path} não existe.")

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
                    new_data[placa] = [detalhes, status, ts]
            
            self.data = new_data
            self.current_file_path = file_path
            return self.data
        except Exception as e:
            raise IOError(f"Erro ao carregar CSV: {e}")

    def save(self, data, file_path):
        """
        Saves data to a CSV file using atomic write pattern.
        """
        if not file_path:
            raise ValueError("Caminho do arquivo não fornecido.")

        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path), prefix="tmp_")
        
        try:
            with os.fdopen(fd, 'w', encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=self.delimiter)
                for placa, values in data.items():
                    # values: [detalhes, status, timestamp]
                    row = [placa] + values
                    # Ensure row has exactly 4 elements for consistency
                    while len(row) < 4:
                        row.append("")
                    writer.writerow(row[:4])
            
            # Atomic swap
            shutil.move(temp_path, file_path)
            self.current_file_path = file_path
            self.data = data.copy()
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError(f"Erro ao salvar CSV (escrita atômica falhou): {e}")

    def find_by_query(self, query, ignore_case=True, authorized_only=False, authorized_statuses=None):
        """
        Searches through the loaded data.
        """
        if authorized_statuses is None:
            authorized_statuses = []

        results = []
        query_clean = query.strip().upper()

        for placa, values in self.data.items():
            # values: [detalhes, status, timestamp]
            status = values[1]
            detalhes = values[0]

            # Skip deleted items
            if status == "excluido":
                continue

            # Search logic
            match = False
            if not query_clean:
                match = True
            elif ignore_case:
                if query_clean in placa:
                    match = True
            else:
                if query_clean == placa:
                    match = True

            if not match:
                continue

            # Filter by authorized status
            if authorized_only and status not in authorized_statuses:
                continue

            results.append((placa, detalhes, status))
        
        return results

    def add_or_update(self, placa, detalhes, status):
        """
        Updates the internal data dictionary.
        """
        self.data[placa] = [detalhes, status, datetime.now().isoformat()]

    def delete(self, placa):
        """
        Marks a record as deleted (soft delete).
        """
        if placa in self.data:
            self.data[placa][1] = "excluido"
            self.data[placa][2] = datetime.now().isoformat()
            return True
        return False

    def get_all(self):
        return self.data
