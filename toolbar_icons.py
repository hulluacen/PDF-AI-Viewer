"""Small, independently drawn line icons. No SVG plugin, font or image files."""
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPainterPath, QPen, QPixmap


class ToolbarIcon(QIconEngine):
    def __init__(self, name, theme="light"):
        super().__init__()
        if name not in ("bookmarks", "open", "close", "summary", "chat",
                        "page_up", "page_down", "previous_match", "next_match", "search"):
            raise ValueError("Unknown toolbar icon")
        self.name = name
        self.theme = theme

    def clone(self):
        return ToolbarIcon(self.name, self.theme)

    def paint(self, painter, rect, mode, state):
        dark = self.theme == "dark"
        color = "#cccccc" if dark else "#444444"
        if mode == QIcon.Mode.Disabled:
            color = "#666666" if dark else "#b0b0b0"
        elif state == QIcon.State.On:
            color = "#80b7ff" if dark else "#2d7ff9"
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 24, rect.height() / 24)
        painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        def path(points, close=False):
            outline = QPainterPath()
            outline.moveTo(*points[0])
            for point in points[1:]:
                outline.lineTo(*point)
            if close:
                outline.closeSubpath()
            painter.drawPath(outline)

        if self.name == "bookmarks":
            path([(4, 3.5), (20, 3.5), (20, 20.5), (4, 20.5)], True)
            path([(9, 3.5), (9, 20.5)])
            for y in (8, 12, 16):
                path([(12, y), (17, y)])
        elif self.name == "open":
            path([(3, 17), (3, 5), (9, 5), (11, 8), (20, 8), (20, 10)])
            path([(3, 19), (6, 11), (22, 11), (19, 19)], True)
        elif self.name == "close":
            path([(5, 3), (14, 3), (19, 8), (19, 21), (5, 21)], True)
            path([(14, 3), (14, 8), (19, 8)])
            path([(9, 12), (15, 18)])
            path([(15, 12), (9, 18)])
        elif self.name == "summary":
            path([(12, 3), (5, 3), (5, 21), (19, 21), (19, 14)])
            path([(8, 11), (12, 11)])
            path([(8, 15), (15, 15)])
            path([(8, 18), (13, 18)])
            path([(18, 2), (19.3, 5.7), (23, 7), (19.3, 8.3),
                  (18, 12), (16.7, 8.3), (13, 7), (16.7, 5.7)], True)
        elif self.name in ("page_up", "page_down"):
            if self.name == "page_down":
                painter.translate(0, 24)
                painter.scale(1, -1)
            painter.setBrush(QColor(color))
            path([(12, 4), (20, 12), (15, 12), (15, 20),
                  (9, 20), (9, 12), (4, 12)], True)
        elif self.name in ("previous_match", "next_match"):
            if self.name == "next_match":
                painter.translate(0, 24)
                painter.scale(1, -1)
            path([(5, 15), (12, 8), (19, 15)])
        elif self.name == "search":
            painter.drawEllipse(QRect(4, 4, 11, 11))
            path([(14, 14), (21, 21)])
        else:
            path([(3, 4), (21, 4), (21, 17), (10, 17), (5, 21), (5, 17), (3, 17)], True)
            for x in (7, 12, 17):
                painter.drawEllipse(QRect(x - 1, 10, 2, 2))
        painter.restore()

    def pixmap(self, size, mode, state):
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, scale):
        pixmap = QPixmap(round(size.width() * scale), round(size.height() * scale))
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap


def apply_toolbar_icons(window):
    for attribute, name in (("bookmark_action", "bookmarks"), ("open_pdf_action", "open"),
                            ("close_action", "close"), ("summary_action", "summary"),
                            ("chat_action", "chat")):
        getattr(window, attribute).setIcon(QIcon(ToolbarIcon(name, window.theme)))
    for attribute, name in (("page_prev_btn", "page_up"), ("page_next_btn", "page_down"),
                            ("search_prev_btn", "previous_match"), ("search_next_btn", "next_match"),
                            ("search_btn", "search")):
        getattr(window, attribute).setIcon(QIcon(ToolbarIcon(name, window.theme)))
