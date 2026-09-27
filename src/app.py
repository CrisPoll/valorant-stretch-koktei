"""Simple Windows UI for custom VALORANT stretched resolutions."""

import json
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


class StretchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("VALORANT Stretch · koktei")
        self.root.geometry("690x670")
        self.root.minsize(640, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.initial_mode = current_mode()
        self.events = queue.Queue()
        self.session = None
        self.worker = None
        self.monitors = []

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
        self.ratio_label = tk.StringVar()
        self.status_label = tk.StringVar(value="Listo")
        self.build_ui()
        self.refresh_monitors()
        for name in ("source_width", "source_height", "output_width", "output_height"):
            self.vars[name].trace_add("write", lambda *_: self.update_ratio())
        self.update_ratio()
        self.post(f"Pantalla actual: {mode_text(self.initial_mode)}")
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
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="VALORANT Stretch", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Resolución personalizada para NVIDIA · Desarrollado por koktei",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))

        resolution = ttk.LabelFrame(frame, text="Resolución", padding=12)
        resolution.pack(fill="x")
        row1 = ttk.Frame(resolution)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Imagen del juego", width=19).pack(side="left")
        self.entry(row1, "source_width")
        ttk.Label(row1, text="×").pack(side="left", padx=5)
        self.entry(row1, "source_height")
        ttk.Label(row1, text="píxeles").pack(side="left", padx=8)
        row2 = ttk.Frame(resolution)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Salida de vídeo", width=19).pack(side="left")
        self.entry(row2, "output_width")
        ttk.Label(row2, text="×").pack(side="left", padx=5)
        self.entry(row2, "output_height")
        ttk.Label(row2, text="píxeles").pack(side="left", padx=8)
        row3 = ttk.Frame(resolution)
        row3.pack(fill="x", pady=3)
        ttk.Label(row3, text="Frecuencia", width=19).pack(side="left")
        self.entry(row3, "hz")
        ttk.Label(row3, text="Hz").pack(side="left", padx=8)
        ttk.Label(resolution, textvariable=self.ratio_label).pack(anchor="w", pady=(8, 0))

        options = ttk.LabelFrame(frame, text="Juego y monitor", padding=12)
        options.pack(fill="x", pady=(12, 0))
        row4 = ttk.Frame(options)
        row4.pack(fill="x", pady=3)
        ttk.Label(row4, text="Monitor", width=15).pack(side="left")
        self.monitor_box = ttk.Combobox(row4, textvariable=self.monitor_label, state="readonly")
        self.monitor_box.pack(side="left", fill="x", expand=True)
        self.monitor_box.bind("<<ComboboxSelected>>", self.on_monitor_selected)
        ttk.Button(row4, text="Actualizar", command=self.refresh_monitors).pack(side="left", padx=(6, 0))
        self.path_row(options, "Riot Client", "client", self.browse_client)
        self.path_row(options, "Archivo VALORANT", "game_config", self.browse_config)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=14)
        self.play_button = ttk.Button(controls, text="Jugar", command=self.start)
        self.play_button.pack(side="left")
        ttk.Button(controls, text="Estirar / F8", command=self.toggle).pack(side="left", padx=7)
        ttk.Button(controls, text="Volver / F9", command=self.unstretch).pack(side="left")
        ttk.Button(controls, text="Restaurar todo", command=self.restore_all).pack(side="right")
        ttk.Label(frame, textvariable=self.status_label).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(frame, height=10, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Label(frame, text="F8: estirar dentro de la partida · F9: volver · Al cerrar el juego se restaura la pantalla.",
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 0))

    def entry(self, parent, name):
        ttk.Entry(parent, textvariable=self.vars[name], width=9).pack(side="left")

    def path_row(self, parent, label, name, browse):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=15).pack(side="left")
        ttk.Entry(row, textvariable=self.vars[name]).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Elegir", command=browse).pack(side="left", padx=(6, 0))

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
        except Exception as error:
            self.post(f"No se pudieron detectar monitores: {error}")

    def on_monitor_selected(self, *_):
        index = self.monitor_box.current()
        if index >= 0:
            self.vars["monitor_id"].set(self.monitors[index]["InstanceId"])

    def update_ratio(self):
        try:
            sw = int(self.vars["source_width"].get())
            sh = int(self.vars["source_height"].get())
            ow = int(self.vars["output_width"].get())
            oh = int(self.vars["output_height"].get())
            multiplier = (ow / sw) / (oh / sh)
            self.ratio_label.set(
                f"Proporción: {sw / sh:.3f} → {ow / oh:.3f}  ·  "
                f"ancho relativo: {multiplier:.2f}×"
            )
        except (ValueError, ZeroDivisionError):
            self.ratio_label.set("Introduce números válidos para ver el estirado.")

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
