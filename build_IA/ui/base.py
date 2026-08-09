from tkinter import ttk


class BaseTab(ttk.Frame):
    TAB_NAME = "Tab"

    def __init__(self, notebook, app):
        super().__init__(notebook)
        self.app = app
        self._build()

    def _build(self):
        pass

    def on_tab_selected(self):
        pass
