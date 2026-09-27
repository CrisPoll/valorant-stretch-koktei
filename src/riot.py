"""Find Riot/VALORANT, prepare the windowed Fill setting, and track the game."""

import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


GAME_EXE = "VALORANT-Win64-Shipping.exe"


def game_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {GAME_EXE}", "/FO", "CSV", "/NH"],
        capture_output=True, check=False, creationflags=0x08000000,
    )
    rows = csv.reader(result.stdout.decode("utf-8", errors="replace").splitlines())
    return any(row and row[0].casefold() == GAME_EXE.casefold() for row in rows)


def find_client() -> Path:
    installs = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Riot Games" / "RiotClientInstalls.json"
    if installs.is_file():
        try:
            data = json.loads(installs.read_text(encoding="utf-8"))
            candidates = [data.get("rc_default"), data.get("rc_live")]
            candidates.extend(data.get("associated_client", {}).values())
            for candidate in candidates:
                if candidate and Path(candidate).is_file():
                    return Path(candidate)
        except (OSError, ValueError, TypeError):
            pass
    for drive in "CDEFGH":
        candidate = Path(f"{drive}:/Riot Games/Riot Client/RiotClientServices.exe")
        if candidate.is_file():
            return candidate
    raise RuntimeError("No se encontró RiotClientServices.exe. Selecciónalo manualmente.")


def find_game_config() -> Path:
    root = Path(os.environ["LOCALAPPDATA"]) / "VALORANT" / "Saved" / "Config"
    candidates = [path for path in root.glob("*/WindowsClient/GameUserSettings.ini")
                  if path.parent.parent.name != "WindowsClient"]
    if not candidates:
        raise RuntimeError("No se encontró GameUserSettings.ini. Selecciónalo manualmente.")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def prepare_config(path: Path, native_width: int, native_height: int) -> Path:
    if not path.is_file():
        raise RuntimeError(f"No existe el archivo de VALORANT: {path}")
    data = path.read_bytes()
    content = data.decode("utf-8-sig")
    values = {
        "bShouldLetterbox": "False",
        "bLastConfirmedShouldLetterbox": "False",
        "ResolutionSizeX": str(native_width),
        "ResolutionSizeY": str(native_height),
        "LastUserConfirmedResolutionSizeX": str(native_width),
        "LastUserConfirmedResolutionSizeY": str(native_height),
        "DesiredScreenWidth": str(native_width),
        "DesiredScreenHeight": str(native_height),
        "LastUserConfirmedDesiredScreenWidth": str(native_width),
        "LastUserConfirmedDesiredScreenHeight": str(native_height),
        "FullscreenMode": "1",  # Windowed Fullscreen
        "LastConfirmedFullscreenMode": "1",
        "PreferredFullscreenMode": "1",
        "bUseVSync": "False",
    }
    for key, value in values.items():
        content, count = re.subn(rf"(?m)^{re.escape(key)}=.*$", f"{key}={value}",
                                 content, count=1)
        if count != 1:
            raise RuntimeError(f"Falta {key} en {path.name}; el juego debe recrear ese archivo.")
    backup_dir = (Path(os.environ["LOCALAPPDATA"]) / "KokteiValorantStretch" / "backups" /
                  datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{path.parent.parent.name}-GameUserSettings.ini"
    shutil.copy2(path, backup)
    temporary = path.with_name(path.name + ".koktei-tmp")
    try:
        temporary.write_bytes(content.encode("utf-8"))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return backup


def launch_client(client: Path) -> None:
    subprocess.Popen(
        [str(client), "--launch-product=valorant", "--launch-patchline=live"],
        cwd=str(client.parent), creationflags=0x08000000,
    )
