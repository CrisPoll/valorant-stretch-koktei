"""Register user-selected NVIDIA source/output display modes via NVAPI."""

import ctypes
from ctypes import wintypes


class DisplayDevice(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("device_name", wintypes.WCHAR * 32),
                ("device_string", wintypes.WCHAR * 128), ("state_flags", wintypes.DWORD),
                ("device_id", wintypes.WCHAR * 128), ("device_key", wintypes.WCHAR * 128)]


enum_devices = ctypes.WinDLL("user32", use_last_error=True).EnumDisplayDevicesW
enum_devices.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                         ctypes.POINTER(DisplayDevice), wintypes.DWORD]
enum_devices.restype = wintypes.BOOL


def primary_display_name() -> str:
    index = 0
    while True:
        device = DisplayDevice()
        device.cb = ctypes.sizeof(DisplayDevice)
        if not enum_devices(None, index, ctypes.byref(device), 0):
            break
        if device.state_flags & 0x4:  # DISPLAY_DEVICE_PRIMARY_DEVICE
            return device.device_name
        index += 1
    raise RuntimeError("No se encontró la pantalla principal de Windows.")


class TimingExt(ctypes.Structure):
    _fields_ = [("flag", ctypes.c_uint), ("rr", ctypes.c_ushort),
                ("rrx1k", ctypes.c_uint), ("aspect", ctypes.c_uint),
                ("rep", ctypes.c_ushort), ("status", ctypes.c_uint),
                ("name", ctypes.c_ubyte * 40)]


class Timing(ctypes.Structure):
    _fields_ = [("hvisible", ctypes.c_ushort), ("hborder", ctypes.c_ushort),
                ("hfront", ctypes.c_ushort), ("hsync", ctypes.c_ushort),
                ("htotal", ctypes.c_ushort), ("hpol", ctypes.c_ubyte),
                ("vvisible", ctypes.c_ushort), ("vborder", ctypes.c_ushort),
                ("vfront", ctypes.c_ushort), ("vsync", ctypes.c_ushort),
                ("vtotal", ctypes.c_ushort), ("vpol", ctypes.c_ubyte),
                ("interlaced", ctypes.c_ushort), ("pclk", ctypes.c_uint),
                ("etc", TimingExt)]


class TimingInput(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint), ("width", ctypes.c_uint),
                ("height", ctypes.c_uint), ("rr", ctypes.c_float),
                ("flag", ctypes.c_uint * 3), ("type", ctypes.c_int)]


class Viewport(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float),
                ("w", ctypes.c_float), ("h", ctypes.c_float)]


class CustomDisplay(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint), ("width", ctypes.c_uint),
                ("height", ctypes.c_uint), ("depth", ctypes.c_uint),
                ("color_format", ctypes.c_int), ("partition", Viewport),
                ("x_ratio", ctypes.c_float), ("y_ratio", ctypes.c_float),
                ("timing", Timing), ("hw_mode_set_only", ctypes.c_uint)]


def version(structure: type[ctypes.Structure]) -> int:
    return (1 << 16) | ctypes.sizeof(structure)


