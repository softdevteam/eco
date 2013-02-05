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

from gparser import Terminal, MagicTerminal
from astree import TextNode, BOS, EOS

from languages import languages

from token_lexer import TokenLexer

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

        self.parsers = {}
        self.lexers = {}
        self.priorities = {}

        self.edit_rightnode = False

    def reset(self):
        self.max_cols = []
        self.node_map = {}
        self.cursor = [0,0]
        self.update()

    def set_lrparser(self, lrp):
        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.lrp = lrp
        self.ast = lrp.previous_version
        self.parsers[lrp.previous_version.parent] = self.lrp
        self.lexers[lrp.previous_version.parent] = self.getTL()
        self.priorities[lrp.previous_version.parent] = self.getPL()

    def set_sublanguage(self, language):
        self.sublanguage = language

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def paintEvent(self, event):
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

        x, y = self.paintAST(paint, bos, x, y)
        self.max_cols.append(x) # last line

        if self.hasFocus() and self.show_cursor:
            #paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)
            paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, 1, self.fontht)

        paint.end()

    def paintAST(self, paint, bos, x, y):
        node = bos.next_terminal()
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = 0
                self.node_map[(x,y)] = node
            else:
                if isinstance(node.symbol, MagicTerminal):
                    paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), " ")
                    x_before = x
                    x, y = self.paintAST(paint, node.symbol.parser.previous_version.get_bos(), x, y)
                    paint.drawRect(3 + x_before*self.fontwt, 2 + y*self.fontht, (x-x_before)*self.fontwt, self.fontht)
                else:
                    paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), node.symbol.name)
                    x += len(node.symbol.name)
                    self.node_map[(x,y)] = node

            node = node.next_terminal()
        return x,y


    def recalculate_positions(self): # without painting
        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []

        x, y = self.recalculate_positions_rec(bos, x, y)
        self.max_cols.append(x) # last line

    def recalculate_positions_rec(self, bos, x, y):
        node = bos.next_terminal()
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = 0
                self.node_map[(x,y)] = node
            else:
                if isinstance(node.symbol, MagicTerminal):
                    bos = node.symbol.parser.previous_version.get_bos()
                    x, y = self.recalculate_positions_rec(bos, x, y)
                else:
                    x += len(node.symbol.name)
                    self.node_map[(x,y)] = node

            node = node.next_terminal()

        return x, y


    def get_nodes_at_position(self):
        print("==================== Get nodes at pos ====================== ")
        print("Position:", self.cursor)
        # Look up node in position map (if there is no direct match, i.e. inbetween node, try to find end of node)
        node_at_pos = None
        x = self.cursor[0]
        y = self.cursor[1]
        inbetween = False
        while not node_at_pos and x <= self.max_cols[y]:
            try:
                node_at_pos = self.node_map[(x, y)]
                break
            except KeyError:
                x += 1
                inbetween = True
        #print(self.node_map)
        print("node at pos:", node_at_pos)
        selected_nodes = [node_at_pos, node_at_pos.next_terminal()]
        print("Selected Nodes:", selected_nodes)
        #if isinstance(selected_nodes[1].symbol, MagicTerminal) and self.edit_rightnode:
        if self.edit_rightnode:
            print("edit right", selected_nodes)
            if isinstance(selected_nodes[1], EOS):
                root = selected_nodes[1].get_root()
                magic = root.get_magicterminal()
                if magic:
                    selected_nodes = [magic, magic.next_terminal()]
            if isinstance(selected_nodes[1].symbol, MagicTerminal):
                bos = selected_nodes[1].symbol.parser.previous_version.get_bos()
                selected_nodes = [bos, bos.next_terminal()]

        print("Final selected nodes", selected_nodes)
        print("==================== END (get_nodes_at_pos) ====================== ")
        return (selected_nodes, inbetween, x)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            cursor_x = e.x() / self.fontwt
            cursor_y = e.y() / self.fontht
            if cursor_y < len(self.max_cols):
                self.cursor[1] = cursor_y
            else:
                self.cursor[1] = len(self.max_cols) - 1
            if cursor_x <= self.max_cols[self.cursor[1]]:
                self.cursor[0] = cursor_x
            else:
                self.cursor[0] = self.max_cols[self.cursor[1]]

        selected_nodes, _, _ = self.get_nodes_at_position()
        self.getWindow().btReparse(selected_nodes)

        self.getWindow().showLookahead()
        self.update()

    def keyPressEvent(self, e):
        print("====================== KEYPRESS (>>%s<<) ============================" % (repr(e.text()),))
        print("first get_nodes_at_pos")
        selected_nodes, inbetween, x = self.get_nodes_at_position()

        text = e.text()

        if e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.cursor_movement(e.key())
        elif text != "":
            self.edit_rightnode = False
            if e.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                if e.key() == Qt.Key_Backspace:
                    if self.cursor[0] > 0:
                        self.cursor[0] -= 1
                    else:
                        # if at beginning of line: move to previous line
                        if self.cursor[1] > 0:
                            self.cursor[1] -= 1
                            self.cursor[0] = self.max_cols[self.cursor[1]]
                if inbetween:   # inside node
                    internal_position = len(selected_nodes[0].symbol.name) - (x - self.cursor[0])
                    selected_nodes[0].backspace(internal_position)
                    repairnode = selected_nodes[0]
                else: # between two nodes
                    if e.key() == Qt.Key_Delete: # delete
                        if isinstance(selected_nodes[1].symbol, MagicTerminal):
                            self.edit_rightnode = True
                            selected_nodes, _, _ = self.get_nodes_at_position()
                            self.edit_rightnode = False
                        node = selected_nodes[1]
                        other = selected_nodes[0]
                        node.backspace(0)
                    else: # backspace
                        node = selected_nodes[0]
                        other = selected_nodes[1]
                        node.backspace(-1)
                    if node.symbol.name == "" and not isinstance(node, BOS): # if node is empty, delete it and repair previous/next node
                        if isinstance(other, BOS):
                            repairnode = node.next_terminal()
                        elif isinstance(other, EOS):
                            repairnode = node.previous_terminal()
                        else:
                            repairnode = other
                        # check if magic terminal is empty
                        root = node.get_root()
                        print("root", root)
                        magic = root.get_magicterminal()
                        print("magic", magic)
                        #if magic and len(root.children) == 3:
                        #    pass
                        #    magic.parent.children.remove(magic)
                        #    del self.parsers[root]
                        #    del self.lexers[root]
                        #    del self.priorities[root]
                        #else:
                        node.parent.children.remove(node)

                    else:
                        repairnode = node
            else:
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    self.showSubgrammarMenu()
                    newnode = self.add_magic()
                    self.edit_rightnode = True # writes next char into magic ast
                elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
                    self.edit_rightnode = True # writes next char into magic ast
                    return
                else:
                    newnode = self.create_node(str(text))
                if inbetween:
                    print("BETWEEN")
                    node = selected_nodes[0]
                    # split, insert new node, repair
                    internal_position = len(node.symbol.name) - (x - self.cursor[0])
                    node2 = newnode
                    node3 = self.create_node(node.symbol.name[internal_position:])
                    node.symbol.name = node.symbol.name[:internal_position]
                    print("node1", node)
                    print("node2", node2)
                    print("node3", node3)
                    self.add_node(node, node2)
                    self.add_node(node2, node3)
                    self.repair(node)
                    self.repair(node3)
                    #node.parent.insert_after_node(node, node2)
                    #node.parent.insert_after_node(node2, node3)
                    repairnode = node2
                else:
                    # insert node, repair
                    node = selected_nodes[0]
                    self.add_node(node, newnode)
                    #node.parent.insert_after_node(node, newnode)
                    repairnode = newnode
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    pass # do nothing
                elif e.key() == Qt.Key_Return:
                    self.cursor[0] = 0
                    self.cursor[1] += 1
                else:
                    self.cursor[0] += 1
            self.repair(repairnode)

        self.recalculate_positions() # XXX ensures that positions are up to date before next keypress is called
        print("second get_nodes_at_pos")
        selected_nodes, _, _ = self.get_nodes_at_position()
        self.getWindow().btReparse(selected_nodes)

        self.getWindow().showLookahead()
        self.update()

    def add_magic(self):
        # Create magic token
        magictoken = self.create_node("<%s>" % self.sublanguage.name, magic=True)

        # Create parser, priorities and lexer
        parser = IncParser(self.sublanguage.grammar, 1, True)
        parser.init_ast()
        root = parser.previous_version.parent
        root.magic_backpointer = magictoken
        pl = PriorityLexer(self.sublanguage.priorities)
        tl = TokenLexer(pl.rules)
        self.parsers[root] = parser
        self.lexers[root] = tl
        self.priorities[root] = pl
        # Add starting token to new tree
        #starting_node = self.create_node("")
        #self.add_node(parser.previous_version.get_bos(), starting_node)
        #self.node_map[(self.cursor[0], self.cursor[1])] = root.children[0]

        magictoken.symbol.parser = parser
        return magictoken

    def create_node(self, text, magic=False):
        if magic:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        return node

    def add_node(self, previous_node, new_node):
        previous_node.parent.insert_after_node(previous_node, new_node)
        root = new_node.get_root()
        if not isinstance(new_node.symbol, MagicTerminal):
            pl = self.priorities[root]
            text = new_node.symbol.name
            new_node.regex = pl.regex(text)
            new_node.priority = pl.priority(text)
            new_node.lookup = pl.name(text)

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
        if isinstance(startnode, BOS) or isinstance(startnode, EOS):
            return
        if isinstance(startnode.symbol, MagicTerminal):
            return
        print("========== Starting Repair procedure ==========")
        print("Startnode", startnode.symbol)
        root = startnode.get_root()
        regex_list = []
        # find all regexs that include the new input string
        for regex in self.lexers[root].regexlist.keys():
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
        print("    Relexing:", repr("".join(newtoken_text)))


        tl = self.lexers[root]
        success = tl.match("".join(newtoken_text))
        #return

        # relex token
       #from lexer import Lexer
       #lex = Lexer("".join(newtoken_text))
       #regex_dict = {}
       #i = 0
       #print("creating groups")
       #for regex in self.getPL().rules.keys():
       #    regex_dict["Group_" + str(i)] = regex
       #    print(i, regex)
       #    i += 1
       #lex.set_regex(regex_dict)
       #print("check for valid lex")
       #success = lex.lex()
       #print(lex.tokens)
       #print("relexing done")

        # if relexing successfull, replace old tokens with new ones
        if success: #XXX is this false at any time?
            print("success", success)
            parent = startnode.parent
            # remove old tokens
            # XXX this removes the first appearance of that token (which isn't always the one relexed)
            for token in left_tokens:
                #print("left remove", token)
                token.parent.remove_child(token)
            for token in right_tokens:
                #print("right remove", token)
                token.parent.remove_child(token) #XXX maybe invoke mark_changed here
            # create and insert new tokens
            #print("parent children before", parent.children)
            #lex.tokens.reverse()
            success.reverse()
            for match in success:#lex.tokens:
                symbol = Terminal(match[0])
                node = TextNode(symbol, -1, [], -1)
                node.lookup = match[1]
                #node = self.create_new_node(token)#token.value)
                parent.insert_after_node(startnode, node)
            parent.remove_child(startnode)
            #print("parent children after", parent.children)
            parent.mark_changed() # XXX changed or not changed? if it fits this hasn't really changed. only the removed nodes have changed
        print("Repaired to", startnode)
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
            if c not in ["+", "*", ".", "\\"]:
                return True

            if c == "+" and regex.find("\+") != -1:
                return True
            if c == "*" and regex.find("\*") != -1:
                return True
            if c == "." and regex.find("\.") != -1:
                return True
            if c == "\\" and regex == "\"([a-zA-Z0-9 ]|\\\\\")*\"":
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
        if re.match("^" + regex + "$", c):
            return True
        return False

    def dead_create_new_node(self, text, magic=False):
        if magic:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

    def getNodesAtPosition(self):
        nodes = self.ast.get_nodes_at_position(self.cursor[0])
        return nodes

    def getTL(self):
        return self.getWindow().tl

    def getPL(self):
        return self.getWindow().pl

    def getLRP(self):
        return self.getWindow().lrp

    def getWindow(self):
        #XXX better way to find window
        return self.parent().parent().parent().parent()

    def showSubgrammarMenu(self):
        # Create menu
        menu = QtGui.QMenu( self )
        # Create actions
        toolbar = QtGui.QToolBar()
        for l in languages:
            item = toolbar.addAction(str(l), self.createMenuFunction(l))
            menu.addAction(item)
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + self.cursor[0]*self.fontwt, 3 + (self.cursor[1]+1)*self.fontht))

    def createMenuFunction(self, l):
        def action():
            self.sublanguage = l
            self.edit_rightnode = True
        return action

    def selectSubgrammar(self, item):
        print("SELECTED GRAMMAR", item)

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

        self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.btRefresh)
        self.connect(self.ui.cb_toggle_ast, SIGNAL("clicked()"), self.btRefresh)

        self.connect(self.ui.btShowSingleState, SIGNAL("clicked()"), self.showSingleState)
        self.connect(self.ui.btShowWholeGraph, SIGNAL("clicked()"), self.showWholeGraph)

        for l in languages:
            self.ui.listWidget.addItem(str(l))

        self.ui.listWidget.item(0).setSelected(True)

        self.loadLanguage(self.ui.listWidget.item(0))

        self.connect(self.ui.listWidget, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()#"Open File", "", "Files (*.*)")
        for c in open(filename, "r").read()[:-1]:
            print(c)
            if c == "\n":
                key = Qt.Key_Return
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
            QCoreApplication.postEvent(self.ui.frame, event)

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
        self.pl = PriorityLexer(new_priorities)
        self.tl = TokenLexer(self.pl.rules)
        self.ui.frame.set_lrparser(self.lrp)
        self.ui.frame.reset()
        self.ui.graphicsView.setScene(QGraphicsScene())
        print("Done.")

    def showWholeGraph(self):
        img = Viewer("pydot").create_pydot_graph(self.lrp.graph)
        self.showImage(self.ui.gvStategraph, img)

    def showSingleState(self):
        img = Viewer("pydot").show_single_state(self.lrp.graph, int(self.ui.leSingleState.text()))
        self.showImage(self.ui.gvStategraph, img)

    def btRefresh(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, [], whitespaces)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        results = []
        for key in self.ui.frame.parsers:
            status = self.ui.frame.parsers[key].inc_parse()
            if status:
                results.append("Accept")
            else:
                results.append("Error")
        self.ui.leParserStatus.setText(", ".join(results))

        if self.ui.cb_toggle_ast.isChecked():
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
