import tkinter as tk
from tkinter import filedialog
import datetime
import re
from repository import Repository
from ui import UI

class App:
    """
    Controller class that manages the flow between UI and Repository.
    """

    APP_NAME = "Confere Placa"
    VERSION = "2.0 (Refactored)"
    AUTHORIZED_STATUSES = ["autorizado", "autorizado_patio"]
    STATUS_VALIDOS = ["autorizado", "não autorizado", "para recepção", "para entrega", "autorizado_patio"]

    def __init__(self):
        self.repository = Repository(delimiter=";")
        self.ui = UI(self)
        
        self.credits = f"{self.APP_NAME}\nVersão {self.VERSION}\nArquitetura Refatorada"
        self.csv_path = None
        self.history_list = []

    def run(self):
        self.ui.mainloop()

    # --- UI Callbacks (Event Handlers) ---

    def on_search_requested(self):
        query = self.ui.var_busca.get().strip().upper()
        
        if not query:
            results = self.repository.find_by_query("", 
                                                authorized_only=self.ui.var_autorizado.get(),
                                                authorized_statuses=self.AUTHORIZED_STATUSES)
            self.ui.update_table(results)
            return

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.ui.update_history(query, now_str)
        self.history_list.append((query, now_str))

        results = self.repository.find_by_query(
            query,
            ignore_case=self.ui.var_case.get(),
            authorized_only=self.ui.var_autorizado.get(),
            authorized_statuses=self.AUTHORIZED_STATUSES
        )
        self.ui.update_table(results)

    def on_open_csv_requested(self):
        path = filedialog.askopenfilename(title="Selecione o CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        
        try:
            self.repository.load(path)
            self.csv_path = path
            self.ui.update_status(f"Pronto • {path.split('/')[-1]}")
            self.on_search_requested()
        except Exception as e:
            self.ui.show_error("Erro", f"Falha ao carregar: {e}")

    def on_add_requested(self):
        self.ui.create_editor_window(mode="add")

    def on_edit_requested(self):
        selected = self.ui.tree.selection()
        if not selected:
            self.ui.show_warning("Aviso", "Selecione uma placa para editar.")
            return
        
        values = self.ui.tree.item(selected[0])["values"]
        self.ui.create_editor_window(mode="edit", p=values[0], d=values[1], s=values[2])

    def on_delete_requested(self):
        selected = self.ui.tree.selection()
        if not selected:
            self.ui.show_warning("Aviso", "Selecione uma placa para excluir.")
            return
        
        placa = self.ui.tree.item(selected[0])["values"][0]
        if self.ui.confirm_action("Confirmar", f"Deseja excluir a placa {placa}?"):
            try:
                self.repository.delete(placa)
                self.repository.save(self.repository.get_all(), self.csv_path)
                self.on_search_requested()
            except Exception as e:
                self.ui.show_error("Erro", f"Falha ao excluir: {e}")

    def on_clear_history(self):
        if self.ui.confirm_action("Limpar Histórico", "Deseja limpar todo o histórico?"):
            self.history_list.clear()
            self.ui.clear_history_ui()

    def save_entry(self, placa, detalhes, status):
        placa_clean = placa.strip().upper().replace("-", "")
        if not placa_clean:
            self.ui.show_error("Erro", "Informe a placa.")
            return False
        
        if not re.match(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$", placa_clean):
             self.ui.show_error("Erro", "Formato de placa inválido!")
             return False

        if status not in self.STATUS_VALIDOS:
            self.ui.show_error("Erro", "Status inválido.")
            return False

        if not self.csv_path:
            self.ui.show_error("Erro", "Abra um arquivo CSV primeiro.")
            return False

        try:
            self.repository.add_or_update(placa_clean, detalhes.strip(), status)
            self.repository.save(self.repository.get_all(), self.csv_path)
            self.on_search_requested()
            return True
        except Exception as e:
            self.ui.show_error("Erro", f"Falha ao salvar: {e}")
            return False

if __name__ == "__main__":
    pass
