#https://chart.googleapis.com/chart?chs=250x100&cht=gv&chl=graph{A--B--C}
import sys
sys.path.append("../")
import pydot

class Viewer(object):

    def __init__(self, dot_type='google'):
        self.dot_type = dot_type

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

    def get_tree_image(self, tree, selected_node):
        if self.dot_type == 'google':
            import urllib.request
            s = self.create_ast_string(tree)
            url = "https://chart.googleapis.com/chart?cht=gv&chl=graph{%s}" % (s,)
            temp = urllib.request.urlretrieve(url)
            return temp[0]
        elif self.dot_type == 'pydot':
            graph = pydot.Dot(graph_type='graph')
            self.add_node_to_tree(tree, graph)

            # mark currently selected node as red
            for node in selected_node:
                m = graph.get_node(str(id(node)))
                if len(m) > 0:
                    m[0].set('color','red')

            graph.write_png('temp.png')
            return 'temp.png'

    def add_node_to_tree(self, node, graph):

        dotnode = pydot.Node(id(node), label="%s (%s)" % (node.symbol.name, node.seen))
        graph.add_node(dotnode)

        for c in node.children:
            c_node = self.add_node_to_tree(c, graph)
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
            for state in stateset:
                stateset_info.append(str(state))
            dotnode = pydot.Node(i, shape='rect', label="%s\n%s" % (i, "\n".join(stateset_info)))
            pydotgraph.add_node(dotnode)
            i += 1

        for key in graph.edges.keys():
            start = key[0]
            end = graph.edges[key]
            pydotgraph.add_edge(pydot.Edge(pydot.Node(start), pydot.Node(end), label=key[1].name))

        pydotgraph.write_png('graphtemp.png')
        return 'graphtemp.png'

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

