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

        self.node_editor = parent

        # Start and end colours in the gradient
        self.alpha = 100
        self.colour_low  = (222.0, 235.0, 247.0)
        self.colour_high = (49.0, 130.0, 189.0)

        # line no -> (float, node)
        self._data = dict()
        # line no -> QColor
        self._colours = dict()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        vals = [self._data[lineno][0] for lineno in self._data]
        val_min = float(min(vals))
        val_max = float(max(vals))
        val_diff = val_max - val_min
        for lineno in self._data:
            val, node = self._data[lineno]
            # Linear normalisation:
            normed = (val - val_min) / val_diff
            self._colours[lineno] = self.get_colour(normed)

    def get_colour(self, value):
        red   = float(self.colour_high[0] - self.colour_low[0]) * value + self.colour_low[0]
        green = float(self.colour_high[1] - self.colour_low[1]) * value + self.colour_low[1]
        blue  = float(self.colour_high[2] - self.colour_low[2]) * value + self.colour_low[2]
        return QColor(int(red), int(green), int(blue), self.alpha)

    def paintEvent(self, event):
        """Paint the visualisation of current tool data.
        """
        if self._data is None:
            return

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Current system font.
        gfont = QApplication.instance().gfont

        # Draw the visualisation.
        x_top = event.rect().top() + 3 + self.node_editor.paint_start[1] * gfont.fontht  # Start a top of widget.
        lineno = self.node_editor.paint_start[0] + 1
        last_lineno = max(self._colours.keys())
        lines = self.node_editor.lines
        while lineno <= last_lineno:
            if lineno in self._colours:
                # __init__ (self, int aleft, int atop, int awidth, int aheight)
                rect = QRect(0,
                             x_top,
                             event.rect().width(),
                             gfont.fontht * lines[lineno - 1].height)
                painter.fillRect(rect, QBrush(self._colours[lineno]))
            x_top += gfont.fontht * lines[lineno - 1].height
            lineno += 1
