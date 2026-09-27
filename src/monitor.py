"""Temporarily disable a selected monitor device, with an elevated watchdog."""

import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid


CREATE_NO_WINDOW = 0x08000000


def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / name
    return Path(__file__).resolve().parent.parent / "assets" / name


def encoded_command(command: str) -> str:
    return base64.b64encode(command.encode("utf-16le")).decode("ascii")


def ps_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_powershell(command: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
         encoded_command(command)],
        capture_output=True, text=True, timeout=timeout,
        creationflags=CREATE_NO_WINDOW, check=False,
    )


def list_monitors() -> list[dict]:
    command = ("Get-PnpDevice -Class Monitor | "
               "Select-Object FriendlyName,InstanceId,Status | ConvertTo-Json -Compress")
    result = run_powershell(command)
    if result.returncode:
        raise RuntimeError("No se pudieron detectar los monitores de Windows.")
    if not result.stdout.strip():
        return []
    data = json.loads(result.stdout)
    return data if isinstance(data, list) else [data]


def launch_elevated(action: str, instance_id: str, status_path: Path,
                    parent_pid: int = 0, signal_path: Path | None = None) -> None:
    helper = resource_path("monitor_helper.ps1")
    if not helper.is_file():
        raise RuntimeError("Falta el componente de restauración del monitor.")
    inner = (f"& {ps_literal(str(helper))} -Action {ps_literal(action)} "
             f"-InstanceId {ps_literal(instance_id)} "
             f"-StatusPath {ps_literal(str(status_path))}")
    if action == "Disable":
        inner += (f" -ParentPid {parent_pid} "
                  f"-SignalPath {ps_literal(str(signal_path))}")
    payload = encoded_command(inner)
    outer = (
        "$p = Start-Process -FilePath 'powershell.exe' -Verb RunAs "
        "-WindowStyle Hidden -PassThru "
        "-ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',"
        f"'-EncodedCommand','{payload}'); "
        "if (-not $p) { exit 1 }"
    )
    result = run_powershell(outer, timeout=90)
    if result.returncode:
        raise RuntimeError("Windows no autorizó el cambio temporal del monitor.")


def wait_status(path: Path, expected: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        if path.is_file():
            last = path.read_text(encoding="utf-8-sig").strip()
            if last == expected or last.startswith("error:"):
                return last
        time.sleep(0.25)
    return last or "sin respuesta"


class MonitorLease:
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        token = uuid.uuid4().hex
        root = Path(tempfile.gettempdir())
        self.signal = root / f"koktei-stretch-{token}.signal"
        self.status = root / f"koktei-stretch-{token}.status"
        self.active = False

    def acquire(self) -> None:
        self.signal.write_text("active", encoding="ascii")
        try:
            launch_elevated("Disable", self.instance_id, self.status,
                            parent_pid=__import__("os").getpid(), signal_path=self.signal)
            response = wait_status(self.status, "disabled", 40)
            if response != "disabled":
                raise RuntimeError(f"El monitor no pudo prepararse: {response}")
            self.active = True
        except BaseException:
            self.signal.unlink(missing_ok=True)
            raise

    def release(self) -> None:
        self.signal.unlink(missing_ok=True)
        if not self.active:
            return
        response = wait_status(self.status, "restored", 25)
        self.active = False
        if response != "restored":
            raise RuntimeError("No se confirmó la restauración del monitor. Usa el botón Restaurar.")
        self.status.unlink(missing_ok=True)


def restore_monitor(instance_id: str) -> None:
    status = Path(tempfile.gettempdir()) / f"koktei-restore-{uuid.uuid4().hex}.status"
    try:
        launch_elevated("Restore", instance_id, status)
        response = wait_status(status, "restored", 40)
        if response != "restored":
            raise RuntimeError(f"No se pudo restaurar el monitor: {response}")
    finally:
        status.unlink(missing_ok=True)
