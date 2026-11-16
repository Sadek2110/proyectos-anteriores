"""Descarga, caché en disco y descubrimiento (og:image) de las imágenes de portada de las noticias."""

from __future__ import annotations

import hashlib
import html
from pathlib import Path
import re
from typing import Optional

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from src.providers import USER_AGENT


DEFAULT_CACHE_DIR = Path.home() / ".cache" / "ai-news-widget" / "images"
MAX_HTML_BYTES = 400_000
MAX_IMAGE_BYTES = 6_000_000

_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([a-zA-Z_:-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')
_IMAGE_META_KEYS = ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src")


def extract_preview_image(page_html: str, base_url: str = "") -> Optional[str]:
    """Devuelve la imagen de previsualización (og:image / twitter:image) declarada en una página HTML."""
    found: dict[str, str] = {}
    for tag in _META_TAG_RE.findall(page_html):
        attrs = {
            m.group(1).lower(): (m.group(3) if m.group(3) is not None else m.group(4))
            for m in _ATTR_RE.finditer(tag)
        }
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        content = (attrs.get("content") or "").strip()
        if key in _IMAGE_META_KEYS and content and key not in found:
            found[key] = html.unescape(content)

    for key in _IMAGE_META_KEYS:
        url = found.get(key)
        if not url:
            continue
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/") and base_url:
            match = re.match(r"^(https?://[^/]+)", base_url)
            return (match.group(1) + url) if match else None
        if url.startswith("http"):
            return url
    return None


def cache_path_for(url: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    return cache_dir / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:32] + ".img")


def _read_limited(resp: requests.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=32_768):
        chunks.append(chunk)
        total += len(chunk)
        if total >= limit:
            break
    return b"".join(chunks)


def discover_image_url(article_url: str, session: requests.Session, timeout: float = 8.0) -> Optional[str]:
    """Descarga el principio de la página del artículo y busca su imagen de previsualización."""
    resp = session.get(
        article_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=timeout,
        stream=True,
    )
    with resp:
        if resp.status_code != 200 or "html" not in resp.headers.get("Content-Type", ""):
            return None
        raw = _read_limited(resp, MAX_HTML_BYTES)
    return extract_preview_image(raw.decode(resp.encoding or "utf-8", errors="replace"), article_url)


def download_image(image_url: str, session: requests.Session, cache_dir: Path, timeout: float = 10.0) -> Optional[Path]:
    """Descarga una imagen a la caché de disco (si no estaba ya) y devuelve su ruta."""
    target = cache_path_for(image_url, cache_dir)
    if target.exists() and target.stat().st_size > 0:
        return target
    resp = session.get(image_url, headers={"User-Agent": USER_AGENT}, timeout=timeout, stream=True)
    with resp:
        if resp.status_code != 200 or not resp.headers.get("Content-Type", "").startswith("image/"):
            return None
        data = _read_limited(resp, MAX_IMAGE_BYTES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(target)
    return target


class _ImageSignals(QObject):
    finished = Signal(str, str, str, bool)  # (article_id, image_url or "", local_path or "", lookup_ok)


class _ImageJob(QRunnable):
    def __init__(self, article_id: str, article_url: str, image_url: Optional[str], cache_dir: Path, signals: _ImageSignals) -> None:
        super().__init__()
        self.article_id = article_id
        self.article_url = article_url
        self.image_url = image_url
        self.cache_dir = cache_dir
        self.signals = signals

    def run(self) -> None:
        image_url = self.image_url or ""
        local_path = ""
        lookup_ok = True
        try:
            with requests.Session() as session:
                if not image_url and self.article_url:
                    image_url = discover_image_url(self.article_url, session) or ""
                if image_url:
                    path = download_image(image_url, session, self.cache_dir)
                    local_path = str(path) if path else ""
        except Exception:
            lookup_ok = bool(image_url)
        self.signals.finished.emit(self.article_id, image_url, local_path, lookup_ok)


class ImageLoader(QObject):
    """
    Carga asíncrona de portadas: usa image_url si existe; si no, la descubre (og:image) en la página.
    Emite image_ready con la ruta local y image_url_resolved para que el repositorio la recuerde.
    """

    image_ready = Signal(str, str)  # (article_id, local_path)
    image_url_resolved = Signal(str, str)  # (article_id, image_url or "" si no hay imagen)

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR, enabled: bool = True, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.enabled = enabled
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(4)
        self._in_flight: set[str] = set()
        self._done: dict[str, str] = {}
        self._signals = _ImageSignals()
        self._signals.finished.connect(self._on_job_finished)

    def request(self, article_id: str, article_url: str, image_url: Optional[str]) -> Optional[str]:
        """Devuelve la ruta local si ya está disponible; si no, programa la descarga y devuelve None."""
        if article_id in self._done:
            return self._done[article_id] or None
        if image_url:
            cached = cache_path_for(image_url, self.cache_dir)
            if cached.exists() and cached.stat().st_size > 0:
                self._done[article_id] = str(cached)
                return str(cached)
        # image_url == "" significa que ya se buscó y la noticia no tiene imagen
        if not self.enabled or image_url == "" or article_id in self._in_flight:
            return None
        self._in_flight.add(article_id)
        self._pool.start(_ImageJob(article_id, article_url, image_url, self.cache_dir, self._signals))
        return None

    def _on_job_finished(self, article_id: str, image_url: str, local_path: str, lookup_ok: bool) -> None:
        self._in_flight.discard(article_id)
        self._done[article_id] = local_path
        # Un fallo de red no debe marcar la noticia como "sin imagen" para siempre
        if lookup_ok:
            self.image_url_resolved.emit(article_id, image_url)
        if local_path:
            self.image_ready.emit(article_id, local_path)


_shared_loader: Optional[ImageLoader] = None


def shared_image_loader() -> ImageLoader:
    global _shared_loader
    if _shared_loader is None:
        _shared_loader = ImageLoader()
    return _shared_loader
