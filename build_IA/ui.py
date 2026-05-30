import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class UI(tk.Tk):
    """
    Handles the graphical user interface, user inputs, and visual feedback.
    """

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.title(f"{self.app.APP_NAME} - v{self.app.VERSION}")
        self.geometry("1150x650")
        self.resizable(True, True)

        self._build_menu()
        self._build_ui()
        
        self._search_after_id = None

    def _build_menu(self):
        menubar = tk.Menu(self)
        m_arquivo = tk.Menu(menubar, tearoff=0)
        m_arquivo.add_command(label="Abrir CSV...", command=self._on_abrir_csv)
        m_arquivo.add_separator()
        m_arquivo.add_command(label="Sair", command=self.destroy)
        menubar.add_cascade(label="Arquivo", menu=m_arquivo)

        m_ajuda = tk.Menu(menubar, tearoff=0)
        m_ajuda.add_command(label="Sobre", command=self._on_mostrar_sobre)
        menubar.add_cascade(label="Ajuda", menu=m_ajuda)
        self.config(menu=menubar)

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Treeview", font=('Helvetica', 14))
        style.configure("Treeview.Heading", font=('Helvetica', 11, 'bold'))

        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=8, pady=8)

        # --- LEFT PANEL ---
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=3)

        top_bar = ttk.Frame(left_frame, padding=8)
        top_bar.pack(fill="x")

        ttk.Button(top_bar, text="Abrir CSV...", command=self._on_abrir_csv).pack(side="left")

        ttk.Label(top_bar, text="Buscar placa:").pack(side="left", padx=(15, 5))
        self.var_busca = tk.StringVar()
        self.var_busca.trace("w", self._on_search_trace)
        
        ent_busca = ttk.Entry(top_bar, textvariable=self.var_busca, width=25, font=("verdana", 18))
        ent_busca.pack(side="left")
        ent_busca.bind("<Return>", lambda e: self.app.on_search_requested())

        ttk.Button(top_bar, text="Pesquisar", command=self.app.on_search_requested).pack(side="left", padx=(8, 0))

        ttk.Button(top_bar, text="Adicionar...", command=self._on_add_clicked).pack(side="left", padx=(25, 5))
        ttk.Button(top_bar, text="Editar", command=self._on_edit_clicked).pack(side="left", padx=5)
        ttk.Button(top_bar, text="Excluir", command=self._on_delete_clicked).pack(side="left", padx=5)

        self.var_case = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_bar, text="Ignorar maiúsc/minúsc", variable=self.var_case, 
                        command=self.app.on_search_requested).pack(side="left", padx=(10, 0))

        self.var_autorizado = tk.BooleanVar(value=False)
        ttk.Checkbutton(top_bar, text="Somente autorizadas", variable=self.var_autorizado, 
                        command=self.app.on_search_requested).pack(side="left", padx=(10, 0))

        self.var_count = tk.StringVar(value="0 resultados")
        ttk.Label(left_frame, textvariable=self.var_count, padding=(10, 6)).pack(anchor="w")

        cols = ("placa", "detalhes", "status")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        for c, w, a in (("placa", 140, "w"), ("detalhes", 450, "w"), ("status", 140, "center")):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor=a)
        
        self.tree.tag_configure("autorizado", foreground="green")
        self.tree.tag_configure("nao_autorizado", foreground="red")

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        vsb.pack(side="right", fill="y")

        self.var_status_msg = tk.StringVar(value="Pronto.")
        ttk.Label(left_frame, textvariable=self.var_status_msg, relief="sunken", anchor="w", padding=5).pack(fill="x", side="bottom")

        # --- RIGHT PANEL ---
        right_frame = ttk.Frame(main_pane, width=280)
        main_pane.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Histórico de Pesquisas", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        
        hist_top = ttk.Frame(right_frame)
        hist_top.pack(fill="x", padx=8, pady=4)
        ttk.Button(hist_top, text="Limpar Histórico", command=self.app.on_clear_history).pack(side="right")

        self.hist_tree = ttk.Treeview(right_frame, columns=("placa", "hora"), show="headings", height=20)
        self.hist_tree.heading("placa", text="Placa")
        self.hist_tree.heading("hora", text="Hora")
        self.hist_tree.column("placa", width=110, anchor="w")
        self.hist_tree.column("hora", width=100, anchor="center")

        hist_vsb = ttk.Scrollbar(right_frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscroll=hist_vsb.set)
        self.hist_tree.pack(fill="both", expand=True, padx=8, pady=4)
        hist_vsb.pack(side="right", fill="y")
        self.hist_tree.bind("<Double-1>", self._on_history_double_click)

    def _on_search_trace(self, *args):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(400, self.app.on_search_requested)

    def _on_abrir_csv(self):
        self.app.on_open_csv_requested()

    def _on_add_clicked(self):
        self.app.on_add_requested()

    def _on_edit_clicked(self):
        self.app.on_edit_requested()

    def _on_delete_clicked(self):
        self.app.on_delete_requested()

    def _on_mostrar_sobre(self):
        self.app.on_mostrar_sobre()

    def _on_history_double_click(self, event):
        selected = self.hist_tree.selection()
        if not selected:
            return
        placa = self.hist_tree.item(selected[0])["values"][0]
        self.var_busca.set(placa)
        self.app.on_search_requested()

    def update_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for placa, detalhes, status in rows:
            tag = "autorizado" if status in self.app.AUTHORIZED_STATUSES else "nao_autorizado"
            self.tree.insert("", "end", values=(placa, detalhes, status), tags=(tag,))
        self.var_count.set(f"{len(rows)} resultado(s)")

    def update_status(self, message):
        self.var_status_msg.set(message)

    def update_history(self, placa, time_str):
        self.hist_tree.insert("", 0, values=(placa, time_str))

    def clear_history_ui(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)

    def show_error(self, title, message):
        messagebox.showerror(title, message, parent=self)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message, parent=self)

    def show_info(self, title, message):
        messagebox.showinfo(title, message, parent=self)

    def confirm_action(self, title, message):
        return messagebox.askyesno(title, message, parent=self)

    def create_editor_window(self, mode, p="", d="", s=""):
        win = tk.Toplevel(self)
        win.title("Adicionar Placa" if mode == "add" else "Editar Placa")
        win.transient(self)
        win.grab_set()
        win.geometry("520x260")

        frm = ttk.Frame(win, padding=15)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Placa:").grid(row=0, column=0, sticky="w")
        var_placa = tk.StringVar(value=p)
        ent_placa = ttk.Entry(frm, textvariable=var_placa, width=20, font=("verdana", 14))
        ent_placa.grid(row=0, column=1, sticky="we", padx=(10, 0))
        if mode == "edit":
            ent_placa.config(state="readonly")

        ttk.Label(frm, text="Observações:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        var_det = tk.StringVar(value=d)
        ent_det = ttk.Entry(frm, textvariable=var_det, width=50)
        ent_det.grid(row=1, column=1, sticky="we", padx=(10, 0), pady=(12, 0))

        ttk.Label(frm, text="Status:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        var_status = tk.StringVar(value=s if s else self.app.STATUS_VALIDOS[0])
        cb = ttk.Combobox(frm, textvariable=var_status, values=self.app.STATUS_VALIDOS, state="readonly", width=25)
        cb.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(12, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(20, 0))
        
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side="right", padx=(10,0))
        
        def on_save():
            if self.app.save_entry(var_placa.get(), var_det.get(), var_status.get()):
                win.destroy()

        ttk.Button(btns, text="Salvar", command=on_save).pack(side="right")

        frm.columnconfigure(1, weight=1)
        (ent_placa if mode == "add" else ent_det).focus_set()
