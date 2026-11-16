---
name: ai-news-ingestion
description: >-
  Arquitectura de obtención, normalización, deduplicación y almacenamiento en caché
  de noticias de IA desde API propia (n8n / panel.dksaa.com) y fuentes públicas en
  tiempo real (Hugging Face, Hacker News, Reddit, RSS oficiales).
---

# Skill: AI News Ingestion & Scheduling Engine

## Cuándo usar esta skill
Activar cuando se implementen o modifiquen conectores de noticias (`src/services/`, `src/providers/`), la caché SQLite (`src/storage/`), o el planificador de actualizaciones (`src/scheduler/`).

## Modelo de Datos Unificado (`NewsItem`)
Toda fuente (API propia en n8n o proveedores directos) debe normalizarse a la estructura:
- `id` (`str`): Hash SHA-256 único generado a partir de la URL canónica o `(source + title)`.
- `title` (`str`): Titular limpio sin HTML residual.
- `summary` (`str`): Resumen conciso (máx. 280-400 caracteres, generado por IA si viene de n8n o extraído/limpiado del feed).
- `url` (`str`): Enlace directo a la noticia original.
- `source` (`str`): Nombre de la fuente (ej. `OpenAI`, `Anthropic`, `HuggingFace Papers`, `Hacker News AI`, `r/LocalLLaMA`, `MIT Tech Review`).
- `category` (`str`): Categoría (`LLMs`, `Research`, `Open Source`, `Industry`, `Tools`).
- `published_at` (`datetime` / ISO-8601 UTC): Fecha de publicación real para ordenar por recencia.
- `fetched_at` (`datetime` / ISO-8601 UTC): Momento de captura.
- `image_url` (`Optional[str]`): Miniatura opcional.
- `is_new` (`bool`): Indica si llegó en la última sincronización.

## Estrategia de Actualización Dual (Cada 12h + Detección de Novedades)
1. **Sincronización Completa (Cada 12 horas)**:
   - Re-escanea todas las fuentes activas, limpia entradas antiguas (> 7 días salvo favoritos) y refresca el carrusel completo.
2. **Detección Rápida de Novedades ("Cada que salga algo nuevo")**:
   - Sondeo ligero configurable (por defecto cada 15 minutos) usando cabeceras condicionales (`ETag` / `If-Modified-Since`) o consultando el endpoint `/api/v1/ai-news/latest` en `panel.dksaa.com` y las APIs JSON rápidas.
   - Si se detecta un `id` que no existe en SQLite, se inserta inmediatamente, se emite la señal `new_articles_discovered(list[NewsItem])`, se muestra un indicador visual ("¡Nueva noticia!") en el widget y se coloca al inicio del carrusel.
