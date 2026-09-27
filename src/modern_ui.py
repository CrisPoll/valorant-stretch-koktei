"""Visual simulator UI. Session and monitor handling remain in app.StretchApp."""

import ctypes
from ctypes import wintypes
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

from app import SETTINGS_FILE, StretchApp, format_ratio
from display import current_mode, mode_text


BG = "#100F1B"
SIDEBAR = "#1B1829"
CARD = "#1C1A2C"
FIELD = "#151424"
LINE = "#403C5C"
TEXT = "#F4F2FA"
MUTED = "#A6A2BA"
MINT = "#75EFC0"
MINT_DARK = "#18362C"


class ModernStretchApp(StretchApp):
    def build_ui(self):
        self.root.geometry("1260x840")
        self.root.minsize(1050, 750)
        self.root.configure(bg=BG)
        self.root.after(20, self.dark_titlebar)
        self.pages = {}
        self.nav_buttons = {}
        self.source_title = tk.StringVar()
        self.output_title = tk.StringVar()
        self.source_ratio = tk.StringVar()
        self.output_ratio = tk.StringVar()
        self.summary = tk.StringVar()
        self.profile_data = self.load_profiles()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Modern.TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=LINE,
                        lightcolor=LINE, darkcolor=LINE, padding=7)
        style.map("Modern.TCombobox", fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", TEXT)])

        header = tk.Frame(self.root, bg=SIDEBAR, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="◢", bg=SIDEBAR, fg=MINT,
                 font=("Segoe UI", 22, "bold")).pack(side="left", padx=(24, 10))
        tk.Label(header, text="VALORANT", bg=SIDEBAR, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(header, text="Stretch", bg=SIDEBAR, fg=MINT,
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=(5, 0))
        tk.Label(header, text="por koktei", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left", padx=(10, 0))

        workspace = tk.Frame(self.root, bg=BG)
        workspace.pack(fill="both", expand=True)
        sidebar = tk.Frame(workspace, bg=SIDEBAR, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.content = tk.Frame(workspace, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

        for key, title in (("simulator", "▣   Simulador"),
                           ("configuration", "⚙   Configuración"),
                           ("profiles", "▤   Perfiles"),
                           ("hotkeys", "⌨   Teclas rápidas"),
                           ("details", "☷   Detalles"),
                           ("about", "ⓘ   Acerca de")):
            button = tk.Button(sidebar, text=title, anchor="w", borderwidth=0,
                               relief="flat", bg=SIDEBAR, fg=MUTED,
                               activebackground=CARD, activeforeground=MINT,
                               font=("Segoe UI", 11), padx=22, pady=14,
                               command=lambda page=key: self.show_page(page))
            button.pack(fill="x", pady=(7 if key == "simulator" else 0, 0))
            self.nav_buttons[key] = button
        tk.Label(sidebar, text="Desarrollado por koktei", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=18, pady=18)

        self.build_simulator()
        self.build_configuration()
        self.build_profiles()
        self.build_hotkeys()
        self.build_details()
        self.build_about()
        self.show_page("simulator")

        status = tk.Frame(self.root, bg=SIDEBAR, height=34)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)
        tk.Label(status, text="●", bg=SIDEBAR, fg=MINT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(18, 6))
        tk.Label(status, textvariable=self.status_label, bg=SIDEBAR, fg=TEXT,
                 font=("Segoe UI", 9), anchor="w").pack(side="left", fill="x", expand=True)

    def dark_titlebar(self):
        try:
            user32 = ctypes.WinDLL("user32")
            user32.GetParent.argtypes = [wintypes.HWND]
            user32.GetParent.restype = wintypes.HWND
            hwnd = user32.GetParent(self.root.winfo_id())
            enabled = ctypes.c_int(1)
            ctypes.WinDLL("dwmapi").DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
        except Exception:
            pass

    def panel(self, parent, padx=16, pady=13):
        frame = tk.Frame(parent, bg=CARD, padx=padx, pady=pady,
                         highlightthickness=1, highlightbackground=LINE)
        return frame

    def label(self, parent, text=None, variable=None, size=10, color=TEXT, bold=False, **kwargs):
        return tk.Label(parent, text=text, textvariable=variable, bg=parent.cget("bg"),
                        fg=color, font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", **kwargs)

    def button(self, parent, text, command, primary=False, **kwargs):
        return tk.Button(parent, text=text, command=command, borderwidth=0, relief="flat",
                         bg=MINT if primary else "#302D43", fg=MINT_DARK if primary else TEXT,
                         activebackground="#A7F9D8" if primary else "#45415E",
                         activeforeground=MINT_DARK if primary else TEXT,
                         disabledforeground="#79768D", cursor="hand2", padx=15, pady=10,
                         font=("Segoe UI", 11, "bold" if primary else "normal"), **kwargs)

    def build_simulator(self):
        page = tk.Frame(self.content, bg=BG, padx=24, pady=18)
        self.pages["simulator"] = page

        now = self.panel(page, padx=19, pady=13)
        now.pack(fill="x")
        self.label(now, "▣", size=19, color=MINT).pack(side="left", padx=(0, 12))
        self.label(now, f"Ahora: {mode_text(current_mode())}", size=17, bold=True).pack(side="left")
        self.label(now, "Resolución actual de Windows", color=MUTED).pack(side="right")

        previews = tk.Frame(page, bg=BG)
        previews.pack(fill="both", expand=True, pady=(15, 0))
        source_card = self.panel(previews, padx=12, pady=11)
        source_card.pack(side="left", fill="both", expand=True)
        self.label(source_card, variable=self.source_title, size=14, bold=True).pack(anchor="center")
        self.source_canvas = tk.Canvas(source_card, bg=CARD, highlightthickness=0,
                                       height=245)
        self.source_canvas.pack(fill="both", expand=True, pady=(9, 0))
        self.source_canvas.bind("<Configure>", lambda _event: self.draw_previews())

        connector = tk.Frame(previews, bg=BG, width=38)
        connector.pack(side="left", fill="y")
        connector.pack_propagate(False)
        tk.Label(connector, text="↔", bg=BG, fg=MINT,
                 font=("Segoe UI", 23, "bold")).pack(expand=True)

        output_card = self.panel(previews, padx=12, pady=11)
        output_card.pack(side="left", fill="both", expand=True)
        self.label(output_card, variable=self.output_title, size=14, bold=True).pack(anchor="center")
        self.output_canvas = tk.Canvas(output_card, bg=CARD, highlightthickness=0,
                                       height=245)
        self.output_canvas.pack(fill="both", expand=True, pady=(9, 0))
        self.output_canvas.bind("<Configure>", lambda _event: self.draw_previews())

        values = self.panel(page, padx=18, pady=13)
        values.pack(fill="x", pady=(15, 0))
        self.label(values, "Cambia estos valores para usar tu propia resolución",
                   size=12, color=MUTED).pack(anchor="center", pady=(0, 11))
        fields = tk.Frame(values, bg=CARD)
        fields.pack(fill="x")
        self.number_field(fields, "Juego ancho", "source_width")
        self.number_field(fields, "Juego alto", "source_height")
        self.ratio_badge(fields, self.source_ratio)
        tk.Frame(fields, bg=LINE, width=1).pack(side="left", fill="y", padx=11)
        self.number_field(fields, "Pantalla ancho", "output_width")
        self.number_field(fields, "Pantalla alto", "output_height")
        self.ratio_badge(fields, self.output_ratio)
        tk.Frame(fields, bg=LINE, width=1).pack(side="left", fill="y", padx=11)
        self.number_field(fields, "Hz", "hz", width=5)
        self.label(values, variable=self.summary, color=MUTED, size=10).pack(anchor="center", pady=(10, 0))

        controls = tk.Frame(page, bg=BG)
        controls.pack(fill="x", pady=(14, 0))
        self.play_button = self.button(controls, "▶   Abrir VALORANT", self.start, primary=True)
        self.play_button.pack(side="left", fill="x", expand=True)
        self.stretch_button = self.button(controls, "F8  Estirar", self.toggle, state="disabled")
        self.stretch_button.pack(side="left", padx=(9, 0))
        self.back_button = self.button(controls, "F9  Volver", self.unstretch, state="disabled")
        self.back_button.pack(side="left", padx=(9, 0))
        self.button(controls, "⟳  Restaurar", self.restore_all).pack(side="left", padx=(9, 0))

    def number_field(self, parent, title, key, width=6):
        column = tk.Frame(parent, bg=CARD)
        column.pack(side="left", padx=(0, 7))
        self.label(column, title, color=MUTED, size=9).pack(anchor="w", pady=(0, 4))
        entry = tk.Entry(column, textvariable=self.vars[key], width=width, bg=FIELD, fg=TEXT,
                         insertbackground=TEXT, relief="flat", borderwidth=6,
                         highlightthickness=1, highlightbackground=LINE,
                         highlightcolor=MINT, font=("Segoe UI", 15))
        entry.pack(anchor="w")

    def ratio_badge(self, parent, variable):
        column = tk.Frame(parent, bg=CARD)
        column.pack(side="left", padx=(0, 5))
        self.label(column, "Formato", color=MUTED, size=9).pack(anchor="w", pady=(0, 4))
        self.label(column, variable=variable, color=MINT, size=15, bold=True).pack(anchor="w", pady=6)

    def draw_previews(self):
        for canvas, width_key, height_key, color in (
            (self.source_canvas, "source_width", "source_height", "#9B96BD"),
            (self.output_canvas, "output_width", "output_height", MINT),
        ):
            canvas.delete("all")
            try:
                ratio = int(self.vars[width_key].get()) / int(self.vars[height_key].get())
                if ratio <= 0:
                    continue
            except (ValueError, ZeroDivisionError):
                continue
            width = max(canvas.winfo_width(), 150)
            height = max(canvas.winfo_height(), 120)
            max_w, max_h = width - 28, height - 22
            box_h = min(max_h, max_w / ratio)
            box_w = box_h * ratio
            left, top = (width - box_w) / 2, (height - box_h) / 2
            right, bottom = left + box_w, top + box_h
            canvas.create_rectangle(left, top, right, bottom, fill=FIELD,
                                    outline=color, width=2)
            for index in range(1, 9):
                x = left + box_w * index / 9
                canvas.create_line(x, top, x, bottom, fill="#34344A")
            for index in range(1, 6):
                y = top + box_h * index / 6
                canvas.create_line(left, y, right, y, fill="#34344A")
            inner_left, inner_top = left + box_w * .20, top + box_h * .20
            inner_right, inner_bottom = right - box_w * .20, bottom - box_h * .20
            canvas.create_rectangle(inner_left, inner_top, inner_right, inner_bottom,
                                    outline="#55546E", width=1)
            for x1, y1, x2, y2 in ((left, top, inner_left, inner_top),
                                    (right, top, inner_right, inner_top),
                                    (left, bottom, inner_left, inner_bottom),
                                    (right, bottom, inner_right, inner_bottom)):
                canvas.create_line(x1, y1, x2, y2, fill="#55546E")

    def update_ratio(self):
        try:
            sw, sh = int(self.vars["source_width"].get()), int(self.vars["source_height"].get())
            ow, oh = int(self.vars["output_width"].get()), int(self.vars["output_height"].get())
            if min(sw, sh, ow, oh) <= 0:
                raise ValueError
            game, output = format_ratio(sw, sh), format_ratio(ow, oh)
            self.source_title.set(f"Juego {sw} × {sh}  ({game})")
            self.output_title.set(f"Pantalla {ow} × {oh}  ({output})")
            self.source_ratio.set(game)
            self.output_ratio.set(output)
            self.summary.set(f"El juego crea una imagen {game}; se adapta para llenar {ow}×{oh} ({output}).")
            self.draw_previews()
        except (ValueError, ZeroDivisionError):
            self.source_title.set("Juego · escribe ancho y alto")
            self.output_title.set("Pantalla · escribe ancho y alto")
            self.source_ratio.set("—")
            self.output_ratio.set("—")
            self.summary.set("Introduce resoluciones válidas para ver la comparación.")

    def build_configuration(self):
        page = tk.Frame(self.content, bg=BG, padx=30, pady=25)
        self.pages["configuration"] = page
        self.label(page, "Configuración", size=22, bold=True).pack(anchor="w")
        self.label(page, "La aplicación detecta estos datos. Cámbialos solo si hace falta.",
                   color=MUTED).pack(anchor="w", pady=(5, 20))
        card = self.panel(page, padx=18, pady=17)
        card.pack(fill="x")
        self.label(card, "Monitor activo", size=12, bold=True).pack(anchor="w")
        monitor_row = tk.Frame(card, bg=CARD)
        monitor_row.pack(fill="x", pady=(7, 15))
        self.monitor_box = ttk.Combobox(monitor_row, textvariable=self.monitor_label,
                                        state="readonly", style="Modern.TCombobox")
        self.monitor_box.pack(side="left", fill="x", expand=True)
        self.monitor_box.bind("<<ComboboxSelected>>", self.on_monitor_selected)
        self.button(monitor_row, "Actualizar", self.refresh_monitors).pack(side="left", padx=(8, 0))
        self.path_control(card, "Riot Client", "client", self.browse_client)
        self.path_control(card, "Archivo de configuración de VALORANT", "game_config", self.browse_config)
        self.label(card, variable=self.monitor_summary, color=MUTED).pack(anchor="w", pady=(14, 0))

    def path_control(self, parent, title, name, browse):
        self.label(parent, title, size=11, bold=True).pack(anchor="w", pady=(0, 5))
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 15))
        tk.Entry(row, textvariable=self.vars[name], bg=FIELD, fg=TEXT,
                 insertbackground=TEXT, relief="flat", borderwidth=8,
                 highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=MINT, font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
        self.button(row, "Elegir", browse).pack(side="left", padx=(8, 0))

    def load_profiles(self):
        try:
            data = json.loads((SETTINGS_FILE.parent / "profiles.json").read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def build_profiles(self):
        page = tk.Frame(self.content, bg=BG, padx=30, pady=25)
        self.pages["profiles"] = page
        self.label(page, "Perfiles", size=22, bold=True).pack(anchor="w")
        self.label(page, "Guarda una combinación de resoluciones y Hz para usarla después.",
                   color=MUTED).pack(anchor="w", pady=(5, 20))
        card = self.panel(page)
        card.pack(fill="x")
        self.label(card, "Modo probado · 1200×900 → 1600×900 · 240 Hz",
                   size=12, bold=True).pack(side="left")
        self.button(card, "Aplicar", self.apply_verified_profile).pack(side="right")
        self.profile_list = tk.Listbox(page, bg=FIELD, fg=TEXT, selectbackground="#3D755F",
                                       selectforeground=TEXT, relief="flat", borderwidth=10,
                                       font=("Segoe UI", 11), height=10)
        self.profile_list.pack(fill="x", pady=(15, 8))
        self.refresh_profiles()
        row = tk.Frame(page, bg=BG)
        row.pack(fill="x")
        self.button(row, "Guardar valores actuales", self.save_profile, primary=True).pack(side="left")
        self.button(row, "Cargar seleccionado", self.apply_profile).pack(side="left", padx=(8, 0))
        self.button(row, "Eliminar seleccionado", self.delete_profile).pack(side="left", padx=(8, 0))

    def refresh_profiles(self):
        self.profile_list.delete(0, "end")
        for name in sorted(self.profile_data):
            self.profile_list.insert("end", name)

    def apply_verified_profile(self):
        self.use_verified_mode()
        self.show_page("simulator")

    def save_profile(self):
        name = simpledialog.askstring("Guardar perfil", "Nombre del perfil:", parent=self.root)
        if not name:
            return
        try:
            settings = self.get_settings()
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Perfil", str(error))
            return
        self.profile_data[name] = {
            "source_width": settings.source_width, "source_height": settings.source_height,
            "output_width": settings.output_width, "output_height": settings.output_height,
            "hz": settings.hz,
        }
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        (SETTINGS_FILE.parent / "profiles.json").write_text(
            json.dumps(self.profile_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.refresh_profiles()

    def selected_profile(self):
        selection = self.profile_list.curselection()
        if not selection:
            messagebox.showinfo("Perfiles", "Selecciona un perfil de la lista.")
            return None
        return self.profile_list.get(selection[0])

    def apply_profile(self):
        name = self.selected_profile()
        if name is None:
            return
        for key, value in self.profile_data[name].items():
            self.vars[key].set(str(value))
        self.show_page("simulator")

    def delete_profile(self):
        name = self.selected_profile()
        if name is None:
            return
        del self.profile_data[name]
        (SETTINGS_FILE.parent / "profiles.json").write_text(
            json.dumps(self.profile_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.refresh_profiles()

    def build_hotkeys(self):
        page = tk.Frame(self.content, bg=BG, padx=30, pady=25)
        self.pages["hotkeys"] = page
        self.label(page, "Teclas rápidas", size=22, bold=True).pack(anchor="w")
        self.label(page, "La app usa resolución normal en el lobby y durante la carga; estira al entrar al mapa.",
                   color=MUTED).pack(anchor="w", pady=(5, 20))
        for key, title, detail in (("F8", "Estirar", "Reaplica el estirado manualmente si reaparecen bordes negros dentro de la partida."),
                                   ("F9", "Volver", "Regresa a la resolución anterior.")):
            card = self.panel(page)
            card.pack(fill="x", pady=(0, 12))
            self.label(card, key, size=20, bold=True, color=MINT).pack(side="left", padx=(0, 25))
            block = tk.Frame(card, bg=CARD)
            block.pack(side="left")
            self.label(block, title, size=13, bold=True).pack(anchor="w")
            self.label(block, detail, color=MUTED).pack(anchor="w")
        self.label(page, "Al cerrar VALORANT, la aplicación restaura el monitor.",
                   color=MUTED).pack(anchor="w", pady=(7, 0))

    def build_details(self):
        page = tk.Frame(self.content, bg=BG, padx=30, pady=25)
        self.pages["details"] = page
        self.label(page, "Detalles", size=22, bold=True).pack(anchor="w")
        self.label(page, "Actividad de la sesión y mensajes de error.", color=MUTED).pack(anchor="w", pady=(5, 15))
        self.log = scrolledtext.ScrolledText(page, state="disabled", wrap="word", bg=FIELD,
                                              fg=TEXT, insertbackground=TEXT, relief="flat",
                                              borderwidth=12, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True)

    def build_about(self):
        page = tk.Frame(self.content, bg=BG, padx=30, pady=25)
        self.pages["about"] = page
        self.label(page, "VALORANT Stretch", size=23, bold=True).pack(anchor="w")
        self.label(page, "Desarrollado por koktei", size=13, color=MINT).pack(anchor="w", pady=(4, 20))
        card = self.panel(page)
        card.pack(fill="x")
        self.label(card, "Configura una resolución del juego y una salida final del monitor.",
                   size=12).pack(anchor="w")
        self.label(card, "Ejemplo: 1200×900 (4:3) estirado hasta 1600×900 (16:9).",
                   color=MUTED).pack(anchor="w", pady=(8, 0))
        self.label(card, "Puedes escribir otras resoluciones compatibles en el Simulador.",
                   color=MUTED).pack(anchor="w", pady=(6, 0))

    def show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for key, button in self.nav_buttons.items():
            active = key == name
            button.configure(bg=CARD if active else SIDEBAR,
                             fg=MINT if active else MUTED)

    def toggle_advanced(self):
        self.show_page("configuration")

    def toggle_details(self):
        self.show_page("details")


def main():
    root = tk.Tk()
    ModernStretchApp(root)
    root.mainloop()
