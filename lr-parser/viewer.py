#https://chart.googleapis.com/chart?chs=250x100&cht=gv&chl=graph{A--B--C}
import sys
sys.path.append("../")
import urllib.request

class Viewer(object):

    def show_ast(self, grammar, _input):
        from incparser import IncParser
        from constants import LR1
        lrp = IncParser(grammar, LR1)
        lrp.check(_input)
        self.show_tree(lrp.get_ast().parent)

    def show_graph(self, grammar):
        from gparser import Parser
        from stategraph import StateGraph
        parser = Parser(grammar)
        parser.parse()

        from constants import LR1
        graph = StateGraph(parser.start_symbol, parser.rules, LR1)
        graph.build()

        s = self.create_graph_string(graph)
        url = "https://chart.googleapis.com/chart?cht=gv&chl=digraph{%s}" % (s,)
        temp = urllib.request.urlretrieve(url)
        self.show(temp[0])

    def show_tree(self, tree):
        s = self.create_ast_string(tree)
        url = "https://chart.googleapis.com/chart?cht=gv&chl=graph{%s}" % (s,)
        temp = urllib.request.urlretrieve(url)
        self.show(temp[0])

    def get_tree_image(self, tree):
        s = self.create_ast_string(tree)
        url = "https://chart.googleapis.com/chart?cht=gv&chl=graph{%s}" % (s,)
        temp = urllib.request.urlretrieve(url)
        return temp[0]

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

    def create_ast_string(self, ast):
        s = []
        l = [ast]
        while len(l) > 0:
            node = l.pop(0)
            node_id = id(node)
            s.append("%s[label=\"%s\"]" % (node_id, node.symbol.name))
            for c in node.children:
                child_id = id(c)
                #s.append("%s[label=\"%s\n%s\"]" % (child_id, c.symbol.name, id(c)))
                s.append("%s--%s" % (node_id, id(c)))
                l.append(c)
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

