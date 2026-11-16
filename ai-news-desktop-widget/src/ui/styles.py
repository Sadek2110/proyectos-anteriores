"""Estilos QSS con estética Nordic + Lila (integrado con el esquema real del escritorio #181825 / #1E1E2E / #CBA6F7)."""

from __future__ import annotations

# Paleta extraída directamente de ~/.config/kdeglobals del sistema del usuario:
# Base:    #1E1E2E (30, 30, 46)
# Mantle:  #181825 (24, 24, 37)
# Crust:   #11111B (17, 17, 27)
# Surface: #313244 (49, 50, 68)
# Text:    #CDD6F4 (205, 214, 244)
# Subtext: #A6ADC8 / #6C7086
# Accent:  #CBA6F7 (203, 166, 247 - Lila / Mauve) & #B4BEFE (Lavanda)

CATEGORY_COLORS: dict[str, tuple[str, str]] = {
    "LLMs": ("#CBA6F7", "rgba(203, 166, 247, 28)"),        # Lila principal
    "Papers": ("#B4BEFE", "rgba(180, 190, 254, 26)"),      # Lavanda nórdico
    "Open Source": ("#94E2D5", "rgba(148, 226, 213, 24)"), # Teal nórdico suave
    "Industria": ("#89B4FA", "rgba(137, 180, 250, 24)"),   # Azul ártico
    "Tools": ("#F5C2E7", "rgba(245, 194, 231, 24)"),       # Rosa lila suave
}


WIDGET_STYLESHEET = """
QWidget#MainContainer {
    background-color: rgba(24, 24, 37, 244);
    border: 1px solid #313244;
    border-radius: 10px;
}

QLabel {
    color: #CDD6F4;
    font-family: "Inter", "Noto Sans", "Cantarell", sans-serif;
    background: transparent;
}

QLabel#AccentDot {
    color: #CBA6F7;
    font-size: 11px;
}

QLabel#HeaderTitle {
    color: #CDD6F4;
    font-family: "JetBrains Mono", "Fira Code", "Noto Sans Mono", monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
}

QLabel#StatusBadge {
    color: #6C7086;
    font-family: "JetBrains Mono", "Noto Sans Mono", monospace;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    background-color: rgba(49, 50, 68, 110);
}

QPushButton#IconButton {
    background-color: transparent;
    color: #6C7086;
    border: 1px solid transparent;
    border-radius: 5px;
    font-family: "JetBrains Mono", "Noto Sans", monospace;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 6px;
}

QPushButton#IconButton:hover {
    background-color: #313244;
    color: #CBA6F7;
    border: 1px solid rgba(203, 166, 247, 70);
}

QPushButton#FilterChip {
    background-color: transparent;
    color: #6C7086;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    font-size: 11px;
    font-weight: 500;
    padding: 3px 6px;
}

QPushButton#FilterChip:hover {
    color: #CDD6F4;
}

QPushButton#FilterChip[active="true"] {
    color: #CBA6F7;
    border-bottom: 2px solid #CBA6F7;
    font-weight: 600;
}

QFrame#NewsCard {
    background-color: rgba(30, 30, 46, 215);
    border: 1px solid #313244;
    border-radius: 10px;
}

QFrame#NewsCard:hover {
    border: 1px solid rgba(203, 166, 247, 90);
}

QLabel#SourceLabel {
    color: #B4BEFE;
    font-family: "JetBrains Mono", "Noto Sans Mono", monospace;
    font-size: 10px;
    font-weight: 600;
}

QLabel#TimeLabel {
    color: #6C7086;
    font-family: "JetBrains Mono", "Noto Sans Mono", monospace;
    font-size: 10px;
}

QLabel#NewBadge {
    background-color: rgba(203, 166, 247, 35);
    color: #CBA6F7;
    border: 1px solid rgba(203, 166, 247, 90);
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 4px;
}

QLabel#ArticleTitle {
    color: #CDD6F4;
    font-size: 14px;
    font-weight: 600;
}

QLabel#ArticleSummary {
    color: #A6ADC8;
    font-size: 12px;
    line-height: 1.4;
}

QPushButton#ReadArticleBtn {
    background-color: rgba(49, 50, 68, 140);
    color: #CBA6F7;
    border: 1px solid rgba(203, 166, 247, 65);
    border-radius: 5px;
    font-family: "JetBrains Mono", "Noto Sans", monospace;
    font-size: 10px;
    font-weight: 600;
    padding: 3px 9px;
}

QPushButton#ReadArticleBtn:hover {
    background-color: #CBA6F7;
    color: #11111B;
    border: 1px solid #CBA6F7;
}

QPushButton#NavArrowBtn {
    background-color: transparent;
    color: #6C7086;
    border: 1px solid #313244;
    border-radius: 5px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
    min-width: 22px;
    max-width: 22px;
    min-height: 20px;
    max-height: 20px;
}

QPushButton#NavArrowBtn:hover {
    background-color: #313244;
    color: #CBA6F7;
    border: 1px solid rgba(203, 166, 247, 90);
}
"""
