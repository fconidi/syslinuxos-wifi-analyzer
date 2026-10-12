"""Painted instruments for the signal window. SPDX-License-Identifier: GPL-3.0-or-later"""

from i18n import tr

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget


INK = QColor('#e5eef5')
MUTED = QColor('#a3b7c8')
BACKGROUND = QColor('#142633')
ACCENT = QColor('#54d6b0')


class SignalGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = None
        self.weak = -90
        self.strong = -40
        self.setMinimumSize(300, 230)
        self.setAccessibleName(tr('WiFi signal gauge'))

    def set_value(self, value, weak, strong):
        self.value, self.weak, self.strong = value, weak, strong
        self.setAccessibleDescription(tr('No signal') if value is None else f'{value:.1f} dBm')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), BACKGROUND)
        center = QPointF(self.width() / 2, self.height() * 0.66)
        radius = min(self.width() * 0.40, self.height() * 0.56)
        arc = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        for start, span, color in [(210, -80, '#bf6b68'), (130, -80, '#e5bc65'), (50, -80, '#54d6b0')]:
            painter.setPen(QPen(QColor(color), 9, Qt.SolidLine, Qt.FlatCap))
            painter.drawArc(arc, start * 16, span * 16)
        font = QFont(self.font())
        font.setPointSize(10)
        painter.setFont(font)
        for index in range(6):
            angle = math.radians(210 - 240 * index / 5)
            outer = QPointF(center.x() + math.cos(angle) * (radius - 13), center.y() - math.sin(angle) * (radius - 13))
            inner = QPointF(center.x() + math.cos(angle) * (radius - 22), center.y() - math.sin(angle) * (radius - 22))
            painter.setPen(QPen(MUTED, 2))
            painter.drawLine(inner, outer)
            label = str(round(self.weak + (self.strong - self.weak) * index / 5))
            pos = QPointF(center.x() + math.cos(angle) * (radius - 40), center.y() - math.sin(angle) * (radius - 40))
            painter.setPen(INK)
            painter.drawText(QRectF(pos.x() - 20, pos.y() - 10, 40, 20), Qt.AlignCenter, label)
        if self.value is not None:
            strength = max(0, min(1, (self.value - self.weak) / (self.strong - self.weak)))
            angle = math.radians(210 - 240 * strength)
            tip = QPointF(center.x() + math.cos(angle) * (radius - 55), center.y() - math.sin(angle) * (radius - 55))
            side = QPointF(math.sin(angle) * 5, math.cos(angle) * 5)
            painter.setPen(Qt.NoPen)
            painter.setBrush(ACCENT)
            painter.drawPolygon(QPolygonF([center + side, tip, center - side]))
            painter.drawEllipse(center, 8, 8)
        font.setPointSize(26)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(INK)
        text = '—' if self.value is None else f'{self.value:.1f}'
        painter.drawText(QRectF(0, center.y() + 19, self.width(), 42), Qt.AlignCenter, text)
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(MUTED)
        painter.drawText(QRectF(0, center.y() + 60, self.width(), 24), Qt.AlignCenter, tr('dBm · received signal strength'))
        painter.end()


class SignalHistory(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.setMinimumHeight(110)
        self.setAccessibleName(tr('Recent signal history'))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), BACKGROUND)
        plot = QRectF(42, 12, self.width() - 54, self.height() - 32)
        for value in [-90, -60, -30]:
            y = plot.bottom() - (value + 100) / 80 * plot.height()
            painter.setPen(QPen(QColor('#304959'), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(MUTED)
            painter.drawText(QRectF(2, y - 8, 34, 16), Qt.AlignRight, str(value))
        if self.points:
            end = self.points[-1][0]
            previous = None
            for timestamp, signal in self.points:
                if timestamp < end - 60:
                    continue
                point = QPointF(plot.right() - (end - timestamp) / 60 * plot.width(),
                                plot.bottom() - max(0, min(80, signal + 100)) / 80 * plot.height())
                painter.setPen(QPen(ACCENT, 2))
                if previous is not None and timestamp - previous[0] < 4:
                    painter.drawLine(previous[1], point)
                painter.drawEllipse(point, 2, 2)
                previous = (timestamp, point)
        painter.setPen(MUTED)
        painter.drawText(QRectF(42, self.height() - 19, self.width() - 54, 18), Qt.AlignRight,
                         tr('Last 60 seconds of observations'))
        painter.end()
