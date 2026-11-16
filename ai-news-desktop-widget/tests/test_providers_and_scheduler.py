"""Tests SDD Iteración 2: Proveedores de noticias (n8n, HuggingFace, HackerNews, RSS) y Planificador 12h + Tiempo Real (RF-03, RF-05)."""

from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from src.models import NewsItem, WidgetConfig
from src.providers import (
    AINewsAggregator,
    CustomN8nApiProvider,
    HackerNewsAIProvider,
    HuggingFacePapersProvider,
    RssFeedAIProvider,
)
from src.scheduler import UpdateScheduler
from src.storage import NewsRepository


class _DummyResponse:
    def __init__(self, json_data: Any = None, content: bytes = b"", status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self._json = json_data
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._json


def test_custom_n8n_api_provider_parses_contract() -> None:
    fake_session = MagicMock()
    fake_session.get.return_value = _DummyResponse(
        json_data={
            "status": "ok",
            "articles": [
                {
                    "id": "n8n-001",
                    "title": "Nuevo flujo de agentes en n8n con Claude MCP",
                    "summary": "Integración directa de servidores MCP en flujos de trabajo.",
                    "url": "https://panel.dksaa.com/news/mcp-n8n",
                    "source": "n8n AI Hub",
                    "category": "Tools",
                    "published_at": "2026-10-23T11:30:00Z",
                }
            ],
        },
        headers={"ETag": '"v1-etag"'},
    )

    provider = CustomN8nApiProvider(api_url="https://n8n.panel.dksaa.com/webhook/ai-news")
    items = provider.fetch_news(session=fake_session)
    assert len(items) == 1
    assert items[0].id == "n8n-001"
    assert items[0].category == "Tools"

    # Si el servidor devuelve 304 Not Modified en el sondeo en tiempo real, devuelve lista vacía
    fake_session.get.return_value = _DummyResponse(status_code=304)
    items_304 = provider.fetch_news(session=fake_session)
    assert items_304 == []


def test_huggingface_and_hackernews_providers() -> None:
    fake_session = MagicMock()
    fake_session.get.return_value = _DummyResponse(
        json_data=[
            {
                "title": "Scaling Test-Time Compute for Open LLMs",
                "publishedAt": "2026-10-23T09:00:00Z",
                "paper": {
                    "id": "2610.12345",
                    "summary": "We demonstrate a novel inference scaling law for open weights.",
                    "upvotes": 142,
                },
            }
        ]
    )
    hf = HuggingFacePapersProvider(limit=5)
    hf_items = hf.fetch_news(session=fake_session)
    assert len(hf_items) == 1
    assert hf_items[0].category == "Papers"
    assert "huggingface.co/papers/2610.12345" in hf_items[0].url
    assert "[+142 upvotes]" in hf_items[0].summary

    fake_session.get.return_value = _DummyResponse(
        json_data={
            "hits": [
                {
                    "objectID": "998877",
                    "title": "Show HN: Open-source local LLM router in Python",
                    "url": "https://github.com/example/llm-router",
                    "points": 120,
                    "num_comments": 45,
                    "created_at": "2026-10-23T10:15:00Z",
                }
            ]
        }
    )
    hn = HackerNewsAIProvider(limit=5)
    hn_items = hn.fetch_news(session=fake_session)
    assert len(hn_items) == 1
    assert hn_items[0].source == "Hacker News AI"


def test_rss_provider_parses_xml_feed() -> None:
    sample_rss = b"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>OpenAI News</title>
        <item>
          <title>Introducing Next-Gen Reasoning Agents</title>
          <link>https://openai.com/index/reasoning-agents</link>
          <description>&lt;p&gt;New autonomous coding and research capabilities.&lt;/p&gt;</description>
          <pubDate>Fri, 23 Oct 2026 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    fake_session = MagicMock()
    fake_session.get.return_value = _DummyResponse(content=sample_rss)
    rss = RssFeedAIProvider(feeds=(("OpenAI News", "https://openai.com/news/rss.xml", "LLMs"),))
    items = rss.fetch_news(session=fake_session)
    assert len(items) == 1
    assert items[0].title == "Introducing Next-Gen Reasoning Agents"
    assert items[0].category == "LLMs"


def test_update_scheduler_12h_and_realtime_signals() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp:
        repo = NewsRepository(db_path=Path(tmp) / "sched.db")
        cfg = WidgetConfig(full_sync_hours=12, realtime_check_minutes=10)

        fake_aggregator = MagicMock(spec=AINewsAggregator)
        fake_aggregator.fetch_all_sources.return_value = [
            NewsItem(
                title="Noticia IA en Tiempo Real #1",
                url="https://example.com/ai-1",
                source="AI Feed",
                category="LLMs",
            )
        ]

        scheduler = UpdateScheduler(config=cfg, repository=repo, aggregator=fake_aggregator)
        assert scheduler.full_sync_timer.interval() == 12 * 3600 * 1000
        assert scheduler.realtime_watcher_timer.interval() == 10 * 60 * 1000

        discovered_batches: list[list[NewsItem]] = []
        scheduler.new_articles_discovered.connect(lambda items: discovered_batches.append(items))

        scheduler.trigger_manual_refresh(is_full_sync=True)
        scheduler.thread_pool.waitForDone(3000)
        app.processEvents()

        assert len(discovered_batches) == 1
        assert discovered_batches[0][0].title == "Noticia IA en Tiempo Real #1"


def test_n8n_provider_force_refresh_and_api_only_aggregation() -> None:
    fake_session = MagicMock()
    fake_resp = MagicMock(status_code=200, headers={})
    fake_resp.json.return_value = {
        "status": "ok",
        "articles": [{"id": "hn-1", "title": "Titular traducido", "url": "https://example.com/1", "source": "Hacker News", "category": "Industry"}],
    }
    fake_session.get.return_value = fake_resp

    provider = CustomN8nApiProvider(api_url="https://n8n.example.com/webhook/ai-news")
    provider.fetch_news(session=fake_session, force_refresh=True)
    _, kwargs = fake_session.get.call_args
    assert kwargs["params"] == {"refresh": "1"}
    assert kwargs["timeout"] >= 60

    # Si la API responde, no se mezclan las fuentes integradas (evita duplicados sin traducir)
    aggregator = AINewsAggregator(custom_api_url="https://n8n.example.com/webhook/ai-news", enable_builtin_sources=True)
    aggregator.n8n_provider.fetch_news = MagicMock(return_value=[NewsItem(title="Titular traducido", url="https://example.com/1", source="HN")])
    aggregator.hn_provider.fetch_news = MagicMock(return_value=[])
    items = aggregator.fetch_all_sources(force_refresh=True)
    assert [i.title for i in items] == ["Titular traducido"]
    aggregator.n8n_provider.fetch_news.assert_called_once()
    assert aggregator.n8n_provider.fetch_news.call_args.kwargs == {"force_refresh": True}
    aggregator.hn_provider.fetch_news.assert_not_called()
