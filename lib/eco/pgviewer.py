import re
import pydot
from dotviewer import drawgraph
from grammar_parser.gparser import MagicTerminal
from threading import Thread
from grammar_parser.bootstrap import AstNode, ListNode

class PGThread(Thread):

    def __init__(self, gl):
        Thread.__init__(self)
        self.gl = gl

    def run(self):
        self.gl.display()

    def quit(self):
        drawgraph.display_async_quit()

class PGViewer(object):

    def __init__(self, root, version):
        self.root = root

        self.whitespaces = True
        self.showast = False
        self.version = version
        self.restrict_nodes = []
        self.ast = None
        self.links = {}
        self.gl = drawgraph.GraphLayout(0,0,0)
        self.gl.pgviewer = self
        self.max_version = 0
        self.t = None

    def quit(self):
        self.t.quit()

    def run(self):
        self.create_graph()
        self.t = PGThread(self.gl)
        self.t.start()

    def is_alive(self):
        if not self.t:
            return False
        return self.t.is_alive()

    def send(self, command, *args):
        if command == "refresh":
            self.refresh(self.version + args[0])
        elif command == "toggle_ws":
            self.whitespaces = self.whitespaces ^ True
            self.refresh(self.version)
        elif command == "toggle_ast":
            self.showast = self.showast ^ True
            self.refresh(self.version)

    def refresh(self, version):
        if self.is_alive():
            if version > 0 and version <= self.max_version:
                self.version = version
                self.create_graph()
                self.gl.gdisplay.zoom(self.gl.scale)
                self.gl.gdisplay.updated_viewer()
                self.gl.gdisplay.redraw_now()

    def create_graph(self):
        self.links = {}
        self.gl.reset()
        graph = pydot.Dot(graph_type='digraph')
        if self.showast:
            self.add_node_ast(self.root, graph)
        else:
            self.add_node(self.root, graph)

        lines = graph.create_dot("plain").splitlines(True)

        _, scale, width, height = lines[0].strip("\n").split(" ")
        self.gl.scale = float(scale)
        self.gl.boundingbox = float(width), float(height)
        self.gl.links = self.links

        for line in lines[1:]:
            args = splitline(line)
            if args[0] == "node":
                self.gl.add_node(*args[1:])
            elif args[0] == "edge":
                self.gl.add_edge(*args[1:])

    def add_node(self, node, graph):
        self.links["%s" % id(node)] = node
        try:
            label = node.get_attr("symbol.name", self.version)
            lookup = node.get_attr("lookup", self.version)
        except AttributeError:
            label = node.symbol.name
            lookup = node.lookup
        if label == "\r":
            label = "<return>"
        if lookup == "<ws>":
            label = "<ws> x%s" % len(label)
        label = label.replace("\"", "\\\"")
        label = label.replace("\\\\\"", "\\\\\\\"")
        dotnode = pydot.Node("\"%s\"" % id(node), label='"%s"' % label, shape="box")

        try:
            changed = node.get_attr("changed", self.version)
        except AttributeError:
            changed = node.changed
        if changed:
            dotnode.set('color','green')

        graph.add_node(dotnode)

        children = node.children
        #if node.symbol.name == "Root" and self.version >= 0 :
        if self.version >= 0 :
            try:
                children = node.get_attr("children", self.version)
            except AttributeError:
                pass
        for c in children:
            if not self.whitespaces and c.symbol.name == "WS":
                continue
            c_node = self.add_node(c, graph)
            if c_node is not None:
                graph.add_edge(pydot.Edge(dotnode, c_node))

        if isinstance(node.symbol, MagicTerminal):
            c_node = self.add_node(node.symbol.parser, graph)
            graph.add_edge(pydot.Edge(dotnode, c_node))

        return dotnode

    def add_node_ast(self, node, graph):
        if not isinstance(node, AstNode) and not isinstance(node, ListNode) and node.alternate:
            node = node.alternate
        if isinstance(node, ListNode):
            name = "[" + node.symbol.name + "]"
        else:
            name = node.symbol.name
        if name == "\r":
            name = "<return>"
        dotnode = pydot.Node("\"%s\"" % id(node), label='"%s"' % name, shape="box")
        graph.add_node(dotnode)

        children = node.children
        if self.version >= 0 :
            try:
                children = node.get_attr("children", self.version)
            except AttributeError:
                pass
        for c in children:
            key = ""
            if isinstance(node, AstNode):
                key = c
                c = node.children[c]
            if not self.whitespaces and c.symbol.name == "WS":
                continue
            c_node = self.add_node_ast(c, graph)
            if c_node is not None:
                if key != "":
                    graph.add_edge(pydot.Edge(dotnode, c_node, label=key, fontsize="10", fontname="Arial"))
                else:
                    graph.add_edge(pydot.Edge(dotnode, c_node))

        if isinstance(node.symbol, MagicTerminal):
            c_node = self.add_node_ast(node.symbol.parser, graph)
            graph.add_edge(pydot.Edge(dotnode, c_node))

        return dotnode

def splitline(line, re_word = re.compile(r'[^\s"]\S*|["]["]|["].*?[^\\]["]')):
    result = []
    for word in re_word.findall(line):
        if word.startswith("\""):
            assert word[-1] == "\""
            word = word[1:-1]
        result.append(word)
    return result

def debug(treemanager):
    PGViewer(treemanager.get_mainparser().previous_version.parent, treemanager.version).run()
