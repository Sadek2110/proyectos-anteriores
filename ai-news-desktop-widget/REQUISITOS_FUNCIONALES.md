# Requisitos Funcionales y Especificación SDD — AI News Desktop Widget

## 1. Visión General
Widget de escritorio en Python (`PySide6`) para Linux (KDE Plasma / Wayland y X11) que muestra en un **carrusel interactivo y redimensionable** las noticias más recientes sobre Inteligencia Artificial, actualizándose automáticamente **cada 12 horas** y **cada vez que se publica una noticia nueva**.

---

## 2. Catálogo de Requisitos Funcionales (RF)

### RF-01: Ventana de Escritorio Redimensionable y Personalizable
- **Descripción**: El widget debe comportarse como un componente nativo de escritorio, sin bordes pesados del sistema, con estética moderna (Dark Glassmorphism) y capacidad de redimensionarse libremente.
- **Funciones requeridas**:
  - `DesktopWidgetWindow.__init__()`: Inicializa ventana sin marcos (`FramelessWindowHint`) con fondo translúcido y bordes redondeados.
  - `DesktopWidgetWindow.mousePressEvent() / mouseMoveEvent()`: Permite arrastrar el widget desde la barra superior y redimensionarlo desde cualquiera de sus bordes/esquinas o mediante el grip inferior derecho (`QSizeGrip`).
  - `DesktopWidgetWindow.resizeEvent()`: Adapta dinámicamente la tipografía, longitud del resumen visible y disposición de controles según el tamaño actual (modo compacto, estándar o expandido).
  - `DesktopWidgetWindow.toggle_pin_mode()`: Permite alternar entre mantener en el escritorio (`WindowStaysOnBottomHint`), siempre visible (`WindowStaysOnTopHint`) o ventana normal.
  - `DesktopWidgetWindow.save_window_state() / restore_window_state()`: Guarda y restaura posición `(x, y)`, dimensiones `(width, height)` y opacidad entre sesiones.

### RF-02: Carrusel Interactivo de Noticias (`NewsCarouselWidget`)
- **Descripción**: Muestra las noticias una a una en formato tarjeta deslizable/animada con controles intuitivos.
- **Funciones requeridas**:
  - `NewsCarouselWidget.set_articles(articles: list[NewsItem])`: Carga la lista de noticias y actualiza los indicadores de paginación.
  - `NewsCarouselWidget.next_slide() / prev_slide() / go_to_slide(index: int)`: Navega con animación suave de opacidad/desplazamiento (`QPropertyAnimation`).
  - `NewsCarouselWidget.toggle_auto_rotate(enabled: bool)`: Rota automáticamente cada `N` segundos (por defecto 8s), pausándose automáticamente cuando el cursor entra en el widget (`enterEvent`) y reanudándose al salir (`leaveEvent`).
  - `NewsCarouselWidget.wheelEvent() / keyPressEvent()`: Permite pasar de noticia con la rueda del ratón o las flechas del teclado (`◀` / `▶`).
  - `NewsCardWidget.open_in_browser()`: Abre la URL original en el navegador predeterminado al hacer clic en el titular o botón `"Leer artículo ↗"`.

### RF-03: Motor Híbrido de Obtención de Noticias IA (`AINewsAggregator`)
- **Descripción**: Obtiene noticias reales de IA combinando tanto el endpoint propio en `panel.dksaa.com` (n8n/EasyPanel) como fuentes directas gratuitas de alta señal (sin necesidad de API keys obligatorias).
- **Funciones requeridas**:
  - `CustomN8nApiProvider.fetch_news()`: Consulta el webhook/API en `https://panel.dksaa.com/...` (configurable en `config.json` o variables de entorno) creado con n8n.
  - `HuggingFacePapersProvider.fetch_news()`: Obtiene los papers y lanzamientos diarios destacados de IA desde `https://huggingface.co/api/daily_papers`.
  - `HackerNewsAIProvider.fetch_news()`: Consulta la API Algolia de Hacker News filtrando noticias recientes de alto impacto sobre `LLM`, `OpenAI`, `Anthropic`, `Claude`, `Gemini`, `DeepSeek`, `AI`.
  - `RssFeedAIProvider.fetch_news()`: Parsea feeds RSS/Atom oficiales de IA (OpenAI News, Anthropic, Google AI, MIT Tech Review AI, The Verge AI, TechCrunch AI, Reddit `r/LocalLLaMA` y `r/MachineLearning`).
  - `AINewsAggregator.fetch_all_sources()`: Ejecuta todos los proveedores habilitados en paralelo (`ThreadPoolExecutor`), normaliza a objetos `NewsItem`, elimina duplicados y ordena por fecha de publicación descendente.

### RF-04: Caché Local SQLite y Deduplicación (`NewsRepository`)
- **Descripción**: Persiste las noticias localmente para carga instantánea al abrir el widget, modo offline y detección exacta de qué noticias son nuevas.
- **Funciones requeridas**:
  - `NewsRepository.init_db()`: Crea las tablas `articles` y `sync_metadata` en SQLite.
  - `NewsRepository.upsert_articles(items: list[NewsItem]) -> list[NewsItem]`: Inserta nuevas noticias y devuelve únicamente aquellas que **no existían previamente** (para disparar alertas de novedad).
  - `NewsRepository.get_recent_articles(limit: int, category: str | None) -> list[NewsItem]`: Recupera noticias filtradas por categoría o fuente.
  - `NewsRepository.toggle_bookmark(article_id: str) -> bool`: Marca/desmarca noticias favoritas.
  - `NewsRepository.prune_old_articles(days: int = 7)`: Limpia noticias antiguas no marcadas como favoritas.

### RF-05: Planificador de Actualización Dual 12h + Tiempo Real (`UpdateScheduler`)
- **Descripción**: Garantiza que el widget se actualice cada 12 horas en barrido completo y detecte en segundo plano cada vez que salga una noticia nueva sin bloquear la interfaz.
- **Funciones requeridas**:
  - `UpdateScheduler.start()`: Inicia dos temporizadores en segundo plano (`QTimer` + `QThreadPool`):
    1. **Ciclo Principal (cada 12 horas / 43.200 s)**: Sincronización completa de todas las fuentes y limpieza de caché.
    2. **Watcher de Novedades ("Cada que salga algo nuevo", configurable cada 10-15 min)**: Sondeo rápido con `ETag`/`If-Modified-Since` para detectar publicaciones recién salidas.
  - `UpdateScheduler.trigger_manual_refresh()`: Permite forzar una actualización inmediata desde el botón `↻` del widget.
  - `UpdateScheduler.on_new_articles_found(new_items: list[NewsItem])`: Destaca las noticias recién llegadas con el badge `NUEVO`, coloca la más reciente al principio del carrusel y muestra notificación opcional en bandeja del sistema.

### RF-06: Filtrado Rápido, Bandeja del Sistema y Panel de Ajustes
- **Descripción**: Controles integrados para filtrar por categoría (`Todas`, `LLMs`, `Papers`, `Open Source`, `Industria`, `Favoritos`), configurar el intervalo de rotación, la opacidad y la URL de la API de `panel.dksaa.com`.
- **Funciones requeridas**:
  - `CategoryFilterBar.set_active_category(category: str)`
  - `SettingsDialog.save_settings()`
  - `SystemTrayController`: Icono en bandeja del sistema KDE con menú rápido (`Mostrar/Ocultar Widget`, `Actualizar ahora`, `Fijar posición`, `Salir`).
