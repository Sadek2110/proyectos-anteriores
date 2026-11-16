"""Proveedores de noticias de IA (API propia n8n en panel.dksaa.com + APIs públicas + RSS oficiales)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import os
import time
from typing import Any, Optional

import feedparser
import requests

from src.models import NewsItem, clean_html_text, infer_category


USER_AGENT = "AINewsDesktopWidget/1.0 (Linux; KDE Plasma; +https://panel.dksaa.com)"
# Un refresco forzado recoge todas las fuentes y traduce con Gemini antes de responder
FORCE_REFRESH_TIMEOUT = 120.0

DEFAULT_AI_RSS_FEEDS: tuple[tuple[str, str, str], ...] = (
    ("OpenAI News", "https://openai.com/news/rss.xml", "LLMs"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "LLMs"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "Industria"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "Industria"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "Industria"),
    ("r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/hot/.rss?limit=10", "Open Source"),
)


def _struct_time_to_iso(st: time.struct_time | None, fallback_str: str = "") -> str:
    """Convierte struct_time de feedparser o cabeceras RFC2822 a ISO-8601 UTC."""
    if st is not None:
        try:
            dt = datetime(
                st.tm_year,
                st.tm_mon,
                st.tm_mday,
                st.tm_hour,
                st.tm_min,
                st.tm_sec,
                tzinfo=timezone.utc,
            )
            return dt.isoformat()
        except ValueError:
            pass
    if fallback_str:
        try:
            dt = parsedate_to_datetime(fallback_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return fallback_str
    return datetime.now(timezone.utc).isoformat()


class CustomN8nApiProvider:
    """Conector para la API propia desplegada en n8n / EasyPanel (panel.dksaa.com)."""

    def __init__(self, api_url: str = "", timeout: float = 8.0) -> None:
        self.api_url = (api_url or os.environ.get("AI_NEWS_CUSTOM_API_URL", "")).strip()
        self.timeout = timeout
        self._etag: Optional[str] = None

    def fetch_news(self, session: Optional[requests.Session] = None, force_refresh: bool = False) -> list[NewsItem]:
        """Lee la caché de la API; con force_refresh pide a n8n que recoja y traduzca las fuentes en ese momento."""
        if not self.api_url:
            return []

        http = session or requests.Session()
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self._etag and not force_refresh:
            headers["If-None-Match"] = self._etag

        try:
            if force_refresh:
                resp = http.get(
                    self.api_url, headers=headers, params={"refresh": "1"}, timeout=FORCE_REFRESH_TIMEOUT
                )
            else:
                resp = http.get(self.api_url, headers=headers, timeout=self.timeout)
            if resp.status_code == 304:
                return []
            resp.raise_for_status()
            if "ETag" in resp.headers:
                self._etag = resp.headers["ETag"]
            payload = resp.json()
        except Exception:
            return []

        raw_list: list[dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("articles"), list):
            raw_list = payload["articles"]
        elif isinstance(payload, list):
            raw_list = payload

        items: list[NewsItem] = []
        for entry in raw_list:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "").strip()
            url = str(entry.get("url") or entry.get("link") or "").strip()
            if not title or not url:
                continue
            source = str(entry.get("source") or "n8n AI Feed")
            summary = str(entry.get("summary") or entry.get("description") or "")
            category = str(entry.get("category") or "")
            published_at = str(
                entry.get("published_at")
                or entry.get("pubDate")
                or datetime.now(timezone.utc).isoformat()
            )
            items.append(
                NewsItem(
                    id=str(entry.get("id") or ""),
                    title=title,
                    url=url,
                    source=source,
                    summary=summary,
                    category=category,
                    published_at=published_at,
                    image_url=entry.get("image_url"),
                )
            )
        return items


class HuggingFacePapersProvider:
    """Obtiene los papers diarios destacados de IA directamente desde Hugging Face API."""

    API_URL = "https://huggingface.co/api/daily_papers"

    def __init__(self, limit: int = 8, timeout: float = 8.0) -> None:
        self.limit = limit
        self.timeout = timeout

    def fetch_news(self, session: Optional[requests.Session] = None) -> list[NewsItem]:
        http = session or requests.Session()
        try:
            resp = http.get(
                self.API_URL,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        items: list[NewsItem] = []
        for entry in data[: self.limit]:
            if not isinstance(entry, dict):
                continue
            paper = entry.get("paper") if isinstance(entry.get("paper"), dict) else entry
            paper_id = str(paper.get("id") or entry.get("id") or "").strip()
            title = str(entry.get("title") or paper.get("title") or "").strip()
            if not title or not paper_id:
                continue
            summary = str(paper.get("summary") or entry.get("summary") or "")
            published = str(
                entry.get("publishedAt")
                or paper.get("publishedAt")
                or datetime.now(timezone.utc).isoformat()
            )
            upvotes = paper.get("upvotes") or entry.get("upvotes") or 0
            prefix = f"[+{upvotes} upvotes] " if upvotes else ""
            items.append(
                NewsItem(
                    title=title,
                    url=f"https://huggingface.co/papers/{paper_id}",
                    source="HuggingFace Papers",
                    summary=f"{prefix}{clean_html_text(summary, max_length=320)}",
                    category="Papers",
                    published_at=published,
                    image_url=entry.get("thumbnail"),
                )
            )
        return items


class HackerNewsAIProvider:
    """Obtiene noticias recientes y populares sobre IA desde la API Algolia de Hacker News."""

    API_URL = "https://hn.algolia.com/api/v1/search_by_date"

    def __init__(self, limit: int = 10, min_points: int = 10, timeout: float = 8.0) -> None:
        self.limit = limit
        self.min_points = min_points
        self.timeout = timeout

    def fetch_news(self, session: Optional[requests.Session] = None) -> list[NewsItem]:
        http = session or requests.Session()
        params = {
            "tags": "story",
            "query": "AI OR LLM OR OpenAI OR Anthropic OR Gemini OR DeepSeek OR Claude",
            "numericFilters": f"points>={self.min_points}",
            "hitsPerPage": str(self.limit),
        }
        try:
            resp = http.get(
                self.API_URL,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        hits = data.get("hits", []) if isinstance(data, dict) else []
        items: list[NewsItem] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            title = str(hit.get("title") or "").strip()
            object_id = str(hit.get("objectID") or "").strip()
            if not title or not object_id:
                continue
            url = str(hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}")
            points = hit.get("points") or 0
            comments = hit.get("num_comments") or 0
            story_text = clean_html_text(hit.get("story_text") or "", max_length=260)
            summary = (
                story_text
                if story_text
                else f"Tendencia en Hacker News ({points} puntos · {comments} comentarios en la comunidad)."
            )
            category = infer_category(title, summary, "Hacker News AI")
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="Hacker News AI",
                    summary=summary,
                    category=category,
                    published_at=str(hit.get("created_at") or datetime.now(timezone.utc).isoformat()),
                )
            )
        return items


class RssFeedAIProvider:
    """Proveedor de feeds RSS/Atom oficiales de medios y laboratorios de IA."""

    def __init__(
        self,
        feeds: tuple[tuple[str, str, str], ...] = DEFAULT_AI_RSS_FEEDS,
        items_per_feed: int = 5,
        timeout: float = 8.0,
    ) -> None:
        self.feeds = feeds
        self.items_per_feed = items_per_feed
        self.timeout = timeout
        self._etags: dict[str, str] = {}
        self._modified: dict[str, str] = {}

    def _fetch_single_feed(
        self,
        source_name: str,
        feed_url: str,
        default_category: str,
        session: requests.Session,
    ) -> list[NewsItem]:
        headers = {"User-Agent": USER_AGENT}
        if feed_url in self._etags:
            headers["If-None-Match"] = self._etags[feed_url]
        if feed_url in self._modified:
            headers["If-Modified-Since"] = self._modified[feed_url]

        try:
            resp = session.get(feed_url, headers=headers, timeout=self.timeout)
            if resp.status_code == 304:
                return []
            resp.raise_for_status()
            if "ETag" in resp.headers:
                self._etags[feed_url] = resp.headers["ETag"]
            if "Last-Modified" in resp.headers:
                self._modified[feed_url] = resp.headers["Last-Modified"]
            parsed = feedparser.parse(resp.content)
        except Exception:
            return []

        results: list[NewsItem] = []
        for entry in parsed.entries[: self.items_per_feed]:
            title = str(getattr(entry, "title", "") or "").strip()
            link = str(getattr(entry, "link", "") or "").strip()
            if not title or not link:
                continue

            raw_summary = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or ""
            )
            published_parsed = getattr(entry, "published_parsed", None) or getattr(
                entry, "updated_parsed", None
            )
            published_raw = str(
                getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
            )
            published_iso = _struct_time_to_iso(published_parsed, published_raw)
            category = infer_category(title, raw_summary, source_name, default=default_category)

            results.append(
                NewsItem(
                    title=title,
                    url=link,
                    source=source_name,
                    summary=raw_summary,
                    category=category,
                    published_at=published_iso,
                )
            )
        return results

    def fetch_news(self, session: Optional[requests.Session] = None) -> list[NewsItem]:
        http = session or requests.Session()
        all_items: list[NewsItem] = []
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(self.feeds)))) as pool:
            futures = [
                pool.submit(self._fetch_single_feed, name, url, cat, http)
                for name, url, cat in self.feeds
            ]
            for fut in as_completed(futures):
                try:
                    all_items.extend(fut.result())
                except Exception:
                    continue
        return all_items


class AINewsAggregator:
    """Orquestador paralelo que combina la API propia en n8n y los proveedores directos de IA."""

    def __init__(
        self,
        custom_api_url: str = "",
        enable_builtin_sources: bool = True,
        timeout: float = 8.0,
    ) -> None:
        self.custom_api_url = custom_api_url
        self.enable_builtin_sources = enable_builtin_sources
        self.timeout = timeout
        self.n8n_provider = CustomN8nApiProvider(api_url=custom_api_url, timeout=timeout)
        self.hf_provider = HuggingFacePapersProvider(timeout=timeout)
        self.hn_provider = HackerNewsAIProvider(timeout=timeout)
        self.rss_provider = RssFeedAIProvider(timeout=timeout)

    def update_config(self, custom_api_url: str, enable_builtin_sources: bool = True) -> None:
        self.custom_api_url = custom_api_url
        self.enable_builtin_sources = enable_builtin_sources
        self.n8n_provider.api_url = custom_api_url.strip()

    def fetch_all_sources(self, force_refresh: bool = False) -> list[NewsItem]:
        """
        Consulta las fuentes, deduplica y ordena por fecha.
        Si la API de n8n responde con noticias (ya traducidas), se usan solo esas; las fuentes
        integradas quedan como respaldo cuando la API no está configurada o no devuelve nada.
        """
        collected: list[NewsItem] = []
        with requests.Session() as session:
            if self.n8n_provider.api_url:
                collected = self.n8n_provider.fetch_news(session, force_refresh=force_refresh)
            use_builtin = not collected and (self.enable_builtin_sources or not self.n8n_provider.api_url)
            providers: list[Any] = [self.hf_provider, self.hn_provider, self.rss_provider] if use_builtin else []
            with ThreadPoolExecutor(max_workers=max(1, len(providers))) as pool:
                futures = [pool.submit(p.fetch_news, session) for p in providers]
                for fut in as_completed(futures):
                    try:
                        collected.extend(fut.result())
                    except Exception:
                        continue

        # Deduplicación por ID y por titular normalizado
        unique_by_id: dict[str, NewsItem] = {}
        seen_titles: set[str] = set()
        for item in collected:
            norm_title = item.title.strip().lower()
            if item.id in unique_by_id or norm_title in seen_titles:
                continue
            unique_by_id[item.id] = item
            seen_titles.add(norm_title)

        sorted_items = sorted(
            unique_by_id.values(),
            key=lambda x: x.published_datetime,
            reverse=True,
        )
        return sorted_items
