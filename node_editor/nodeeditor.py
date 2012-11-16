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
from astree import TextNode

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
        self.lastpos = 0
        QTextEdit.__init__(self, text)

    def keyPressEvent(self, e):
        print("====================== KEYPRESS ============================")
        lrp = self.getLRP()
        if self.document().isEmpty():
            lrp.init_ast()

        selected_nodes = self.getNodesAtPosition()
        print("Selected Nodes:", selected_nodes)

        QTextEdit.keyPressEvent(self, e)

        cursor = self.textCursor()
        pos = cursor.position()

        # type directly into current node
        print(e.key())
        if e.text() != "":
            if e.key() == 16777219:
                selected_nodes[0].backspace(pos)
            elif e.key() == 16777223:
                if selected_nodes[1] is not None:
                    selected_nodes[1].backspace(pos)
                else:
                    selected_nodes[0].backspace(pos)
            else:
                if len(selected_nodes) == 1:
                    # split, insert new node, repair
                    pass
                else:
                    # insert node, repair
                    newnode = self.create_new_node(str(e.text()))
                    node = selected_nodes[0]
                    node.parent.insert_after_node(node, newnode)
                    self.repair(newnode)
                #self.apply_change_to_nodes(selected_nodes, str(e.text()), pos)
            #else:
            #    selected_node.insert(str(e.text()), pos)
            # find all nodes that come after the changed node
            change = pos - self.lastpos
            #lrp.previous_version.adjust_nodes_after_node(selected_nodes, change)
            # mark changed nodes
            #selected_node.mark_changed()
        self.lastpos = pos

        selected_nodes = self.getNodesAtPosition()
        self.getWindow().btReparse(selected_nodes)

        self.getWindow().showLookahead()

    def repair(self, startnode):
        print("========== Starting Repair procedure ==========")
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
        print("   Tokenlist:", left_tokens, right_tokens)
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

    def get_matching_tokens(self, startnode, regex_list, direction):
        token_list = []
        done = False
        token = startnode
        while not done:
            if direction == "left":
                token = token.left_sibling()
            elif direction == "right":
                token = token.right_sibling()
            if token is None:
                break
            if token.symbol.name == "":
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
            if c not in ["+", ".", "*"]:
            # XXX be carefull to not accidentially match chars with non-escaped
            # regex chars like ., [, etc (only escaped ones)
                return True
        if c in string.lowercase and re.findall("\[.*a-z.*\]", regex):
            return True
        if c in string.uppercase and re.findall("\[.*A-Z.*\]", regex):
            return True
        if c in string.digits and re.findall("\[.*0-9.*\]", regex):
            return True
        return False

    def change_node(self, node, text, pos):
        print("change_node", node, text, pos)
        if node is None:
            return None

        #XXX bos and eos not changable
        # special case: empty starting node
        if node.symbol.name == "":
            print("    node is empty")
            node.change_text(text)
            node.regex = self.getPL().regex(text)
            node.lookup = self.getPL().name(text)
            return True

        print("   not empty")
        new_text = list(node.symbol.name)
        internal_position = pos - node.position - 1
        new_text.insert(internal_position, text)
        if node.matches("".join(new_text)):
            node.change_text("".join(new_text))
            print("   node changed", node)
            return True
        else:
            print("   not changed")
            return False

    def apply_change_to_nodes(self, nodes, text, pos):
        print("apply_changes", nodes, text, pos)
        try:
            nodes.remove(None)
        except:
            pass
        # sort nodes by priority
        sorted_nodes = sorted(nodes, key=lambda node: node.priority)

        # CASE 1: inside text -> change or split
        if len(sorted_nodes) == 1:
            node = sorted_nodes[0]
            internal_pos = pos - node.position - 1
            result = self.change_node(node, text, pos)
            if result:
                return
            text1 = node.symbol.name[:internal_pos]
            text2 = node.symbol.name[internal_pos:]
            text3 = text
            print(text1, text2, text3)

            node.change_text(text1) # this may result in a invalid node
            node2 = self.create_new_node(text2)
            node.parent.insert_after_node(node, node2)
            self.apply_change_to_nodes([node, node2], text, pos)

            return

        # CASE 2: between two nodes -> choose correct node and change it

        for node in sorted_nodes:
            # try to change node and continue with the next one if the change isn't valid
            result = self.change_node(node, text, pos)
            if result:
                return
        # if none of the nodes matches, insert a new node
        print("no match at all, creating new node instead. insertion after", nodes[0])
        new_node = self.create_new_node(text)
        # add to left node
        nodes[0].parent.insert_after_node(nodes[0], new_node)

    def create_new_node(self, text):
        symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

    def getCurrentNodeText(self):
        start = self.typing_start
        end = self.typing_end
        return self.toPlainText()[start:end]

    def getNodesAtPosition(self):
        pl = self.getPL()
        #XXX return only one node if "inside" text
        cursor_pos = self.textCursor().position()
        ast = self.getLRP().previous_version
        nodes = ast.get_nodes_at_position(cursor_pos)
        return nodes

    def getPL(self):
        #XXX better way to find window
        return self.getWindow().pl

    def getLRP(self):
        return self.getWindow().lrp

    def getWindow(self):
        return self.parent().parent().parent()

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

        self.btUpdateGrammar()
        #self.lrp = IncParser(grammar, 1)
        #self.lrp.init_ast()

        #self.pl = PriorityLexer(priorities)

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
        image = Viewer().get_tree_image(self.lrp.previous_version.parent)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        self.lrp.inc_parse()
        image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, selected_node)
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
    app.setStyle('cde')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
