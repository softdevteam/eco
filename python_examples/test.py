class Parser(object):

    def __init__(self, code, whitespaces=False):
        self.lexer = Lexer(code)
        self.lexer.lex()
        self.curtok = 0
        self.start_symbol = None
        self.rules = {}
        self.whitespaces = whitespaces
