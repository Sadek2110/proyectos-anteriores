---
name: pyside6-desktop-widget
description: >-
  Diseño, arquitectura e implementación de widgets de escritorio redimensionables en Linux
  (KDE Plasma / Wayland y X11) usando PySide6 (Qt6), con soporte para carrusel animado,
  bordes de redimensionado personalizados, bandeja del sistema y estética glassmorphism.
---

# Skill: PySide6 Desktop Widget (Linux / KDE Plasma / Wayland)

## Cuándo usar esta skill
Activar siempre que se diseñe, modifique o depure la interfaz gráfica del widget de noticias (`src/ui/`), animaciones del carrusel, eventos de ventana o integración con el escritorio Linux.

## Directrices Técnicas Clave

### 1. Ventana de Escritorio Redimensionable sin Marcos (`Frameless + Resizable`)
En KDE Plasma sobre Wayland/X11, una ventana con `Qt.FramelessWindowHint` necesita soporte explícito para moverse y redimensionarse:
- **Flags recomendados**:
  - Modo normal / escritorio: `Qt.Window | Qt.FramelessWindowHint` (con opción de alternar `Qt.WindowStaysOnTopHint` o `Qt.WindowStaysOnBottomHint` desde la barra del widget o bandeja del sistema).
  - Atributo visual: `setAttribute(Qt.WA_TranslucentBackground, True)` para bordes redondeados limpios mediante QSS.
- **Movimiento y Redimensionado**:
  - Usar `windowHandle().startSystemMove()` y `windowHandle().startSystemResize(edges)` en Qt6 cuando estén disponibles (funcionan de forma nativa en Wayland/KDE Plasma 6), con fallback manual por geometría (`setGeometry`) para máxima compatibilidad.
  - Incluir un `QSizeGrip` visible/estilizado en la esquina inferior derecha y detección de cursores en los 8 bordes/esquinas (margen de 6-8px).
  - Persistir tamaño (`width`, `height`) y posición (`x`, `y`) en la configuración del usuario.

### 2. Diseño Responsivo al Redimensionar
- Al cambiar el tamaño del widget (`resizeEvent`), las tarjetas de noticias del carrusel deben adaptar:
  - El tamaño de fuente o número de líneas visibles del título y resumen.
  - En modo compacto (`height < 260px`), ocultar elementos secundarios y priorizar titular + fuente + controles.
  - En modo expandido (`width > 500px`), mostrar resumen completo, etiquetas de categorías y metadatos ampliados.

### 3. Carrusel Fluido (`NewsCarouselWidget`)
- Utilizar `QStackedWidget` combinado con `QGraphicsOpacityEffect` y `QPropertyAnimation` (150–250 ms, `QEasingCurve.OutCubic`) para transiciones suaves.
- Pausar el temporizador de auto-rotación (`QTimer`) en `enterEvent` (cuando el usuario sitúa el cursor encima) y reanudarlo en `leaveEvent`.
- Soportar navegación por:
  - Botones `◀` / `▶`
  - Indicadores inferiores (dots/puntos clicables)
  - Teclas `Left` / `Right` y rueda del ratón (`wheelEvent`)

### 4. Testing Headless (Offscreen)
- Para verificar la interfaz en el bucle SDD sin requerir interacción manual, ejecutar con `QT_QPA_PLATFORM=offscreen pytest`.
