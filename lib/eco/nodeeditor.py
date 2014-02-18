from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

BODY_FONT = "Courier"
BODY_FONT_SIZE = 9

from treemanager import TreeManager, Cursor
from grammars.grammars import languages, lang_dict
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from jsonmanager import JsonManager

import syntaxhighlighter
import editor

class NodeEditor(QFrame):

    # ========================== init stuff ========================== #

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.defaultFont = self.font()
        self.boldDefaultFont = QFont(self.defaultFont)
        self.boldDefaultFont.setBold(True)

        self.font = QtGui.QFont(BODY_FONT, BODY_FONT_SIZE)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

        self.infofont = QtGui.QFont('Courier', 6)
        self.infofontht = QtGui.QFontMetrics(self.infofont).height() + 3
        self.infofontwt = QtGui.QFontMetrics(self.infofont).width(" ")

        self.viewport_y = 0 # top visible line
        self.imagemode = False
        self.image = None

    def setImageMode(self, boolean):
        self.imagemode = boolean

    def set_treemanager(self, tm):
        self.tm = tm

    def reset(self):
        self.getWindow().ui.scrollArea.horizontalScrollBar().setValue(0)
        self.getWindow().ui.scrollArea.verticalScrollBar().setValue(0)
        self.update()

    def set_mainlanguage(self, parser, lexer, lang_name):
        self.tm = TreeManager()
        self.tm.add_parser(parser, lexer, lang_name)
        self.tm.set_font(self.fontm)

    def set_sublanguage(self, language):
        self.sublanguage = language

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def sliderChanged(self, value):
        change = self.viewport_y - value
        self.viewport_y = value
        self.update()

    def sliderXChanged(self, value):
        self.move(-value*self.fontwt,0)
        self.resize(self.parentWidget().geometry().width() + value*self.fontwt, self.geometry().height())
        self.update()

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        if self.imagemode:
            self.image = QImage()
            paint.begin(self.image)
        else:
            paint.begin(self)
        paint.setFont(self.font)

        y = 0
        x = 0

        self.longest_column = 0

        # calculate how many lines we need to show
        self.init_height = self.geometry().height()

        self.paintLines(paint, self.viewport_y)

        paint.end()

        self.getWindow().ui.scrollArea.verticalScrollBar().setMinimum(0)
        total_lines = 0
        max_width = 0
        for l in self.lines:
            total_lines += l.height
            max_width = max(max_width, l.width)
        max_visible_lines = self.geometry().height() / self.fontht
        vmax = max(0, total_lines - max_visible_lines)
        self.getWindow().ui.scrollArea.verticalScrollBar().setMaximum(vmax)
        self.getWindow().ui.scrollArea.verticalScrollBar().setPageStep(1)

        current_width = self.parentWidget().geometry().width() / self.fontwt
        hmax = max(0, max_width - current_width)
        self.getWindow().ui.scrollArea.horizontalScrollBar().setMaximum(hmax)
        self.getWindow().ui.scrollArea.horizontalScrollBar().setPageStep(1)

        self.getWindow().ui.fLinenumbers.setMinimumWidth(self.fontm.width("000: "))
        self.getWindow().ui.fLinenumbers.setMaximumWidth(self.fontm.width("000: "))

        self.getWindow().ui.fLinenumbers.update()


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

        self.paint_nodes(paint, node, x, y, line, max_y)


    #XXX if starting node is inside language box, init lbox with amout of languge boxes
    def paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):
        first_node = node
        selected_language = self.tm.mainroot
        error_node = self.tm.get_mainparser().error_node

        highlighter = self.get_highlighter(node)
        selection_start = min(self.tm.selection_start, self.tm.selection_end)
        selection_end = max(self.tm.selection_start, self.tm.selection_end)
        draw_selection_start = (0,0,0)
        draw_selection_end = (0,0,0)
        start_lbox = self.get_languagebox(node)
        editor = self.get_editor(node)

        self.selected_lbox = self.tm.get_languagebox(self.tm.cursor.node)

        if start_lbox and self.selected_lbox is start_lbox:
            lbox += 1
            draw_lbox = True
        else:
            draw_lbox = False
        self.lines = self.tm.lines
        self.cursor = self.tm.cursor
        self.lines[line].height = 1 # reset height
        draw_cursor = True
        while y < max_y:

            # if we found a language box, continue drawing inside of it
            if isinstance(node.symbol, MagicTerminal):
                lbox += 1
                lbnode = node.symbol.ast
                if self.selected_lbox is node:
                    draw_lbox = True
                    selected_language = lbnode
                else:
                    draw_lbox = False
                node = lbnode.children[0]
                highlighter = self.get_highlighter(node)
                editor = self.get_editor(node)
                error_node = self.tm.get_parser(lbnode).error_node
                continue

            if isinstance(node, EOS):
                lbnode = self.get_languagebox(node)
                if self.cursor.node is lbnode:
                    self.draw_cursor(paint, x, 5 + y * self.fontht)
                if lbnode:
                    lbox -= 1
                    node = lbnode.next_term
                    highlighter = self.get_highlighter(node)
                    editor = self.get_editor(node)
                    error_node = self.tm.get_parser(lbnode.symbol.ast).error_node
                    if self.selected_lbox is lbnode:
                        draw_lbox = False
                    lbnode = self.get_languagebox(node)
                    if lbnode and self.selected_lbox is lbnode:
                        draw_lbox = True
                    continue
                else:
                    self.lines[line].width = x / self.fontwt
                    break

            # draw language boxes
            if lbox > 0 and draw_lbox:
                #color = self.nesting_colors[lbox % 5]
                color = QColor(0,0,0,30)
                if node.symbol.name != "\r":
                    if not node.image or node.plain_mode:
                        paint.fillRect(QRectF(x,3 + y*self.fontht, len(node.symbol.name)*self.fontwt, self.fontht), color)

            # prepare selection drawing
            if node is selection_start.node:
                draw_selection_start = (x + selection_start.pos * self.fontwt, y, line)

            if node is selection_end.node:
                draw_selection_end = (x + selection_end.pos * self.fontwt, y, line)

            # draw node
            dx, dy = editor.paint_node(paint, node, x, y, highlighter)
            x += dx
            #y += dy
            self.lines[line].height = max(self.lines[line].height, dy)

            # after we drew a return, update line information
            if node.lookup == "<return>" and not node is first_node:
                self.getWindow().ui.fLinenumbers.info.append((y,line, self.lines[line].indent))
                # draw lbox to end of line
                if draw_lbox:
                    paint.fillRect(QRectF(x,3+y*self.fontht, self.geometry().width()-x, self.fontht), color)

                self.lines[line].width = x / self.fontwt
                x = 0
                y += self.lines[line].height
                line += 1
                self.lines[line].height = 1 # reset height

            # draw cursor
            if node is self.cursor.node:
                draw_x = max(0, x-dx)
                cursor_pos = self.cursor.pos

                if node.symbol.name == "\r":
                    cursor_pos = 0
                if node.image and not node.plain_mode:
                    draw_x = x
                    cursor_pos = 0
                self.draw_cursor(paint, draw_x + cursor_pos * self.fontwt, 5 + y * self.fontht)


            if False and line == self.cursor.y and x/self.fontwt >= self.cursor.x and draw_cursor:
                draw_cursor_at = QRect(0 + self.cursor.x * self.fontwt, 5 + y * self.fontht, 0, self.fontht - 3)
                paint.drawRect(draw_cursor_at)

                # set lbox info coordinates
                infobox_coordinates = (self.cursor.x * self.fontwt, (y+1) * self.fontht)
                draw_cursor = False

            node = node.next_term

            # draw squiggly line
            if node is error_node:
                if isinstance(node, EOS):
                    length = self.fontwt
                else:
                    length = len(error_node.symbol.name)*self.fontwt
                if isinstance(node.symbol, MagicTerminal):
                    self.draw_vertical_squiggly_line(paint,x,y)
                else:
                    self.draw_squiggly_line(paint,x,y,length)

        self.draw_selection(paint, draw_selection_start, draw_selection_end)

        self.getWindow().ui.fLinenumbers.info.append((y,line, self.lines[line].indent))
        # paint infobox
        if False:
            lang_name = self.parser_langs[selected_language]
            lang_status = self.parsers[selected_language].last_status
            if lang_status is True:
                color = QColor(100,255,100)
            else:
                color = QColor(255,100,100)
            paint.setFont(self.infofont)
            paint.fillRect(QRect(infobox_coordinates[0], 5 + infobox_coordinates[1], len(lang_name)*self.infofontwt, self.infofontht), color)
            paint.drawText(QtCore.QPointF(infobox_coordinates[0], -3 + self.fontht + infobox_coordinates[1]), lang_name)
            paint.setFont(self.font)

        return x, y, line

    def draw_cursor(self, paint, x, y):
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

    def draw_squiggly_line(self, paint, x, y, length):
        paint.setPen(Qt.CustomDashLine)
        pen = paint.pen()
        pen.setDashPattern([2,2])
        pen.setColor(QColor("red"))
        paint.setPen(pen)
        #x -= length
        y = (y+1)*self.fontht+1
        paint.drawLine(x, y, x+length, y)
        paint.drawLine(x+2, y+1, x+2+length, y+1)
        paint.setPen(Qt.SolidLine)

    def draw_selection(self, paint, draw_selection_start, draw_selection_end):
        x1, y1, line1 = draw_selection_start
        x2, y2, line2 = draw_selection_end
        if y1 == y2:
            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, x2-x1, self.fontht), QColor(0,0,255,100))
        else:
            paint.fillRect(QRectF(x1, 3 + y1 * self.fontht, self.tm.lines[line1].width*self.fontwt - x1, self.fontht), QColor(0,0,255,100))
            y = y1 + self.tm.lines[line1].height
            for i in range(line1+1, line2):
                paint.fillRect(QRectF(0, 3 + y * self.fontht, self.tm.lines[i].width*self.fontwt, self.fontht), QColor(0,0,255,100))
                y = y + self.tm.lines[i].height
            paint.fillRect(QRectF(0, 3 + y2 * self.fontht, x2, self.fontht), QColor(0,0,255,100))

    def paint_node(self, paint, node, x, y, highlighter):
        dx, dy = (0, 0)
        if node.symbol.name == "\r" or isinstance(node, EOS) or isinstance(node.symbol, IndentationTerminal):
            return dx, dy
        if node.image is not None and not node.plain_mode:
            paint.drawImage(QPoint(x, 3 + y * self.fontht), node.image)
            dx = int(math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt)
            dy = int(math.ceil(node.image.height() * 1.0 / self.fontht))
        # comment in to display indentation nodes in the editor
       #elif isinstance(node.symbol, IndentationTerminal):
       #    if node.symbol.name == "INDENT":
       #        text = "{"
       #    elif node.symbol.name == "DEDENT":
       #        text = "}"
       #    elif node.symbol.name == "UNBALANCED":
       #        text = "[E]"
       #    else:
       #        return dx, dy

       #    paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
       #    return dx, dy
        elif isinstance(node, TextNode):
            paint.setPen(QPen(QColor(highlighter.get_color(node))))
            text = node.symbol.name
            paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
            #print("drawing node", text, "at", x,y)
            dx = len(text) * self.fontwt
            dy = 0
        return dx, dy

    def get_highlighter(self, node):
        root = node.get_root()
        base = lang_dict[self.tm.get_language(root)].base
        return syntaxhighlighter.get_highlighter(base)

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

    def get_editor(self, node):
        root = node.get_root()
        base = lang_dict[self.tm.get_language(root)].base
        return editor.get_editor(base, self.fontwt, self.fontht)

    def focusNextPrevChild(self, b):
        # don't switch to next widget on TAB
        return False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.coordinate_to_cursor(e.x(), e.y())
           # self.tm.cursor = cursor
            self.tm.selection_start = self.tm.cursor.copy()
            self.tm.selection_end = self.tm.cursor.copy()
            #self.tm.fix_cursor_on_image()
            self.getWindow().showLookahead()
            self.update()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.coordinate_to_cursor(e.x(), e.y())
            node = self.tm.get_node_from_cursor()
            if node.image is None:
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
        y = y - self.getWindow().ui.scrollArea.verticalScrollBar().value() * self.fontht
        return (x,y)

    def coordinate_to_cursor(self, x, y):

        mouse_y = y / self.fontht
        first_line = self.paint_start[0]
        y_offset = self.paint_start[1]

        y = y_offset
        line = first_line
        while line < len(self.tm.lines) - 1:
            y += self.tm.lines[line].height
            if y > mouse_y:
                break
            line += 1

        self.tm.cursor.line = line
        cursor_x = x / self.fontwt
        self.tm.cursor.move_to_x(cursor_x, self.tm.lines)


    def mouseMoveEvent(self, e):
        # apparaently this is only called when a mouse button is clicked while
        # the mouse is moving
        self.coordinate_to_cursor(e.x(), e.y())
        self.tm.selection_end = self.tm.cursor.copy()
        self.update()

    def XXXkeyPressEvent(self, e):
        import cProfile
        cProfile.runctx("self.linkkeyPressEvent(e)", globals(), locals())

    def key_to_string(self, key):
        if key == Qt.Key_Up:
            return "up"
        if key == Qt.Key_Down:
            return "down"
        if key == Qt.Key_Left:
            return "left"
        if key == Qt.Key_Right:
            return "right"

    def keyPressEvent(self, e):

        if e.key() in [Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta, Qt.Key_AltGr]:
            if e.key() == Qt.Key_Shift:
                self.tm.key_shift()
            return

        #selected_node, inbetween, x = self.tm.get_nodes_from_cursor()

        text = e.text()

        self.edit_rightnode = False # has been processes in get_nodes_at_pos -> reset

        if e.key() == Qt.Key_Escape:
            self.tm.key_escape()
        elif e.key() == Qt.Key_Backspace:
            self.tm.key_backspace()
        elif e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            if e.modifiers() == Qt.ShiftModifier:
                self.tm.key_cursors(self.key_to_string(e.key()), True)
            else:
                self.tm.key_cursors(self.key_to_string(e.key()), False)
        elif e.key() == Qt.Key_Home:
            self.tm.key_home()
        elif e.key() == Qt.Key_End:
            self.tm.key_end()
        elif e.key() == Qt.Key_C and e.modifiers() == Qt.ControlModifier:
            text = self.tm.copySelection()
            QApplication.clipboard().setText(text)
        elif e.key() == Qt.Key_V and e.modifiers() == Qt.ControlModifier:
            text = QApplication.clipboard().text()
            self.tm.pasteText(text)
        elif e.key() == Qt.Key_X and e.modifiers() == Qt.ControlModifier:
            self.tm.cutSelection()
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
            self.showSubgrammarMenu()
            if self.sublanguage:
                if self.tm.hasSelection():
                    self.tm.surround_with_languagebox(self.sublanguage)
                else:
                    self.tm.add_languagebox(self.sublanguage)
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
            self.tm.leave_languagebox()
        elif e.key() == Qt.Key_Delete:
            self.tm.key_delete()
        else:
            if e.key() == Qt.Key_Tab:
                text = "    "
            else:
                text = e.text()
            self.tm.key_normal(text)

        self.getWindow().btReparse([])
        self.fix_scrollbars()
        self.update()
        self.getWindow().showLookahead()

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

    def fix_scrollbars(self):
        self.cursor = self.tm.cursor
        x, y = self.cursor_to_coordinate()

        scrollbar_height = self.getWindow().ui.scrollArea.horizontalScrollBar().geometry().height()

        # fix vertical bar
        if y < 0:
            while y < 0:
                self.getWindow().ui.scrollArea.decVSlider()
                y += self.fontht
        if y+3 > self.geometry().height() - scrollbar_height: # the 3 is the padding of the canvas
            while y+3 > self.geometry().height() - scrollbar_height:
                self.getWindow().ui.scrollArea.incVSlider()
                y -= self.fontht

        # fix horizontal bar
        cursor_x = self.cursor.get_x()
        while cursor_x < self.getWindow().ui.scrollArea.horizontalScrollBar().value():
             self.getWindow().ui.scrollArea.decHSlider()
        while cursor_x > self.parentWidget().geometry().width()/self.fontwt + self.getWindow().ui.scrollArea.horizontalScrollBar().value():
            self.getWindow().ui.scrollArea.incHSlider()
            if self.getWindow().ui.scrollArea.horizontalScrollBar().value() == self.getWindow().ui.scrollArea.horizontalScrollBar().maximum():
                break

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

    def showSubgrammarMenu(self):
        self.sublanguage = None
        lookaheads = self.tm.getLookaheadList()
        # Create menu
        menu = QtGui.QMenu( self )
        # Create actions
        toolbar = QtGui.QToolBar()
        for l in languages:
            item = toolbar.addAction(str(l), self.createMenuFunction(l))
            l = "<%s>" % (l)
            if l in lookaheads:
                item.setFont(self.boldDefaultFont)
            menu.addAction(item)
        x,y = self.cursor_to_coordinate()
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + x, y + self.fontht))

    def createMenuFunction(self, l):
        def action():
            self.sublanguage = l
            self.edit_rightnode = True
        return action

    def selectSubgrammar(self, item):
        pass

    def randomDeletion(self):
        import random
        from time import sleep
        deleted = []
        for i in range(30):
            # choose random line
            y = random.randint(0, len(self.max_cols)-1)
            if self.max_cols[y] > 0:
                x = random.randint(0, self.max_cols[y])
                self.cursor = Cursor(x,y)

                event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier, "delete")
                #QCoreApplication.postEvent(self, event)
                self.keyPressEvent(event)

                if self.last_delchar: # might be none if delete at end of file
                    deleted.append((self.cursor.copy(), self.last_delchar))
        self.deleted_chars = deleted

    def undoDeletion(self):
        self.indentation = False
        for cursor, c in reversed(self.deleted_chars):
            self.cursor = cursor
            if c in ["\n","\r"]:
                key = Qt.Key_Return
                modifier = Qt.NoModifier
            elif ord(c) in range(97, 122): # a-z
                key = ord(c) - 32
                modifier = Qt.NoModifier
            elif ord(c) in range(65, 90): # A-Z
                key = ord(c)
                modifier = Qt.ShiftModifier
            else:   # !, {, }, ...
                key = ord(c)
                modifier = Qt.NoModifier
            event = QKeyEvent(QEvent.KeyPress, key, modifier, c)
            self.keyPressEvent(event)
        self.indentation = True

    def saveToJson(self, filename):
        whitespaces = self.getWindow().ui.cb_add_implicit_ws.isChecked()

        root = self.tm.parsers[0][0].previous_version.parent
        language = self.tm.parsers[0][2]
        manager = JsonManager()
        manager.save(root, language, whitespaces, filename)

    def loadFromJson(self, filename):
        manager = JsonManager()
        language_boxes = manager.load(filename)

        self.tm = TreeManager()
        self.tm.set_font(self.fontm)

        self.tm.load_file(language_boxes)
        self.reset()
        self.getWindow().btReparse([])

    def change_font(self, font):
        self.font = font[0]
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")
        self.tm.set_font(self.fontm)

    def export_unipycation(self):
        self.tm.export_unipycation()
