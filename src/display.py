"""Windows display modes for the primary monitor."""

import ctypes
from ctypes import wintypes


class PointL(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class DisplaySettings(ctypes.Structure):
    _fields_ = [("position", PointL), ("orientation", wintypes.DWORD),
                ("fixed_output", wintypes.DWORD)]


class PrinterSettings(ctypes.Structure):
    _fields_ = [("unused", wintypes.SHORT * 8)]


class ModeUnion(ctypes.Union):
    _fields_ = [("display", DisplaySettings), ("printer", PrinterSettings)]


class DevMode(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [
        ("device_name", wintypes.WCHAR * 32),
        ("spec_version", wintypes.WORD),
        ("driver_version", wintypes.WORD),
        ("size", wintypes.WORD),
        ("driver_extra", wintypes.WORD),
        ("fields", wintypes.DWORD),
        ("union", ModeUnion),
        ("color", wintypes.SHORT),
        ("duplex", wintypes.SHORT),
        ("y_resolution", wintypes.SHORT),
        ("tt_option", wintypes.SHORT),
        ("collate", wintypes.SHORT),
        ("form_name", wintypes.WCHAR * 32),
        ("log_pixels", wintypes.WORD),
        ("bits_per_pel", wintypes.DWORD),
        ("width", wintypes.DWORD),
        ("height", wintypes.DWORD),
        ("display_flags", wintypes.DWORD),
        ("frequency", wintypes.DWORD),
        ("icm_method", wintypes.DWORD),
        ("icm_intent", wintypes.DWORD),
        ("media_type", wintypes.DWORD),
        ("dither_type", wintypes.DWORD),
        ("reserved1", wintypes.DWORD),
        ("reserved2", wintypes.DWORD),
        ("panning_width", wintypes.DWORD),
        ("panning_height", wintypes.DWORD),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)
enum_modes = user32.EnumDisplaySettingsW
enum_modes.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DevMode)]
enum_modes.restype = wintypes.BOOL
change_mode = user32.ChangeDisplaySettingsExW
change_mode.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(DevMode), wintypes.HWND,
                        wintypes.DWORD, wintypes.LPVOID]
change_mode.restype = wintypes.LONG


def current_mode() -> DevMode:
    mode = DevMode()
    mode.size = ctypes.sizeof(DevMode)
    if not enum_modes(None, 0xFFFFFFFF, ctypes.byref(mode)):
        raise RuntimeError("Windows no devolvió la resolución actual.")
    return mode


def list_modes() -> list[DevMode]:
    matches = []
    index = 0
    while True:
        mode = DevMode()
        mode.size = ctypes.sizeof(DevMode)
        if not enum_modes(None, index, ctypes.byref(mode)):
            return matches
        matches.append(mode)
        index += 1


def modes_for_resolution(width: int, height: int) -> list[DevMode]:
    return [mode for mode in list_modes()
            if (mode.width, mode.height) == (width, height)]


def available_mode(width: int, height: int, hz: int) -> DevMode | None:
    candidates = [mode for mode in modes_for_resolution(width, height)
                  if mode.bits_per_pel in (24, 32) and abs(mode.frequency - hz) <= 1]
    return min(candidates, key=lambda mode: (abs(mode.frequency - hz),
                                              mode.bits_per_pel != 32)) if candidates else None


def apply_mode(mode: DevMode, stretch: bool = False) -> None:
    if stretch:
        mode.fields |= 0x20000000  # DM_DISPLAYFIXEDOUTPUT
        mode.display.fixed_output = 1  # DMDFO_STRETCH
    result = change_mode(None, ctypes.byref(mode), None, 2, None)  # CDS_TEST
    if result != 0:
        raise RuntimeError(f"Windows rechazó el modo de vídeo (código {result}).")
    result = change_mode(None, ctypes.byref(mode), None, 0, None)
    if result != 0:
        raise RuntimeError(f"Windows no pudo aplicar el modo de vídeo (código {result}).")


def mode_text(mode: DevMode) -> str:
    return f"{mode.width}×{mode.height} · {mode.frequency} Hz"
