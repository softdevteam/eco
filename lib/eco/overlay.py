from PyQt4.QtCore import *
from PyQt4.QtGui import *

from colorsys import hsv_to_rgb

import random

GOLDEN_RATIO = 1.618033988749895
SATURATION = 0.5
VALUE = 0.99
SPACING = 5    # Pixels of space between text and railroad line.
HOFFSET = 10   # Min chars in a horizontal railroad line.
VOFFSET = -2   # Adjust railroad line to vertical centre of text.


class Overlay(QWidget):
    """A transparent overlay which can be placed on top of another QWidget.
    """

    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)
        self.node_editor = parent
        palette = QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)

        # line no -> normalised float in [0.0, 1.0]
        self._heatmap_data = dict()

        # { method_name :
        #     { 'definition' : (line_no, char_no),
        #        'calls' : [ (line_no, char_no) ],
        #        'max_x' : max_char_no
        #     }
        # }
        self._railroad_data = dict()

        # Generate a list of random colours. Seeded so that the user
        # sees the same colours on each invocation of Eco.
        self._random_colours = list()
        rangen = random.Random(0.5)
        for _ in xrange(1000):
            hue = rangen.random() + GOLDEN_RATIO
            hue %= 1
            rgb = [col * 255 for col in hsv_to_rgb(hue, SATURATION, VALUE)]
            self._random_colours.append(QColor(*rgb))

    def add_heatmap_datum(self, lineno, datum):
        self._heatmap_data[lineno] = datum

    def add_railroad_datum(self, datum):
        for method in datum:  # Should only be one method per annotation.
            if method in self._railroad_data:
                self._railroad_data[method]['calls'] = self._railroad_data[method]['calls'].union(datum[method]['calls'])
                self._railroad_data[method]['max_x'] = max(datum[method]['max_x'],
                                                           self._railroad_data[method]['max_x'])
            else:
                self._railroad_data[method] = datum[method]

    def clear_data(self):
        self._heatmap_data = dict()
        self._railroad_data = dict()

    def get_heatmap_colour(self, value):
        """Map a normalised value [0.0, 0.1] to a QColor.
        """
        low = QColor(QApplication.instance().heatmap_low)
        high = QColor(QApplication.instance().heatmap_high)
        transparency = QApplication.instance().heatmap_alpha.toInt()[0]

        # If data is out of date, draw the heatmap with 10% less opacity
        if self.node_editor.tm.tool_data_is_dirty:
            transparency_new = int(transparency * 0.8)
            if transparency_new > 0:
                transparency = transparency_new

        red   = float(high.red() - low.red()) * value + low.red()
        green = float(high.green() - low.green()) * value + low.green()
        blue  = float(high.blue() - low.blue()) * value + low.blue()

        return QColor(int(red), int(green), int(blue), alpha=transparency)

    def paintEvent(self, event):
        """Paint the visualisation of current tool data.
        """
        if self._heatmap_data:
            self._paint_heatmap(event)
        if self._railroad_data:
            self._paint_railroad(event)

    def _paint_railroad(self, event):
        """Draw a railroad on the current overlay.
        """
        if not self._railroad_data:
            return

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gfont = QApplication.instance().gfont  # Current system font.
        qlines = dict()                        # QColor -> QLine to draw.
        col = -1                               # Next random colour in the list.

        def get_rhs_of_hline(nchars):
            return ((nchars + HOFFSET) * gfont.fontwt) + SPACING

        # Compute lines (and their colours).
        for method_name in self._railroad_data:
            col += 1
            colour = self._random_colours[col]
            qlines[colour] = list()
            method = self._railroad_data[method_name]
            def_line = QLine((gfont.fontwt * method['definition'][1]) + SPACING,
                             (gfont.fontht * method['definition'][0]) + VOFFSET,
                             get_rhs_of_hline(method['max_x']),
                             (gfont.fontht * method['definition'][0]) + VOFFSET)
            qlines[colour].append(def_line)
            last_line = -1
            for call in self._railroad_data[method_name]['calls']:
                c_line = QLine((gfont.fontwt * call[1]) + SPACING,
                               (gfont.fontht * call[0]) + VOFFSET,
                               get_rhs_of_hline(method['max_x']),
                               (gfont.fontht * call[0]) + VOFFSET)
                qlines[colour].append(c_line)
                if (gfont.fontht * call[0]) + VOFFSET > last_line:
                    last_line = (gfont.fontht * call[0]) + VOFFSET
            # Vertical line
            v_line = QLine(get_rhs_of_hline(method['max_x']),
                           (gfont.fontht * method['definition'][0]) + VOFFSET,
                           get_rhs_of_hline(method['max_x']),
                           last_line)
            qlines[colour].append(v_line)

        # Draw lines.
        for colour in qlines:
            painter.setPen(colour)
            for qline in qlines[colour]:
                painter.drawLine(qline)

    def _paint_heatmap(self, event):
        """Draw a heatmap on the current overlay.
        """
        if not self._heatmap_data:
            return

        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Current system font.
        gfont = QApplication.instance().gfont

        # Draw the visualisation.
        x_top = event.rect().top() + 3 + self.node_editor.paint_start[1] * gfont.fontht  # Start a top of widget.
        lineno = self.node_editor.paint_start[0] + 1
        last_lineno = max(self._heatmap_data.keys())
        lines = self.node_editor.lines
        while lineno <= last_lineno:
            if lineno in self._heatmap_data:
                # __init__ (self, int aleft, int atop, int awidth, int aheight)
                rect = QRect(0,
                             x_top,
                             event.rect().width(),
                             gfont.fontht * lines[lineno - 1].height)
                painter.fillRect(rect, QBrush(self.get_heatmap_colour(self._heatmap_data[lineno])))
            x_top += gfont.fontht * lines[lineno - 1].height
            lineno += 1
