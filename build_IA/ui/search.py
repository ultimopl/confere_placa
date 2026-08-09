import tkinter as tk
from tkinter import ttk
from .base import BaseTab


class SearchTab(BaseTab):
    TAB_NAME = "Pesquisa"

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Buscar placa:").pack(side="left", padx=(0, 5))
        self.var_busca = tk.StringVar()
        self._after_id = None
        self.var_busca.trace("w", self._on_trace)
        ent = ttk.Entry(top, textvariable=self.var_busca, width=25, font=("verdana", 18))
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self._search())

        ttk.Button(top, text="Pesquisar", command=self._search).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Editar", command=self._edit).pack(side="left", padx=(20, 5))
        ttk.Button(top, text="Excluir", command=self._delete).pack(side="left", padx=5)

        self.var_case = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Ignorar maiúsc/minúsc", variable=self.var_case,
                        command=self._search).pack(side="left", padx=(20, 0))

        self.var_auth_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Somente autorizadas", variable=self.var_auth_only,
                        command=self._search).pack(side="left", padx=(10, 0))

        self.var_count = tk.StringVar(value="0 resultado(s)")
        ttk.Label(self, textvariable=self.var_count, padding=(10, 4)).pack(anchor="w")

        cols = ("placa", "detalhes", "status", "expira em")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for col, width, anchor in (
            ("placa", 130, "w"),
            ("detalhes", 420, "w"),
            ("status", 160, "center"),
            ("expira em", 160, "center"),
        ):
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.tag_configure("autorizado", foreground="green")
        self.tree.tag_configure("nao_autorizado", foreground="red")
        self.tree.tag_configure("temp_ativo", foreground="darkorange")
        self.tree.tag_configure("temp_expirado", foreground="gray")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        vsb.pack(side="right", fill="y")

        self.var_status_bar = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.var_status_bar, relief="sunken",
                  anchor="w", padding=4).pack(fill="x", side="bottom")

    def _on_trace(self, *args):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(400, self._search)

    def _search(self):
        query = self.var_busca.get().strip()
        results = self.app.search(query, self.var_case.get(), self.var_auth_only.get())
        self._populate(results)
        if query:
            self.app.add_history(query)
            self.app.ui.history_tab.refresh()

    def _populate(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for placa, detalhes, status, expired, expires_display in rows:
            if status == "autorizado_temp":
                tag = "temp_expirado" if expired else "temp_ativo"
                status_display = "temp ({})".format("expirado" if expired else "ativo")
            elif status in self.app.AUTHORIZED_STATUSES:
                tag = "autorizado"
                status_display = status
            else:
                tag = "nao_autorizado"
                status_display = status

            self.tree.insert("", "end",
                             values=(placa, detalhes, status_display, expires_display),
                             tags=(tag,))

        self.var_count.set("{} resultado(s)".format(len(rows)))
        self.var_status_bar.set("Pronto • {}".format(self.app.csv_label()))

    def _edit(self):
        selected = self.tree.selection()
        if not selected:
            self.app.ui.show_warning("Aviso", "Selecione uma placa para editar.")
            return
        placa = self.tree.item(selected[0])["values"][0]
        record = self.app.repository.data.get(placa)
        if record:
            detalhes = record[0]
            status = record[1]
            expires_at = record[3] if len(record) > 3 else ""
            self.app.ui.add_tab.prefill(placa, detalhes, status, expires_at, edit_mode=True)
            self.app.ui.notebook.select(self.app.ui.add_tab)

    def _delete(self):
        selected = self.tree.selection()
        if not selected:
            self.app.ui.show_warning("Aviso", "Selecione uma placa para excluir.")
            return
        placa = self.tree.item(selected[0])["values"][0]
        if self.app.ui.confirm_action("Confirmar", "Excluir a placa {}?".format(placa)):
            self.app.delete_entry(placa)
            self._search()

    def on_tab_selected(self):
        self._search()
