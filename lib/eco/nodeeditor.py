# Copyright (c) 2012--2014 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

BODY_FONT = "Monospace"
BODY_FONT_SIZE = 9

from treemanager import TreeManager
from grammars.grammars import submenu_langs as languages, lang_dict
from grammar_parser.gparser import MagicTerminal, IndentationTerminal
from grammar_parser.bootstrap import ListNode, AstNode
from incparser.astree import BOS, EOS
from jsonmanager import JsonManager
from utils import KeyPress
from overlay import Overlay
from incparser.annotation import Eval, Footnote, Heatmap, Railroad, ToolTip, Types
from incparser.astree import TextNode

import syntaxhighlighter
import editor

import logging

whitelist = set(u"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!\"$%^&*()_-+=;:'@#~[]{},.<>/?|\\`\r ")

def debug_trace():
  '''Set a tracepoint in the Python debugger that works with Qt'''
  from PyQt4.QtCore import pyqtRemoveInputHook

  # Or for Qt5
  #from PyQt5.QtCore import pyqtRemoveInputHook

  from pdb import set_trace
  pyqtRemoveInputHook()
  set_trace()


class NodeEditor(QFrame):

    # ========================== init stuff ========================== #

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.viewport_y = 0 # top visible line
        self.imagemode = False
        self.image = None

        self.scroll_height = 0
        self.scroll_width = 0

        self.timer = QTimer(self)
        self.backuptimer = QTimer(self)
        self.connect(self.timer, SIGNAL("timeout()"), self.analysis_timer)
        self.connect(self.backuptimer, SIGNAL("timeout()"), self.backup_timer)
        self.backuptimer.start(30000)
        self.undotimer = QTimer(self)
        self.connect(self.undotimer, SIGNAL("timeout()"), self.trigger_undotimer)

        self.blinktimer = QTimer(self)
        self.blinktimer.start(500)
        self.connect(self.blinktimer, SIGNAL("timeout()"), self.trigger_blinktimer)
        self.show_cursor = True

        self.boxcolors = [QColor("#DC322F"), QColor("#268BD2"), QColor("#2Ac598"), QColor("#D33682"), QColor("#B58900"), QColor("#859900")]
        self.setCursor(Qt.IBeamCursor)

        # Semi-transparent overlay.
        # Used to display heat-map visualisation of profiler info, etc.
        self.overlay = Overlay(self)
        # Start hidden, make (in)visible with self.toggle_overlay().
        self.overlay.hide()

        # Set to True if the user wants to see tool visualisations.
        self.show_tool_visualisations = True

        # Set True if Eco should be running profiler and other tools,
        # continuously in the background.
        self.run_background_tools = False

        # Show / don't show HUD visualisations.
        self.hud_callgraph = False
        self.hud_eval = False
        self.hud_heat_map = False
        self.hud_types = False

    def hud_show_callgraph(self):
        self.hud_callgraph = True
        self.hud_eval = False
        self.hud_heat_map = False
        self.hud_types = False

    def hud_show_eval(self):
        self.hud_callgraph = False
        self.hud_eval = True
        self.hud_heat_map = False
        self.hud_types = False

    def hud_show_types(self):
        self.hud_callgraph = False
        self.hud_eval = False
        self.hud_heat_map = False
        self.hud_types = True

    def hud_show_heat_map(self):
        self.hud_callgraph = False
        self.hud_eval = False
        self.hud_heat_map = True
        self.hud_types = False

    def hud_off(self):
        self.hud_callgraph = False
        self.hud_eval = False
        self.hud_heat_map = False
        self.hud_types = False

    def focusOutEvent(self, event):
        self.blinktimer.stop()
        self.show_cursor = True
        self.update()

    def focusInEvent(self, event):
        self.blinktimer.start()

    def toggle_overlay(self):
        self.hide_overlay() if self.overlay.isVisible() else self.show_overlay()

    def show_overlay(self):
        self.overlay.show()

    def hide_overlay(self):
        self.overlay.hide()

    def is_overlay_visible(self):
        return self.overlay.isVisible()

    def resizeEvent(self, event):
        self.overlay.resize(event.size())
        event.accept()

    def analysis_timer(self):
        if self.getWindow().show_namebinding():
            self.tm.analyse()
            self.update()
        self.timer.stop()

        # save swap
        filename = self.getEditorTab().filename
        if filename:
            self.saveToJson(filename + ".swp", True)

    def backup_timer(self):
        filename = self.getEditorTab().filename
        if filename:
            self.saveToJson(filename + ".bak", True)

    def trigger_blinktimer(self):
        if self.timer.isActive():
            self.show_cursor = True
            return
        self.show_cursor ^= True
        self.update()

    def trigger_undotimer(self):
        self.tm.undo_snapshot()
        self.undotimer.stop()

    def setImageMode(self, boolean):
        self.imagemode = boolean

    def reset(self):
        self.update()

    def set_mainlanguage(self, parser, lexer, lang_name):
        self.tm = TreeManager()
        self.tm.add_parser(parser, lexer, lang_name)

    def get_mainlanguage(self):
        return self.tm.parsers[0][2]

    def set_sublanguage(self, language):
        self.sublanguage = language

    def event(self, event):
        if event.type() == QEvent.ToolTip:
            pos = event.pos()
            temp_cursor = self.tm.cursor.copy()
            result = self.coordinate_to_cursor(pos.x(), pos.y())
            node = self.tm.cursor.node
            self.tm.cursor.line = temp_cursor.line
            self.tm.cursor.node = temp_cursor.node
            self.tm.cursor.pos = temp_cursor.pos
            if not result:
                QToolTip.hideText()
                event.ignore()
                return True
            # Draw errors, if there are any.
            msg = self.tm.get_error(node)
            if msg:
                QToolTip.showText(event.globalPos(), msg)
                return True
            # Draw annotations if there are any.
            elif self.show_tool_visualisations:
                annotes = [annote.annotation for annote in node.get_annotations_with_hint(ToolTip)]
                msg = "\n".join(annotes)
                if msg.strip() != "":
                    if self.tm.tool_data_is_dirty:
                        msg += "\n[Warning: Information may be out of date.]"
                    QToolTip.showText(event.globalPos(), msg)
                    return True
            QToolTip.hideText()
            event.ignore()
            return True
        return QFrame.event(self, event)

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def sliderChanged(self, value):
        self.viewport_y = value
        self.overlay.start_line = self.viewport_y
        self.update()

    def sliderXChanged(self, value):
        self.move(-value*self.fontwt,0)
        self.resize(self.parentWidget().geometry().width() + value*self.fontwt, self.geometry().height())
        if self.x() == 0:
            self.updateGeometry()
        self.update()

    def getScrollSizes(self):
        total_lines = 0
        max_width = 0
        for l in self.lines:
            total_lines += l.height
            max_width = max(max_width, l.width)
        max_visible_lines = self.geometry().height() / self.fontht
        self.scroll_height = max(0, total_lines - max_visible_lines)

        current_width = self.parentWidget().geometry().width() / self.fontwt
        self.scroll_width = max(0, max_width - current_width)

    def paintEvent(self, event):
        # Clear data in the visualisation overlay
        self.overlay.clear_data()

        gfont = QApplication.instance().gfont
        self.font = gfont.font
        self.fontwt = gfont.fontwt
        self.fontht = gfont.fontht
        self.fontd  = gfont.fontd
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        if self.imagemode:
            self.image = QImage()
            paint.begin(self.image)
        else:
            paint.begin(self)
        paint.setFont(self.font)

        self.longest_column = 0

        # calculate how many lines we need to show
        self.init_height = self.geometry().height()

        self.paintLines(paint, self.viewport_y)

        paint.end()

        total_lines = 0
        max_width = 0
        for l in self.lines:
            total_lines += l.height
            max_width = max(max_width, l.width)
        max_visible_lines = self.geometry().height() / self.fontht
        self.scroll_height = max(0, total_lines - max_visible_lines)

        current_width = self.parentWidget().geometry().width() / self.fontwt
        self.scroll_width = max(0, max_width - current_width)

        railroad_annotations = self.tm.get_all_annotations_with_hint(Railroad)
        self.overlay.add_railroad_data(railroad_annotations)

        self.emit(SIGNAL("painted()"))

    # paint lines using new line manager
    def paintLines(self, paint, startline):

        # find internal line corresponding to visual line
        visual_line = 0
        internal_line = 0
        for l in self.tm.lines:
            if visual_line + l.height > startline:
                break
            visual_line += l.height
            internal_line += 1

        x = 0
        y = visual_line - startline # start drawing outside of viewport to display partial images
        self.paint_start = (internal_line, y)

        max_y = self.geometry().height() / self.fontht

        line = internal_line
        node = self.tm.lines[line].node

        _, _, self.end_line = self.paint_nodes(paint, node, x, y, line, max_y)


    #XXX if starting node is inside language box, init lbox with amount of language boxes

    def new_paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):
        from nodepainter import NodePainter
        np = NodePainter(paint, node, x, y, line, max_y, lbox)
        np.cursor = self.tm.cursor
        np.repaint()
        self.lines = self.tm.lines
        self.cursor = self.tm.cursor
        return np.x, np.y, np.line

    def paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):

        settings = QSettings("softdev", "Eco")
        colors = self.boxcolors
        if settings.value("app_theme", "Light").toString() in ["Dark"]:
            alpha = 100
            self.highlight_line_color = QColor(250,250,250,20)
        elif settings.value("app_theme", "Light").toString() in ["Gruvbox"]:
            alpha = 100
            self.highlight_line_color = QColor(250,250,250,20)
        else:
            alpha = 60
            self.highlight_line_color = QColor(0,0,0,10)
        self.show_highlight_line = settings.value("highlight_line", False).toBool()

        first_node = node
        selected_language = self.tm.mainroot
        error_node = self.tm.get_mainparser().error_node
        error_node = self.fix_errornode(error_node)

        highlighter = self.get_highlighter(node)
        selection_start = min(self.tm.selection_start, self.tm.selection_end)
        selection_end = max(self.tm.selection_start, self.tm.selection_end)
        draw_selection_start = (0,0,0)
        draw_selection_end = (0,0,0)
        start_lbox = self.get_languagebox(node)
        editor = self.get_editor(node)

        self.selected_lbox = self.tm.get_languagebox(self.tm.cursor.node)
        #XXX get initial x for langbox

        if start_lbox:
            lbox += 1
        if start_lbox and self.selected_lbox is start_lbox:
            draw_lbox = True
        else:
            draw_lbox = False

        draw_all_boxes = self.getWindow().show_languageboxes()

        self.lines = self.tm.lines
        self.cursor = self.tm.cursor
        self.lines[line].height = 1 # reset height
        draw_cursor = True
        show_namebinding = self.getWindow().show_namebinding()
        while y < max_y:

            # if we found a language box, continue drawing inside of it
            if isinstance(node.symbol, MagicTerminal):
                lbox += 1
                lbnode = node.symbol.ast
                if self.selected_lbox is node:
                    color = colors[(lbox-1) % len(colors)]
                    self.draw_lbox_bracket(paint, '[', node, x, y, color)
                    draw_lbox = True
                    selected_language = lbnode
                else:
                    draw_lbox = False
                node = lbnode.children[0]
                highlighter = self.get_highlighter(node)
                editor = self.get_editor(node)
                error_node = self.tm.get_parser(lbnode).error_node
                error_node = self.fix_errornode(error_node)
                continue

            if isinstance(node, EOS):
                lbnode = self.get_languagebox(node)
                if self.cursor.node is lbnode:
                    self.draw_cursor(paint, x, 4 + y * self.fontht)
                if lbnode:
                    color = colors[(lbox-1) % len(colors)]
                    if lbox > 0:
                        lbox -= 1
                    node = lbnode.next_term
                    highlighter = self.get_highlighter(node)
                    editor = self.get_editor(node)
                    if self.selected_lbox is lbnode:
                        # draw bracket
                        self.draw_lbox_bracket(paint, ']', node, x, y, color)
                        draw_lbox = False
                    lbnode = self.get_languagebox(node)
                    if lbnode and self.selected_lbox is lbnode:
                        draw_lbox = True
                        error_node = self.tm.get_parser(lbnode.symbol.ast).error_node
                        error_node = self.fix_errornode(error_node)
                    else:
                        error_node = self.tm.get_mainparser().error_node
                        error_node = self.fix_errornode(error_node)
                    continue
                else:
                    self.lines[line].width = x / self.fontwt
                    break

            if isinstance(node.symbol.name, list):
                node = node.symbol.name[0]
                continue

            # draw language boxes
            if lbox > 0 and (draw_lbox or draw_all_boxes):
                if draw_all_boxes:
                    color = colors[(lbox-1) % len(colors)]
                    color.setAlpha(alpha)
                else:
                    color = colors[0]
                    color.setAlpha(alpha)
                if draw_lbox and draw_all_boxes: # we are drawing the currently selected language box
                    color.setAlpha(20)
                editor.update_image(node)
                if node.symbol.name != "\r" and not isinstance(node.symbol, IndentationTerminal):
                    if not node.image or node.plain_mode:
                        if isinstance(node, BOS) and isinstance(node.next_term, EOS):
                            self.draw_lbox_hints(paint, node, x, y, color)
                        else:
                            paint.fillRect(QRectF(x,3 + y*self.fontht, len(node.symbol.name)*self.fontwt, self.fontht), color)

            # prepare selection drawing
            if node is selection_start.node:
                if node.lookup == "<return>":
                    sel_x = x
                else:
                    sel_x = x + selection_start.pos * self.fontwt
                draw_selection_start = (sel_x, y, line)

            if node is selection_end.node:
                draw_selection_end = (x + selection_end.pos * self.fontwt, y, line)


            # draw node
            dx, dy = editor.paint_node(paint, node, x, y, highlighter)
            x += dx
            self.lines[line].height = max(self.lines[line].height, dy)

            # Draw footnotes and add heatmap data to overlay.
            annotes = [annote.annotation for annote in node.get_annotations_with_hint(Heatmap)]
            for annote in annotes:
                self.overlay.add_heatmap_datum(line + 1, annote)
            if self.show_tool_visualisations:
                # Draw footnotes.
                infofont = QApplication.instance().tool_info_font
                annotes = []
                annotes_ = node.get_annotations_with_hint(Footnote)
                if self.hud_eval:
                    for annote in annotes_:
                        if annote.has_hint(Eval):
                            annotes.append(annote)
                elif self.hud_types:
                    for annote in annotes_:
                        if annote.has_hint(Types):
                            annotes.append(annote)
                footnote = " ".join([annote.annotation for annote in annotes])
                if footnote.strip() != "":
                    if not self.tm.tool_data_is_dirty:
                        infofont.font.setBold(True)
                    else:
                        infofont.font.setBold(False)
                    paint.setFont(infofont.font)
                    paint.setPen(QPen(QColor((highlighter.get_default_color()))))
                    start_y = self.fontht + ((y + 1) * self.fontht)
                    paint.drawText(QtCore.QPointF(x-dx, start_y), footnote)
                    self.lines[line].height = max(self.lines[line].height, 2)
                    paint.setFont(self.font)

            # after we drew a return, update line information
            if (node.lookup == "<return>" or node.symbol.name == "\r") and not node is first_node:
                # draw lbox to end of line
                if draw_lbox or (draw_all_boxes and lbox > 0):
                    paint.fillRect(QRectF(x,3+y*self.fontht, self.geometry().width()-x, self.fontht), color)

                self.lines[line].width = x / self.fontwt
                x = 0
                y += self.lines[line].height
                line += 1
                self.lines[line].height = 1 # reset height

            if self.show_highlight_line:
                if node.lookup == "<return>" or isinstance(node, BOS):
                    if self.cursor.line == line:
                        self.highlight_line(paint, y)

            # draw cursor
            if node is self.cursor.node and self.show_cursor:
                draw_x = max(0, x-dx)
                cursor_pos = self.cursor.pos

                if node.symbol.name == "\r":
                    cursor_pos = 0
                if node.image and not node.plain_mode:
                    draw_x = x
                    cursor_pos = 0
                self.draw_cursor(paint, draw_x + cursor_pos * self.fontwt, 4 + y * self.fontht)


            if False and line == self.cursor.y and x/self.fontwt >= self.cursor.x and draw_cursor:
                draw_cursor_at = QRect(0 + self.cursor.x * self.fontwt, 5 + y * self.fontht, 0, self.fontht - 3)
                paint.drawRect(draw_cursor_at)

                # set lbox info coordinates
                infobox_coordinates = (self.cursor.x * self.fontwt, (y+1) * self.fontht)
                draw_cursor = False

            # draw squiggly line
            if node is error_node or (show_namebinding and self.tm.has_error(node)):
                if isinstance(node, EOS):
                    length = self.fontwt
                else:
                    length = len(node.symbol.name)*self.fontwt
                if isinstance(node.symbol, MagicTerminal):
                    self.draw_vertical_squiggly_line(paint,x,y)
                else:
                    if self.tm.has_error(node):
                        err_color = "orange"
                    else:
                        err_color = "red"
                    self.draw_squiggly_line(paint,x-length,y,length, err_color)

            node = node.next_terminal()

        if selection_start != selection_end:
            self.draw_selection(paint, draw_selection_start, draw_selection_end, max_y)

        # paint infobox
        if False:
            lang_name = self.tm.parsers[selected_language]
            lang_status = self.tm.get_parser[selected_language][0].last_status
            if lang_status is True:
                color = QColor(100,255,100)
            else:
                color = QColor(255,100,100)
            paint.setFont(infofont)
            paint.fillRect(QRect(infobox_coordinates[0], 5 + infobox_coordinates[1], len(lang_name)*infofontwt, infofontht), color)
            paint.drawText(QtCore.QPointF(infobox_coordinates[0], -3 + self.fontht + infobox_coordinates[1]), lang_name)
            paint.setFont(self.font)

        return x, y, line

    def highlight_line(self, paint, y):
        width = self.parentWidget().geometry().width()
        paint.fillRect(QRect(-5, y * self.fontht + 3, width, self.fontht), self.highlight_line_color)

    def draw_lbox_hints(self, paint, node, x, y, color):
        if node is self.cursor.node:
            return
        alpha = color.alpha()
        color.setAlpha(255)
        path = QPainterPath()
        x = x - 2
        y = y*self.fontht + 4

        path.moveTo(x, y)
        path.lineTo(x+6, y)
        path.lineTo(x+3, y+3)
        path.lineTo(x, y)

        paint.fillPath (path, QBrush (color));
        color.setAlpha(alpha)

    def draw_lbox_bracket(self, paint, bracket, node, x, y, color):
        assert bracket in ['[',']']
        oldpen = paint.pen()
        newpen = QPen()
        color.setAlpha(255)
        newpen.setColor(color)
        newpen.setWidth(1)
        paint.setPen(newpen)

        # paint brackets
        path = QPainterPath()
        if bracket == '[':
            if x == 0:
                tmpx = x + 2
            else:
                tmpx = x + 1 # adjust bracket position
            path.moveTo(tmpx,   3+y*self.fontht)
            path.lineTo(tmpx-2, 3+y*self.fontht)
            path.moveTo(tmpx-2, 3+y*self.fontht)
            path.lineTo(tmpx-2, 3+y*self.fontht + self.fontht - 1)
        else:
            tmpx = x - 1
            path.moveTo(tmpx,   3+y*self.fontht)
            path.lineTo(tmpx+2, 3+y*self.fontht)
            path.moveTo(tmpx+2, 3+y*self.fontht)
            path.lineTo(tmpx+2, 3+y*self.fontht + self.fontht - 1)
        path.lineTo(tmpx, 3+y*self.fontht + self.fontht - 1)
        paint.drawPath(path)

        paint.setPen(oldpen)

    def fix_errornode(self, error_node):
        if not error_node:
            return
        while isinstance(error_node.symbol, IndentationTerminal):
            error_node = error_node.next_term
        return error_node

    def draw_cursor(self, paint, x, y):
        pen = paint.pen()
        colorhex = self.palette().color(QPalette.Text)
        pen.setColor(QColor(colorhex))
        paint.setPen(pen)
        draw_cursor_at = QRect(x, y, 0, self.fontht - 3)
        paint.drawRect(draw_cursor_at)

    def draw_vertical_squiggly_line(self, paint, x, y):
        paint.setPen(Qt.CustomDashLine)
        pen = paint.pen()
        pen.setDashPattern([2,2])
        pen.setColor(QColor("red"))
        paint.setPen(pen)
        y = 3+y*self.fontht
        paint.drawLine(x-1, y, x-1, y+self.fontht)
        paint.drawLine(x, y+2, x, y+self.fontht)
        paint.setPen(Qt.SolidLine)

    def draw_squiggly_line(self, paint, x, y, length, color):
        paint.setPen(Qt.CustomDashLine)
        pen = paint.pen()
        pen.setDashPattern([2,2])
        pen.setColor(QColor(color))
        paint.setPen(pen)
        y = (y+1)*self.fontht+1
        paint.drawLine(x, y, x+length, y)
        paint.drawLine(x+2, y+1, x+2+length, y+1)
        paint.setPen(Qt.SolidLine)

    def draw_selection(self, paint, draw_selection_start, draw_selection_end, max_y):
        x1, y1, line1 = draw_selection_start
        x2, y2, line2 = draw_selection_end
        start = min(self.tm.selection_start, self.tm.selection_end)
        end = max(self.tm.selection_start, self.tm.selection_end)
        if x1 + y1 + line1 + x2 + y2 + line2 == 0:
            # everything out of viewport, draw nothing
            # unless start and end are on opposite sides of the viewport
            if not(start.line <= self.paint_start[0] and end.line >= self.paint_start[0] + max_y):
                    return
        if x1 + y1 + line1 == 0:
            # start outside of viewport
            line1 = self.paint_start[0]
        if x2 + y2 + line2 == 0:
            # end outside of viewport
            line2 = self.paint_start[0] + max_y
            y2 = max_y
        if y1 == y2:
            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, x2-x1, self.fontht), QColor(0,0,255,100))
        else:
            width = max(self.fontwt, self.tm.lines[line1].width*self.fontwt)
            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, width - x1, self.fontht), QColor(0,0,255,100))
            y = y1 + self.tm.lines[line1].height
            for i in range(line1+1, line2):
                width = self.tm.lines[i].width*self.fontwt
                if width == 0:
                    width = self.fontwt
                paint.fillRect(QRectF(0, 3 + y * self.fontht, width, self.fontht), QColor(0,0,255,100))
                y = y + self.tm.lines[i].height
            paint.fillRect(QRectF(0, 3 + y2 * self.fontht, x2, self.fontht), QColor(0,0,255,100))

    def get_highlighter(self, node):
        root = node.get_root()
        base = lang_dict[self.tm.get_language(root)].base
        s = syntaxhighlighter.get_highlighter(base, self.palette())
        return s

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

    def get_editor(self, node):
        root = node.get_root()
        base = lang_dict[self.tm.get_language(root)].base
        return editor.get_editor(base, self.fontwt, self.fontht, self.fontd)

    def focusNextPrevChild(self, b):
        # don't switch to next widget on TAB
        return False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.tm.input_log.append("# mousePressEvent")
            self.coordinate_to_cursor(e.x(), e.y())
            self.tm.selection_start = self.tm.cursor.copy()
            self.tm.selection_end = self.tm.cursor.copy()
            self.tm.input_log.append("self.selection_start = self.cursor.copy()")
            self.tm.input_log.append("self.selection_end = self.cursor.copy()")
            self.getWindow().showLookahead()
            self.update()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.coordinate_to_cursor(e.x(), e.y())
            node = self.tm.get_node_from_cursor()
            lbox = self.get_languagebox(node)
            if lbox and lbox.symbol.name == "<IPython>":
                if lbox.plain_mode is False:
                    lbox.plain_mode = True
                else:
                    lbox.plain_mode = False
                self.update()
                return
            elif node.image is None:
                self.tm.doubleclick_select()
                self.update()
                return

            if node.plain_mode is False:
                node.plain_mode = True
                self.tm.cursor.pos = len(node.symbol.name)
            else:
                node.plain_mode = False
            self.update()

    def cursor_to_coordinate(self):
        y = 0
        for l in self.tm.lines[:self.cursor.line]:
            y += l.height * self.fontht
        x = self.tm.cursor.get_x() * self.fontwt
        y = y - self.getScrollArea().verticalScrollBar().value() * self.fontht
        return (x,y)

    def coordinate_to_cursor(self, x, y):
        mouse_y = y / self.fontht
        first_line = self.paint_start[0]
        y_offset = self.paint_start[1]

        y = y_offset
        line = first_line
        if mouse_y < 0:
            while line > 0:
                y -= self.tm.lines[line].height
                if y < mouse_y:
                    break
                line -= 1
        else:
            while line < len(self.tm.lines) - 1:
                y += self.tm.lines[line].height
                if y > mouse_y:
                    break
                line += 1

        self.tm.cursor.line = line
        cursor_x = int(round(float(x) / self.fontwt))
        self.tm.cursor.move_to_x(cursor_x)

        self.tm.input_log.append("self.cursor.line = %s" % str(line))
        self.tm.log_input("cursor.move_to_x", str(cursor_x))

        if mouse_y > y or self.tm.cursor.get_x() != cursor_x:
            return False
        return True

    def mouseMoveEvent(self, e):
        # apparently this is only called when a mouse button is clicked while
        # the mouse is moving
        if self.tm.input_log[-2].startswith("self.cursor.move_to_x"):
            # only log the last move event
            self.tm.input_log.pop()
            self.tm.input_log.pop()
            self.tm.input_log.pop()
        self.coordinate_to_cursor(e.x(), e.y())
        self.tm.selection_end = self.tm.cursor.copy()
        self.tm.input_log.append("self.selection_end = self.cursor.copy()")
        self.update()
        self.getEditorTab().keypress()

    def keyPressEvent(self, e):
        self.timer.start(500)
        self.show_cursor = True

        startundotimer = False
        key = KeyPress(e)

        # key presses to ignore
        if key.is_modifier or key.page_up or key.page_down:
            return

        # has been processes in get_nodes_at_pos -> reset
        self.edit_rightnode = False

        if key.escape:
            self.tm.key_escape()
        elif key.backspace:
            startundotimer = True
            self.tm.key_backspace()
        elif key.home:
            self.tm.key_home(shift=key.m_shift)
        elif key.end:
            self.tm.key_end(shift=key.m_shift)
        elif key.is_arrow:
            if key.jump_word:
                self.tm.ctrl_cursor(key, shift=key.m_shift)
            else:
                self.tm.key_cursors(key, shift=key.m_shift)
        elif key.delete:
            startundotimer = True
            self.tm.key_delete()
        elif e.key() == Qt.Key_F3:
            self.tm.find_next()
        # User pressed Ctrl- Or Alt- (etc.) i.e. a character we can't
        # sensibly insert into the text.
        elif key.has_action_modifier:
            pass
        # every other normal key press
        else:
            startundotimer = True
            if e.key() == Qt.Key_Tab:
                text = "    "
            else:
                # text is a char array, so we need the first letter
                # to match it against the set
                text = e.text()
                if text.isEmpty() or text.toUtf8()[0] not in whitelist:
                    logging.debug("Key %s not supported" % text)
                    return
            self.tm.key_normal(text)

        self.getWindow().btReparse([])
        self.update()
        self.emit(SIGNAL("keypress(QKeyEvent)"), e)
        self.getWindow().showLookahead()

        if startundotimer:
            self.undotimer.start(500)

    def showLanguageBoxMenu(self):
        self.showSubgrammarMenu()
        self.create_languagebox()

    def create_languagebox(self):
        if self.sublanguage:
            if self.tm.hasSelection():
                self.tm.surround_with_languagebox(self.sublanguage)
            else:
                self.tm.add_languagebox(self.sublanguage)

    def change_languagebox(self):
        if self.sublanguage:
            self.tm.change_languagebox(self.sublanguage)

    def showCodeCompletion(self):
        l = self.tm.getCompletion()
        if l:
            self.showCodeCompletionMenu(l)

    def println(self, prestring, y):
        node = self.lines[y].node.next_term
        x = []
        while node is not None and node.symbol.name != "\r":
            x.append(node.symbol.name)
            node = node.next_term
        print(prestring, "".join(x))

    def print_line(self, y):
        current = self.lines[y].node
        while True:
            print(current)
            current = current.next_term
            if current is None:
                return

    # ========================== AST modification stuff ========================== #

    def insertTextNoSim(self, text):
        self.viewport_y = 0
        self.tm.import_file(text)
        return

    def getTL(self):
        return self.getWindow().tl

    def getPL(self):
        return self.getWindow().pl

    def getLRP(self):
        return self.getWindow().lrp

    def getWindow(self):
        return self.window()

    def getEditorTab(self):
        return self.parent().parent().parent()

    def getScrollArea(self):
        return self.parent().parent()

    def createSubgrammarMenu(self, menu, change=False):
        self.sublanguage = None

        tmp = None
        if change:
            # try and find lbox and set cursor to previous node before getting
            # lookahead list
            root = self.tm.cursor.node.get_root()
            lbox = root.get_magicterminal()
            if lbox:
                tmp = self.tm.cursor.node
                self.tm.cursor.node = lbox.prev_term

        # Create actions
        bf = QFont()
        bf.setBold(True)
        valid_langs = []
        for l in languages:
            if "<%s>" % l in self.tm.getLookaheadList():
                valid_langs.append(l)

        if tmp:
            # undo cursor change
            self.tm.cursor.node = tmp
        if len(valid_langs) > 0:
            for l in valid_langs:
                item = QAction(str(l), menu)
                item.setData(l)
                self._set_icon(item, l)
                item.setFont(bf)
                menu.addAction(item)
            menu.addSeparator()
        for l in languages:
            item = QAction(str(l), menu)
            item.setData(l)
            self._set_icon(item, l)
            menu.addAction(item)
        return menu

    def showSubgrammarMenu(self):
        menu = QtGui.QMenu("Language", self)
        self.createSubgrammarMenu(menu)
        x,y = self.cursor_to_coordinate()
        action = menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + x, y + self.fontht))
        if action:
            self.sublanguage = action.data().toPyObject()
            self.edit_rightnode = True

    def _set_icon(self, mitem, lang):
        if lang.base.lower() == "html":
            icon = QIcon.fromTheme("text-xhtml+xml")
        else:
            icon = QIcon.fromTheme("text-x-" + lang.base.lower())
        if icon.isNull():
            icon = QIcon.fromTheme("application-x-" + lang.base.lower())
            if icon.isNull():
                icon = QIcon.fromTheme("text-x-generic")
        mitem.setIcon(icon)

    def showCodeCompletionMenu(self, l):
        menu = QtGui.QMenu( self )
        # Create actions
        toolbar = QtGui.QToolBar()
        for n in l:
            path = []
            for p in n.path:
                if p and p.name:
                    path.append(p.name)
            if n.vartype:
                vartype = n.vartype
                while vartype.children != []:
                    try:
                        vartype = vartype.children[0]
                    except KeyError:
                        vartype = vartype.children["name"]
                text = "%s : %s - %s (%s)" % (n.name, vartype.symbol.name, ".".join(path), n.kind)
            elif n.kind == "method":
                text = self.cc_method(n) + " - %s" % (".".join(path))
            else:
                text = "%s - %s (%s)" % (n.name, ".".join(path), n.kind)
            item = toolbar.addAction(text, self.createCCFunc(n.name))
            item.setIcon(QIcon("gui/" + n.kind + ".png"))
            menu.addAction(item)
        x,y = self.cursor_to_coordinate()
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + x, y + self.fontht))

    def cc_method(self, n):
        s = [n.name, "("]
        param_ln = n.astnode.children["params"]
        if isinstance(param_ln, ListNode):
            for p in param_ln.children:
                tmp = p.children["type"]
                if isinstance(tmp, AstNode):
                    s.append(tmp.children["name"].symbol.name)
                else:
                    s.append(tmp.symbol.name)
                s.append(" ")
                s.append(p.children["name"].symbol.name)
                if p != param_ln.children[-1]:
                    s.append(", ")
        s.append(")")
        return "".join(s)

    def createMenuFunction(self, l):
        def action():
            self.sublanguage = l
            self.edit_rightnode = True
        return action

    def createCCFunc(self, text):
        def action():
            self.tm.pasteCompletion(text)
        return action

    def selectSubgrammar(self, item):
        pass

    def saveToJson(self, filename, swap=False):
        whitespaces = self.tm.get_mainparser().whitespaces
        root = self.tm.parsers[0][0].previous_version.parent
        language = self.tm.parsers[0][2]
        manager = JsonManager()
        manager.save(root, language, whitespaces, filename)
        if not swap:
            self.tm.changed = False
            self.emit(SIGNAL("painted()"))

    def loadFromJson(self, filename):
        manager = JsonManager()
        language_boxes = manager.load(filename)

        self.tm = TreeManager()

        self.tm.load_file(language_boxes)
        self.reset()

    def export(self, run=False, profile=False, source=None, debug=False):
        return self.tm.export(None, run, profile, source=source, debug=debug)
