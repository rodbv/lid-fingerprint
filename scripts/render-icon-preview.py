#!/usr/bin/env python3
"""Render docs/icons.png: the three tray states on a dark and a light panel.

Run with the system Python, which has PyQt6 on Fedora KDE: python3 scripts/render-icon-preview.py
"""

import re
import sys
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "docs" / "icons.png"
STATES = [
    ("Lid open", REPO / "data/icons/fprint-lid-open-symbolic.svg"),
    ("Lid closed", REPO / "data/icons/fprint-lid-closed-symbolic.svg"),
    ("No lid check", Path("/usr/share/icons/breeze/actions/16/action-unavailable-symbolic.svg")),
]
PANELS = [("#202326", "#fcfcfc"), ("#eff0f1", "#232629")]
ICON = 64
CELL_W, CELL_H = 180, 130


TEXT_COLOR = re.compile(r"(\.ColorScheme-Text\s*\{\s*color:\s*)#[0-9a-fA-F]+")


def recolored(svg: Path, color: str) -> bytes:
    return TEXT_COLOR.sub(rf"\g<1>{color}", svg.read_text()).encode()


def main() -> None:
    _app = QGuiApplication(sys.argv)  # QPainter needs a live application
    image = QImage(CELL_W * len(STATES), CELL_H * len(PANELS), QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPixelSize(16)
    painter.setFont(font)

    for row, (background, foreground) in enumerate(PANELS):
        painter.fillRect(0, row * CELL_H, image.width(), CELL_H, QColor(background))
        for column, (label, svg) in enumerate(STATES):
            x, y = column * CELL_W, row * CELL_H
            icon_box = QRectF(x + (CELL_W - ICON) / 2, y + 16, ICON, ICON)
            QSvgRenderer(recolored(svg, foreground)).render(painter, icon_box)
            painter.setPen(QColor(foreground))
            painter.drawText(QRectF(x, y + 92, CELL_W, 24), Qt.AlignmentFlag.AlignCenter, label)

    painter.end()
    OUTPUT.parent.mkdir(exist_ok=True)
    image.save(str(OUTPUT))
    print(OUTPUT)


if __name__ == "__main__":
    main()
