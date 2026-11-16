# AGENT.md — AI News Desktop Widget (`Widget-Noticias`)

## 1. Contexto del Proyecto
Widget de escritorio moderno, redimensionable y ligero en **Python** para Linux (**CachyOS / KDE Plasma 6 sobre Wayland/X11**), diseñado para mostrar las noticias más recientes del mundo de la Inteligencia Artificial en formato **carrusel interactivo**, con actualización programada cada **12 horas** y detección inteligente de **nuevas noticias en tiempo real** (polling ligero / webhook / ETag).

## 2. Entorno Detectado
- **SO**: CachyOS Linux (Arch-based, rolling)
- **Escritorio**: KDE Plasma (`XDG_CURRENT_DESKTOP=KDE`, `XDG_SESSION_TYPE=wayland`)
- **Python**: `3.14.8`
- **Node.js**: `v26.11.1`
- **GUI Nativa Disponible**: `PySide6 6.12.0` (Qt6 nativo en KDE Plasma), `requests`, `sqlite3`
- **Infraestructura Externa**: VPS con EasyPanel (`panel.dksaa.com`) + Claude Code Pro conectado por MCP a **n8n**, **EasyPanel** y **GitHub**.

## 3. Arquitectura y Stack Tecnológico
- **UI Framework**: `PySide6` (Qt6). Ventana sin bordes (`Qt.FramelessWindowHint`), fondo translúcido estilizado (Dark Glassmorphism), `QSizeGrip` y bordes interactivos para redimensionar libremente, anclado opcional al escritorio (`Qt.WindowStaysOnBottomHint` / `Qt.Tool`) e icono en bandeja del sistema (`QSystemTrayIcon`).
- **Carrusel**: `QStackedWidget` + `QPropertyAnimation` para transiciones suaves, indicadores de página (dots), auto-rotación configurable (pausada al pasar el ratón), navegación por botones/teclado/rueda del ratón, filtro por categoría/fuente y apertura directa en navegador.
- **Motor de Datos (Híbrido API Propia + Fuentes Directas)**:
  1. **API Propia en n8n / EasyPanel (`panel.dksaa.com`)**: Endpoint REST JSON enriquecido con resúmenes IA (Gemini / Claude) desplegable automáticamente por Claude vía MCP (instrucciones en `claude-api-instructions/`).
  2. **Agregador Directo Integrado (Zero-Config / Fallback autónomo)**: Conecta directamente a APIs públicas gratuitas sin API key y feeds RSS oficiales:
     - **Hugging Face Daily Papers API** (`https://huggingface.co/api/daily_papers`)
     - **Hacker News Algolia API** (filtrado por LLMs, OpenAI, Anthropic, DeepMind, AI)
     - **Reddit JSON API** (`r/LocalLLaMA`, `r/MachineLearning`, `r/artificial`, `r/singularity`)
     - **RSS Oficiales**: OpenAI Blog, Anthropic News, Google AI Blog, MIT Technology Review AI, The Verge AI, TechCrunch AI.
- **Almacenamiento Local**: Base de datos `SQLite` (`~/.local/share/ai-news-widget/news_cache.db`) para caché offline, deduplicación por hash de URL/título, estado de lectura/favoritos y control de timestamps de actualización.
- ** Concurrencia**: `QThread` / `QRunnable` (`QThreadPool`) para que ninguna petición de red bloquee jamás el hilo principal de la interfaz gráfica.

## 4. Metodología de Desarrollo: SDD (Specification-Driven Development) en Bucle
1. **Especificar**: Toda función debe estar documentada en `REQUISITOS_FUNCIONALES.md` con entradas, salidas y criterios de aceptación claros.
2. **Testear primero / Validar**: Crear tests automatizados (`pytest` / `unittest`) para cada módulo (modelos, conectores de datos, caché SQLite, programador de actualizaciones y componentes UI en modo `offscreen`).
3. **Implementar**: Escribir código modular, tipado (`typing`) y limpio bajo `src/`.
4. **Verificar en bucle**: Ejecutar la suite de tests y pruebas de humo (`QT_QPA_PLATFORM=offscreen`) tras cada iteración hasta alcanzar 0 errores y 100% de requisitos cumplidos.

## 5. Reglas para el Agente
- **Permiso antes de instalar**: Nunca instalar paquetes del sistema o de Python sin preguntar antes al usuario y recibir confirmación.
- **No bloquear la UI**: Todas las llamadas HTTP o de base de datos pesadas deben correr fuera del hilo principal de Qt.
- **Resiliencia de Red**: Si una fuente o la API de `panel.dksaa.com` falla o no está disponible, el widget debe seguir funcionando de forma transparente con las demás fuentes y con la caché SQLite local.
- **Skills del Proyecto**: Consultar siempre `.agent/skills/` antes de modificar el motor de ingesta, la interfaz PySide6 o el ciclo SDD.
