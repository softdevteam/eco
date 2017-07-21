import random
from grammars.grammars import javapy, python
from treemanager import TreeManager
from grammar_parser.gparser import Nonterminal, Terminal

# helper functions

def next_node(node):
    while(node.right is None):
        node = node.parent
    return node.right

def prev_node(node):
    while(node.left is None):
        node = node.parent
    return node.left

def subtree_to_text(subtree):
    l = []
    if subtree.children:
        for child in subtree.children:
            l.append(subtree_to_text(child))
    elif type(subtree.symbol) is Terminal:
        l.append(subtree.symbol.name)
    return "".join(l)

def truncate(string):
    return string[:15] + "..." + string[-15:]

class FuzzyLboxStats:

    def __init__(self):
        parser, lexer = javapy.load()
        self.lexer = lexer
        self.parser = parser
        self.ast = parser.previous_version
        self.treemanager = TreeManager()
        self.treemanager.add_parser(parser, lexer, javapy.name)

        parser.setup_autolbox(javapy.name)

    def load_main(self, filename):
        f = open(filename, "r")
        content = f.read()
        f.close()
        self.treemanager.import_file(content)
        self.mainexprs = self.find_nonterms_by_name(self.treemanager, self.main_repl_str)

    def load_expr(self, filename):
        f = open(filename, "r")
        content = f.read()
        f.close()

        self.replexprs = self.find_expressions(content, self.sub_repl_str)

    def set_replace(self, main, sub):
        self.main_repl_str = main
        self.sub_repl_str = sub

    def find_nonterms_by_name(self, tm, name):
        l = []
        bos = tm.get_bos()
        eos = tm.get_eos()
        node = bos.right_sibling()
        while node is not eos:
            if node.symbol.name == name:
                l.append(node)
            if node.children:
                node = node.children[0]
                continue
            node = next_node(node)
        return l

    def find_expressions(self, program, expr):
        parser, lexer = python.load()
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, python.name)
        treemanager.import_file(program)

        # find all python expressions
        l = self.find_nonterms_by_name(treemanager, expr)
        l2 = []
        for st in l:
            l2.append(subtree_to_text(st).rstrip())
        return l2

    def insert_python_expression(self, expr):
        for c in expr:
            self.treemanager.key_normal(c)

    def delete_expr(self, expr):
        # find first term and last term
        # select + delete
        node = expr
        while type(node.symbol) is Nonterminal:
            if node.children:
                node = node.children[0]
            else:
                node = next_node(node)
        first = node

        node = expr
        while type(node.symbol) is Nonterminal:
            if node.children:
                node = node.children[-1]
            else:
                node = prev_node(node)
        last = node

        if first.deleted or last.deleted:
            return None

        self.treemanager.select_nodes(first, last)
        deleted = self.treemanager.copySelection()
        self.treemanager.deleteSelection()
        return deleted

    def run(self):
        assert len(self.treemanager.parsers) == 1

        #print "mainexpr", [subtree_to_text(x) for x in self.mainexprs]
        #print "pyexpr", self.replexprs
        random.shuffle(self.mainexprs)
        for e in self.mainexprs[:10]:
            if e.get_root() is None:
                continue
            before = len(self.treemanager.parsers)
            deleted = self.delete_expr(e)
            if deleted:
                choice = random.choice(self.replexprs)
                print "Replacing '{}' with '{}':".format(truncate(deleted), truncate(choice))
                self.insert_python_expression(choice)
                valid = self.parser.last_status
                if before == len(self.treemanager.parsers):
                    result = "No box inserted"
                else:
                    result = "Box inserted"
                print "    => {} ({})".format(result, valid)
            else:
                print "Replacing '{}' with '{}':\n    => Already deleted".format(subtree_to_text(e), choice)

if __name__ == "__main__":
    import sys
    args = sys.argv
    mainfile = args[1]
    exprfile = args[2]
    fuz = FuzzyLboxStats()
    #fuz.set_replace("unary_expression", "testlist")
    fuz.set_replace("method_declaration", "funcdef")
    fuz.load_main(mainfile)
    fuz.load_expr(exprfile)
    fuz.run()

# XXX turn this into a stats tool instead of a test suite
# print out statistics about how often:
# - a python box gets created
#   - box does/doesn't match inserted text
# - inserted python is valid PHP
# - inserted python creates an error
#   - box fixes it
#   - box doesn't fix it
