"""VALORANT Stretch Launcher — desarrollado por koktei."""

import json
from pathlib import Path
import sys


def self_test(path: Path) -> None:
    from display import current_mode, mode_text
    from monitor import list_monitors, resource_path
    from nvapi import NvidiaApi, primary_display_name
    from riot import find_client, find_game_config

    result = {}
    try:
        result["desktop"] = mode_text(current_mode())
        result["display_name"] = primary_display_name()
        result["monitors"] = list_monitors()
        result["monitor_helper_present"] = resource_path("monitor_helper.ps1").is_file()
        result["riot_client"] = str(find_client())
        result["game_config"] = str(find_game_config())
        with NvidiaApi() as nvidia:
            identifier = nvidia.display_id()
            result["custom_modes"] = [
                {
                    "source": [mode.width, mode.height],
                    "output": [mode.timing.hvisible, mode.timing.vvisible],
                    "hz": mode.timing.etc.rrx1k / 1000,
                }
                for mode in nvidia.custom_modes(identifier)
            ]
        result["ok"] = True
    except Exception as error:
        result["ok"] = False
        result["error"] = str(error)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        self_test(Path(sys.argv[2]))
    else:
        from app import main
        main()
