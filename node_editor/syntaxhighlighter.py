class SyntaxHighlighter(object):
    colors = {
        "green": "#859900",
        "red": "#DC322F",
        "blue": "#268BD2",
        "grey": "#839496",
        "cyan": "#2AA198",
        "yellow": "#B58900",
        "purple": "#D33682",
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
        "object": "blue",
        "import": "red",
        "public": "yellow",
        "private": "yellow",
        "static": "yellow",
        "void": "yellow",
        "int": "yellow",
        "float": "yellow",
        "BOOLEAN_LITERAL": "cyan",
        "STRING_LITERAL": "cyan",
        "INTEGER_LITERAL": "cyan",
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
