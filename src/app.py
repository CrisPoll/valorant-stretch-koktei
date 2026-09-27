"""Simple Windows UI for custom VALORANT stretched resolutions."""

import json
import math
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from display import apply_mode, current_mode, mode_text
from monitor import list_monitors, restore_monitor
from riot import find_client, find_game_config
from session import GameSession, Settings


SETTINGS_FILE = Path(os.environ["LOCALAPPDATA"]) / "KokteiValorantStretch" / "settings.json"
BG = "#0B1020"
CARD = "#172034"
FIELD = "#10192B"
LINE = "#2B3850"
TEXT = "#F5F7FC"
MUTED = "#AEBBD0"
ACCENT = "#5BE1E8"


def format_ratio(width: int, height: int) -> str:
    """Show familiar screen formats without unwieldy fractions."""
    value = width / height
    for label, ratio in (("4:3", 4 / 3), ("16:9", 16 / 9),
                         ("16:10", 16 / 10), ("5:4", 5 / 4),
                         ("21:9", 21 / 9)):
        if abs(value - ratio) < 0.015:
            return label
    divisor = math.gcd(width, height)
    short_width, short_height = width // divisor, height // divisor
    if max(short_width, short_height) <= 30:
        return f"{short_width}:{short_height}"
    return f"personalizado ({value:.2f}:1)"


class StretchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VALORANT Stretch · koktei")
        self.root.geometry("850x720")
        self.root.minsize(760, 700)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.initial_mode = current_mode()
        self.events = queue.Queue()
        self.history = []
        self.session = None
        self.worker = None
        self.monitors = []
        self.advanced_open = False
        self.details_open = False

        saved = self.load_settings()
        self.vars = {
            "source_width": tk.StringVar(value=str(saved.get("source_width", 1200))),
            "source_height": tk.StringVar(value=str(saved.get("source_height", 900))),
            "output_width": tk.StringVar(value=str(saved.get("output_width", 1600))),
            "output_height": tk.StringVar(value=str(saved.get("output_height", 900))),
            "hz": tk.StringVar(value=str(saved.get("hz", self.initial_mode.frequency))),
            "client": tk.StringVar(value=saved.get("client", self.detect(find_client))),
            "game_config": tk.StringVar(value=saved.get("game_config", self.detect(find_game_config))),
            "monitor_id": tk.StringVar(value=saved.get("monitor_id", "")),
        }
        self.monitor_label = tk.StringVar()
        self.monitor_summary = tk.StringVar(value="Buscando monitor...")
        self.ratio_label = tk.StringVar()
        self.game_format = tk.StringVar(value="4:3")
        self.output_format = tk.StringVar(value="16:9")
        self.effect_label = tk.StringVar()
        self.status_label = tk.StringVar(value="Listo para jugar")
        self.build_ui()
        self.refresh_monitors()
        for name in ("source_width", "source_height", "output_width", "output_height"):
            self.vars[name].trace_add("write", lambda *_: self.update_ratio())
        self.update_ratio()
        self.history.append(f"Pantalla actual: {mode_text(self.initial_mode)}")
        self.root.after(100, self.process_events)

    @staticmethod
    def detect(function) -> str:
        try:
            return str(function())
        except Exception:
            return ""

    @staticmethod
    def load_settings() -> dict:
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def save_settings(self) -> None:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {key: var.get() for key, var in self.vars.items()}
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 24, "bold"))
        style.configure("Section.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 13, "bold"))
        style.configure("Accent.TLabel", background=CARD, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, padding=6,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEXT, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)])
        style.configure("TButton", background=LINE, foreground=TEXT,
                        font=("Segoe UI", 10), padding=(12, 8), borderwidth=0)
        style.map("TButton", background=[("active", "#40516D")])
        style.configure("Primary.TButton", background=ACCENT, foreground=BG,
                        font=("Segoe UI", 11, "bold"), padding=(17, 10), borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#9AF2F4")])

        frame = ttk.Frame(self.root, padding=(22, 17))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="VALORANT Stretch", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Resoluciones estiradas personalizadas · Desarrollado por koktei",
                  foreground=MUTED).pack(anchor="w", pady=(0, 16))

        resolution = ttk.Frame(frame, style="Card.TFrame", padding=16)
        resolution.pack(fill="x")
        heading = ttk.Frame(resolution, style="Card.TFrame")
        heading.pack(fill="x", pady=(0, 9))
        ttk.Label(heading, text="Tu resolución", style="Section.TLabel").pack(side="left")
        ttk.Button(heading, text="Usar modo probado", command=self.use_verified_mode).pack(side="right")
        settings_content = ttk.Frame(resolution, style="Card.TFrame")
        settings_content.pack(fill="x")
        form = ttk.Frame(settings_content, style="Card.TFrame")
        form.pack(side="left", anchor="n", padx=(0, 20))
        row = ttk.Frame(form, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Juego", style="Card.TLabel", width=10).pack(side="left")
        self.entry(row, "source_width")
        ttk.Label(row, text="×", style="Card.TLabel").pack(side="left", padx=6)
        self.entry(row, "source_height")
        self.format_box = ttk.Combobox(row, textvariable=self.game_format,
                                       values=("4:3", "16:9", "Personalizado"),
                                       state="readonly", width=13)
        self.format_box.pack(side="left", padx=(9, 0))
        self.format_box.bind("<<ComboboxSelected>>", self.choose_game_format)

        row = ttk.Frame(form, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Pantalla", style="Card.TLabel", width=10).pack(side="left")
        self.entry(row, "output_width")
        ttk.Label(row, text="×", style="Card.TLabel").pack(side="left", padx=6)
        self.entry(row, "output_height")
        ttk.Label(row, textvariable=self.output_format, style="Accent.TLabel").pack(side="left", padx=(12, 0))

        row = ttk.Frame(form, style="Card.TFrame")
        row.pack(fill="x", pady=(5, 0))
        ttk.Label(row, text="Frecuencia", style="Card.TLabel", width=10).pack(side="left")
        self.entry(row, "hz")
        ttk.Label(row, text="Hz", style="Muted.TLabel").pack(side="left", padx=(8, 0))

        explanation = ttk.Frame(settings_content, style="Card.TFrame")
        explanation.pack(side="left", fill="both", expand=True, anchor="n")
        ttk.Label(explanation, text="¿Qué significa cada valor?", style="Section.TLabel").pack(anchor="w")
        ttk.Label(explanation, text="Juego: el formato de la imagen. Elige 4:3 si buscas el efecto estirado.",
                  style="Muted.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=(7, 0))
        ttk.Label(explanation, text="Pantalla: tamaño final que recibe tu monitor. Si es más ancho, la imagen se estira.",
                  style="Muted.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=(5, 0))
        ttk.Label(explanation, text="Hz: frecuencia de tu monitor. Usa la que tienes configurada en Windows.",
                  style="Muted.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=(5, 0))

        ttk.Label(resolution, textvariable=self.ratio_label, style="Accent.TLabel").pack(anchor="w", pady=(12, 0))
        ttk.Label(resolution, textvariable=self.effect_label, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

        flow = ttk.Frame(frame, style="Card.TFrame", padding=16)
        flow.pack(fill="x", pady=(12, 0))
        ttk.Label(flow, text="Cómo jugar", style="Section.TLabel").pack(anchor="w")
        ttk.Label(flow, text="1  Abre VALORANT    →    2  Entra a una partida    →    3  Pulsa F8 para estirar",
                  style="Muted.TLabel").pack(anchor="w", pady=(7, 13))
        controls = ttk.Frame(flow, style="Card.TFrame")
        controls.pack(fill="x")
        self.play_button = ttk.Button(controls, text="▶  Abrir VALORANT", style="Primary.TButton", command=self.start)
        self.play_button.pack(side="left")
        self.stretch_button = ttk.Button(controls, text="Estirar · F8", command=self.toggle, state="disabled")
        self.stretch_button.pack(side="left", padx=(9, 0))
        self.back_button = ttk.Button(controls, text="Volver · F9", command=self.unstretch, state="disabled")
        self.back_button.pack(side="left", padx=(9, 0))
        ttk.Button(controls, text="Restaurar", command=self.restore_all).pack(side="right")

        status = ttk.Frame(frame, style="Card.TFrame", padding=(14, 10))
        status.pack(fill="x", pady=(12, 0))
        ttk.Label(status, text="●", style="Accent.TLabel").pack(side="left", padx=(0, 9))
        ttk.Label(status, textvariable=self.status_label, style="Card.TLabel").pack(side="left")

        footer = ttk.Frame(frame)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.monitor_summary,
                  foreground=MUTED).pack(side="left")
        ttk.Button(footer, text="Detalles", command=self.toggle_details).pack(side="right")
        ttk.Button(footer, text="Configuración avanzada", command=self.toggle_advanced).pack(side="right", padx=(0, 8))

        self.advanced = ttk.Frame(frame, style="Card.TFrame", padding=12)
        row4 = ttk.Frame(self.advanced, style="Card.TFrame")
        row4.pack(fill="x", pady=3)
        ttk.Label(row4, text="Monitor", style="Card.TLabel", width=18).pack(side="left")
        self.monitor_box = ttk.Combobox(row4, textvariable=self.monitor_label, state="readonly")
        self.monitor_box.pack(side="left", fill="x", expand=True)
        self.monitor_box.bind("<<ComboboxSelected>>", self.on_monitor_selected)
        ttk.Button(row4, text="Actualizar", command=self.refresh_monitors).pack(side="left", padx=(6, 0))
        self.path_row(self.advanced, "Riot Client", "client", self.browse_client)
        self.path_row(self.advanced, "Archivo VALORANT", "game_config", self.browse_config)

        self.log = scrolledtext.ScrolledText(frame, height=7, state="disabled", wrap="word",
                                              bg=FIELD, fg=TEXT, relief="flat",
                                              font=("Consolas", 9))

    def entry(self, parent, name):
        ttk.Entry(parent, textvariable=self.vars[name], width=9).pack(side="left")

    def path_row(self, parent, label, name, browse):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, style="Card.TLabel", width=18).pack(side="left")
        ttk.Entry(row, textvariable=self.vars[name]).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Elegir", command=browse).pack(side="left", padx=(6, 0))

    def use_verified_mode(self):
        for name, value in (("source_width", 1200), ("source_height", 900),
                            ("output_width", 1600), ("output_height", 900),
                            ("hz", 240)):
            self.vars[name].set(str(value))
        self.post("Modo probado: 1200×900 → 1600×900 a 240 Hz.")

    def choose_game_format(self, *_):
        selected = self.game_format.get()
        if selected == "Personalizado":
            return
        try:
            height = int(self.vars["source_height"].get())
            if height <= 0:
                raise ValueError
            numerator, denominator = (4, 3) if selected == "4:3" else (16, 9)
            self.vars["source_width"].set(str(round(height * numerator / denominator)))
        except ValueError:
            self.ratio_label.set("Escribe primero una altura válida para el juego.")

    def toggle_advanced(self):
        if self.advanced_open:
            self.advanced.pack_forget()
            self.advanced_open = False
        else:
            if self.details_open:
                self.log.pack_forget()
                self.details_open = False
            self.advanced.pack(fill="x", pady=(8, 0))
            self.advanced_open = True
        self.resize_for_panel()

    def toggle_details(self):
        if self.details_open:
            self.log.pack_forget()
            self.details_open = False
        else:
            if self.advanced_open:
                self.advanced.pack_forget()
                self.advanced_open = False
            self.log.pack(fill="both", expand=True, pady=(8, 0))
            self.details_open = True
        self.resize_for_panel()

    def resize_for_panel(self):
        width = max(self.root.winfo_width(), 760)
        height = 860 if self.advanced_open or self.details_open else 720
        self.root.geometry(f"{width}x{height}")

    def browse_client(self):
        chosen = filedialog.askopenfilename(title="Selecciona RiotClientServices.exe",
                                            filetypes=[("Ejecutable", "*.exe")])
        if chosen:
            self.vars["client"].set(chosen)

    def browse_config(self):
        chosen = filedialog.askopenfilename(title="Selecciona GameUserSettings.ini",
                                            filetypes=[("Configuración", "*.ini")])
        if chosen:
            self.vars["game_config"].set(chosen)

    def refresh_monitors(self):
        try:
            self.monitors = list_monitors()
            labels = [f"{m['FriendlyName']} · {m['Status']} · {m['InstanceId']}" for m in self.monitors]
            self.monitor_box["values"] = labels
            wanted = self.vars["monitor_id"].get()
            index = next((i for i, m in enumerate(self.monitors)
                          if m["InstanceId"] == wanted), None)
            if index is None:
                index = next((i for i, m in enumerate(self.monitors)
                              if m["Status"] == "OK"), None)
            if index is not None:
                self.monitor_box.current(index)
                self.on_monitor_selected()
            else:
                self.monitor_summary.set("No se encontró un monitor activo")
        except Exception as error:
            self.post(f"No se pudieron detectar monitores: {error}")

    def on_monitor_selected(self, *_):
        index = self.monitor_box.current()
        if index >= 0:
            monitor = self.monitors[index]
            self.vars["monitor_id"].set(monitor["InstanceId"])
            self.monitor_summary.set(
                f"Monitor: {monitor['FriendlyName']} · {mode_text(current_mode())}"
            )

    def update_ratio(self):
        try:
            sw = int(self.vars["source_width"].get())
            sh = int(self.vars["source_height"].get())
            ow = int(self.vars["output_width"].get())
            oh = int(self.vars["output_height"].get())
            if min(sw, sh, ow, oh) <= 0:
                raise ValueError
            multiplier = (ow / sw) / (oh / sh)
            game = format_ratio(sw, sh)
            output = format_ratio(ow, oh)
            self.game_format.set(game if game in ("4:3", "16:9") else "Personalizado")
            self.output_format.set(output)
            self.ratio_label.set(f"Juego {game}  →  Pantalla {output}")
            percent = round(abs(multiplier - 1) * 100)
            if percent < 2:
                self.effect_label.set("Ambas imágenes tienen casi el mismo formato: apenas habrá estirado.")
            elif multiplier > 1:
                self.effect_label.set(f"Efecto estimado: la imagen se ensancha un {percent} % al pulsar F8.")
            else:
                self.effect_label.set(f"Efecto estimado: la imagen se estrecha un {percent} % al pulsar F8.")
        except (ValueError, ZeroDivisionError):
            self.ratio_label.set("Introduce números válidos para ver el formato.")
            self.effect_label.set("")

    def get_settings(self) -> Settings:
        settings = Settings(
            int(self.vars["source_width"].get()),
            int(self.vars["source_height"].get()),
            int(self.vars["output_width"].get()),
            int(self.vars["output_height"].get()),
            int(self.vars["hz"].get()),
            self.vars["monitor_id"].get(),
            Path(self.vars["client"].get()),
            Path(self.vars["game_config"].get()),
        )
        settings.validate()
        return settings

    def start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("VALORANT Stretch", "Ya hay una sesión en curso.")
            return
        try:
            settings = self.get_settings()
            self.save_settings()
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Revisa los datos", str(error))
            return
        self.session = GameSession(settings, self.post)
        self.play_button.configure(state="disabled")
        self.status_label.set("Preparando...")
        self.worker = threading.Thread(target=self.run_session, daemon=True)
        self.worker.start()

    def run_session(self):
        try:
            self.session.run()
            self.events.put(("done", "Sesión terminada."))
        except Exception as error:
            self.events.put(("error", str(error)))

    def toggle(self):
        if self.session and self.session.running:
            self.session.toggle_event.set()
        else:
            self.post("Inicia VALORANT y entra a una partida antes de estirar.")

    def unstretch(self):
        if self.session and self.session.running:
            self.session.restore_event.set()
        else:
            self.post("No hay una sesión activa.")

    def restore_all(self):
        if self.worker and self.worker.is_alive():
            self.session.stop_event.set()
            self.post("Restaurando pantalla y monitor...")
            return

        def restore_worker():
            try:
                apply_mode(self.initial_mode)
                monitor_id = self.vars["monitor_id"].get()
                if monitor_id:
                    restore_monitor(monitor_id)
                self.events.put(("done", "Pantalla y monitor restaurados."))
            except Exception as error:
                self.events.put(("error", str(error)))

        threading.Thread(target=restore_worker, daemon=True).start()

    def post(self, message: str):
        self.events.put(("log", message))

    def process_events(self):
        try:
            while True:
                kind, message = self.events.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", message + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                    self.status_label.set(message)
                elif kind == "error":
                    self.play_button.configure(state="normal")
                    self.status_label.set("Error")
                    messagebox.showerror("VALORANT Stretch", message)
                elif kind == "done":
                    self.play_button.configure(state="normal")
                    self.status_label.set(message)
                active = bool(self.session and self.session.running)
                self.stretch_button.configure(state="normal" if active else "disabled")
                self.back_button.configure(state="normal" if active else "disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)

    def on_close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Cerrar", "Se restaurará la pantalla y el monitor. ¿Cerrar?"):
                return
            self.session.stop_event.set()
            self.root.after(300, self.finish_close)
        else:
            self.root.destroy()

    def finish_close(self):
        if self.worker and self.worker.is_alive():
            self.root.after(300, self.finish_close)
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    StretchApp(root)
    root.mainloop()
