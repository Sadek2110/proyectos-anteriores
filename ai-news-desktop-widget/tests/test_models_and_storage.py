"""Tests SDD Iteración 1: Modelos de datos (NewsItem, WidgetConfig) y Persistencia SQLite (RF-04)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from src.models import (
    NewsItem,
    WidgetConfig,
    clean_html_text,
    generate_article_id,
    infer_category,
)
from src.storage import ConfigManager, NewsRepository


def test_clean_html_and_category_inference() -> None:
    raw = "<p>OpenAI lanza <b>GPT-5</b> con capacidades avanzadas &amp; razonamiento.</p><script>alert(1)</script>"
    cleaned = clean_html_text(raw)
    assert cleaned == "OpenAI lanza GPT-5 con capacidades avanzadas & razonamiento."
    assert infer_category(cleaned, "", "OpenAI Blog") == "LLMs"
    assert infer_category("New GGUF quantization in llama.cpp", "", "r/LocalLLaMA") == "Open Source"
    assert infer_category("Attention is All You Need v2", "", "HuggingFace Papers") == "Papers"


def test_deterministic_article_id_ignores_utm_params() -> None:
    id1 = generate_article_id("https://openai.com/index/new-model?utm_source=twitter&utm_medium=social")
    id2 = generate_article_id("https://openai.com/index/new-model")
    assert id1 == id2


def test_news_item_relative_time_es() -> None:
    now = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
    item_recent = NewsItem(
        title="Claude Code MCP Update",
        url="https://anthropic.com/news/mcp",
        source="Anthropic",
        published_at=(now - timedelta(minutes=25)).isoformat(),
    )
    assert item_recent.relative_time_es(now) == "Hace 25 min"

    item_hours = NewsItem(
        title="Gemini 2.5 Pro",
        url="https://blog.google/ai/gemini",
        source="Google AI",
        published_at=(now - timedelta(hours=5)).isoformat(),
    )
    assert item_hours.relative_time_es(now) == "Hace 5 h"


def test_sqlite_repository_upsert_deduplication_and_filtering() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_news.db"
        repo = NewsRepository(db_path=db_path)

        items = [
            NewsItem(
                title="DeepSeek R2 Open Weights Released",
                url="https://deepseek.com/r2",
                source="DeepSeek",
                category="Open Source",
                published_at="2026-10-23T10:00:00+00:00",
            ),
            NewsItem(
                title="Anthropic Claude 4 Sonnet",
                url="https://anthropic.com/claude-4",
                source="Anthropic",
                category="LLMs",
                published_at="2026-10-23T11:00:00+00:00",
            ),
        ]

        # Primera inserción: ambos deben detectarse como nuevos
        new_found = repo.upsert_articles(items)
        assert len(new_found) == 2

        # Segunda inserción con los mismos artículos: 0 nuevos (deduplicación)
        new_found_again = repo.upsert_articles(items)
        assert len(new_found_again) == 0

        # Orden por fecha descendente
        all_articles = repo.get_recent_articles(limit=10)
        assert len(all_articles) == 2
        assert all_articles[0].title == "Anthropic Claude 4 Sonnet"

        # Filtro por categoría
        llm_only = repo.get_recent_articles(limit=10, category="LLMs")
        assert len(llm_only) == 1
        assert llm_only[0].source == "Anthropic"

        # Favoritos
        toggled = repo.toggle_bookmark(all_articles[0].id)
        assert toggled is True
        bookmarked = repo.get_recent_articles(only_bookmarked=True)
        assert len(bookmarked) == 1
        assert bookmarked[0].id == all_articles[0].id


def test_config_manager_persistence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        mgr = ConfigManager(config_path=cfg_path)
        cfg = mgr.load()
        assert cfg.full_sync_hours == 12

        cfg.width = 520
        cfg.custom_api_url = "https://n8n.panel.dksaa.com/webhook/ai-news"
        mgr.save(cfg)

        reloaded = mgr.load()
        assert reloaded.width == 520
        assert reloaded.custom_api_url == "https://n8n.panel.dksaa.com/webhook/ai-news"
