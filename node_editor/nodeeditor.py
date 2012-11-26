from __future__ import print_function

import sys
sys.path.append("../")
sys.path.append("../lr-parser/")

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

class NodeEditor(QTextEdit):

    def __init__(self, text=None):
        QTextEdit.__init__(self, text)

    def keyPressEvent(self, e):
        print("====================== KEYPRESS (>>%s<<) ============================" % (e.text(),))
        lrp = self.getLRP()
        if self.document().isEmpty():
            lrp.init_ast()

        selected_nodes = self.getNodesAtPosition()
        print("Selected Nodes:", selected_nodes)

        QTextEdit.keyPressEvent(self, e)

        cursor = self.textCursor()
        pos = cursor.position()

        if e.text() != "":
            if e.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                if selected_nodes[1] is None:   # inside node
                    selected_nodes[0].backspace(pos)
                    repairnode = selected_nodes[0]
                else: # between two nodes
                    if e.key() == Qt.Key_Delete: # delete
                        node = selected_nodes[1]
                        other = selected_nodes[0]
                    else:
                        node = selected_nodes[0]
                        other = selected_nodes[1]
                    node.backspace(pos)
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
                if selected_nodes[1] is None:
                    node = selected_nodes[0]
                    # split, insert new node, repair
                    internal_position = pos - node.position - 1
                    node2 = self.create_new_node(str(e.text()))
                    node3 = self.create_new_node(node.symbol.name[internal_position:])
                    node.symbol.name = node.symbol.name[:internal_position]
                    node.parent.insert_after_node(node, node2)
                    node.parent.insert_after_node(node2, node3)
                    repairnode = node2
                else:
                    # insert node, repair
                    newnode = self.create_new_node(str(e.text()))
                    node = selected_nodes[0]
                    node.parent.insert_after_node(node, newnode)
                    repairnode = newnode
            self.repair(repairnode)

        selected_nodes = self.getNodesAtPosition() # needed for coloring selected nodes
        self.getWindow().btReparse(selected_nodes)

        self.getWindow().showLookahead()

    def update_info(self):
        selected_nodes = self.getNodesAtPosition() # needed for coloring selected nodes
        self.getWindow().btReparse(selected_nodes)

    def repair(self, startnode):
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
        for regex in self.getPL().rules.keys():
            regex_dict["Group_" + str(i)] = regex
            i += 1
        lex.set_regex(regex_dict)
        success = lex.lex()
        print(lex.tokens)

        # if relexing successfull, replace old tokens with new ones
        if success:
            parent = startnode.parent
            # remove old tokens
            for token in left_tokens:
                token.parent.children.remove(token)
            for token in right_tokens:
                token.parent.children.remove(token)
            # create and insert new tokens
            lex.tokens.reverse()
            for token in lex.tokens:
                node = self.create_new_node(token.value)
                parent.insert_after_node(startnode, node)
            parent.children.remove(startnode)
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
        if c == " " and regex == "[ ]+":
            return True
        return False

    def create_new_node(self, text):
        symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

    def getNodesAtPosition(self):
        pl = self.getPL()
        cursor_pos = self.textCursor().position()
        ast = self.getLRP().previous_version
        nodes = ast.get_nodes_at_position(cursor_pos)
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

        self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.ui.textEdit.update_info)

        self.btUpdateGrammar()

        for l in languages:
            self.ui.listWidget.addItem(str(l))

        self.connect(self.ui.listWidget, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)

    def loadLanguage(self, item):
        language = languages[self.ui.listWidget.row(item)]
        self.ui.teGrammar.document().setPlainText(language.grammar)
        self.ui.tePriorities.document().setPlainText(language.priorities)
        self.btUpdateGrammar()

    def btUpdateGrammar(self):
        new_grammar = str(self.ui.teGrammar.document().toPlainText())
        new_priorities = str(self.ui.tePriorities.document().toPlainText())
        self.lrp = IncParser(new_grammar, 1)
        self.lrp.init_ast()
        self.pl = PriorityLexer(new_priorities)

        self.ui.textEdit.document().setPlainText("")
        self.ui.graphicsView.setScene(QGraphicsScene())

        img = Viewer("pydot").create_pydot_graph(self.lrp.graph)
        self.showImage(self.ui.gvStategraph, img)

    def btRefresh(self):
        image = Viewer().get_tree_image(self.lrp.previous_version.parent, whitespaces)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        self.lrp.inc_parse()
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
    app.setStyle('cleanlooks')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
