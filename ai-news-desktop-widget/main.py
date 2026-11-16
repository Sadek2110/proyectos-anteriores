#!/usr/bin/env python3
"""Punto de entrada principal del Widget de Escritorio de Noticias de IA."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from src.providers import AINewsAggregator
from src.storage import ConfigManager, NewsRepository
from src.ui.widget_window import DesktopWidgetWindow


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Pulse — Widget de Escritorio con Carrusel de Noticias de IA"
    )
    parser.add_argument(
        "--check-sources",
        action="store_true",
        help="Sincroniza las fuentes de noticias en consola, muestra el resumen y termina.",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="",
        help="URL personalizada del endpoint de n8n en panel.dksaa.com.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_mgr = ConfigManager()
    config = config_mgr.load()
    if args.api_url:
        config.custom_api_url = args.api_url.strip()
        config_mgr.save(config)

    repo = NewsRepository()

    if args.check_sources:
        aggregator = AINewsAggregator(
            custom_api_url=config.custom_api_url,
            enable_builtin_sources=config.enable_builtin_sources,
        )
        items = aggregator.fetch_all_sources()
        new_items = repo.upsert_articles(items)
        print(
            f"[OK] Fuentes sincronizadas: {len(items)} noticias obtenidas "
            f"({len(new_items)} nuevas guardadas en caché SQLite)."
        )
        for idx, item in enumerate(items[:5], start=1):
            print(f"  {idx}. [{item.category}] {item.title} ({item.source})")
        return 0

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AI Pulse Desktop Widget")
    window = DesktopWidgetWindow(config_manager=config_mgr, repository=repo)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
