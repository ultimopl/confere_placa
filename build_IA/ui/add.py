import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from .base import BaseTab


def _parse_dt(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


class AddTab(BaseTab):
    TAB_NAME = "Adicionar Placa"

    def _build(self):
        self._mode = "add"
        self._edit_placa = None

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        self.var_mode_label = tk.StringVar(value="Adicionar nova placa")
        ttk.Label(frm, textvariable=self.var_mode_label,
                  font=("Helvetica", 13, "bold")).grid(row=0, column=0, columnspan=2,
                                                        sticky="w", pady=(0, 16))

        ttk.Label(frm, text="Placa:").grid(row=1, column=0, sticky="w")
        self.var_placa = tk.StringVar()
        self.ent_placa = ttk.Entry(frm, textvariable=self.var_placa,
                                   width=20, font=("verdana", 14))
        self.ent_placa.grid(row=1, column=1, sticky="w", padx=(10, 0))

        ttk.Label(frm, text="Observações:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.var_det = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_det, width=50).grid(
            row=2, column=1, sticky="we", padx=(10, 0), pady=(12, 0))

        ttk.Label(frm, text="Status:").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.var_status = tk.StringVar(value="autorizado")
        self.cb_status = ttk.Combobox(frm, textvariable=self.var_status,
                                      values=self.app.STATUS_VALIDOS,
                                      state="readonly", width=25)
        self.cb_status.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(12, 0))
        self.cb_status.bind("<<ComboboxSelected>>", self._on_status_change)

        # Temp auth section
        self.temp_frame = ttk.LabelFrame(frm, text="Autorização temporária", padding=12)
        self.temp_frame.grid(row=4, column=0, columnspan=2, sticky="we", pady=(16, 0))

        ttk.Label(self.temp_frame, text="Duração (horas):").grid(row=0, column=0, sticky="w")
        self.var_hours = tk.IntVar(value=24)
        ttk.Spinbox(self.temp_frame, from_=1, to=8760, textvariable=self.var_hours,
                    width=7).grid(row=0, column=1, padx=(8, 4), sticky="w")
        ttk.Label(self.temp_frame, text="horas a partir de agora").grid(row=0, column=2, sticky="w")

        ttk.Label(self.temp_frame, text="Ou data/hora exata:").grid(
            row=1, column=0, sticky="w", pady=(10, 0))
        date_frm = ttk.Frame(self.temp_frame)
        date_frm.grid(row=1, column=1, columnspan=2, sticky="w", pady=(10, 0))
        self.var_expires_date = tk.StringVar()
        self.var_expires_time = tk.StringVar()
        ttk.Entry(date_frm, textvariable=self.var_expires_date, width=12).pack(side="left")
        ttk.Label(date_frm, text=" ").pack(side="left")
        ttk.Entry(date_frm, textvariable=self.var_expires_time, width=7).pack(side="left")
        ttk.Label(date_frm, text="  AAAA-MM-DD  HH:MM  (deixe vazio para usar duração)").pack(
            side="left", padx=(6, 0))

        self.temp_frame.grid_remove()

        # Buttons
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=5, column=0, columnspan=2, sticky="w", pady=(24, 0))
        ttk.Button(btn_frm, text="Salvar", command=self._save).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frm, text="Limpar", command=self._clear).pack(side="left")

        self.var_msg = tk.StringVar()
        self.lbl_msg = ttk.Label(frm, textvariable=self.var_msg, foreground="green")
        self.lbl_msg.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))

        frm.columnconfigure(1, weight=1)

    def _on_status_change(self, event=None):
        if self.var_status.get() == "autorizado_temp":
            self.temp_frame.grid()
        else:
            self.temp_frame.grid_remove()

    def _compute_expires_at(self):
        date_str = self.var_expires_date.get().strip()
        time_str = self.var_expires_time.get().strip()
        if date_str:
            combined = "{} {}".format(date_str, time_str if time_str else "00:00")
            dt = _parse_dt(combined)
            if dt is None:
                return None
            return dt.isoformat()
        hours = self.var_hours.get()
        return (datetime.now() + timedelta(hours=hours)).isoformat()

    def _save(self):
        expires_at = None
        if self.var_status.get() == "autorizado_temp":
            expires_at = self._compute_expires_at()
            if expires_at is None:
                self.app.ui.show_error("Erro", "Data/hora inválida.\nFormato: AAAA-MM-DD HH:MM")
                return

        placa_val = self._edit_placa if self._mode == "edit" else self.var_placa.get()
        ok = self.app.save_entry(placa_val, self.var_det.get(), self.var_status.get(), expires_at)
        if ok:
            self.var_msg.set("Placa {} salva com sucesso!".format(placa_val.strip().upper()))
            self.lbl_msg.config(foreground="green")
            if self._mode == "add":
                self._clear_fields()
            else:
                self._reset_mode()

    def _clear_fields(self):
        self.var_placa.set("")
        self.var_det.set("")
        self.var_status.set("autorizado")
        self.var_hours.set(24)
        self.var_expires_date.set("")
        self.var_expires_time.set("")
        self.temp_frame.grid_remove()

    def _reset_mode(self):
        self._mode = "add"
        self._edit_placa = None
        self.var_mode_label.set("Adicionar nova placa")
        self.ent_placa.config(state="normal")

    def _clear(self):
        self._clear_fields()
        self._reset_mode()
        self.var_msg.set("")

    def prefill(self, placa, detalhes, status, expires_at="", edit_mode=False):
        self._clear()
        self.var_placa.set(placa)
        self.var_det.set(detalhes)
        self.var_status.set(status)
        if edit_mode:
            self._mode = "edit"
            self._edit_placa = placa
            self.ent_placa.config(state="readonly")
            self.var_mode_label.set("Editar placa: {}".format(placa))
        if status == "autorizado_temp":
            self.temp_frame.grid()
            if expires_at:
                dt = _parse_dt(expires_at)
                if dt:
                    self.var_expires_date.set(dt.strftime("%Y-%m-%d"))
                    self.var_expires_time.set(dt.strftime("%H:%M"))
