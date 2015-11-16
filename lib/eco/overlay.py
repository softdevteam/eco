from PyQt4.QtCore import *
from PyQt4.QtGui import *


class Overlay(QWidget):
    """A transparent overlay which can be placed on top of another QWidget.
    """

    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)

        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)

        self.setPalette(palette)

        # line no -> (float, node)
        self.data = dict()

    def paintEvent(self, event):
        """Paint the visualisation of current tool data.
        """
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # A semi-transparent fill over the widget below.
        painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))

        if self.data:
            pass  # FIXME: Draw a heatmap here.
