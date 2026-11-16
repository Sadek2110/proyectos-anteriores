# Instrucciones para Claude Code (MCP: n8n + EasyPanel + GitHub)

Este directorio contiene todo lo necesario para que **Claude Code** (conectado mediante MCP a **n8n**, **EasyPanel** en `panel.dksaa.com` y **GitHub**) despliegue automáticamente la API personalizada de noticias de IA y la conecte con el widget de escritorio.

---

## Objetivo para Claude Code
Desplegar un flujo automatizado en **n8n** (alojado en `panel.dksaa.com`) y/o un repositorio en **GitHub** desplegado en **EasyPanel** que exponga un endpoint REST JSON:
- `GET https://<tu-instancia-n8n-o-api>.panel.dksaa.com/webhook/ai-news`

El widget de escritorio en Python ya está preparado para consumir este endpoint automáticamente en cuanto esté activo (y mientras tanto o como respaldo, utiliza su propio motor híbrido integrado).

---

## Paso 1: Crear/Importar el Workflow en n8n vía MCP

1. Usa tu herramienta MCP de **n8n** (`create_workflow` o `import_workflow`) utilizando la definición JSON incluida en `./n8n-ai-news-workflow.json`.
2. El workflow realiza lo siguiente:
   - **Triggers**:
     - `Schedule Trigger`: Se ejecuta automáticamente **cada 12 horas** y también un sub-trigger ligero **cada 30 minutos** para detectar noticias recién publicadas.
     - `Webhook Trigger` (`GET /webhook/ai-news`): Devuelve inmediatamente el JSON con las últimas noticias agregadas y resumidas.
   - **Fuentes que consulta n8n en paralelo**:
     - API de Hugging Face Daily Papers (`https://huggingface.co/api/daily_papers`)
     - API de Hacker News Algolia (`https://hn.algolia.com/api/v1/search_by_date?tags=story&query=AI+OR+LLM+OR+OpenAI+OR+Anthropic+OR+Gemini`)
     - Feeds RSS oficiales (OpenAI, Anthropic, Google AI, MIT Tech Review AI, The Verge AI, Reddit `r/LocalLLaMA`).
   - **Procesamiento IA (Google Gemini / Claude)**:
     - Traduce al español el titular y genera un resumen ejecutivo de 2 líneas para mostrar directamente en el carrusel del widget.
     - Clasifica cada noticia en una categoría (`LLMs`, `Research`, `Open Source`, `Industry`, `Tools`).

---

## Paso 2: Formato del Contrato JSON Esperado por el Widget

El endpoint `GET /webhook/ai-news` debe devolver un HTTP `200 OK` con la siguiente estructura JSON:

```json
{
  "status": "ok",
  "updated_at": "2026-10-23T12:00:00Z",
  "articles": [
    {
      "id": "sha256-o-slug-unico",
      "title": "Titular de la noticia en español",
      "summary": "Resumen conciso de 2-3 líneas generado por IA o extraído del artículo.",
      "url": "https://enlace-original.com/noticia",
      "source": "OpenAI / HuggingFace / Hacker News",
      "category": "LLMs",
      "published_at": "2026-10-23T11:45:00Z",
      "image_url": null
    }
  ]
}
```

---

## Paso 3: Conectar con el Widget Local

Una vez que Claude haya activado el workflow en n8n y obtenido la URL pública del webhook (por ejemplo `https://n8n.panel.dksaa.com/webhook/ai-news`):
1. Escribir la URL en el archivo `~/.config/ai-news-widget/config.json` bajo la clave `"custom_api_url"`, o definir la variable de entorno `AI_NEWS_CUSTOM_API_URL`.
2. Opcionalmente, usar el MCP de **GitHub** para crear el repositorio privado/público `ai-news-desktop-widget` y subir el código del proyecto.
