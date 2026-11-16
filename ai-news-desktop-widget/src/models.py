"""Modelos de datos y configuración para el Widget de Noticias de IA."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import html
import re
from typing import Any, Optional


VALID_CATEGORIES = ("LLMs", "Papers", "Open Source", "Industria", "Tools")

# Nombres que usa la API de n8n (en inglés) -> categorías del widget
CATEGORY_ALIASES: dict[str, str] = {"Research": "Papers", "Industry": "Industria"}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Papers": (
        "arxiv",
        "paper",
        "benchmark",
        "dataset",
        "diffusion",
        "transformer",
        "attention",
        "huggingface.co/papers",
    ),
    "Open Source": (
        "open source",
        "open-source",
        "ollama",
        "llama.cpp",
        "gguf",
        "vllm",
        "localllama",
        "huggingface",
        "weights",
        "apache 2.0",
        "mit license",
        "qwen",
        "mistral",
        "deepseek",
    ),
    "LLMs": (
        "gpt",
        "claude",
        "gemini",
        "llm",
        "openai",
        "anthropic",
        "reasoning",
        "token",
        "prompt",
        "chatbot",
        "sonnet",
        "opus",
        "o1",
        "o3",
    ),
    "Tools": (
        "cursor",
        "copilot",
        "mcp",
        "n8n",
        "sdk",
        "api",
        "cli",
        "agent",
        "IDE",
        "workflow",
        "playwright",
    ),
}


def clean_html_text(raw_text: str | None, max_length: int = 360) -> str:
    """Elimina etiquetas HTML, entidades y espacios redundantes."""
    if not raw_text:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 1].rstrip() + "…"
    return text


def infer_category(title: str, summary: str = "", source: str = "", default: str = "Industria") -> str:
    """Clasifica automáticamente una noticia de IA según palabras clave y fuente."""
    combined = f"{title} {summary} {source}".lower()
    if "huggingface" in source.lower() and "paper" in source.lower():
        return "Papers"
    if "localllama" in source.lower():
        return "Open Source"
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined:
                return category
    return default if default in VALID_CATEGORIES else "Industria"


def generate_article_id(url: str, title: str = "") -> str:
    """Genera un identificador SHA-256 determinista a partir de la URL canónica o el título."""
    canonical = (url or "").strip().lower()
    if canonical:
        # Eliminar parámetros de tracking frecuentes
        canonical = re.sub(r"[?&](utm_[^=&]+|ref|source)=[^&]*", "", canonical)
    seed = canonical or title.strip().lower()
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def parse_iso_datetime(value: str | datetime | None) -> datetime:
    """Convierte cadenas ISO-8601 o fechas RSS a un objeto datetime en UTC."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not value or not isinstance(value, str):
        return datetime.now(timezone.utc)
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


@dataclass
class NewsItem:
    """Representa una noticia normalizada del mundo de la IA."""

    title: str
    url: str
    source: str
    summary: str = ""
    category: str = "Industria"
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = ""
    image_url: Optional[str] = None
    is_new: bool = False
    is_bookmarked: bool = False

    def __post_init__(self) -> None:
        self.title = clean_html_text(self.title, max_length=200)
        self.summary = clean_html_text(self.summary, max_length=360)
        if not self.summary:
            self.summary = f"Noticia publicada en {self.source}. Haz clic para leer el artículo completo."
        self.url = (self.url or "").strip()
        if not self.id:
            self.id = generate_article_id(self.url, self.title)
        self.category = CATEGORY_ALIASES.get(self.category, self.category)
        if not self.category or self.category not in VALID_CATEGORIES:
            self.category = infer_category(self.title, self.summary, self.source)
        self.published_at = parse_iso_datetime(self.published_at).isoformat()
        self.fetched_at = parse_iso_datetime(self.fetched_at).isoformat()

    @property
    def published_datetime(self) -> datetime:
        return parse_iso_datetime(self.published_at)

    def relative_time_es(self, now: Optional[datetime] = None) -> str:
        """Devuelve el tiempo transcurrido en formato legible en español."""
        ref = now or datetime.now(timezone.utc)
        delta = ref - self.published_datetime
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return "Ahora mismo"
        minutes = seconds // 60
        if minutes < 60:
            return f"Hace {minutes} min"
        hours = minutes // 60
        if hours < 24:
            return f"Hace {hours} h"
        days = hours // 24
        if days == 1:
            return "Ayer"
        return f"Hace {days} días"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsItem:
        return cls(
            id=str(data.get("id") or ""),
            title=str(data.get("title") or "Sin título"),
            url=str(data.get("url") or ""),
            source=str(data.get("source") or "AI News"),
            summary=str(data.get("summary") or ""),
            category=str(data.get("category") or ""),
            published_at=str(data.get("published_at") or datetime.now(timezone.utc).isoformat()),
            fetched_at=str(data.get("fetched_at") or datetime.now(timezone.utc).isoformat()),
            image_url=data.get("image_url"),
            is_new=bool(data.get("is_new", False)),
            is_bookmarked=bool(data.get("is_bookmarked", False)),
        )


@dataclass
class WidgetConfig:
    """Configuración persistente del widget de escritorio."""

    width: int = 440
    height: int = 310
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None
    opacity: float = 0.94
    pin_mode: str = "normal"  # "normal", "top", "bottom"
    auto_rotate: bool = True
    carousel_interval_sec: int = 8
    full_sync_hours: int = 12
    realtime_check_minutes: int = 10
    custom_api_url: str = ""
    enable_builtin_sources: bool = True
    max_articles_in_carousel: int = 25

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetConfig:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
