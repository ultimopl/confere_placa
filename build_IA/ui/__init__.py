import tkinter as tk
from tkinter import ttk, messagebox
from .search import SearchTab
from .add import AddTab
from .history import HistoryTab
from .config import ConfigTab


class UI(tk.Tk):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.title("{} - v{}".format(app.APP_NAME, app.VERSION))
        self.geometry("1200x700")
        self.resizable(True, True)
        self._build_menu()
        self._build_notebook()

    def _build_menu(self):
        menubar = tk.Menu(self)
        m_ajuda = tk.Menu(menubar, tearoff=0)
        m_ajuda.add_command(label="Sobre",
                            command=lambda: self.show_info("Sobre", self.app.credits))
        menubar.add_cascade(label="Ajuda", menu=m_ajuda)
        self.config(menu=menubar)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.search_tab = SearchTab(self.notebook, self.app)
        self.add_tab = AddTab(self.notebook, self.app)
        self.history_tab = HistoryTab(self.notebook, self.app)
        self.config_tab = ConfigTab(self.notebook, self.app)

        self.notebook.add(self.search_tab, text="  Pesquisa  ")
        self.notebook.add(self.add_tab, text="  Adicionar Placa  ")
        self.notebook.add(self.history_tab, text="  Histórico  ")
        self.notebook.add(self.config_tab, text="  Configurações  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        tab_id = self.notebook.select()
        tab = self.notebook.nametowidget(tab_id)
        if hasattr(tab, "on_tab_selected"):
            tab.on_tab_selected()

    # --- helpers called by app or tabs ---

    def show_error(self, title, message):
        messagebox.showerror(title, message, parent=self)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message, parent=self)

    def show_info(self, title, message):
        messagebox.showinfo(title, message, parent=self)

    def confirm_action(self, title, message):
        return messagebox.askyesno(title, message, parent=self)
