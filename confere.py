import csv
import os
import re
from datetime import datetime
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    raise RuntimeError("Requer Python 3.x com tkinter.")

APP_NOME = "Confere Placa"
APP_VERSAO = "1.3"  # Atualizada com Histórico
APP_CREDITOS = f"""Confere Placa
Versão {APP_VERSAO}
Desenvolvido em Python 3 + Tkinter
Nova funcionalidade: Histórico de placas pesquisadas"""

STATUS_VALIDOS = ["autorizado", "não autorizado", "para recepção", "para entrega", "autorizado_patio"]
AUTORIZADO_STATUSES = ["autorizado", "autorizado_patio"]

class App(tk.Tk):
    def __init__(self, db_inicial=None):
        tk.Tk.__init__(self)
        self.title(f"{APP_NOME} - v{APP_VERSAO}")
        self.geometry("1150x650")
        self.resizable(True, True)
        
        self.db = db_inicial or {}                    # {placa: [detalhes, status, timestamp]}
        self.csv_path = None
        self.historico = []                           # Lista de (placa, datetime)

        self._build_menu()
        self._build_ui()
        self._popular_tabela(self._iter_rows(self.db))

    def _build_menu(self):
        menubar = tk.Menu(self)
        m_arquivo = tk.Menu(menubar, tearoff=0)
        m_arquivo.add_command(label="Abrir CSV…", command=self.abrir_csv)
        m_arquivo.add_separator()
        m_arquivo.add_command(label="Sair", command=self.destroy)
        menubar.add_cascade(label="Arquivo", menu=m_arquivo)

        m_ajuda = tk.Menu(menubar, tearoff=0)
        m_ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        menubar.add_cascade(label="Ajuda", menu=m_ajuda)

        self.config(menu=menubar)

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Treeview", font=('Helvetica', 16))
        style.configure("Treeview.Heading", font=('Helvetica', 12, 'bold'))

        # ==================== PANEL PRINCIPAL ====================
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=8, pady=8)

        # ==================== ÁREA ESQUERDA (Tabela + Busca) ====================
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=3)

        # Barra superior
        top = ttk.Frame(left_frame, padding=8)
        top.pack(fill="x")

        ttk.Button(top, text="Abrir CSV…", command=self.abrir_csv).pack(side="left")
        
        ttk.Label(top, text="Buscar placa:").pack(side="left", padx=(15, 5))
        self.var_busca = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.var_busca, width=25, font=("verdana", 22))
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self.buscar())

        ttk.Button(top, text="Pesquisar", command=self.buscar).pack(side="left", padx=(8, 0))

        # Botões de ação
        ttk.Button(top, text="Adicionar…", command=self.abrir_dialogo_adicionar).pack(side="left", padx=(25, 5))
        ttk.Button(top, text="Editar", command=self._abrir_dialogo_editar).pack(side="left", padx=5)
        ttk.Button(top, text="Excluir", command=self._excluir_entrada).pack(side="left", padx=5)

        self.var_case = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Ignorar maiúsc./minúsc.", variable=self.var_case).pack(side="left", padx=(20, 0))

        self.var_autorizado = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Somente autorizadas", variable=self.var_autorizado, 
                       command=self.buscar).pack(side="left", padx=(15, 0))

        self.var_count = tk.StringVar(value="0 resultados")
        ttk.Label(left_frame, textvariable=self.var_count, padding=(10, 6)).pack(anchor="w")

        # Tabela
        cols = ("placa", "detalhes", "status")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        
        for c, w, a in (("placa", 140, "w"), ("detalhes", 520, "w"), ("status", 140, "center")):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor=a)

        self.tree.tag_configure("autorizado", foreground="green")
        self.tree.tag_configure("nao_autorizado", foreground="red")

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        vsb.pack(side="right", fill="y")

        self.var_status = tk.StringVar(value="Pronto.")
        ttk.Label(left_frame, textvariable=self.var_status, relief="sunken", anchor="w", padding=5).pack(fill="x", side="bottom")

        # ==================== ÁREA DIREITA - HISTÓRICO ====================
        right_frame = ttk.Frame(main_pane, width=280)
        main_pane.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Histórico de Pesquisas", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=8, pady=(8,4))

        hist_top = ttk.Frame(right_frame)
        hist_top.pack(fill="x", padx=8, pady=4)
        ttk.Button(hist_top, text="Limpar Histórico", command=self.limpar_historico).pack(side="right")

        # Lista de Histórico
        self.hist_tree = ttk.Treeview(right_frame, columns=("placa", "hora"), show="headings", height=20)
        self.hist_tree.heading("placa", text="Placa")
        self.hist_tree.heading("hora", text="Hora")
        self.hist_tree.column("placa", width=110, anchor="w")
        self.hist_tree.column("hora", width=100, anchor="center")

        hist_vsb = ttk.Scrollbar(right_frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscroll=hist_vsb.set)

        self.hist_tree.pack(fill="both", expand=True, padx=8, pady=4)
        hist_vsb.pack(side="right", fill="y")

        self.hist_tree.bind("<Double-1>", self._carregar_do_historico)

    def adicionar_ao_historico(self, placa):
        """Adiciona placa ao histórico com timestamp"""
        agora = datetime.now()
        hora_formatada = agora.strftime("%H:%M:%S")
        self.historico.append((placa, agora))
        
        # Atualiza a Treeview do histórico (mais recente primeiro)
        self.hist_tree.insert("", 0, values=(placa, hora_formatada))

    def limpar_historico(self):
        if messagebox.askyesno("Limpar Histórico", "Deseja limpar todo o histórico de pesquisas?", parent=self):
            self.historico.clear()
            for item in self.hist_tree.get_children():
                self.hist_tree.delete(item)

    def _carregar_do_historico(self, event=None):
        selected = self.hist_tree.selection()
        if not selected:
            return
        placa = self.hist_tree.item(selected[0])["values"][0]
        self.var_busca.set(placa)
        self.buscar()

    # ==================== RESTO DAS FUNÇÕES (mantidas e ajustadas) ====================
    def mostrar_sobre(self):
        messagebox.showinfo("Sobre", APP_CREDITOS, parent=self)

    def abrir_dialogo_adicionar(self):
        self._abrir_dialogo_edicao(mode="add")

    def _abrir_dialogo_editar(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma placa para editar.", parent=self)
            return
        values = self.tree.item(selected[0])["values"]
        self._abrir_dialogo_edicao(mode="edit", placa_atual=values[0], 
                                  detalhes_atual=values[1], status_atual=values[2])

    def _abrir_dialogo_edicao(self, mode="add", placa_atual="", detalhes_atual="", status_atual="autorizado"):
        # (mesmo código da versão anterior - mantido igual)
        win = tk.Toplevel(self)
        win.title("Adicionar Placa" if mode == "add" else "Editar Placa")
        win.transient(self)
        win.grab_set()
        win.geometry("520x240")

        frm = ttk.Frame(win, padding=15)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Placa:").grid(row=0, column=0, sticky="w")
        var_placa = tk.StringVar(value=placa_atual)
        ent_placa = ttk.Entry(frm, textvariable=var_placa, width=20, font=("verdana", 14))
        ent_placa.grid(row=0, column=1, sticky="we", padx=(10, 0))
        if mode == "edit":
            ent_placa.config(state="readonly")

        ttk.Label(frm, text="Observações:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        var_det = tk.StringVar(value=detalhes_atual)
        ent_det = ttk.Entry(frm, textvariable=var_det, width=50)
        ent_det.grid(row=1, column=1, sticky="we", padx=(10, 0), pady=(12, 0))

        ttk.Label(frm, text="Status:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        var_status = tk.StringVar(value=status_atual)
        cb = ttk.Combobox(frm, textvariable=var_status, values=STATUS_VALIDOS, state="readonly", width=25)
        cb.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(12, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side="right", padx=(10,0))
        ttk.Button(btns, text="Salvar", command=lambda: self._salvar_edicao(
            var_placa.get(), var_det.get(), var_status.get(), win, mode, placa_atual)
        ).pack(side="right")

        frm.columnconfigure(1, weight=1)
        (ent_placa if mode == "add" else ent_det).focus_set()

    def _salvar_edicao(self, placa_nova, detalhes, status, win, mode, placa_antiga=""):
        placa_nova = (placa_nova or "").strip().upper().replace("-", "")
        if not placa_nova:
            messagebox.showerror("Erro", "Informe a placa.", parent=win)
            return
        if not re.match(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$", placa_nova):
            messagebox.showerror("Erro", "Formato de placa inválido!\nEx: ABC1234 ou ABC1D23", parent=win)
            return

        detalhes = (detalhes or "").strip()
        status = (status or "").strip()

        if status not in STATUS_VALIDOS:
            messagebox.showerror("Erro", "Status inválido.", parent=win)
            return

        if not self.csv_path:
            messagebox.showerror("Erro", "Abra um arquivo CSV primeiro.", parent=win)
            return

        self.db[placa_nova] = [detalhes, status, datetime.now().isoformat()]

        self._salvar_csv()
        win.destroy()
        self.buscar()

    def _excluir_entrada(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma placa para excluir.", parent=self)
            return
        placa = self.tree.item(selected[0])["values"][0]

        if not messagebox.askyesno("Confirmar", f"Excluir a placa {placa}?", parent=self):
            return

        if placa in self.db:
            self.db[placa][1] = "excluido"
            self.db[placa][2] = datetime.now().isoformat()

        self._salvar_csv()
        self.buscar()

    def _salvar_csv(self):
        if not self.csv_path:
            return
        try:
            with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                for p, lst in self.db.items():
                    writer.writerow([p, lst[0], lst[1], lst[2] if len(lst) > 2 else ""])
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar CSV:\n{e}")

    def abrir_csv(self):
        path = filedialog.askopenfilename(title="Selecione o CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        try:
            self.db = self._carregar_csv_dict(path)
            self.csv_path = path
            self.var_status.set(f"CSV: {os.path.basename(path)} ({len(self.db)} placas)")
            self.buscar()   # mostra todas ao carregar
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar CSV:\n{e}")

    def _carregar_csv_dict(self, path):
        data = {}
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                if len(row) < 3 or not row[0].strip():
                    continue
                placa = row[0].strip().upper()
                detalhes = row[1].strip() if len(row) > 1 else ""
                status = row[2].strip() if len(row) > 2 else "não autorizado"
                ts = row[3].strip() if len(row) > 3 else ""
                data[placa] = [detalhes, status, ts]
        return data

    def _iter_rows(self, dbdict):
        for placa, lst in dbdict.items():
            if len(lst) > 1 and lst[1] == "excluido":
                continue
            yield (placa, lst[0], lst[1] if len(lst) > 1 else "")

    def buscar(self):
        termo = self.var_busca.get().strip().upper()
        if not termo:
            # Se não digitou nada, mostra tudo
            resultados = list(self._iter_rows(self.db))
            self._popular_tabela(resultados)
            return

        # Adiciona ao histórico
        self.adicionar_ao_historico(termo)

        ignore_case = self.var_case.get()
        somente_aut = self.var_autorizado.get()

        resultados = []
        for placa, lst in self.db.items():
            if len(lst) > 1 and lst[1] == "excluido":
                continue

            status = lst[1]
            detalhes = lst[0]

            # Busca na placa
            if ignore_case:
                match = termo.lower() in placa.lower()
            else:
                match = termo in placa

            if not match:
                continue

            if somente_aut and status not in AUTORIZADO_STATUSES:
                continue

            resultados.append((placa, detalhes, status))

        self._popular_tabela(resultados)

    def _popular_tabela(self, linhas):
        for i in self.tree.get_children():
            self.tree.delete(i)

        count = 0
        for placa, detalhes, status in linhas:
            tag = "autorizado" if status in AUTORIZADO_STATUSES else "nao_autorizado"
            self.tree.insert("", "end", values=(placa, detalhes, status), tags=(tag,))
            count += 1

        self.var_count.set(f"{count} resultado(s)")

        if self.csv_path:
            self.var_status.set(f"Pronto • {os.path.basename(self.csv_path)}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
