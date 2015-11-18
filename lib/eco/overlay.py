from PyQt4.QtCore import *
from PyQt4.QtGui import *


class Overlay(QWidget):
    """A transparent overlay which can be placed on top of another QWidget.
    """

    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)
        self.node_editor = parent
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)
        # line no -> (float, node)
        self._data = dict()
        # line no -> normalised float [0.0, 1.0]
        self._norms = dict()

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
            self._norms[lineno] = (val - val_min) / val_diff

    def get_colour(self, value):
        """Map a normalised value [0.0, 0.1] to a QColor.
        """
        low = QColor(QApplication.instance().heatmap_low)
        high = QColor(QApplication.instance().heatmap_high)
        transparency = QApplication.instance().heatmap_alpha.toInt()[0]

        red   = float(high.red() - low.red()) * value + low.red()
        green = float(high.green() - low.green()) * value + low.green()
        blue  = float(high.blue() - low.blue()) * value + low.blue()

        return QColor(int(red), int(green), int(blue), alpha=transparency)

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
        last_lineno = max(self._norms.keys())
        lines = self.node_editor.lines
        while lineno <= last_lineno:
            if lineno in self._norms:
                # __init__ (self, int aleft, int atop, int awidth, int aheight)
                rect = QRect(0,
                             x_top,
                             event.rect().width(),
                             gfont.fontht * lines[lineno - 1].height)
                painter.fillRect(rect, QBrush(self.get_colour(self._norms[lineno])))
            x_top += gfont.fontht * lines[lineno - 1].height
            lineno += 1
