"""Capa de persistencia SQLite y gestión de configuración del widget."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Optional

from src.models import NewsItem, WidgetConfig


DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "ai-news-widget"
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "ai-news-widget"


class ConfigManager:
    """Gestiona la carga y guardado de la configuración del usuario en JSON."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or (DEFAULT_CONFIG_DIR / "config.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> WidgetConfig:
        if not self.config_path.exists():
            cfg = WidgetConfig()
            self.save(cfg)
            return cfg
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return WidgetConfig.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return WidgetConfig()

    def save(self, config: WidgetConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


class NewsRepository:
    """Repositorio SQLite para caché local, deduplicación y detección de noticias nuevas."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (DEFAULT_DATA_DIR / "news_cache.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    image_url TEXT,
                    is_new INTEGER NOT NULL DEFAULT 1,
                    is_bookmarked INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_articles_published
                ON articles(published_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_articles(self, items: list[NewsItem]) -> list[NewsItem]:
        """Inserta o actualiza artículos y devuelve la lista de artículos genuinamente NUEVOS."""
        if not items:
            return []

        newly_discovered: list[NewsItem] = []
        with self._connect() as conn:
            existing_rows = conn.execute("SELECT id FROM articles").fetchall()
            existing_ids = {row["id"] for row in existing_rows}

            for item in items:
                if item.id not in existing_ids:
                    item.is_new = True
                    newly_discovered.append(item)
                    existing_ids.add(item.id)
                    conn.execute(
                        """
                        INSERT INTO articles (
                            id, title, summary, url, source, category,
                            published_at, fetched_at, image_url, is_new, is_bookmarked
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.id,
                            item.title,
                            item.summary,
                            item.url,
                            item.source,
                            item.category,
                            item.published_at,
                            item.fetched_at,
                            item.image_url,
                            1,
                            1 if item.is_bookmarked else 0,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE articles
                        SET title = ?, summary = ?, category = ?, image_url = COALESCE(?, image_url)
                        WHERE id = ?
                        """,
                        (item.title, item.summary, item.category, item.image_url, item.id),
                    )
            conn.commit()

        return newly_discovered

    def get_recent_articles(
        self,
        limit: int = 25,
        category: Optional[str] = None,
        only_bookmarked: bool = False,
    ) -> list[NewsItem]:
        """Recupera las noticias más recientes aplicando filtros opcionales."""
        query = "SELECT * FROM articles WHERE 1=1"
        params: list[object] = []

        if only_bookmarked:
            query += " AND is_bookmarked = 1"
        elif category and category not in ("Todas", "All", ""):
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            NewsItem(
                id=row["id"],
                title=row["title"],
                summary=row["summary"],
                url=row["url"],
                source=row["source"],
                category=row["category"],
                published_at=row["published_at"],
                fetched_at=row["fetched_at"],
                image_url=row["image_url"],
                is_new=bool(row["is_new"]),
                is_bookmarked=bool(row["is_bookmarked"]),
            )
            for row in rows
        ]

    def set_image_url(self, article_id: str, image_url: str) -> None:
        """Guarda la portada descubierta ("" = la noticia no tiene imagen) para no volver a buscarla."""
        with self._connect() as conn:
            conn.execute("UPDATE articles SET image_url = ? WHERE id = ?", (image_url, article_id))
            conn.commit()

    def toggle_bookmark(self, article_id: str) -> bool:
        """Alterna el estado de favorito de una noticia y devuelve el nuevo estado."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT is_bookmarked FROM articles WHERE id = ?", (article_id,)
            ).fetchone()
            if not row:
                return False
            new_state = 0 if row["is_bookmarked"] else 1
            conn.execute(
                "UPDATE articles SET is_bookmarked = ? WHERE id = ?",
                (new_state, article_id),
            )
            conn.commit()
            return bool(new_state)

    def mark_all_seen(self) -> None:
        """Limpia el indicador 'is_new' de noticias anteriores antes de un nuevo lote."""
        with self._connect() as conn:
            conn.execute("UPDATE articles SET is_new = 0 WHERE is_new = 1")
            conn.commit()

    def prune_old_articles(self, days: int = 7) -> int:
        """Elimina noticias antiguas (> days) que no estén marcadas como favoritas."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM articles WHERE published_at < ? AND is_bookmarked = 0",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount

    def set_metadata(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()

    def get_metadata(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM sync_metadata WHERE key = ?", (key,)
            ).fetchone()
            return str(row["value"]) if row else default
