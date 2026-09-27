"""Find or create a real 4:3 game mode that Windows accepts."""

import time

from display import available_mode, current_mode
from nvapi import NvidiaApi


def prepare_auto_mode(report):
    desktop = current_mode()
    output = (desktop.width, desktop.height, desktop.frequency)
    candidates = ((1280, 960), (1200, 900), (1440, 1080),
                  (1152, 864), (1024, 768), (1600, 1200))
    candidates = [(width, height) for width, height in candidates
                  if width < desktop.width and height <= desktop.height]
    if not candidates:
        raise RuntimeError("El monitor no tiene espacio para una imagen 4:3 más estrecha.")

    errors = []
    with NvidiaApi() as nvidia:
        for width, height in candidates:
            name = f"{width}×{height}"
            try:
                previous = nvidia.find_custom_mode(width, height)
                if previous is not None:
                    existing_output = (previous.timing.hvisible, previous.timing.vvisible)
                    existing_hz = previous.timing.etc.rrx1k / 1000
                    if existing_output != output[:2] or abs(existing_hz - output[2]) >= .6:
                        errors.append(f"{name}: ya existe con otra salida o frecuencia")
                        continue
                if available_mode(width, height, output[2]) is not None:
                    report(f"Windows ya ofrece {name} a {output[2]} Hz.")
                    return width, height, *output

                report(f"Creando {name} para {output[0]}×{output[1]} · {output[2]} Hz...")
                created = nvidia.ensure_mode(width, height, *output,
                                             desktop.width, desktop.height)
                for _ in range(12):
                    if available_mode(width, height, output[2]) is not None:
                        report(f"Windows confirmó {name}.")
                        return width, height, *output
                    time.sleep(.5)
                if created:
                    nvidia.delete_created_mode(width, height, *output)
                errors.append(f"{name}: Windows no la ofrece")
            except Exception as error:
                errors.append(f"{name}: {error}")

    raise RuntimeError(
        "No se pudo crear automáticamente una resolución 4:3 que Windows acepte "
        f"a {output[2]} Hz. Prueba bajar los Hz en Windows o elige una resolución "
        "disponible. Detalles: " + "; ".join(errors[:3])
    )
