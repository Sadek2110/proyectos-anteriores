"""Ventana principal del Widget de Escritorio con estética Nordic + Lila (RF-01, RF-06)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QIcon,
    QMouseEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizeGrip,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.models import NewsItem, WidgetConfig
from src.scheduler import UpdateScheduler
from src.storage import ConfigManager, NewsRepository
from src.ui.carousel import NewsCarouselWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.styles import WIDGET_STYLESHEET


RESIZE_MARGIN = 8


def create_ai_sparkle_icon() -> QIcon:
    """Genera un icono minimalista Nordic + Lila (#181825 + #CBA6F7) para la bandeja del sistema."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#181825"))
    painter.setPen(QColor("#CBA6F7"))
    painter.drawRoundedRect(6, 6, 52, 52, 12, 12)
    painter.setPen(QColor("#CBA6F7"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(24)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, "ia")
    painter.end()
    return QIcon(pix)


class CategoryFilterBar(QWidget):
    """Barra horizontal minimalista con pestañas subrayadas en lila (#CBA6F7)."""

    category_selected = Signal(str)

    CATEGORIES = ("Todas", "LLMs", "Papers", "Open Source", "Industria", "★")

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.active_category = "Todas"
        self.buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(6)

        for cat in self.CATEGORIES:
            btn = QPushButton(cat)
            btn.setObjectName("FilterChip")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setProperty("active", "true" if cat == self.active_category else "false")
            btn.clicked.connect(lambda _checked=False, c=cat: self.set_active_category(c))
            self.buttons[cat] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

    @Slot(str)
    def set_active_category(self, category: str) -> None:
        if category not in self.buttons:
            category = "Todas"
        self.active_category = category
        for cat, btn in self.buttons.items():
            btn.setProperty("active", "true" if cat == category else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.category_selected.emit(category)


class DesktopWidgetWindow(QWidget):
    """
    Ventana principal del widget de escritorio integrada con el tema Nordic + Lila de KDE:
    - Superficie mate #181825 / #1E1E2E con borde #313244 y acentos lila #CBA6F7.
    - Sin marcos del sistema y redimensionable desde los 8 bordes/esquinas o el grip inferior.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        repository: Optional[NewsRepository] = None,
        scheduler: Optional[UpdateScheduler] = None,
        start_scheduler: bool = True,
    ) -> None:
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.config: WidgetConfig = self.config_manager.load()
        self.repository = repository or NewsRepository()
        self.scheduler = scheduler or UpdateScheduler(
            config=self.config, repository=self.repository, parent=self
        )

        self._drag_offset: Optional[QPoint] = None
        self._resize_edges: Qt.Edges = Qt.Edges()
        self._resize_start_geom: Optional[QRect] = None
        self._resize_start_mouse: Optional[QPoint] = None

        self.setWindowTitle("ai.news")
        self.setWindowIcon(create_ai_sparkle_icon())
        self.setMinimumSize(320, 210)
        self.setMouseTracking(True)

        self._apply_window_flags(show_after=False)
        self._build_ui()
        self._restore_window_state()
        self._connect_signals()

        self.reload_from_repository(reset_index=True)

        if start_scheduler:
            self.scheduler.start(initial_sync=True)

    def _apply_window_flags(self, show_after: bool = True) -> None:
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.config.pin_mode == "top":
            flags |= Qt.WindowStaysOnTopHint
        elif self.config.pin_mode == "bottom":
            flags |= Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(max(0.55, min(1.0, self.config.opacity)))
        if show_after:
            self.show()

    def _build_ui(self) -> None:
        self.setStyleSheet(WIDGET_STYLESHEET)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setMouseTracking(True)
        outer.addWidget(self.container)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(14, 10, 14, 8)
        main_layout.setSpacing(6)

        # 1. Cabecera minimalista estilo Waybar / Nordic
        header = QHBoxLayout()
        header.setSpacing(6)

        self.accent_dot = QLabel("●")
        self.accent_dot.setObjectName("AccentDot")
        header.addWidget(self.accent_dot)

        self.title_label = QLabel("ai.news")
        self.title_label.setObjectName("HeaderTitle")
        header.addWidget(self.title_label)

        self.status_badge = QLabel("ready")
        self.status_badge.setObjectName("StatusBadge")
        header.addWidget(self.status_badge)

        header.addStretch(1)

        self.pin_btn = QPushButton(self._pin_icon_text())
        self.pin_btn.setObjectName("IconButton")
        self.pin_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.pin_btn.setToolTip("Modo de ventana (normal / top / fondo de escritorio)")
        self.pin_btn.clicked.connect(self.toggle_pin_mode)
        header.addWidget(self.pin_btn)

        self.refresh_btn = QPushButton("sync")
        self.refresh_btn.setObjectName("IconButton")
        self.refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.refresh_btn.setToolTip("Refrescar ahora: recoge y traduce las últimas noticias")
        self.refresh_btn.clicked.connect(self.force_refresh)
        header.addWidget(self.refresh_btn)

        self.settings_btn = QPushButton("cfg")
        self.settings_btn.setObjectName("IconButton")
        self.settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.settings_btn.setToolTip("Ajustes del widget y API n8n")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        header.addWidget(self.settings_btn)

        self.min_btn = QPushButton("–")
        self.min_btn.setObjectName("IconButton")
        self.min_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.min_btn.setToolTip("Minimizar")
        self.min_btn.clicked.connect(self.showMinimized)
        header.addWidget(self.min_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("IconButton")
        self.close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.close_btn.setToolTip("Cerrar")
        self.close_btn.clicked.connect(self.close)
        header.addWidget(self.close_btn)

        main_layout.addLayout(header)

        # 2. Barra de pestañas minimalistas
        self.filter_bar = CategoryFilterBar(self.container)
        main_layout.addWidget(self.filter_bar)

        # 3. Carrusel de noticias
        self.carousel = NewsCarouselWidget(
            auto_rotate=self.config.auto_rotate,
            interval_sec=self.config.carousel_interval_sec,
            parent=self.container,
        )
        main_layout.addWidget(self.carousel, stretch=1)

        # 4. Pie discreto + grip de redimensionado
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        self.schedule_info_label = QLabel(self._schedule_summary_text())
        self.schedule_info_label.setObjectName("TimeLabel")
        footer.addWidget(self.schedule_info_label)
        footer.addStretch(1)

        self.size_grip = QSizeGrip(self.container)
        self.size_grip.setFixedSize(14, 14)
        self.size_grip.setToolTip("Arrastra para redimensionar")
        footer.addWidget(self.size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        main_layout.addLayout(footer)

        self._init_system_tray()

    def _init_system_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(create_ai_sparkle_icon(), self)
        self.tray_icon.setToolTip("ai.news · Widget de Noticias IA")
        menu = QMenu()
        act_show = QAction("Mostrar widget", self)
        act_show.triggered.connect(self._show_and_raise)
        act_refresh = QAction("Sincronizar ahora", self)
        act_refresh.triggered.connect(self.force_refresh)
        act_settings = QAction("Ajustes…", self)
        act_settings.triggered.connect(self.open_settings_dialog)
        act_quit = QAction("Salir", self)
        act_quit.triggered.connect(QApplication.instance().quit if QApplication.instance() else self.close)
        menu.addAction(act_show)
        menu.addAction(act_refresh)
        menu.addAction(act_settings)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray_icon.setContextMenu(menu)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def _show_and_raise(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _connect_signals(self) -> None:
        self.filter_bar.category_selected.connect(lambda _cat: self.reload_from_repository(reset_index=True))
        self.carousel.bookmark_toggled.connect(self._on_bookmark_toggled)
        self.carousel.image_loader.image_url_resolved.connect(self.repository.set_image_url)
        self.scheduler.sync_started.connect(self._on_sync_started)
        self.scheduler.sync_completed.connect(self._on_sync_completed)
        self.scheduler.new_articles_discovered.connect(self._on_new_articles_discovered)
        self.scheduler.sync_error.connect(self._on_sync_error)

    def _pin_icon_text(self) -> str:
        if self.config.pin_mode == "top":
            return "pin:top"
        if self.config.pin_mode == "bottom":
            return "pin:bg"
        return "pin:off"

    def _schedule_summary_text(self) -> str:
        api_mode = "n8n+rss" if self.config.custom_api_url else "rss+api"
        return f"cada {self.config.full_sync_hours}h · live {self.config.realtime_check_minutes}m · {api_mode}"

    @Slot()
    def force_refresh(self) -> None:
        """Refresco manual: la API recoge y traduce las fuentes en el momento (tarda unos segundos)."""
        self.scheduler.trigger_manual_refresh(is_full_sync=False, force_refresh=True)

    @Slot()
    def toggle_pin_mode(self) -> None:
        order = ("normal", "top", "bottom")
        curr_idx = order.index(self.config.pin_mode) if self.config.pin_mode in order else 0
        self.config.pin_mode = order[(curr_idx + 1) % len(order)]
        self.pin_btn.setText(self._pin_icon_text())
        self.save_window_state()
        self._apply_window_flags(show_after=True)

    @Slot(str)
    def _on_bookmark_toggled(self, article_id: str) -> None:
        self.repository.toggle_bookmark(article_id)
        if self.filter_bar.active_category == "★":
            self.reload_from_repository(reset_index=False)

    @Slot()
    def reload_from_repository(self, reset_index: bool = False) -> None:
        cat = self.filter_bar.active_category
        only_fav = cat == "★"
        items = self.repository.get_recent_articles(
            limit=self.config.max_articles_in_carousel,
            category=None if only_fav else cat,
            only_bookmarked=only_fav,
        )
        self.carousel.set_articles(items, reset_index=reset_index)

    @Slot()
    def _on_sync_started(self) -> None:
        self.status_badge.setText("sync…")
        self.status_badge.setStyleSheet(
            "color: #CBA6F7; font-family: 'JetBrains Mono', monospace; font-size: 10px; "
            "padding: 1px 6px; border-radius: 4px; background-color: rgba(203, 166, 247, 25);"
        )

    @Slot(list, list)
    def _on_sync_completed(self, all_recent: list[NewsItem], new_items: list[NewsItem]) -> None:
        if new_items:
            self.status_badge.setText(f"+{len(new_items)} new")
            self.status_badge.setStyleSheet(
                "color: #CBA6F7; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; "
                "padding: 1px 6px; border-radius: 4px; background-color: rgba(203, 166, 247, 32);"
            )
        else:
            self.status_badge.setText(f"{len(all_recent)} items")
            self.status_badge.setStyleSheet(
                "color: #6C7086; font-family: 'JetBrains Mono', monospace; font-size: 10px; "
                "padding: 1px 6px; border-radius: 4px; background-color: rgba(49, 50, 68, 110);"
            )
        self.reload_from_repository(reset_index=bool(new_items))

    @Slot(list)
    def _on_new_articles_discovered(self, new_items: list[NewsItem]) -> None:
        if not new_items:
            return
        self.carousel.go_to_slide(0)

    @Slot(str)
    def _on_sync_error(self, error_msg: str) -> None:
        self.status_badge.setText("offline")
        self.status_badge.setToolTip(f"Último error de red: {error_msg}")

    @Slot()
    def open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.get_updated_config()
            self.config_manager.save(self.config)
            self.carousel.set_auto_rotate(
                self.config.auto_rotate, self.config.carousel_interval_sec
            )
            self.scheduler.apply_config(self.config)
            self.schedule_info_label.setText(self._schedule_summary_text())
            self._apply_window_flags(show_after=True)
            self.scheduler.trigger_manual_refresh(is_full_sync=False)

    def _restore_window_state(self) -> None:
        w = max(self.minimumWidth(), self.config.width)
        h = max(self.minimumHeight(), self.config.height)
        self.resize(QSize(w, h))
        if self.config.pos_x is not None and self.config.pos_y is not None:
            self.move(self.config.pos_x, self.config.pos_y)

    def save_window_state(self) -> None:
        self.config.width = self.width()
        self.config.height = self.height()
        self.config.pos_x = self.x()
        self.config.pos_y = self.y()
        self.config_manager.save(self.config)

    def _detect_edges(self, pos: QPoint) -> Qt.Edges:
        edges = Qt.Edges()
        rect = self.rect()
        if pos.x() <= rect.left() + RESIZE_MARGIN:
            edges |= Qt.LeftEdge
        elif pos.x() >= rect.right() - RESIZE_MARGIN:
            edges |= Qt.RightEdge
        if pos.y() <= rect.top() + RESIZE_MARGIN:
            edges |= Qt.TopEdge
        elif pos.y() >= rect.bottom() - RESIZE_MARGIN:
            edges |= Qt.BottomEdge
        return edges

    def _update_cursor_for_edges(self, edges: Qt.Edges) -> None:
        if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (Qt.RightEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (Qt.LeftEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edges in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            edges = self._detect_edges(pos)
            win_handle = self.windowHandle()
            if edges:
                if win_handle is not None and win_handle.startSystemResize(edges):
                    event.accept()
                    return
                self._resize_edges = edges
                self._resize_start_geom = self.geometry()
                self._resize_start_mouse = event.globalPosition().toPoint()
                event.accept()
                return

            if pos.y() <= 48:
                if win_handle is not None and win_handle.startSystemMove():
                    event.accept()
                    return
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        global_pos = event.globalPosition().toPoint()
        if self._resize_edges and self._resize_start_geom and self._resize_start_mouse:
            delta = global_pos - self._resize_start_mouse
            geom = QRect(self._resize_start_geom)
            if self._resize_edges & Qt.LeftEdge:
                new_left = geom.left() + delta.x()
                if geom.right() - new_left >= self.minimumWidth():
                    geom.setLeft(new_left)
            if self._resize_edges & Qt.RightEdge:
                geom.setWidth(max(self.minimumWidth(), geom.width() + delta.x()))
            if self._resize_edges & Qt.TopEdge:
                new_top = geom.top() + delta.y()
                if geom.bottom() - new_top >= self.minimumHeight():
                    geom.setTop(new_top)
            if self._resize_edges & Qt.BottomEdge:
                geom.setHeight(max(self.minimumHeight(), geom.height() + delta.y()))
            self.setGeometry(geom)
            event.accept()
            return

        if self._drag_offset is not None and (event.buttons() & Qt.LeftButton):
            self.move(global_pos - self._drag_offset)
            event.accept()
            return

        edges = self._detect_edges(event.position().toPoint())
        self._update_cursor_for_edges(edges)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None or self._resize_edges:
            self._drag_offset = None
            self._resize_edges = Qt.Edges()
            self._resize_start_geom = None
            self._resize_start_mouse = None
            self.unsetCursor()
            self.save_window_state()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.filter_bar.setVisible(h >= 245)
        self.carousel.adapt_cards_to_size(w, h)
        self.save_window_state()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.save_window_state()
        self.scheduler.stop()
        super().closeEvent(event)
