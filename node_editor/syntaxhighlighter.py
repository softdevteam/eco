class SyntaxHighlighter(object):
    colors = {
        "green": "#859900",
        "red": "#DC322F",
        "blue": "#268BD2",
        "grey": "#839496",
        "cyan": "#2AA198",
        "black": "#000000"
    }
    keyword_colors = {
        "class": "green",
        "def": "green",
        "for": "green",
        "while": "green",
        "<ws>": "grey",
        "object": "blue",
        "NUMBER": "cyan",
        "STRING": "cyan",
        "range":"blue",
        "object": "blue"
    }

    def get_color(self, node):
        if node.symbol.name in self.keyword_colors:
            color = self.keyword_colors[node.symbol.name]
        elif node.lookup in self.keyword_colors:
            color = self.keyword_colors[node.lookup]
        else:
            color = "black"
        hexcode = self.colors[color]
        return hexcode
