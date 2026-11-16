"""Diálogo de configuración del widget con estética Nordic + Lila (#181825 / #CBA6F7)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.models import WidgetConfig


class SettingsDialog(QDialog):
    """Ventana modal para ajustar el endpoint de n8n (panel.dksaa.com), intervalos y apariencia."""

    def __init__(self, config: WidgetConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ai.news // ajustes")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._config = config
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background-color: #181825; color: #CDD6F4; }
            QLabel { color: #CDD6F4; font-size: 12px; }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #1E1E2E; color: #CDD6F4;
                border: 1px solid #313244; border-radius: 5px; padding: 5px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #CBA6F7;
            }
            QCheckBox { color: #A6ADC8; }
            QSlider::groove:horizontal {
                background: #313244; height: 5px; border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #CBA6F7; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #CBA6F7; width: 13px; margin: -4px 0; border-radius: 6px;
            }
            QPushButton {
                background-color: #1E1E2E; color: #CBA6F7;
                border: 1px solid #313244; border-radius: 5px; padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #313244; border: 1px solid #CBA6F7;
            }
            """
        )
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.api_url_input = QLineEdit(self._config.custom_api_url)
        self.api_url_input.setPlaceholderText("https://n8n.panel.dksaa.com/webhook/ai-news")
        form.addRow("API n8n (panel.dksaa.com):", self.api_url_input)

        self.builtin_sources_chk = QCheckBox("Activar fuentes directas (HuggingFace, HN, OpenAI, RSS)")
        self.builtin_sources_chk.setChecked(self._config.enable_builtin_sources)
        form.addRow("Fuentes integradas:", self.builtin_sources_chk)

        self.auto_rotate_chk = QCheckBox("Rotar noticias automáticamente en carrusel")
        self.auto_rotate_chk.setChecked(self._config.auto_rotate)
        form.addRow("Auto-rotación:", self.auto_rotate_chk)

        self.carousel_sec_spin = QSpinBox()
        self.carousel_sec_spin.setRange(3, 60)
        self.carousel_sec_spin.setValue(self._config.carousel_interval_sec)
        self.carousel_sec_spin.setSuffix(" seg")
        form.addRow("Velocidad del carrusel:", self.carousel_sec_spin)

        self.full_sync_spin = QSpinBox()
        self.full_sync_spin.setRange(1, 24)
        self.full_sync_spin.setValue(self._config.full_sync_hours)
        self.full_sync_spin.setSuffix(" horas")
        form.addRow("Actualización completa:", self.full_sync_spin)

        self.realtime_spin = QSpinBox()
        self.realtime_spin.setRange(1, 120)
        self.realtime_spin.setValue(self._config.realtime_check_minutes)
        self.realtime_spin.setSuffix(" min")
        form.addRow("Detección de novedades:", self.realtime_spin)

        self.pin_combo = QComboBox()
        self.pin_combo.addItem("Normal", "normal")
        self.pin_combo.addItem("Siempre visible encima (Top)", "top")
        self.pin_combo.addItem("Fijado al escritorio (Bottom)", "bottom")
        idx = self.pin_combo.findData(self._config.pin_mode)
        if idx >= 0:
            self.pin_combo.setCurrentIndex(idx)
        form.addRow("Modo de ventana:", self.pin_combo)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(55, 100)
        self.opacity_slider.setValue(int(self._config.opacity * 100))
        form.addRow("Opacidad del widget:", self.opacity_slider)

        layout.addLayout(form)

        note = QLabel(
            "Nota: En 'claude-api-instructions/' tienes el workflow JSON listo para que Claude "
            "lo despliegue por MCP en tu n8n (panel.dksaa.com)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6C7086; font-size: 11px; padding-top: 4px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_updated_config(self) -> WidgetConfig:
        self._config.custom_api_url = self.api_url_input.text().strip()
        self._config.enable_builtin_sources = self.builtin_sources_chk.isChecked()
        self._config.auto_rotate = self.auto_rotate_chk.isChecked()
        self._config.carousel_interval_sec = self.carousel_sec_spin.value()
        self._config.full_sync_hours = self.full_sync_spin.value()
        self._config.realtime_check_minutes = self.realtime_spin.value()
        self._config.pin_mode = str(self.pin_combo.currentData())
        self._config.opacity = round(self.opacity_slider.value() / 100.0, 2)
        return self._config
