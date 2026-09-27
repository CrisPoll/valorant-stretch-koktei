"""One VALORANT session: prepare, launch, stretch on F8, restore on exit."""

from dataclasses import dataclass
import ctypes
from pathlib import Path
import threading
import time

from display import apply_mode, available_mode, current_mode, mode_text, modes_for_resolution
from monitor import MonitorLease
from nvapi import NvidiaApi
from riot import GameFlowWatcher, game_running, launch_client, prepare_config


user32 = ctypes.WinDLL("user32", use_last_error=True)
get_key_state = user32.GetAsyncKeyState
get_key_state.argtypes = [ctypes.c_int]
get_key_state.restype = ctypes.c_short


def key_down(vk: int) -> bool:
    return bool(get_key_state(vk) & 0x8000)


@dataclass(frozen=True)
class Settings:
    source_width: int
    source_height: int
    output_width: int
    output_height: int
    hz: int
    monitor_id: str
    client: Path
    game_config: Path

    def validate(self) -> None:
        for label, value, minimum, maximum in (
            ("Ancho del juego", self.source_width, 640, 7680),
            ("Alto del juego", self.source_height, 480, 4320),
            ("Ancho de salida", self.output_width, 640, 7680),
            ("Alto de salida", self.output_height, 480, 4320),
            ("Hz", self.hz, 30, 500),
        ):
            if not minimum <= value <= maximum:
                raise ValueError(f"{label} debe estar entre {minimum} y {maximum}.")
        if not self.monitor_id:
            raise ValueError("Selecciona un monitor activo.")
        if not self.client.is_file():
            raise ValueError("Selecciona RiotClientServices.exe.")
        if not self.game_config.is_file():
            raise ValueError("Selecciona GameUserSettings.ini.")


