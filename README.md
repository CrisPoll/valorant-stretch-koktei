# VALORANT Stretch Launcher

**Desarrollado por koktei.** Aplicación de Windows para configurar y activar resoluciones estiradas personalizadas en VALORANT con una GPU NVIDIA.

## Uso

1. Descarga `ValorantStretchKoktei.exe` y ejecútalo.
2. Escribe la **imagen del juego**, la **salida de vídeo** y los **Hz** que quieras, o pulsa **Ver resoluciones de Windows** para elegir una opción que la pantalla principal ya ofrece para Juego o Pantalla. En una instalación nueva, la app usa `1200×900` para el juego y la resolución y frecuencia actuales del monitor como salida. Puedes cambiar cualquiera de estos valores.
3. Pulsa **Abrir VALORANT** y acepta el aviso de Windows para preparar temporalmente el monitor.
4. Entra al campo de tiro o a una partida. La app detecta cuándo el mapa termina de cargar y aplica el estirado automáticamente. **F8** permite reaplicarlo manualmente una vez dentro del mapa; en el lobby se ignora para evitar franjas negras.
5. Al terminar una partida o empezar la carga de la siguiente, la app vuelve a la resolución normal. Vuelve a estirar cuando cargue el nuevo mapa. **F9** restaura el escritorio manualmente. Al cerrar VALORANT, la app restaura la pantalla y el monitor.

Para ensanchar la imagen, el formato de **Pantalla** debe ser más ancho que el de **Juego**. Por ejemplo, `1200×900` es 4:3 y `1600×900` es 16:9; el ancho relativo aumenta `1,33×`. Poner `1600×900` en ambos campos mantiene las proporciones normales.

Si tu escritorio está en `1920×1080`, al estirar el juego pasa a una imagen de `1200×900` (4:3) que se estira hasta la salida del monitor de `1600×900` (16:9). **1600×900 no es una resolución 4:3**: el efecto 4:3 viene de la imagen del juego. Windows puede mostrar la resolución de origen `1200×900` mientras el monitor recibe la salida `1600×900`.

En el **Simulador**, **Juego** es la resolución de la imagen que se estira y **Pantalla** es la salida final que recibe el monitor. Los cinco valores (ancho y alto del juego, ancho y alto de la salida y Hz) son editables; los formatos 4:3 y 16:9 se calculan automáticamente. La comparación visual cambia al editar cualquiera de las resoluciones. **Perfiles** permite guardar y recuperar combinaciones personales. **Configuración** contiene el monitor y las rutas del juego; **Detalles** muestra la actividad.

La aplicación acepta valores personalizados, pero el monitor y el controlador deben admitir la combinación elegida. Si la imagen del juego y la salida nativa ya están disponibles en Windows, usa ese modo sin crear otro en NVIDIA. Para otras combinaciones, NVIDIA prueba la resolución antes de guardarla y Windows la comprueba antes de aplicarla. Si Windows no ofrece el modo guardado, la app muestra las frecuencias disponibles y recomienda usar la salida nativa del monitor. Los cambios del juego pueden alterar el efecto visual; verifica siempre el resultado dentro de una partida.

## Requisitos

- Windows 10 u 11 de 64 bits.
- GPU NVIDIA y controlador que ofrezca NVAPI.
- VALORANT instalado y abierto al menos una vez.
- Permiso de administrador para desactivar temporalmente el dispositivo del monitor. La aplicación solicita ese permiso solo al preparar el monitor.

La app detecta Riot Client, `GameUserSettings.ini` y el monitor activo. Si hace falta, puedes cambiar las rutas y el monitor desde **Configuración avanzada**. **Detalles** muestra la actividad y los errores. El perfil **4:3 con tu monitor** pone `1200×900` como imagen del juego y usa la salida y los Hz actuales del monitor. Se guarda una copia del archivo de configuración en `%LOCALAPPDATA%\KokteiValorantStretch\backups` antes de modificar sus ajustes de vídeo. No se inyecta código en el juego ni se modifica Vanguard.

## Restauración

Pulsa **Restaurar todo** en la aplicación. Mientras haya una partida iniciada por la app, el botón detiene el modo estirado y libera el monitor. El proceso con permisos de administrador también vigila la aplicación y vuelve a activar el monitor si esta se cierra inesperadamente.

Si necesitas restaurar manualmente un monitor desactivado, abre el Administrador de dispositivos de Windows, busca **Monitores**, selecciona tu monitor y pulsa **Habilitar dispositivo**.

## Compilar desde el código fuente

Con Python 3.11 o superior en Windows:

```powershell
.\build.ps1
```

El ejecutable único aparecerá en `dist\ValorantStretchKoktei.exe`. Para ejecutar el código sin compilar:

```powershell
py -3 src\main.py
```

El código está organizado en `src/display.py` (modos de Windows), `src/nvapi.py` (resoluciones NVIDIA), `src/monitor.py` y `assets/monitor_helper.ps1` (preparación y restauración del monitor), `src/riot.py` (configuración y lanzamiento), `src/app.py` (sesión e interfaz base) y `src/modern_ui.py` (simulador visual).

## Notas

Esta aplicación es un proyecto independiente desarrollado por koktei y no está afiliada a Riot Games ni NVIDIA. La técnica se basa en los modos de pantalla de Windows/NVIDIA y en la experiencia de la comunidad de VALORANT. [NVAPI de NVIDIA](https://docs.nvidia.com/nvapi/group__dispcontrol.html) documenta las operaciones de resolución personalizada; [SnapRes](https://github.com/bkuwu/SnapRes) describe el cambio temporal del monitor y el uso de Windowed Fullscreen + Fill.
