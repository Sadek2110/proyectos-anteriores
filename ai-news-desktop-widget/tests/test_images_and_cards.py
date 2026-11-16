"""Tests de portadas: descubrimiento og:image, caché en disco y tarjetas con imagen (RF-02)."""

from pathlib import Path
import tempfile

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from src.images import ImageLoader, cache_path_for, extract_preview_image
from src.models import NewsItem
from src.storage import NewsRepository
from src.ui.carousel import NewsCardWidget


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_extract_preview_image_prefers_og_and_resolves_relative_urls() -> None:
    page = """
    <html><head>
      <meta name="twitter:image" content="https://cdn.example.com/tw.png">
      <meta content="https://cdn.example.com/og.jpg?w=1200&amp;h=630" property="og:image" />
    </head></html>
    """
    assert extract_preview_image(page) == "https://cdn.example.com/og.jpg?w=1200&h=630"
    assert extract_preview_image('<meta property="og:image" content="/img/a.png">', "https://site.dev/post/1") == "https://site.dev/img/a.png"
    assert extract_preview_image('<meta property="og:image" content="//cdn.site.dev/a.png">') == "https://cdn.site.dev/a.png"
    assert extract_preview_image("<html><head><title>sin imagen</title></head></html>") is None


def test_api_categories_are_mapped_to_widget_categories() -> None:
    assert NewsItem(title="x", url="https://a.dev/1", source="HF", category="Research").category == "Papers"
    assert NewsItem(title="x", url="https://a.dev/2", source="HN", category="Industry").category == "Industria"


def test_loader_uses_disk_cache_and_skips_known_missing_images() -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        url = "https://cdn.example.com/cover.png"
        pix = QPixmap(40, 20)
        pix.fill(QColor("#CBA6F7"))
        assert pix.save(str(cache_path_for(url, cache_dir)), "PNG")

        loader = ImageLoader(cache_dir=cache_dir, enabled=False)
        assert loader.request("a1", "https://example.com/a1", url) == str(cache_path_for(url, cache_dir))
        # "" = ya se comprobó que no tiene imagen: no se vuelve a buscar
        assert loader.request("a2", "https://example.com/a2", "") is None
        assert "a2" not in loader._in_flight


def test_card_layout_modes_and_cover_image() -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        url = "https://cdn.example.com/cover.png"
        pix = QPixmap(64, 32)
        pix.fill(QColor("#89B4FA"))
        pix.save(str(cache_path_for(url, cache_dir)), "PNG")

        item = NewsItem(title="OpenAI lanza un nuevo modelo", url="https://openai.com/x", source="OpenAI", category="LLMs", image_url=url)
        card = NewsCardWidget(item, image_loader=ImageLoader(cache_dir=cache_dir, enabled=False))
        card.resize(QSize(420, 200))
        card.show()

        card.adapt_to_size(440, 310)
        assert card.mode == "horizontal"
        assert card.cover.isVisible() and not card.category_badge.isVisible()

        card.adapt_to_size(360, 600)
        assert card.mode == "vertical"

        card.adapt_to_size(340, 220)
        assert card.mode == "compact"
        assert card.cover.isHidden() and card.summary_label.isHidden()

        card.ensure_image()
        assert card.cover.has_image()
        card.grab()  # pinta portada y textos sin errores


def test_repository_remembers_discovered_image_url() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = NewsRepository(db_path=Path(tmp) / "news.db")
        item = NewsItem(title="Noticia", url="https://example.com/n", source="HN")
        repo.upsert_articles([item])
        repo.set_image_url(item.id, "https://cdn.example.com/n.jpg")
        assert repo.get_recent_articles()[0].image_url == "https://cdn.example.com/n.jpg"