class GameSession:
    def __init__(self, settings: Settings, report):
        self.settings = settings
        self.report = report
        self.stop_event = threading.Event()
        self.toggle_event = threading.Event()
        self.restore_event = threading.Event()
        self.running = False

    def run(self) -> None:
        settings = self.settings
        settings.validate()
        if game_running():
            raise RuntimeError("Cierra VALORANT antes de iniciar esta sesión.")
        original = current_mode()
        lease = MonitorLease(settings.monitor_id)
        stretched = False
        try:
            target = available_mode(settings.source_width, settings.source_height, settings.hz)
            native_output = (settings.output_width, settings.output_height) == (
                original.width, original.height
            )
            if target is not None and native_output:
                self.report("Usando una resolución que Windows ya ofrece para este monitor.")
            else:
                self.report("Comprobando la resolución de NVIDIA...")
                with NvidiaApi() as nvidia:
                    created = nvidia.ensure_mode(
                        settings.source_width, settings.source_height,
                        settings.output_width, settings.output_height, settings.hz,
                        original.width, original.height,
                    )
                if created:
                    self.report("Resolución personalizada creada y comprobada.")
                for _ in range(11):
                    target = available_mode(settings.source_width, settings.source_height, settings.hz)
                    if target is not None or self.stop_event.is_set():
                        break
                    time.sleep(0.5)
            if self.stop_event.is_set():
                self.report("Inicio cancelado.")
                return
            if target is None:
                offered = sorted({mode.frequency for mode in modes_for_resolution(
                    settings.source_width, settings.source_height)})
                if offered:
                    raise RuntimeError(
                        f"Windows ofrece {settings.source_width}×{settings.source_height} "
                        f"a {', '.join(map(str, offered))} Hz, pero elegiste {settings.hz} Hz. "
                        "Usa una frecuencia disponible."
                    )
                raise RuntimeError(
                    f"NVIDIA reconoce {settings.source_width}×{settings.source_height}, "
                    "pero Windows no la ofrece en este monitor. "
                    f"Prueba Pantalla {original.width}×{original.height} "
                    f"a {original.frequency} Hz. Si NVIDIA indica que ya existe "
                    "esa resolución del Juego con otra salida, prueba Juego 1280×960 (4:3)."
                )

            apply_mode(original)
            backup = prepare_config(settings.game_config, original.width, original.height)
            self.report(f"Configuración preparada. Copia de seguridad: {backup}")
            shared_config = (Path(__import__("os").environ["LOCALAPPDATA"]) / "VALORANT" /
                             "Saved" / "Config" / "WindowsClient" / "GameUserSettings.ini")
            if shared_config.is_file() and shared_config != settings.game_config:
                prepare_config(shared_config, original.width, original.height)
            self.report("Acepta el aviso de Windows para preparar el monitor.")
            lease.acquire()
            self.report("Monitor preparado. Abriendo VALORANT...")
            launch_client(settings.client)

            deadline = time.monotonic() + 900
            while time.monotonic() < deadline and not game_running():
                if self.stop_event.is_set():
                    self.report("Inicio cancelado.")
                    return
                time.sleep(1)
            if not game_running():
                raise RuntimeError("VALORANT no se abrió en 15 minutos.")

            self.running = True
            self.report("Entra a una partida. La app estirará al cargar el mapa; F8 también permite aplicarlo.")
            was_f8 = False
            was_f9 = False
            next_process_check = 0.0
            next_flow_check = 0.0
            stretch_at = None
            game_state = None
            flow = GameFlowWatcher()
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now >= next_process_check:
                    if not game_running():
                        self.report("VALORANT cerrado.")
                        break
                    next_process_check = now + 2
                if now >= next_flow_check:
                    for state in flow.poll():
                        game_state = state
                        if state in ("TransitionToMainMenu", "MainMenu", "TransitionToPregame",
                                     "Pregame", "TransitionToInGame"):
                            stretch_at = None
                            if stretched:
                                apply_mode(original)
                                stretched = False
                                self.report("Pantalla normal durante el lobby y la carga. Se estirará al entrar al mapa.")
                        elif state == "InGame":
                            stretch_at = now + 3
                            self.report("Partida cargada. Aplicando estirado en unos segundos...")
                    next_flow_check = now + 0.5
                f8 = key_down(0x77)
                f9 = key_down(0x78)
                manual_stretch = (f8 and not was_f8) or self.toggle_event.is_set()
                if manual_stretch and game_state != "InGame":
                    self.report("Espera a estar dentro de la partida: F8 en el lobby provoca franjas negras.")
                    manual_stretch = False
                toggle = manual_stretch or (stretch_at is not None and now >= stretch_at)
                restore = (f9 and not was_f9) or self.restore_event.is_set()
                self.toggle_event.clear()
                self.restore_event.clear()
                if toggle:
                    stretch_at = None
                    # VALORANT may rebuild its viewport after Alt+Tab or between
                    # matches while Windows still reports the custom mode. Cycle
                    # through the desktop mode so the game receives a new display
                    # change even when F8 was already used in this session.
                    if stretched:
                        apply_mode(original)
                        time.sleep(0.2)
                    apply_mode(target, stretch=True)
                    actual = current_mode()
                    if ((actual.width, actual.height) !=
                            (settings.source_width, settings.source_height)
                            or abs(actual.frequency - settings.hz) > 1):
                        raise RuntimeError("Windows no mantuvo la resolución elegida.")
                    stretched = True
                    self.report(
                        f"Estirado aplicado: {settings.source_width}×{settings.source_height} "
                        f"→ salida {settings.output_width}×{settings.output_height} "
                        f"a {settings.hz} Hz. Puedes repetir F8 si reaparecen bordes negros."
                    )
                if restore:
                    stretch_at = None
                    if stretched:
                        apply_mode(original)
                        stretched = False
                        self.report(f"Restaurado: {mode_text(original)}")
                was_f8, was_f9 = f8, f9
                time.sleep(0.08)
        finally:
            errors = []
            try:
                apply_mode(original)
                self.report(f"Pantalla restaurada: {mode_text(original)}")
            except Exception as error:
                errors.append(str(error))
            try:
                lease.release()
                self.report("Monitor restaurado.")
            except Exception as error:
                errors.append(str(error))
            self.running = False
            if errors:
                raise RuntimeError(" | ".join(errors))
