"""Planificador de actualización dual: cada 12 horas + detección de nuevas noticias en segundo plano."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from src.models import NewsItem, WidgetConfig
from src.providers import AINewsAggregator
from src.storage import NewsRepository


class _FetchWorkerSignals(QObject):
    """Señales emitidas por el worker asíncrono de sincronización."""

    finished = Signal(list, list, bool)  # (all_recent_items, newly_discovered_items, is_full_sync)
    error = Signal(str)


class _FetchWorker(QRunnable):
    """Tarea en segundo plano para consultar las fuentes de IA sin bloquear la UI."""

    def __init__(
        self,
        aggregator: AINewsAggregator,
        repository: NewsRepository,
        max_items: int = 25,
        is_full_sync: bool = False,
        force_refresh: bool = False,
    ) -> None:
        super().__init__()
        self.aggregator = aggregator
        self.repository = repository
        self.max_items = max_items
        self.is_full_sync = is_full_sync
        self.force_refresh = force_refresh
        self.signals = _FetchWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            fetched = self.aggregator.fetch_all_sources(force_refresh=self.force_refresh)
            if self.is_full_sync:
                self.repository.prune_old_articles(days=7)

            newly_discovered = self.repository.upsert_articles(fetched)
            now_iso = datetime.now(timezone.utc).isoformat()
            self.repository.set_metadata("last_sync_at", now_iso)
            if self.is_full_sync:
                self.repository.set_metadata("last_full_sync_at", now_iso)

            recent = self.repository.get_recent_articles(limit=self.max_items)
            self.signals.finished.emit(recent, newly_discovered, self.is_full_sync)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class UpdateScheduler(QObject):
    """
    Gestiona las actualizaciones automáticas del widget:
    1. Ciclo principal cada 12 horas (sincronización completa + limpieza).
    2. Watcher rápido ('cada que salga algo nuevo', por defecto cada 10 min) para detectar
       artículos recién publicados y notificar al carrusel al instante.
    """

    sync_started = Signal()
    sync_completed = Signal(list, list)  # (all_articles, new_articles)
    new_articles_discovered = Signal(list)  # (new_articles)
    sync_error = Signal(str)

    def __init__(
        self,
        config: WidgetConfig,
        repository: NewsRepository,
        aggregator: Optional[AINewsAggregator] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.repository = repository
        self.aggregator = aggregator or AINewsAggregator(
            custom_api_url=config.custom_api_url,
            enable_builtin_sources=config.enable_builtin_sources,
        )
        self.thread_pool = QThreadPool.globalInstance()
        self._is_syncing = False

        # Temporizador de ciclo completo (cada 12 horas por defecto)
        self.full_sync_timer = QTimer(self)
        self.full_sync_timer.timeout.connect(self._on_full_sync_timeout)

        # Temporizador de detección rápida de nuevas noticias ("cada que salga algo nuevo")
        self.realtime_watcher_timer = QTimer(self)
        self.realtime_watcher_timer.timeout.connect(self._on_realtime_check_timeout)

        self.apply_config(config)

    def apply_config(self, config: WidgetConfig) -> None:
        """Actualiza los intervalos de los temporizadores y la configuración de fuentes."""
        self.config = config
        self.aggregator.update_config(
            custom_api_url=config.custom_api_url,
            enable_builtin_sources=config.enable_builtin_sources,
        )
        full_ms = max(1, int(config.full_sync_hours)) * 3600 * 1000
        watcher_ms = max(1, int(config.realtime_check_minutes)) * 60 * 1000
        self.full_sync_timer.setInterval(full_ms)
        self.realtime_watcher_timer.setInterval(watcher_ms)

    def start(self, initial_sync: bool = True) -> None:
        """Inicia los temporizadores programados y opcionalmente dispara una carga inicial."""
        if not self.full_sync_timer.isActive():
            self.full_sync_timer.start()
        if not self.realtime_watcher_timer.isActive():
            self.realtime_watcher_timer.start()
        if initial_sync:
            self.trigger_manual_refresh(is_full_sync=True)

    def stop(self) -> None:
        self.full_sync_timer.stop()
        self.realtime_watcher_timer.stop()

    @Slot()
    def trigger_manual_refresh(self, is_full_sync: bool = False, force_refresh: bool = False) -> None:
        """
        Lanza una sincronización en segundo plano si no hay una ya en curso.
        force_refresh pide a la API que recoja y traduzca las fuentes ahora en vez de servir su caché.
        """
        if self._is_syncing:
            return
        self._is_syncing = True
        self.sync_started.emit()

        worker = _FetchWorker(
            aggregator=self.aggregator,
            repository=self.repository,
            max_items=self.config.max_articles_in_carousel,
            is_full_sync=is_full_sync,
            force_refresh=force_refresh,
        )
        worker.signals.finished.connect(self._handle_worker_finished)
        worker.signals.error.connect(self._handle_worker_error)
        self.thread_pool.start(worker)

    @Slot()
    def _on_full_sync_timeout(self) -> None:
        self.trigger_manual_refresh(is_full_sync=True)

    @Slot()
    def _on_realtime_check_timeout(self) -> None:
        self.trigger_manual_refresh(is_full_sync=False)

    @Slot(list, list, bool)
    def _handle_worker_finished(
        self,
        all_recent: list[NewsItem],
        newly_discovered: list[NewsItem],
        is_full_sync: bool,
    ) -> None:
        self._is_syncing = False
        self.sync_completed.emit(all_recent, newly_discovered)
        if newly_discovered:
            self.new_articles_discovered.emit(newly_discovered)

    @Slot(str)
    def _handle_worker_error(self, error_msg: str) -> None:
        self._is_syncing = False
        self.sync_error.emit(error_msg)
