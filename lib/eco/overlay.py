from PyQt4.QtCore import *
from PyQt4.QtGui import *

from incparser.astree import EOS
from colorsys import hsv_to_rgb

import random

GOLDEN_RATIO = 1.618033988749895
SATURATION = 0.5
VALUE = 0.99
SPACING = 5     # Pixels of space between text and railroad line.
HOFFSET = 10    # Min chars in a horizontal railroad line.
VOFFSET = -2    # Adjust railroad line to vertical centre of text.
LINE_WIDTH = 2  # Line width in pixels.

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

        # method name -> is megamorphic : bool
        self._railroad_data = dict()

        # Generate a list of random colours. Seeded so that the user
        # sees the same colours on each invocation of Eco.
        self._random_colours = list()
        self._random_colours_outdated = list()
        rangen = random.Random(0.5)
        for _ in xrange(1000):
            hue = rangen.random() + GOLDEN_RATIO
            hue %= 1
            rgb = [col * 255 for col in hsv_to_rgb(hue, SATURATION, VALUE)]
            self._random_colours.append(QColor(*rgb))
            rgb = [col * 255 for col in hsv_to_rgb(hue, SATURATION / 2.0, VALUE)]
            self._random_colours_outdated.append(QColor(*rgb))

    @property
    def tm(self):
        return self.node_editor.tm

    def add_heatmap_datum(self, lineno, datum):
        self._heatmap_data[lineno] = datum

    def add_railroad_datum(self, datum):
        for key in datum:
            self._railroad_data[key] = datum[key]

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
        if self.tm.tool_data_is_dirty:
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

        def get_rhs_of_hline(nchars):
            return ((nchars + HOFFSET) * gfont.fontwt) + SPACING

        # Translate the method names in self._railroad_data into line and char
        # numbers. railroad_data will look like this:
        #     { method_name : { 'definition': (line_no, char_no),
        #                       'calls': set((line_no, char_no), ...),
        #                        'max_x': <int>,
        #                        'is_mega': <bool> }
        #     }
        railroad_data = dict()
        for method_name in self._railroad_data:
            railroad_data[method_name] = { 'definition': None,
                                           'calls': set(),
                                           'max_x': 0,
                                           'is_mega': False, }
        temp_cursor = self.tm.cursor.copy()  # Save cursor to restore later.
        self.tm.cursor.line = 0  # Start at beginning of syntax tree.
        self.tm.cursor.move_to_x(0)
        while not (isinstance(self.tm.cursor.node, EOS) or
                   isinstance(self.tm.cursor.node.next_term, EOS)):
            if self.tm.cursor.node.symbol.name in self._railroad_data.keys():
                method = self.tm.cursor.node.symbol.name
                saved_x = self.tm.cursor.get_x()
                self.tm.key_end()
                location = (self.tm.cursor.line + 1, self.tm.cursor.get_x())
                self.tm.cursor.move_to_x(saved_x)
                # Assume the first occurrence of the method is its definition.
                if railroad_data[method]['definition'] is None:
                    railroad_data[method]['definition'] = location
                elif railroad_data[method]['definition'] is not None:
                    railroad_data[method]['calls'].add(location)
                max_x = max(railroad_data[method]['max_x'],
                            location[1])
                railroad_data[method]['max_x'] = max_x
                if self._railroad_data[method]:
                    railroad_data[method]['is_mega'] = True
            self.tm.cursor.jump_right()
        self.tm.cursor = temp_cursor # Restore cursor.

        # Compute lines (and their colours).
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gfont = QApplication.instance().gfont  # Current system font.
        qlines = dict()    # QPen -> QLine to draw.
        col = -1           # Next random colour in the list.
        columns = set()    # Keep track of which columns have been drawn in.

        for method_name in railroad_data:
            col += 1
            if railroad_data[method_name]['is_mega']:
                line_style = Qt.SolidLine
            else:
                line_style = Qt.DashLine
            if self.tm.tool_data_is_dirty:
                colour = self._random_colours_outdated[col]
            else:
                colour = self._random_colours[col]
            pen = QPen(colour, LINE_WIDTH, line_style)

            qlines[pen] = list()
            method = railroad_data[method_name]
            max_x = method['max_x']
            while max_x in columns:  # Separate out overlapping vertical lines.
                max_x += 4
            columns.add(max_x)
            def_line = QLine((gfont.fontwt * method['definition'][1]) + SPACING,
                             (gfont.fontht * method['definition'][0]) + VOFFSET,
                             get_rhs_of_hline(max_x),
                             (gfont.fontht * method['definition'][0]) + VOFFSET)
            qlines[pen].append(def_line)
            last_line = -1
            for call in railroad_data[method_name]['calls']:
                c_line = QLine((gfont.fontwt * call[1]) + SPACING,
                               (gfont.fontht * call[0]) + VOFFSET,
                               get_rhs_of_hline(max_x),
                               (gfont.fontht * call[0]) + VOFFSET)
                qlines[pen].append(c_line)
                if (gfont.fontht * call[0]) + VOFFSET > last_line:
                    last_line = (gfont.fontht * call[0]) + VOFFSET
            # Vertical line.
            v_line = QLine(get_rhs_of_hline(max_x),
                           (gfont.fontht * method['definition'][0]) + VOFFSET,
                           get_rhs_of_hline(max_x),
                           last_line)
            qlines[pen].append(v_line)

        # Draw lines.
        for pen in qlines:
            painter.setPen(pen)
            for qline in qlines[pen]:
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
