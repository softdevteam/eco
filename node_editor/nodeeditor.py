from __future__ import print_function

import sys
sys.path.append("../")
sys.path.append("../lr-parser/")

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *


from gui import Ui_MainWindow

from plexer import PriorityLexer
from incparser import IncParser
from viewer import Viewer

from gparser import Terminal
from astree import TextNode, BOS, EOS

from languages import languages

grammar = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "INT"
"""

priorities = """
    "[0-9]+":INT
    "[+]":+
    "[*]":*
"""


grammar = """
    S ::= "a" | "abc" | "bc"
"""

priorities = """
    "abc":abc
    "bc":bc
    "a":a
"""

class NodeEditor(QFrame):

    # ========================== init stuff ========================== #

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.font = QtGui.QFont('Courier', 9)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height()
        self.fontwt = self.fontm.width(" ")
        self.cursor = [0,0]

        # make cursor blink
        self.show_cursor = 1
        self.ctimer = QtCore.QTimer()
        #QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.blink)
        self.ctimer.start(500)

        self.position = 0

        self.node_map = {}
        self.max_cols = []

        self.key_in_progress = 0

    def reset(self):
        self.max_cols = []
        self.node_map = {}
        self.cursor = [0,0]
        self.update()

    def set_lrparser(self, lrp):
        self.lrp = lrp
        self.ast = lrp.previous_version

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def paintEvent(self, event):
        print("============= Painting ================== ")
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)

        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []

        node = bos.next_terminal()
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                print("new line")
                self.max_cols.append(x)
                y += 1
                x = 0
            else:
                paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), node.symbol.name)
                x += len(node.symbol.name)
            self.node_map[(x,y)] = node

            node = node.next_terminal()
        self.max_cols.append(x) # last line

        if self.hasFocus() and self.show_cursor:
            #paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)
            paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, 1, self.fontht)

        print(self.max_cols)
        paint.end()

    def recalculate_positions(self): # without painting
        print("============ Recalculate positions =========== ")
        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []

        node = bos.next_terminal()
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = 0
            else:
                x += len(node.symbol.name)
            self.node_map[(x,y)] = node

            node = node.next_terminal()
        self.max_cols.append(x) # last line

    def keyPressEvent(self, e):
        print("====================== KEYPRESS (>>%s<<) ============================" % (repr(e.text()),))
        if self.key_in_progress == 1: # typed to fast
            print("tryping too fast")
            return
        self.key_in_progress = 1

        # Look up node in position map (if there is no direct match, i.e. inbetween node, try to find end of node)
        node_at_pos = None
        x = self.cursor[0]
        y = self.cursor[1]
        inbetween = False
        while not node_at_pos:
            try:
                node_at_pos = self.node_map[(x, y)]
                break
            except KeyError:
                x += 1
                inbetween = True
        print(self.node_map)
        print("node at pos:", node_at_pos)
        selected_nodes = [node_at_pos, node_at_pos.next_terminal()]
        print("Selected Nodes:", selected_nodes)

        text = e.text()

        if e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.cursor_movement(e.key())
        elif text != "":
            if e.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                if e.key() == Qt.Key_Backspace:
                    if self.cursor[0] > 0:
                        self.cursor[0] -= 1
                if selected_nodes[1] is None:   # inside node
                    selected_nodes[0].backspace(self.cursor[0])
                    repairnode = selected_nodes[0]
                else: # between two nodes
                    if e.key() == Qt.Key_Delete: # delete
                        node = selected_nodes[1]
                        other = selected_nodes[0]
                    else: # backspace
                        node = selected_nodes[0]
                        other = selected_nodes[1]
                    node.backspace(self.cursor[0])
                    if not node.deleted:
                        repairnode = node
                    else:
                        if isinstance(other, BOS):
                            repairnode = node.next_terminal()
                        elif isinstance(other, EOS):
                            repairnode = node.previous_terminal()
                        else:
                            repairnode = other
            else:
                #if selected_nodes[1] is None:
                if inbetween:
                    print("BETWEEN")
                    node = selected_nodes[0]
                    # split, insert new node, repair
                    internal_position = len(node.symbol.name) - (x - self.cursor[0])
                    node2 = self.create_new_node(str(text))
                    node3 = self.create_new_node(node.symbol.name[internal_position:])
                    node.symbol.name = node.symbol.name[:internal_position]
                    print("node1", node)
                    print("node2", node2)
                    print("node3", node3)
                    node.parent.insert_after_node(node, node2)
                    node.parent.insert_after_node(node2, node3)
                    repairnode = node2
                else:
                    # insert node, repair
                    newnode = self.create_new_node(str(text))
                    node = selected_nodes[0]
                    node.parent.insert_after_node(node, newnode)
                    repairnode = newnode
                if e.key() == Qt.Key_Return:
                    self.cursor[0] = 0
                    self.cursor[1] += 1
                else:
                    self.cursor[0] += 1
            self.repair(repairnode)

        self.recalculate_positions() # XXX ensures that positions are up to date before next keypress is called
        selected_nodes = self.getNodesAtPosition() # needed for coloring selected nodes
        self.getWindow().btReparse(selected_nodes) # XXX uses old, slower method

        self.getWindow().showLookahead()
        self.update()

        self.key_in_progress = 0

    def cursor_movement(self, key):
        if key == QtCore.Qt.Key_Up:
            if self.cursor[1] > 0:
                self.cursor[1] -= 1
                if self.cursor[0] > self.max_cols[self.cursor[1]]:
                    self.cursor[0] = self.max_cols[self.cursor[1]]
        elif key == QtCore.Qt.Key_Down:
            if self.cursor[1] < len(self.max_cols)-1:
                self.cursor[1] += 1
                if self.cursor[0] > self.max_cols[self.cursor[1]]:
                    self.cursor[0] = self.max_cols[self.cursor[1]]
        elif key == QtCore.Qt.Key_Left:
            if self.cursor[0] > 0:
                self.cursor[0] -= 1
        elif key == QtCore.Qt.Key_Right:
            if self.cursor[0] < self.max_cols[self.cursor[1]]:
                self.cursor[0] += 1

    def update_info(self):
        selected_nodes = self.getNodesAtPosition() # needed for coloring selected nodes
        self.getWindow().btReparse(selected_nodes)

    # ========================== AST modification stuff ========================== #

    def repair(self, startnode):
        if isinstance(startnode, BOS):
            return
        print("========== Starting Repair procedure ==========")
        print("Startnode", startnode)
        regex_list = []
        # find all regexs that include the new input string
        for regex in self.getPL().rules.keys():
            if self.in_regex(startnode.symbol.name, regex):
                regex_list.append(regex)
        print("    Possible regex:", regex_list)

        # expand to the left as long as all chars of those tokens are inside one of the regexs
        left_tokens = self.get_matching_tokens(startnode, regex_list, "left")
        left_tokens.reverse()
        # expand to the right as long as tokens may match
        right_tokens = self.get_matching_tokens(startnode, regex_list, "right")

        # merge all tokens together
        print("    Tokenlist:", left_tokens, right_tokens)
        newtoken_text = []
        for token in left_tokens:
            newtoken_text.append(token.symbol.name)
        newtoken_text.append(startnode.symbol.name)
        for token in right_tokens:
            newtoken_text.append(token.symbol.name)
        print("    Relexing:", "".join(newtoken_text))

        # relex token
        from lexer import Lexer
        lex = Lexer("".join(newtoken_text))
        regex_dict = {}
        i = 0
        print("creating groups")
        for regex in self.getPL().rules.keys():
            regex_dict["Group_" + str(i)] = regex
            print(i, regex)
            i += 1
        lex.set_regex(regex_dict)
        print("check for valid lex")
        success = lex.lex()
        print(lex.tokens)
        print("relexing done")

        # if relexing successfull, replace old tokens with new ones
        if success:
            print("success", success)
            parent = startnode.parent
            # remove old tokens
            # XXX this removes the first appearance of that token (which isn't always the one relexed)
            for token in left_tokens:
                print("left remove", token)
                token.parent.children.remove(token)
            for token in right_tokens:
                print("right remove", token)
                token.parent.children.remove(token) #XXX maybe invoke mark_changed here
            # create and insert new tokens
            print("parent children before", parent.children)
            lex.tokens.reverse()
            for token in lex.tokens:
                node = self.create_new_node(token.value)
                parent.insert_after_node(startnode, node)
            parent.remove_child(startnode)
            print("parent children after", parent.children)
            parent.mark_changed() # XXX changed or not changed? if it fits this hasn't really changed. only the removed nodes have changed
        print("============== End Repair ================")

    def get_matching_tokens(self, startnode, regex_list, direction):
        token_list = []
        done = False
        token = startnode
        while not done:
            if direction == "left":
                token = token.previous_terminal()
            elif direction == "right":
                token = token.next_terminal()
            if token is None:
                break
            if token.symbol.name == "":
                break
            if isinstance(token, BOS) or isinstance(token, EOS):
                break
            for c in token.symbol.name:
                match = False
                for regex in regex_list:
                    if self.in_regex(c, regex):
                        match = True
                        break
                if not match:
                    done = True # reached a character that matches no regex
                    break
            if not done:
                token_list.append(token)
        return token_list

    def in_regex(self, c, regex):
        #XXX write regex parser that returns all possible tokens
        import string, re
        if c in regex:
            if c not in ["+", "*", "."]:
                return True

            if c == "+" and regex.find("\+") != -1:
                return True
            if c == "*" and regex.find("\*") != -1:
                return True
            if c == "." and regex.find("\.") != -1:
                return True
            return False
        if c in string.lowercase and re.findall("\[.*a-z.*\]", regex):
            return True
        if c in string.uppercase and re.findall("\[.*A-Z.*\]", regex):
            return True
        if c in string.digits and re.findall("\[.*0-9.*\]", regex):
            return True
        if regex == "[ \\n\\t\\r]+" and re.findall(regex, c):
            return True
        #if c in [" ", "\n", "\t", "\r"] and regex == "[ \\n\\t\\r]+":
        #    return True
        return False

    def create_new_node(self, text):
        symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

    def getNodesAtPosition(self):
        nodes = self.ast.get_nodes_at_position(self.cursor[0])
        return nodes

    def getPL(self):
        return self.getWindow().pl

    def getLRP(self):
        return self.getWindow().lrp

    def getWindow(self):
        #XXX better way to find window
        return self.parent().parent().parent().parent().parent()

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #self.connect(self.ui.pushButton, SIGNAL("clicked()"), self.btReparse)

        # init with a grammar and priorities
        self.ui.teGrammar.document().setPlainText(grammar)
        self.ui.tePriorities.document().setPlainText(priorities)
        self.connect(self.ui.btUpdate, SIGNAL("clicked()"), self.btUpdateGrammar)

        #self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.ui.textEdit.update_info)

        self.btUpdateGrammar()

        for l in languages:
            self.ui.listWidget.addItem(str(l))

        self.connect(self.ui.listWidget, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()#"Open File", "", "Files (*.*)")
        for c in open(filename, "r").read()[:-1]:
            print(c)
            if ord(c) in range(97, 122): # a-z
                key = ord(c) - 32
                modifier = Qt.NoModifier
            elif ord(c) in range(65, 90): # A-Z
                key = ord(c)
                modifier = Qt.ShiftModifier
            else:   # !, {, }, ...
                key = ord(c)
                modifier = Qt.NoModifier
            event = QKeyEvent(QEvent.KeyPress, key, modifier, c)
            QCoreApplication.postEvent(self.ui.textEdit, event)

    def loadLanguage(self, item):
        print("Loading Language...")
        language = languages[self.ui.listWidget.row(item)]
        self.ui.teGrammar.document().setPlainText(language.grammar)
        self.ui.tePriorities.document().setPlainText(language.priorities)
        self.btUpdateGrammar()

    def btUpdateGrammar(self):
        new_grammar = str(self.ui.teGrammar.document().toPlainText())
        new_priorities = str(self.ui.tePriorities.document().toPlainText())
        whitespaces = self.ui.cb_add_implicit_ws.isChecked()
        print("Creating Incremental Parser")
        self.lrp = IncParser(new_grammar, 1, whitespaces)
        self.lrp.init_ast()
        self.ui.frame.set_lrparser(self.lrp)
        self.pl = PriorityLexer(new_priorities)

        self.ui.frame.reset()
        self.ui.graphicsView.setScene(QGraphicsScene())

        #img = Viewer("pydot").create_pydot_graph(self.lrp.graph)
        #self.showImage(self.ui.gvStategraph, img)

    def btRefresh(self):
        image = Viewer().get_tree_image(self.lrp.previous_version.parent, whitespaces)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        status = self.lrp.inc_parse()
        if status:
            self.ui.leParserStatus.setText("Accept")
        else:
            self.ui.leParserStatus.setText("Error")
        image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, selected_node, whitespaces)
        self.showImage(self.ui.graphicsView, image)

    def showLookahead(self):
        la = self.lrp.get_next_symbols_string()
        self.ui.lineEdit.setText(la)

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        scene.addItem(item);
        graphicsview.setScene(scene)

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
