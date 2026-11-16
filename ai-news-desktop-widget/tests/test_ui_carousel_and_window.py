"""Tests SDD Iteración 3: Ventana de Escritorio Redimensionable y Carrusel Interactivo (RF-01, RF-02, RF-06)."""

from pathlib import Path
import tempfile

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QApplication

from src.models import NewsItem
from src.storage import ConfigManager, NewsRepository
from src.ui.carousel import NewsCardWidget, NewsCarouselWidget
from src.ui.widget_window import DesktopWidgetWindow


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_carousel_navigation_and_auto_rotate() -> None:
    _ensure_app()
    carousel = NewsCarouselWidget(auto_rotate=True, interval_sec=5)
    sample_articles = [
        NewsItem(title="Noticia 1: GPT-5", url="https://example.com/1", source="OpenAI", category="LLMs"),
        NewsItem(title="Noticia 2: Claude 4", url="https://example.com/2", source="Anthropic", category="LLMs"),
        NewsItem(title="Noticia 3: Llama 4", url="https://example.com/3", source="Meta AI", category="Open Source"),
    ]
    carousel.set_articles(sample_articles)
    assert carousel.stack.count() == 3
    assert carousel.stack.currentIndex() == 0
    assert carousel.counter_label.text() == "1 / 3"

    # Avanzar siguiente slide
    carousel.next_slide()
    assert carousel.stack.currentIndex() == 1
    assert carousel.counter_label.text() == "2 / 3"

    # Avanzar dos más da la vuelta (circular)
    carousel.next_slide()
    carousel.next_slide()
    assert carousel.stack.currentIndex() == 0

    # Retroceder desde 0 va al último (índice 2)
    carousel.prev_slide()
    assert carousel.stack.currentIndex() == 2


def test_desktop_widget_window_resize_filter_and_pin_modes() -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        cfg_mgr = ConfigManager(config_path=Path(tmp) / "cfg.json")
        repo = NewsRepository(db_path=Path(tmp) / "news.db")
        repo.upsert_articles(
            [
                NewsItem(
                    title="Paper: Linear Attention Transformers",
                    url="https://huggingface.co/papers/1",
                    source="HuggingFace Papers",
                    category="Papers",
                ),
                NewsItem(
                    title="DeepSeek Open Weights",
                    url="https://deepseek.com/1",
                    source="r/LocalLLaMA",
                    category="Open Source",
                ),
            ]
        )

        win = DesktopWidgetWindow(
            config_manager=cfg_mgr,
            repository=repo,
            start_scheduler=False,
        )
        win.show()

        # Debe cargar los 2 artículos de la base de datos al iniciar
        assert len(win.carousel.articles) == 2

        # Filtrar por categoría 'Papers'
        win.filter_bar.set_active_category("Papers")
        assert len(win.carousel.articles) == 1
        assert win.carousel.articles[0].category == "Papers"

        # Volver a 'Todas'
        win.filter_bar.set_active_category("Todas")
        assert len(win.carousel.articles) == 2

        # Probar detección de bordes para redimensionar (RF-01)
        edges_bottom_right = win._detect_edges(QPoint(win.width() - 2, win.height() - 2))
        assert bool(edges_bottom_right & Qt.RightEdge)
        assert bool(edges_bottom_right & Qt.BottomEdge)

        # Redimensionar a modo compacto y luego expandido; comprobar persistencia
        win.resize(QSize(340, 220))
        card = win.carousel.stack.currentWidget()
        assert isinstance(card, NewsCardWidget)
        assert card.summary_label.isHidden() is True

        win.resize(QSize(600, 420))
        assert card.summary_label.isHidden() is False
        reloaded_cfg = cfg_mgr.load()
        assert reloaded_cfg.width == 600
        assert reloaded_cfg.height == 420

        # Alternar modo de fijación en escritorio (normal -> top -> bottom)
        assert win.config.pin_mode == "normal"
        win.toggle_pin_mode()
        assert win.config.pin_mode == "top"
        win.toggle_pin_mode()
        assert win.config.pin_mode == "bottom"
        win.close()
