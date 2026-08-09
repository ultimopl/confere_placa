import tkinter as tk
from tkinter import ttk, filedialog
from .base import BaseTab


class ConfigTab(BaseTab):
    TAB_NAME = "Configurações"

    def _build(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Configurações", font=("Helvetica", 13, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 20))

        ttk.Label(frm, text="Arquivo CSV:").grid(row=1, column=0, sticky="w")
        self.var_csv_path = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_csv_path, width=55, state="readonly").grid(
            row=1, column=1, padx=(10, 6), sticky="we")
        ttk.Button(frm, text="Abrir…", command=self._browse_csv).grid(row=1, column=2)

        ttk.Separator(frm, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="we", pady=20)

        ttk.Label(frm, text="Arquivo de configuração:").grid(row=3, column=0, sticky="w")
        self.var_conf_path = tk.StringVar()
        ttk.Label(frm, textvariable=self.var_conf_path, foreground="gray").grid(
            row=3, column=1, columnspan=2, sticky="w", padx=(10, 0))

        self.var_msg = tk.StringVar()
        ttk.Label(frm, textvariable=self.var_msg, foreground="green").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(20, 0))

        frm.columnconfigure(1, weight=1)

    def on_tab_selected(self):
        self.var_csv_path.set(self.app.config.get("last_csv", ""))
        self.var_conf_path.set(self.app.conf_path)

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Selecione o CSV",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        self.app.on_open_csv_requested(path)
        self.var_csv_path.set(path)
        self.var_msg.set("CSV carregado: {}".format(path.split("/")[-1]))
