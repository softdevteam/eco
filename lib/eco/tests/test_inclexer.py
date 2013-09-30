from inclexer.inclexer import IncrementalLexer
from incparser.astree import AST
from grammars.grammars import calc1
from incparser.astree import TextNode, BOS, EOS
from grammar_parser.gparser import Terminal, Nonterminal

class Test_IncrementalLexer:

    def setup_class(cls):
        cls.x = 15

    def lex(self, text):
        return self.lexer.lex(text)

    def relex(self, node):
        self.lexer.relex(node)

class Test_CalcLexer(Test_IncrementalLexer):

    def setup_class(cls):
        cls.lexer = IncrementalLexer(calc1.priorities)

    def test_lex(self):
        tokens = self.lex("1 + 2 * 3")
        expected = []
        expected.append(("1", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("+", "+"))
        expected.append((" ", "<ws>"))
        expected.append(("2", "INT"))
        expected.append((" ", "<ws>"))
        expected.append(("*", "*"))
        expected.append((" ", "<ws>"))
        expected.append(("3", "INT"))
        assert tokens == expected

    def test_lex2(self):
        tokens = self.lex("+2")
        expected = []
        expected.append(("+", "+"))
        expected.append(("2", "INT"))
        assert tokens == expected

    def test_relex(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1 + 2 * 3"))
        bos.insert_after(new)
        self.relex(new)
        assert ast.parent.symbol == Nonterminal("Root")
        assert isinstance(ast.parent.children[0], BOS)
        assert isinstance(ast.parent.children[-1], EOS)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("2")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("*")
        node = node.next_term; assert node.symbol == Terminal(" ")
        node = node.next_term; assert node.symbol == Terminal("3")
        node = node.next_term; assert isinstance(node, EOS)

    def test_relex2(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1"))
        bos.insert_after(new)
        self.relex(new)
        node = bos.next_term; assert node.symbol == Terminal("1")

        new.symbol.name = "1+"
        self.relex(new)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")

        node.symbol.name = "+2"
        self.relex(node)
        node = bos.next_term; assert node.symbol == Terminal("1")
        node = node.next_term; assert node.symbol == Terminal("+")
        node = node.next_term; assert node.symbol == Terminal("2")

    def test_relex_return(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        eos = ast.parent.children[1]
        text = TextNode(Terminal("123\r"))
        bos.insert_after(text)
        self.relex(text)

        last_return = eos.prev_term
        assert last_return.symbol.name == "\r"
        assert last_return.lookup == "<return>"

        new_number = TextNode(Terminal("3"))
        last_return.insert_after(new_number)
        self.relex(new_number)

        new = TextNode(Terminal("\r"))
        last_return.insert_after(new)
        self.relex(new)
        assert new.symbol == Terminal("\r")
        assert new.lookup == "<return>"

