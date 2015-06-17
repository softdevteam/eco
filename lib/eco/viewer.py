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

import os
try:
    import pydot
except ImportError:
    pass

from grammar_parser.gparser import MagicTerminal, Terminal
from grammar_parser.bootstrap import AstNode, ListNode

tempdir = ".temp/"

class Viewer(object):

    def __init__(self, dot_type='google'):
        self.dot_type = dot_type
        self.image = ""
        try:
            os.stat(tempdir)
        except:
            os.mkdir(tempdir)
        self.countnodes = 0

    def __del__(self):
        import shutil
        if os.path.isdir(tempdir):
            shutil.rmtree(tempdir)

    def show_ast(self, grammar, _input):
        from incparser import IncParser
        from constants import LR1
        lrp = IncParser(grammar, LR1)
        lrp.init_ast()
        start_node = lrp.previous_version.find_node_at_pos(0)
        start_node.insert(_input, 0)
        start_node.mark_changed()
        lrp.inc_parse()
        self.show(self.get_tree_image(lrp.previous_version.parent))

    def show_graph(self, grammar):
        import urllib.request
        from gparser import Parser
        from stategraph import StateGraph
        parser = Parser(grammar)
        parser.parse()

        from constants import LR1
        graph = StateGraph(parser.start_symbol, parser.rules, LR1)
        graph.build()

        if self.dot_type == 'google':
            s = self.create_graph_string(graph)
            url = "https://chart.googleapis.com/chart?cht=gv&chl=digraph{%s}" % (s,)
            temp = urllib.request.urlretrieve(url)
            self.show(temp[0])
        elif self.dot_type == 'pydot':
            self.show(self.create_pydot_graph(graph))

    def show_tree(self, tree):
        s = self.create_ast_string(tree)
        url = "https://chart.googleapis.com/chart?cht=gv&chl=graph{%s}" % (s,)
        temp = urllib.request.urlretrieve(url)
        self.show(temp[0])

    def get_terminal_tree(self, tree):
        node = tree
        while not isinstance(node.symbol, Terminal):
            node = node.children[0]

        graph = pydot.Dot(graph_type='graph')
        parent = pydot.Node(0, label="root")
        graph.add_node(parent)
        while node:
            dotnode = pydot.Node(id(node), label=" %s " % node.symbol.name)
            graph.add_node(dotnode)
            graph.add_edge(pydot.Edge(parent, dotnode))
            if node.symbol.name == "\r":
                parent = dotnode
            node = node.next_term

        graph.write_png(tempdir + 'temp.png')
        self.image = tempdir + 'temp.png'

    def get_tree_image(self, tree, selected_node, whitespaces=True, restrict_nodes=None, ast=False, version=0):
        if self.dot_type == 'google':
            import urllib.request
            s = self.create_ast_string(tree)
            url = "https://chart.googleapis.com/chart?cht=gv&chl=graph{%s}" % (s,)
            temp = urllib.request.urlretrieve(url)
            return temp[0]
        elif self.dot_type == 'pydot':
            graph = pydot.Dot(graph_type='graph')
            self.add_node_to_tree(tree, graph, whitespaces, restrict_nodes, ast, version)

            # mark currently selected node as red
            for node in selected_node:
                m = graph.get_node(str(id(node)))
                if len(m) > 0:
                    m[0].set('color','red')

            graph.write_png(tempdir + 'temp.png')
            self.image = tempdir + 'temp.png'

    def add_node_to_tree(self, node, graph, whitespaces, restrict_nodes, ast, version):

        if restrict_nodes and node not in restrict_nodes:
            return None

        addtext = ""
        if ast:
            if not isinstance(node, AstNode) and not isinstance(node, ListNode) and node.alternate:
                node = node.alternate
        try:
            if node.symbol.folding:
                pass#addtext = node.symbol.folding
        except AttributeError:
            pass
        label = []
        if isinstance(node, ListNode):
            label.append("[" + node.symbol.name + "]")
        else:
            label.append(node.symbol.name)
        if isinstance(node.symbol, Terminal) and node.lookup != "":
            label.append("\n")
            if node.lookup.startswith("0,"):
                label.append("?")
            else:
                label.append(str(node.lookup))
        if node.indent:
            label.append("\n")
            label.append(repr(node.indent))
        if node.parent:
            label.append("\n")
            label.append("parent: " + str(node.parent.symbol.name))
        label = "%s" % ("".join(label))
        label = label.replace("\"", "\\\"")
        label = label.replace("\\\\\"", "\\\\\\\"")
        dotnode = pydot.Node("\"%s\"" % id(node), label='"%s"' % label)
        self.countnodes += 1
        if node.changed:
            dotnode.set('color','green')
        try:
            if node.has_changes(version):
                pass#dotnode.set('color','blue')
        except AttributeError:
            pass
        dotnode.set('fontsize', '8')
        dotnode.set('fontname', 'Arial')
        graph.add_node(dotnode)

        children = node.children
        if node.symbol.name == "Root":
            children = node.log[("children", version)]
        for c in children:
            key = ""
            if isinstance(node, AstNode):
                key = c
                c = node.children[c]
            if not whitespaces and c.symbol.name == "WS":
                continue
            c_node = self.add_node_to_tree(c, graph, whitespaces, restrict_nodes, ast, version)
            if c_node is not None:
                if key != "":
                    graph.add_edge(pydot.Edge(dotnode, c_node, label=key, fontsize="10", fontname="Arial"))
                else:
                    graph.add_edge(pydot.Edge(dotnode, c_node))

        if isinstance(node.symbol, MagicTerminal):
            c_node = self.add_node_to_tree(node.symbol.parser, graph, whitespaces, restrict_nodes, ast, version)
            graph.add_edge(pydot.Edge(dotnode, c_node))

        return dotnode

    def create_ast_string(self, ast):
        s = []
        l = [ast]
        while len(l) > 0:
            node = l.pop(0)
            node_id = id(node)
            s.append("%s[label=\"%s (%s)\"]" % (node_id, node.symbol.name, node.seen))
            for c in node.children:
                child_id = id(c)
                #s.append("%s[label=\"%s\n%s\"]" % (child_id, c.symbol.name, id(c)))
                s.append("%s--%s" % (node_id, id(c)))
                l.append(c)
        return ";".join(s)

    def create_pydot_graph(self, graph):
        pydotgraph = pydot.Dot(graph_type='digraph')

        i = 0
        for stateset in graph.state_sets:
            stateset_info = []
            for state in stateset.elements:
                stateset_info.append(str(state) + "{" + str(stateset.lookaheads[state]) + "}")
            dotnode = pydot.Node(i, shape='rect', label="%s\n%s" % (i, "\n".join(stateset_info)))
            pydotgraph.add_node(dotnode)
            i += 1

        for key in graph.edges.keys():
            start = key[0]
            end = graph.edges[key]
            pydotgraph.add_edge(pydot.Edge(pydot.Node(start), pydot.Node(end), label=key[1].name))

        pydotgraph.write_png(tempdir + 'graphtemp.png')
        self.image = tempdir + 'graphtemp.png'

    def show_single_state(self, graph, _id):
        pydotgraph = pydot.Dot(graph_type='digraph')

        stateset = graph.state_sets[_id]
        stateset_info = []
        for state in stateset.elements:
            stateset_info.append(str(state) + "{" + str(stateset.lookaheads[state]) + "}")
        dotnode = pydot.Node(_id, shape='rect', label="%s\n%s" % (_id, "\n".join(stateset_info)))
        pydotgraph.add_node(dotnode)

        pydotgraph.write_png(tempdir + 'graphsingle.png')
        self.image = tempdir + 'graphsingle.png'

    def create_graph_string(self, graph):
        s = []
        i = 0
        # create states with information
        for stateset in graph.state_sets:
            stateset_info = []
            for state in stateset:
                stateset_info.append(str(state))
            s.append("%s[label=\"%s\\n%s\",shape=box]" % (i, i, "\\n".join(stateset_info)))
            i += 1

        # create edges
        for key in graph.edges.keys():
            start = key[0]
            end = graph.edges[key]
            s.append("%s->%s [label=\"%s\"]" % (start, end, key[1].name.strip("\"")))

        return ";".join(s)

    def show(self, image):
        import pygame

        w = 640
        h = 480
        screen = pygame.display.set_mode((w,h))
        graphic = pygame.image.load(image).convert()
        screen = pygame.display.set_mode((graphic.get_width(),graphic.get_height()))
        #screen2 = pygame.transform.scale(screen, (graphic.get_width(), graphic.get_height()))

        running = 1
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = 0
            screen.blit(graphic, (0,0))
            pygame.display.flip()

