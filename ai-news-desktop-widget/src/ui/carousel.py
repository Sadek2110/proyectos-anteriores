"""Componente de carrusel interactivo y tarjetas con portada, estilo Nordic + Lila (RF-02)."""

from __future__ import annotations

from typing import Optional
import webbrowser

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPixmap,
    QResizeEvent,
    QTextLayout,
    QTextOption,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.images import ImageLoader, shared_image_loader
from src.models import NewsItem
from src.ui.styles import CATEGORY_COLORS


DEFAULT_CATEGORY_COLORS = ("#CBA6F7", "rgba(203, 166, 247, 28)")


class ElidedTextLabel(QWidget):
    """Texto con ajuste de línea que se corta con «…» al llegar al máximo de líneas o al alto disponible."""

    def __init__(
        self,
        text: str,
        color: str,
        pixel_size: int,
        bold: bool = False,
        max_lines: int = 3,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._color = QColor(color)
        self._max_lines = max_lines
        self._bold = bold
        self.set_pixel_size(pixel_size)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def text(self) -> str:
        return self._text

    def set_pixel_size(self, pixel_size: int) -> None:
        font = QFont(self.font())
        font.setPixelSize(pixel_size)
        font.setWeight(QFont.DemiBold if self._bold else QFont.Normal)
        self.setFont(font)
        self.updateGeometry()
        self.update()

    def set_max_lines(self, max_lines: int) -> None:
        self._max_lines = max_lines
        self.updateGeometry()
        self.update()

    def _layout_lines(self, width: float) -> list[tuple[int, int]]:
        layout = QTextLayout(self._text, self.font())
        option = QTextOption()
        option.setWrapMode(QTextOption.WordWrap)
        layout.setTextOption(option)
        lines: list[tuple[int, int]] = []
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            lines.append((line.textStart(), line.textLength()))
        layout.endLayout()
        return lines

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        line_count = min(len(self._layout_lines(max(1, width))), self._max_lines)
        return int(QFontMetricsF(self.font()).lineSpacing() * max(1, line_count)) + 2

    def sizeHint(self) -> QSize:
        return QSize(200, self.heightForWidth(200))

    def minimumSizeHint(self) -> QSize:
        return QSize(40, int(QFontMetricsF(self.font()).lineSpacing()) + 2)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(self._color)
        painter.setFont(self.font())
        metrics = QFontMetricsF(self.font())
        spacing = metrics.lineSpacing()
        width = float(self.width())
        visible = max(1, min(self._max_lines, int(self.height() // spacing)))
        lines = self._layout_lines(width)
        for idx, (start, length) in enumerate(lines[:visible]):
            chunk = self._text[start : start + length]
            if idx == visible - 1 and len(lines) > visible:
                chunk = metrics.elidedText(self._text[start:].strip(), Qt.ElideRight, width)
            painter.drawText(QPointF(0, idx * spacing + metrics.ascent()), chunk.rstrip())
        painter.end()


class CoverImageWidget(QWidget):
    """Portada con esquinas redondeadas y recorte tipo «cover»; sin foto muestra un degradado de la categoría."""

    def __init__(self, category: str, source: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.category = category
        self.source = source
        self._pixmap: Optional[QPixmap] = None
        self._scaled: Optional[QPixmap] = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def has_image(self) -> bool:
        return self._pixmap is not None

    def set_image_path(self, path: str) -> bool:
        pix = QPixmap(path)
        if pix.isNull():
            return False
        self._pixmap = pix
        self._scaled = None
        self.update()
        return True

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._scaled = None
        super().resizeEvent(event)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(rect, 7, 7)
        painter.setClipPath(clip)

        fg = QColor(CATEGORY_COLORS.get(self.category, DEFAULT_CATEGORY_COLORS)[0])
        if self._pixmap is not None:
            if self._scaled is None or self._scaled.size() != self.size():
                expanded = self._pixmap.scaled(
                    self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                x = (expanded.width() - self.width()) // 2
                y = (expanded.height() - self.height()) // 2
                self._scaled = expanded.copy(x, y, self.width(), self.height())
            painter.drawPixmap(0, 0, self._scaled)
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            start = QColor(fg)
            start.setAlpha(110)
            gradient.setColorAt(0.0, start)
            gradient.setColorAt(1.0, QColor("#1E1E2E"))
            painter.fillRect(rect, gradient)
            initials = "".join(w[0] for w in self.source.replace("/", " ").split()[:2]).upper() or "IA"
            font = QFont(self.font())
            font.setPixelSize(max(14, int(min(rect.width(), rect.height()) * 0.28)))
            font.setWeight(QFont.Bold)
            painter.setFont(font)
            text_color = QColor(fg)
            text_color.setAlpha(170)
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignCenter, initials)

        # Etiqueta de categoría sobre la portada
        font = QFont(self.font())
        font.setPixelSize(10)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        label = self.category.lower()
        metrics = QFontMetricsF(font)
        pill = QRectF(8, 8, metrics.horizontalAdvance(label) + 14, metrics.height() + 6)
        pill_path = QPainterPath()
        pill_path.addRoundedRect(pill, 5, 5)
        painter.fillPath(pill_path, QColor(17, 17, 27, 200))
        painter.setPen(fg)
        painter.drawText(pill, Qt.AlignCenter, label)
        painter.end()


class NewsCardWidget(QFrame):
    """Tarjeta de noticia con portada, titular y resumen que se adapta al tamaño del widget."""

    bookmark_toggled = Signal(str)  # article_id
    article_opened = Signal(str)  # url

    def __init__(
        self,
        item: NewsItem,
        parent: Optional[QWidget] = None,
        image_loader: Optional[ImageLoader] = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.image_loader = image_loader or shared_image_loader()
        self.mode = "horizontal"
        self.setObjectName("NewsCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._build_ui()
        self.image_loader.image_ready.connect(self._on_image_ready)

    def _build_ui(self) -> None:
        fg, bg = CATEGORY_COLORS.get(self.item.category, DEFAULT_CATEGORY_COLORS)

        self.root_layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.root_layout.setContentsMargins(10, 10, 12, 10)
        self.root_layout.setSpacing(12)

        self.cover = CoverImageWidget(self.item.category, self.item.source, self)
        self.root_layout.addWidget(self.cover)

        text_column = QWidget(self)
        text_layout = QVBoxLayout(text_column)
        text_layout.setContentsMargins(0, 2, 0, 0)
        text_layout.setSpacing(6)

        # Fila superior: categoría (solo sin portada) + fuente + tiempo + marcador
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.category_badge = QLabel(self.item.category.lower())
        self.category_badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            "font-family: 'JetBrains Mono', 'Noto Sans Mono', monospace; "
            "font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px;"
        )
        top_row.addWidget(self.category_badge)

        self.source_label = QLabel(self.item.source)
        self.source_label.setObjectName("SourceLabel")
        top_row.addWidget(self.source_label)

        self.time_label = QLabel(f"· {self.item.relative_time_es()}")
        self.time_label.setObjectName("TimeLabel")
        top_row.addWidget(self.time_label)

        top_row.addStretch(1)

        if self.item.is_new:
            self.new_badge = QLabel("new")
            self.new_badge.setObjectName("NewBadge")
            top_row.addWidget(self.new_badge)
        else:
            self.new_badge = None

        self.bookmark_btn = QPushButton("★" if self.item.is_bookmarked else "☆")
        self.bookmark_btn.setObjectName("IconButton")
        self.bookmark_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.bookmark_btn.setToolTip("Guardar en favoritos")
        self.bookmark_btn.clicked.connect(self._on_bookmark_clicked)
        top_row.addWidget(self.bookmark_btn)

        text_layout.addLayout(top_row)

        self.title_label = ElidedTextLabel(self.item.title, "#CDD6F4", 15, bold=True, max_lines=3, parent=text_column)
        self.title_label.setObjectName("ArticleTitle")
        text_layout.addWidget(self.title_label)

        self.summary_label = ElidedTextLabel(self.item.summary, "#A6ADC8", 12, max_lines=4, parent=text_column)
        self.summary_label.setObjectName("ArticleSummary")
        self.summary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        text_layout.addWidget(self.summary_label, stretch=1)

        self.root_layout.addWidget(text_column, stretch=1)
        self._apply_mode("horizontal")

    def _apply_mode(self, mode: str) -> None:
        self.mode = mode
        show_cover = mode != "compact"
        self.cover.setVisible(show_cover)
        self.category_badge.setVisible(not show_cover)
        self.root_layout.setDirection(QBoxLayout.TopToBottom if mode == "vertical" else QBoxLayout.LeftToRight)
        self._resize_cover()

    def _resize_cover(self) -> None:
        if self.mode == "horizontal":
            self.cover.setMinimumSize(0, 0)
            self.cover.setFixedWidth(max(110, int(self.width() * 0.40)))
            self.cover.setMaximumHeight(16_777_215)
        elif self.mode == "vertical":
            self.cover.setMinimumSize(0, 0)
            self.cover.setFixedHeight(max(90, int(self.height() * 0.45)))
            self.cover.setMaximumWidth(16_777_215)

    def adapt_to_size(self, width: int, height: int) -> None:
        """Elige la disposición según el tamaño del widget: compacta, horizontal (foto a la izquierda) o vertical."""
        if height < 235:
            self._apply_mode("compact")
            self.summary_label.setVisible(False)
            self.title_label.set_pixel_size(13)
            self.title_label.set_max_lines(3)
            return

        self._apply_mode("horizontal" if width >= height * 1.25 else "vertical")
        self.summary_label.setVisible(True)
        if height > 420 or width > 620:
            self.title_label.set_pixel_size(18)
            self.summary_label.set_pixel_size(13)
            self.summary_label.set_max_lines(5)
        else:
            self.title_label.set_pixel_size(15)
            self.summary_label.set_pixel_size(12)
            self.summary_label.set_max_lines(4)

    def ensure_image(self) -> None:
        """Pide la portada al cargador (descarga en segundo plano si aún no está en caché)."""
        if self.cover.has_image():
            return
        path = self.image_loader.request(self.item.id, self.item.url, self.item.image_url)
        if path:
            self.cover.set_image_path(path)

    @Slot(str, str)
    def _on_image_ready(self, article_id: str, local_path: str) -> None:
        if article_id == self.item.id and not self.cover.has_image():
            self.cover.set_image_path(local_path)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_cover()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.open_in_browser()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    @Slot()
    def _on_bookmark_clicked(self) -> None:
        self.item.is_bookmarked = not self.item.is_bookmarked
        self.bookmark_btn.setText("★" if self.item.is_bookmarked else "☆")
        self.bookmark_toggled.emit(self.item.id)

    @Slot()
    def open_in_browser(self) -> None:
        if self.item.url:
            webbrowser.open(self.item.url)
            self.article_opened.emit(self.item.url)


class NewsCarouselWidget(QWidget):
    """Carrusel animado de noticias con indicadores en tono lila (#CBA6F7)."""

    slide_changed = Signal(int, int)  # (current_index, total_count)
    bookmark_toggled = Signal(str)

    def __init__(
        self,
        auto_rotate: bool = True,
        interval_sec: int = 8,
        parent: Optional[QWidget] = None,
        image_loader: Optional[ImageLoader] = None,
    ) -> None:
        super().__init__(parent)
        self.articles: list[NewsItem] = []
        self.image_loader = image_loader or shared_image_loader()
        self._auto_rotate_enabled = auto_rotate
        self._is_hovered = False
        self.setFocusPolicy(Qt.StrongFocus)

        self._rotate_timer = QTimer(self)
        self._rotate_timer.setInterval(max(2, interval_sec) * 1000)
        self._rotate_timer.timeout.connect(self.next_slide)

        self._build_ui()
        if self._auto_rotate_enabled:
            self._rotate_timer.start()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.stack = QStackedWidget(self)
        self.opacity_effect = QGraphicsOpacityEffect(self.stack)
        self.opacity_effect.setOpacity(1.0)
        self.stack.setGraphicsEffect(self.opacity_effect)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setDuration(180)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        root.addWidget(self.stack, stretch=1)

        # Barra inferior de navegación sobria
        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(2, 0, 2, 0)
        nav_bar.setSpacing(8)

        self.prev_btn = QPushButton("‹")
        self.prev_btn.setObjectName("NavArrowBtn")
        self.prev_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.prev_btn.setToolTip("Anterior")
        self.prev_btn.clicked.connect(self.prev_slide)
        nav_bar.addWidget(self.prev_btn)

        nav_bar.addStretch(1)

        self.dots_container = QWidget(self)
        self.dots_layout = QHBoxLayout(self.dots_container)
        self.dots_layout.setContentsMargins(0, 0, 0, 0)
        self.dots_layout.setSpacing(4)
        nav_bar.addWidget(self.dots_container)

        self.counter_label = QLabel("0 / 0")
        self.counter_label.setObjectName("TimeLabel")
        nav_bar.addWidget(self.counter_label)

        nav_bar.addStretch(1)

        self.next_btn = QPushButton("›")
        self.next_btn.setObjectName("NavArrowBtn")
        self.next_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.next_btn.setToolTip("Siguiente")
        self.next_btn.clicked.connect(self.next_slide)
        nav_bar.addWidget(self.next_btn)

        root.addLayout(nav_bar)

    def set_articles(self, articles: list[NewsItem], reset_index: bool = True) -> None:
        prev_idx = self.stack.currentIndex()
        self.articles = list(articles)

        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        if not self.articles:
            empty_card = QFrame()
            empty_card.setObjectName("NewsCard")
            v = QVBoxLayout(empty_card)
            lbl = QLabel("sin entradas en esta vista · pulsa sync para actualizar")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setObjectName("ArticleSummary")
            v.addWidget(lbl)
            self.stack.addWidget(empty_card)
            self._update_indicators()
            return

        for item in self.articles:
            card = NewsCardWidget(item, self, image_loader=self.image_loader)
            card.bookmark_toggled.connect(self.bookmark_toggled.emit)
            card.adapt_to_size(self.width(), self.height())
            self.stack.addWidget(card)

        target_idx = 0 if reset_index else min(max(0, prev_idx), len(self.articles) - 1)
        self.stack.setCurrentIndex(target_idx)
        self._ensure_images_around(target_idx)
        self._update_indicators()
        self.slide_changed.emit(target_idx, len(self.articles))

    def _ensure_images_around(self, index: int) -> None:
        """Carga la portada de la tarjeta visible y precarga la siguiente."""
        total = self.stack.count()
        for offset in (0, 1):
            card = self.stack.widget((index + offset) % total) if total else None
            if isinstance(card, NewsCardWidget):
                card.ensure_image()

    def _update_indicators(self) -> None:
        while self.dots_layout.count() > 0:
            child = self.dots_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        total = len(self.articles)
        if total == 0:
            self.counter_label.setText("0 / 0")
            return

        curr = self.stack.currentIndex()
        self.counter_label.setText(f"{curr + 1} / {total}")

        max_dots = min(total, 9)
        start = max(0, min(curr - max_dots // 2, total - max_dots))
        for i in range(start, start + max_dots):
            dot = QPushButton()
            dot.setCursor(QCursor(Qt.PointingHandCursor))
            is_active = i == curr
            w = 14 if is_active else 6
            color = "#CBA6F7" if is_active else "#313244"
            dot.setFixedSize(w, 5)
            dot.setStyleSheet(
                f"background-color: {color}; border: none; border-radius: 2px;"
            )
            dot.clicked.connect(lambda _checked=False, idx=i: self.go_to_slide(idx))
            self.dots_layout.addWidget(dot)

    @Slot(int)
    def go_to_slide(self, index: int) -> None:
        total = len(self.articles)
        if total == 0:
            return
        target = index % total
        if target == self.stack.currentIndex() and total > 1:
            return
        self.fade_anim.stop()
        self.opacity_effect.setOpacity(0.3)
        self.stack.setCurrentIndex(target)
        self._ensure_images_around(target)
        self.fade_anim.setStartValue(0.3)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
        self._update_indicators()
        self.slide_changed.emit(target, total)

    @Slot()
    def next_slide(self) -> None:
        if len(self.articles) > 1:
            self.go_to_slide(self.stack.currentIndex() + 1)

    @Slot()
    def prev_slide(self) -> None:
        if len(self.articles) > 1:
            self.go_to_slide(self.stack.currentIndex() - 1)

    def set_auto_rotate(self, enabled: bool, interval_sec: Optional[int] = None) -> None:
        self._auto_rotate_enabled = enabled
        if interval_sec is not None:
            self._rotate_timer.setInterval(max(2, interval_sec) * 1000)
        if enabled and not self._is_hovered:
            self._rotate_timer.start()
        else:
            self._rotate_timer.stop()

    def adapt_cards_to_size(self, width: int, height: int) -> None:
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if isinstance(w, NewsCardWidget):
                w.adapt_to_size(width, height)

    def enterEvent(self, event: QEvent) -> None:
        self._is_hovered = True
        if self._rotate_timer.isActive():
            self._rotate_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._is_hovered = False
        if self._auto_rotate_enabled:
            self._rotate_timer.start()
        super().leaveEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta < 0:
            self.next_slide()
        elif delta > 0:
            self.prev_slide()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Right:
            self.next_slide()
            event.accept()
        elif event.key() == Qt.Key_Left:
            self.prev_slide()
            event.accept()
        else:
            super().keyPressEvent(event)