class NvidiaApi:
    def __init__(self):
        try:
            self.library = ctypes.WinDLL("nvapi64.dll")
        except OSError as error:
            raise RuntimeError("Este modo necesita una GPU NVIDIA con su controlador instalado.") from error
        query = self.library.nvapi_QueryInterface
        query.argtypes = [ctypes.c_uint]
        query.restype = ctypes.c_void_p

        def api(interface_id, *argtypes):
            address = query(interface_id)
            if not address:
                raise RuntimeError(f"El controlador NVIDIA no ofrece la función {interface_id:08X}.")
            return ctypes.WINFUNCTYPE(ctypes.c_int, *argtypes)(address)

        self.initialize = api(0x0150E828)
        self.unload = api(0xD22BDD7E)
        self.get_id = api(0xAE457190, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint))
        self.get_timing = api(0x175167E9, ctypes.c_uint,
                              ctypes.POINTER(TimingInput), ctypes.POINTER(Timing))
        self.enumerate_custom = api(0xA2072D59, ctypes.c_uint, ctypes.c_uint,
                                    ctypes.POINTER(CustomDisplay))
        self.try_custom = api(0x1F7DB630, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint,
                              ctypes.POINTER(CustomDisplay))
        self.delete_custom = api(0x552E5B9B, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint,
                                 ctypes.POINTER(CustomDisplay))
        self.save_custom = api(0x49882876, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint,
                               ctypes.c_uint, ctypes.c_uint)
        self.revert_custom = api(0xCBBD40F0, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint)

    def __enter__(self):
        self.check(self.initialize(), "Inicializar NVIDIA")
        return self

    def __exit__(self, *_):
        self.unload()

    @staticmethod
    def check(code: int, action: str) -> None:
        if code != 0:
            raise RuntimeError(f"{action}: NVIDIA devolvió el código {code}.")

    def display_id(self) -> ctypes.c_uint:
        identifier = ctypes.c_uint()
        name = primary_display_name().encode("ascii")
        self.check(self.get_id(name, ctypes.byref(identifier)), "Detectar pantalla NVIDIA")
        return identifier

    def custom_modes(self, identifier: ctypes.c_uint):
        index = 0
        while True:
            mode = CustomDisplay()
            mode.version = version(CustomDisplay)
            code = self.enumerate_custom(identifier.value, index, ctypes.byref(mode))
            if code == -7:  # NVAPI_END_ENUMERATION
                return
            self.check(code, "Enumerar resoluciones NVIDIA")
            yield mode
            index += 1

    def find_custom_mode(self, source_w: int, source_h: int):
        identifier = self.display_id()
        return next((mode for mode in self.custom_modes(identifier)
                     if (mode.width, mode.height) == (source_w, source_h)), None)

    def delete_created_mode(self, source_w: int, source_h: int,
                            output_w: int, output_h: int, hz: int) -> None:
        """Remove only an exact mode created by this run but unavailable in Windows."""
        identifier = self.display_id()
        mode = next((item for item in self.custom_modes(identifier)
                     if (item.width, item.height, item.timing.hvisible,
                         item.timing.vvisible) == (source_w, source_h, output_w, output_h)
                     and abs(item.timing.etc.rrx1k / 1000 - hz) < 0.6), None)
        if mode is not None:
            self.check(self.delete_custom(ctypes.byref(identifier), 1, ctypes.byref(mode)),
                       "Retirar resolución no disponible")

    def ensure_mode(self, source_w: int, source_h: int,
                    output_w: int, output_h: int, hz: int,
                    native_w: int, native_h: int) -> bool:
        identifier = self.display_id()
        for mode in self.custom_modes(identifier):
            if (mode.width, mode.height) == (source_w, source_h):
                actual_hz = mode.timing.etc.rrx1k / 1000
                if ((mode.timing.hvisible, mode.timing.vvisible) == (output_w, output_h)
                        and abs(actual_hz - hz) < 0.6):
                    return False
                raise RuntimeError(
                    f"Ya existe {source_w}×{source_h} con otra salida o frecuencia. "
                    "Elige otro ancho de imagen o elimina ese modo en el panel NVIDIA."
                )

        timing_input = TimingInput(version(TimingInput), output_w, output_h, float(hz),
                                   (ctypes.c_uint * 3)(0, 0, 0),
                                   1 if (output_w, output_h) == (native_w, native_h) else 6)
        custom = CustomDisplay()
        custom.version = version(CustomDisplay)
        custom.width = source_w
        custom.height = source_h
        custom.depth = 32
        custom.color_format = 0
        custom.partition = Viewport(0, 0, 1, 1)
        custom.x_ratio = 1
        custom.y_ratio = 1
        self.check(self.get_timing(identifier.value, ctypes.byref(timing_input),
                                   ctypes.byref(custom.timing)), "Calcular salida de vídeo")
        if (custom.timing.hvisible, custom.timing.vvisible) != (output_w, output_h):
            raise RuntimeError("NVIDIA calculó una salida diferente a la solicitada.")
        tried = False
        try:
            self.check(self.try_custom(ctypes.byref(identifier), 1, ctypes.byref(custom)),
                       "Probar resolución")
            tried = True
            self.check(self.save_custom(ctypes.byref(identifier), 1, 1, 1),
                       "Guardar resolución")
        finally:
            if tried:
                self.check(self.revert_custom(ctypes.byref(identifier), 1),
                           "Restaurar pantalla tras la prueba")
        return True
