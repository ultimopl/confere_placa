import tkinter as tk
from tkinter import ttk
from .base import BaseTab


class HistoryTab(BaseTab):
    TAB_NAME = "Histórico"

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Histórico de Pesquisas",
                  font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Limpar", command=self._clear).pack(side="right")

        cols = ("placa", "hora")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("placa", text="Placa")
        self.tree.heading("hora", text="Hora")
        self.tree.column("placa", width=180, anchor="w")
        self.tree.column("hora", width=120, anchor="center")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for placa, time_str in reversed(self.app.history_list):
            self.tree.insert("", "end", values=(placa, time_str))

    def _clear(self):
        if self.app.ui.confirm_action("Limpar Histórico", "Deseja limpar todo o histórico?"):
            self.app.history_list.clear()
            self.refresh()

    def _on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        placa = self.tree.item(selected[0])["values"][0]
        self.app.ui.search_tab.var_busca.set(placa)
        self.app.ui.notebook.select(self.app.ui.search_tab)
        self.app.ui.search_tab._search()

    def on_tab_selected(self):
        self.refresh()
