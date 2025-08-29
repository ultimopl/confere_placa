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
APP_VERSAO = "1.1"
APP_CREDITOS = "Confere Placa\nVersão {0}\nDesenvolvido em Python 3.5 + Tkinter \nCriado por Lucas com o Chatgpt v5 e Grok v4".format(APP_VERSAO)
STATUS_VALIDOS = ["autorizado", "não autorizado", "para recepção", "para entrega", "autorizado_patio"]
AUTORIZADO_STATUSES = {"autorizado", "autorizado_patio"}

class App(tk.Tk):
    def __init__(self, db_inicial=None):
        tk.Tk.__init__(self)
        self.title("{} - v{}".format(APP_NOME, APP_VERSAO))
        self.geometry("900x550")
        self.resizable(True, True)

        self.db = db_inicial or {}
        self.csv_path = None

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
        style.configure("Treeview", font=('Helvetica', 18))
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Button(top, text="Abrir CSV…", command=self.abrir_csv).pack(side="left")
        ttk.Label(top, text="Buscar placa:").pack(side="left", padx=(10, 4))
        self.var_busca = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.var_busca, width=30, font=("verdana", 26))
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self.buscar())
        ttk.Button(top, text="Pesquisar", command=self.buscar).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Adicionar…", command=self.abrir_dialogo_adicionar).pack(side="left", padx=(10, 0))
        ttk.Button(top, text="Excluir", command=self._excluir_entrada).pack(side="left", padx=(10, 0))  # Novo botão Excluir
        self.var_case = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Ignorar maiúsc./minúsc.", variable=self.var_case).pack(side="left", padx=(12, 0))
        self.var_autorizado = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Somente autorizadas", variable=self.var_autorizado, command=self.buscar).pack(side="left", padx=(12, 0))

        self.var_count = tk.StringVar(value="0 resultados")
        ttk.Label(self, textvariable=self.var_count, padding=(8, 4)).pack(anchor="w")

        cols = ("placa", "detalhes", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c, w, a in (("placa", 120, "w"), ("detalhes", 480, "w"), ("status", 120, "center")):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor=a)

        self.tree.tag_configure("autorizado", foreground="green")
        self.tree.tag_configure("nao_autorizado", foreground="red")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")
        hsb.pack(fill="x", padx=8, pady=(0, 4))

        self.var_status = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.var_status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def mostrar_sobre(self):
        messagebox.showinfo("Sobre", APP_CREDITOS, parent=self)

    def abrir_dialogo_adicionar(self):
        win = tk.Toplevel(self)
        win.title("Adicionar placa")
        win.transient(self)
        win.grab_set()
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Placa:").grid(row=0, column=0, sticky="w")
        var_placa = tk.StringVar()
        ent_placa = ttk.Entry(frm, textvariable=var_placa, width=20)
        ent_placa.grid(row=0, column=1, sticky="we", padx=(6,0))

        ttk.Label(frm, text="Observações:").grid(row=1, column=0, sticky="w", pady=(8,0))
        var_det = tk.StringVar()
        ent_det = ttk.Entry(frm, textvariable=var_det, width=50)
        ent_det.grid(row=1, column=1, sticky="we", padx=(6,0), pady=(8,0))

        ttk.Label(frm, text="Status:").grid(row=2, column=0, sticky="w", pady=(8,0))
        var_status = tk.StringVar(value="autorizado")
        cb = ttk.Combobox(frm, textvariable=var_status, values=STATUS_VALIDOS, state="readonly", width=18)
        cb.grid(row=2, column=1, sticky="w", padx=(6,0), pady=(8,0))

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12,0))
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side="right")
        ttk.Button(btns, text="Salvar", command=lambda: self._salvar_nova_entrada(var_placa.get(), var_det.get(), var_status.get(), win)).pack(side="right", padx=(0,8))

        frm.columnconfigure(1, weight=1)
        ent_placa.focus_set()
        win.bind("<Return>", lambda e: self._salvar_nova_entrada(var_placa.get(), var_det.get(), var_status.get(), win))

    def _salvar_nova_entrada(self, placa, detalhes, status, win):
        placa = (placa or "").strip().upper()
        if not placa:
            messagebox.showerror("Erro", "Informe a placa.", parent=win)
            return
        if not re.match(r"^[A-Z]{3}-?\d{1}[A-Z0-9]\d{2}$", placa):
            messagebox.showerror("Erro", "Formato de placa inválido (ex: ABC1234 ou ABC1D23).", parent=win)
            return
        detalhes = (detalhes or "").strip()
        status = (status or "").strip()
        if not status or status not in STATUS_VALIDOS:
            messagebox.showerror("Erro", "Selecione um status válido.", parent=win)
            return
        if placa in self.db and not messagebox.askyesno("Confirmar", "Placa já existe. Substituir?", parent=win):
            return
        self.db[placa] = [detalhes, status, datetime.now().isoformat()]
        if not self.csv_path:
            messagebox.showerror("Erro", "Selecione um arquivo CSV.", parent=win)
            return
        try:
            with open(self.csv_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, delimiter=";")
                for p, lst in self.db.items():
                    d = lst[0]
                    s = lst[1]
                    t = lst[2] if len(lst) > 2 else ""
                    writer.writerow([p, d, s, t])
        except Exception as e:
            messagebox.showerror("Erro ao salvar CSV", "Falha ao salvar o arquivo: {}".format(str(e)), parent=win)
            return
        win.destroy()
        self.buscar()

    def _excluir_entrada(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione uma placa para excluir.", parent=self)
            return
        placa = self.tree.item(selected_item)["values"][0]
        if not messagebox.askyesno("Confirmar", f"Deseja excluir a placa {placa}?", parent=self):
            return
        # Registrar exclusão com timestamp antes de remover
        self.db[placa][1] = "excluido"  # Alterar status para "excluido"
        self.db[placa][2] = datetime.now().isoformat()  # Atualizar timestamp
        try:
            with open(self.csv_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, delimiter=";")
                for p, lst in self.db.items():
                    d = lst[0]
                    s = lst[1]
                    t = lst[2] if len(lst) > 2 else ""
                    writer.writerow([p, d, s, t])
        except Exception as e:
            messagebox.showerror("Erro ao salvar CSV", "Falha ao salvar o arquivo: {}".format(str(e)), parent=self)
            return
        del self.db[placa]  # Remover do banco de dados em memória
        self.buscar()

    def abrir_csv(self):
        path = filedialog.askopenfilename(title="Selecione o CSV", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            return
        try:
            self.db = self._carregar_csv_dict(path)
        except Exception as e:
            messagebox.showerror("Erro ao ler CSV", "Falha ao carregar o arquivo: {}".format(str(e)), parent=self)
            return
        self.csv_path = path
        self.var_status.set("CSV: {0} ({1} placas)".format(os.path.basename(path), len(self.db)))
        self.var_busca.set("")
        self._popular_tabela(self._iter_rows(self.db))

    def _carregar_csv_dict(self, path):
        data = {}
        with open(path, "rb") as fbin:
            sample = fbin.read(4096)
        encodings = ["utf-8-sig", "utf-8", "latin-1"]
        last_err = None
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as ftxt:
                    try:
                        dialect = csv.Sniffer().sniff(sample.decode(enc, errors="ignore"))
                        ftxt.seek(0)
                    except Exception:
                        dialect = csv.excel
                        ftxt.seek(0)
                        first = ftxt.readline()
                        if ";" in first and "," not in first:
                            dialect.delimiter = ";"
                        ftxt.seek(0)
                    reader = csv.reader(ftxt, dialect)
                    rows = [r for r in reader if any((c.strip() if c else "") for c in r)]
                if not rows:
                    return {}
                header = [c.strip().lower() for c in rows[0]]
                has_header = any(h in header for h in ["placa", "detalhes", "status"])
                start = 1 if has_header else 0
                for r in rows[start:]:
                    placa = (r[0].strip() if len(r) > 0 else "")
                    if not placa:
                        continue
                    detalhes = (r[1].strip() if len(r) > 1 else "")
                    status = (r[2].strip() if len(r) > 2 else "")
                    timestamp = (r[3].strip() if len(r) > 3 else "")
                    if status and status not in STATUS_VALIDOS and status != "excluido":
                        status = ""  # Ignorar status inválido, exceto "excluido"
                    data[placa] = [detalhes, status, timestamp]
                return data
            except Exception as e:
                last_err = e
        if last_err:
            raise RuntimeError("Não foi possível ler o CSV com as codificações tentadas: {}".format(str(last_err)))
        return {}

    def _iter_rows(self, dbdict):
        for placa, lst in dbdict.items():
            detalhes = lst[0] if len(lst) > 0 else ""
            status = lst[1] if len(lst) > 1 else ""
            if status == "excluido":  # Não exibir entradas excluídas na UI
                continue
            yield (placa, detalhes, status)

    def buscar(self):
        if not self.db:
            self._popular_tabela([])
            self.var_status.set("Base vazia.")
            return
        termo = self.var_busca.get().strip()
        ignore_case = self.var_case.get()

        def match(placa):
            if not termo:
                return True
            return (termo.lower() in placa.lower()) if ignore_case else (termo in placa)

        somente_aut = self.var_autorizado.get()
        resultados = []
        for placa, lst in self.db.items():
            detalhes = lst[0]
            status = lst[1]
            if status == "excluido":  # Ignorar entradas excluídas na busca
                continue
            if not match(placa):
                continue
            if somente_aut and (status or "").strip().lower() not in AUTORIZADO_STATUSES:
                continue
            resultados.append((placa, detalhes, status))
        self._popular_tabela(resultados)

    def _popular_tabela(self, linhas):
        for i in self.tree.get_children():
            self.tree.delete(i)
        count = 0
        for placa, detalhes, status in linhas:
            tag = "autorizado" if (status or "").strip().lower() in AUTORIZADO_STATUSES else "nao_autorizado"
            self.tree.insert("", "end", values=(placa, detalhes, status), tags=(tag,))
            count += 1
        self.var_count.set("{0} resultado(s)".format(count))
        if self.csv_path:
            self.var_status.set("Pronto. Fonte: {0}".format(os.path.basename(self.csv_path)))
        else:
            self.var_status.set("Pronto.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
