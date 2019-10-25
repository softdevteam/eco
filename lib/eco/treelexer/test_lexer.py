from .lexer import Lexer, PatternMatcher, RegexParser, LexingError, RE_CHAR, RE_OR, RE_STAR, RE_PLUS, lbph
import pytest

class Test_RegexParser(object):

    def setup_class(cls):
        cls.regparse = RegexParser()

    def test_simple(self):
        assert self.regparse.load("ab|cd") is True
        assert self.regparse.load("ab|(cd") is False

    def test_ast(self):
        assert self.regparse.compile("ab") == [RE_CHAR("a"), RE_CHAR("b")]
        assert self.regparse.compile("a|b") == RE_OR(RE_CHAR("a"), RE_CHAR("b"))
        assert self.regparse.compile("a*") == RE_STAR(RE_CHAR("a"))
        assert self.regparse.compile("a+") == RE_PLUS(RE_CHAR("a"))
        assert self.regparse.compile("(a)") == RE_CHAR("a")
        assert self.regparse.compile("ab") == [RE_CHAR("a"), RE_CHAR("b")]
        assert self.regparse.compile("(ab)") == [RE_CHAR("a"), RE_CHAR("b")]
        assert self.regparse.compile("(ab)*") == RE_STAR([RE_CHAR("a"), RE_CHAR("b")])

        assert self.regparse.compile("(a|b)*|c+") == RE_OR(\
                                                       RE_STAR(\
                                                         RE_OR(\
                                                           RE_CHAR("a"),
                                                           RE_CHAR("b")
                                                         )
                                                       ),
                                                       RE_PLUS(RE_CHAR("c"))
                                                     )

class Test_PatternMatcher(object):

    def setup_class(cls):
        cls.pmatch = PatternMatcher()
        cls.rp = RegexParser()

    def cmp(self, pattern):
        return self.rp.compile(pattern)

    def test_match_one(self):
        assert PatternMatcher().match(RE_CHAR("a"), "a") == "a"
        assert PatternMatcher().match(RE_CHAR("."), "c") == "c"
        assert PatternMatcher().match(RE_CHAR("x"), "c") is None
        #assert PatternMatcher().match(None, "c") == "c"
        assert PatternMatcher().match(RE_CHAR("c"), "") is None

    def test_match_more(self):
        assert PatternMatcher().match(self.cmp("aa"), "aa") == "aa"
        assert PatternMatcher().match(self.cmp("a.b"), "axb") == "axb"

    def test_match_question(self):
        assert PatternMatcher().match(self.cmp("ab?"), "a") == "a"
        assert PatternMatcher().match(self.cmp("ab?"), "ab") == "ab"
        assert PatternMatcher().match(self.cmp("ab?"), "ac") == "a"
        assert PatternMatcher().match(self.cmp("ab(cdef)?"), "ab") == "ab"
        assert PatternMatcher().match(self.cmp("ab(cdef)?"), "abcdef") == "abcdef"

    def test_match_or(self):
        assert PatternMatcher().match(self.cmp("a|b"), "a") == "a"
        assert PatternMatcher().match(self.cmp("a|b"), "b") == "b"
        assert PatternMatcher().match(self.cmp("a|bd|c"), "a") == "a"
        assert PatternMatcher().match(self.cmp("a|bd|c"), "bd") == "bd"
        assert PatternMatcher().match(self.cmp("a|bd|c"), "c") == "c"
        assert PatternMatcher().match(self.cmp("ab|ac"), "ac") == "ac"

        assert PatternMatcher().match(self.cmp("abc|abcde"), "abcde") == "abc"
        assert PatternMatcher().match(self.cmp("abc|abcde"), "abc") == "abc"
        assert PatternMatcher().match(self.cmp("abcde|abc"), "abc") == "abc"

    def test_match_star(self):
        assert PatternMatcher().match(self.cmp("a*"), "") == ""
        assert PatternMatcher().match(self.cmp("a*"), "aaaaaa") == "aaaaaa"
        assert PatternMatcher().match(self.cmp("a*"), "bbbbb") == ""
        assert PatternMatcher().match(self.cmp("ab*"), "abbbbbb") == "abbbbbb"
        assert PatternMatcher().match(self.cmp("a*b*"), "aaaaaabbbbbbbbbb") == "aaaaaabbbbbbbbbb"
        assert PatternMatcher().match(self.cmp(".*"), "absakljsadklajd") == "absakljsadklajd"
        assert PatternMatcher().match(self.cmp(".*bc"), "abcaaabc") == "abcaaabc"
        assert PatternMatcher().match(self.cmp(".*abc"), "abc") == "abc"
        assert PatternMatcher().match(self.cmp("a*a"), "aa") == "aa"
        assert PatternMatcher().match(self.cmp("a*aa"), "aa") == "aa"
        assert PatternMatcher().match(self.cmp("a*aa"), "aaa") == "aaa"
        assert PatternMatcher().match(self.cmp("a*a"), "a") == "a"
        assert PatternMatcher().match(self.cmp("a*a"), "") is None
        assert PatternMatcher().match(self.cmp(".*abc"), "abcabcabc") == "abcabcabc" # greedy
        assert PatternMatcher().match(self.cmp(".*?abc"), "abcabcabc") == "abc" # non-greedy
        assert PatternMatcher().match(self.cmp("(ab)*ab"), "ab") == "ab"
        assert PatternMatcher().match(self.cmp("(ab)*ab"), "abab") == "abab"
        assert PatternMatcher().match(self.cmp("(ab)*ab"), "ababab") == "ababab"
        assert PatternMatcher().match(self.cmp("a*?bc"), "aaaabc") == "aaaabc"
        assert PatternMatcher().match(self.cmp("a*?bc"), "bc") == "bc"
        assert PatternMatcher().match(self.cmp("a*?bc"), "dbc") is None

    def test_match_plus(self):
        assert PatternMatcher().match(self.cmp("a+"), "aaaaaa") == "aaaaaa"
        assert PatternMatcher().match(self.cmp("a+"), "bbbbb") is None
        assert PatternMatcher().match(self.cmp("ab+"), "abbbbbb") == "abbbbbb"
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaabbbbbbbbbb") == "aaaaaabbbbbbbbbb"
        assert PatternMatcher().match(self.cmp("a+b+"), "bbbbbbbbbb") is None
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaaa") is None
        assert PatternMatcher().match(self.cmp("(ab)+"), "abababab") == "abababab"
        assert PatternMatcher().match(self.cmp("(ab)+"), "aaabbb") is None
        assert PatternMatcher().match(self.cmp(".+bc"), "aaabcaaabc") == "aaabcaaabc" # greedy
        assert PatternMatcher().match(self.cmp(".+?bc"), "aaabcaaabc") == "aaabc" # non-greedy

    def test_mixed(self):
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbc") == "aabbc"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbdd") == "aabbdd"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aadd") == "aadd"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbc") == "aabbc"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aac") == "aac"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aad") == "aad"
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "cdd") is None
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "bbcdd") is None
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "abc") == "abc"

    def test_charrange(self):
        assert PatternMatcher().match(self.cmp("[a-z]"), "b") == "b"
        assert PatternMatcher().match(self.cmp("[a-z]"), "x") == "x"
        assert PatternMatcher().match(self.cmp("[a-z]+"), "123") is None
        assert PatternMatcher().match(self.cmp("[a-z]+"), "foobar") == "foobar"
        assert PatternMatcher().match(self.cmp("[a-zA-Z0-9]+"), "fooBAR123") == "fooBAR123"
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z0-9_]*"), "_fooBAR123_") == "_fooBAR123_"
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z0-9_]*"), "123foobar") is None
        assert PatternMatcher().match(self.cmp("[a-z]"), "abc") == "a"
        assert PatternMatcher().match(self.cmp("[+-]"), "+") == "+"

    def test_negatedcharrange(self):
        assert PatternMatcher().match(self.cmp("[^abcd]"), "a") is None
        assert PatternMatcher().match(self.cmp("[^abcd]"), "e") == "e"
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "ABCD") == "ABCD"
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "abcd") is None

    def test_escaped(self):
        assert PatternMatcher().match(self.cmp("[a-z]"), "-") is None
        assert PatternMatcher().match(self.cmp(r"[a\-z]"), "-") == "-"
        assert PatternMatcher().match(self.cmp(r"#[^\-]*"), "-") is None
        assert PatternMatcher().match(self.cmp(r"[\[]*"), "[") == "["
        assert PatternMatcher().match(self.cmp(r"[\.]"), ".") == "."
        assert PatternMatcher().match(self.cmp(r"\."), ".") == "."
        assert PatternMatcher().match(self.cmp(r"\["), "[") == "["
        assert PatternMatcher().match(self.cmp(r"\[\]"), "[]") == "[]"
        assert PatternMatcher().match(self.cmp(r"\*"), "*") == "*"
        assert PatternMatcher().match(self.cmp(r"\+"), "+") == "+"
        assert PatternMatcher().match(self.cmp("\\+"), "+") == "+"
        assert PatternMatcher().match(self.cmp("\'"), "\'") == "'"
        assert PatternMatcher().match(self.cmp("\\'"), "\'") == "'"
        assert PatternMatcher().match(self.cmp('\\"'), '\"') == '\"'
        assert PatternMatcher().match(self.cmp("\r"), "\r") == "\r"
        assert PatternMatcher().match(self.cmp("\\r"), "\r") == "\r"
        assert PatternMatcher().match(self.cmp("\r"), "\\r") is None
        assert PatternMatcher().match(self.cmp("\\r"), "\\r") is None
        assert PatternMatcher().match(self.cmp("\\r"), "\\r") is None
        assert PatternMatcher().match(self.cmp("[\\r\\n]"), "\r") == "\r"
        assert PatternMatcher().match(self.cmp("[\\r\\n]"), "\n") == "\n"

    def test_realworld_examples(self):
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "abc123_") == "abc123_"
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "123abc123_") is None

        assert PatternMatcher().match(self.cmp("#[^\\r]*"), "# abc") == "# abc"
        assert PatternMatcher().match(self.cmp("#[^\r]*"), "# abc \r") == "# abc "

        assert PatternMatcher().match(self.cmp(r"([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "123.456") == "123.456"
        assert PatternMatcher().match(self.cmp(r"([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "1e23") == "1e23"
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a string 123!'") == "'this is a string 123!'"
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a with a newline \r string 123!'") is None

        assert PatternMatcher().match(self.cmp("/"), "/") == "/"
        assert PatternMatcher().match(self.cmp(r"\*"), "*") == "*"
        assert PatternMatcher().match(self.cmp(r"/\*"), "/*") == "/*"
        assert PatternMatcher().match(self.cmp(r"/\*\*/"), "/**/") == "/**/"
        assert PatternMatcher().match(self.cmp(r"/\*[a-z]*\*/"), "/*foo*/") == "/*foo*/"
        assert PatternMatcher().match(self.cmp(r"/\*([^\*])*\*/"), "/*foo*/") == "/*foo*/"
        assert PatternMatcher().match(self.cmp(r"/\*.*?\*/"), "/***/") == "/***/"
        assert PatternMatcher().match(self.cmp(r"/\*.*?\*/"), "/* abc** def */") == "/* abc** def */"
        assert PatternMatcher().match(self.cmp(r"/\*.*?\*/"), "/* abc */ * def */") == "/* abc */"

        # Python
        assert PatternMatcher().match(self.cmp("#[^\\r]*"), "# hello world") == "# hello world"
        assert PatternMatcher().match(self.cmp('\\"\\"\\"[^\\"]*\\"\\"\\"'), '"""this is a test string 123"""') == '"""this is a test string 123"""'
        assert PatternMatcher().match(self.cmp("\\'[^\\'\\r]*\\'"), "'single quoted string'") == "'single quoted string'"
        assert PatternMatcher().match(self.cmp('\\"[^\\"\\r]*\\"'), '"double quoted string"') == '"double quoted string"'
        assert PatternMatcher().match(self.cmp("[ \\t]+"), "    ") == "    "
        assert PatternMatcher().match(self.cmp("\\"), "\\") == "\\"
        assert PatternMatcher().match(self.cmp("\\"), "range") is None
        assert PatternMatcher().match(self.cmp("[\\n\\r]"), "\r") == "\r"
        assert PatternMatcher().match(self.cmp(r"\."), ".") == "."
        assert PatternMatcher().match(self.cmp("&="), "&=") == "&="
        assert PatternMatcher().match(self.cmp(r"0[xX][\da-fA-F]+"), "0xAB") == "0xAB"
        assert PatternMatcher().match(self.cmp("0[oO][0-7]+"), "0o67") == "0o67"
        assert PatternMatcher().match(self.cmp("0[bB][01]+"), "0b10101") == "0b10101"
        assert PatternMatcher().match(self.cmp('\"([^\"\r\\\\]|\\\\")*\"'), '"escaped\\"quote"') == '"escaped\\"quote"'

        # Prolog
        assert PatternMatcher().match(self.cmp("/"), "/") == "/"
        assert PatternMatcher().match(self.cmp("/\\"), "/\\") == "/\\"
        assert PatternMatcher().match(self.cmp("(%[^\\n\\r]*)"), "% comment") == "% comment"
        assert PatternMatcher().match(self.cmp("[A-Z_]([a-zA-Z0-9]|_)*|_"), "Variable_") == "Variable_"
        assert PatternMatcher().match(self.cmp("[A-Z_]([a-zA-Z0-9]|_)*|_"), "VAR") == "VAR"
        assert PatternMatcher().match(self.cmp("[A-Z_]([a-zA-Z0-9]|_)*|_"), "var") is None
        assert PatternMatcher().match(self.cmp("(0|[1-9][0-9]*)"), "0") == "0"
        assert PatternMatcher().match(self.cmp("(0|[1-9][0-9]*)"), "12345") == "12345"
        assert PatternMatcher().match(self.cmp(r"(0|[1-9][0-9]*)(\.[0-9]+)([eE][-+]?[0-9]+)?"), "1213.89e+23") == "1213.89e+23"
        assert PatternMatcher().match(self.cmp("([a-z]([a-zA-Z0-9]|_)*)"), "aH8_") == "aH8_"
        assert PatternMatcher().match(self.cmp("('[^']*')"), "'quoted'") == "'quoted'"
        assert PatternMatcher().match(self.cmp(r"\[\]"), "[]") == "[]"
        assert PatternMatcher().match(self.cmp("!"), "!") == "!"
        assert PatternMatcher().match(self.cmp(r"\+"), "+") == "+"
        assert PatternMatcher().match(self.cmp(r"\-"), "-") == "-"
        assert PatternMatcher().match(self.cmp(r"\{\}"), "{}") == "{}"
        assert PatternMatcher().match(self.cmp(r"([a-z]([a-zA-Z0-9]|_)*)|('[^']*')|\[\]|!|\+|\-|\{\}"), "aH8_") == "aH8_"
        assert PatternMatcher().match(self.cmp("\"[^\"]*\""), '"a string"') == '"a string"'

        # Eco grammar
        assert PatternMatcher().match(self.cmp('\\"([^\\"]|\\\\\\")*\\"'), '"terminal"') == '"terminal"'
        assert PatternMatcher().match(self.cmp('\\"([^\\"]|\\\\\\")*\\"'), '"[a-z]"') == '"[a-z]"'
        assert PatternMatcher().match(self.cmp('\\"([^\\\\"]|\\\\\\")*\\"'), '"\\"[a-z]\\""') == '"\\"[a-z]\\""'
        assert PatternMatcher().match(self.cmp('\\"([^\\\\"]|\\\\\\")*\\"'), '"\\"[a"-z]\\""') == '"\\"[a"'
        assert PatternMatcher().match(self.cmp('"([^\\"\\\\r]|\\\\\")*"'), '"\\"[a-z]\\""') == '"\\"[a-z]\\""'
        assert PatternMatcher().match(self.cmp( '\\"([^\\"\\\\]|\\\\.)*\\"'), '"\\+"') == '"\\+"'
        assert PatternMatcher().match(self.cmp('\\"([^\\"\\\\]|\\\\.)*\\"'), '"escaped\\"quote"') == '"escaped\\"quote"'
        assert PatternMatcher().match(self.cmp('\\"([^\\"\\\\]|\\\\.)*\\"'), "\"escaped\\\"quote\"") == '"escaped\\"quote"'
        assert PatternMatcher().match(self.cmp('\\"([^\\"\\\\]|\\\\.)*\\"'), '"\\"[a"-z]\\""') == '"\\"[a"'

        # Lua
        assert PatternMatcher().match(self.cmp(r'--\[\[.*?\]\]'), '--[[te\nst]]') == '--[[te\nst]]'

    def test_exactmatch(self):
        pm = PatternMatcher()
        pm.match(self.cmp("abc"), "abcd")
        assert pm.exactmatch is True

        pm.match(self.cmp("[abcd]+"), "abcdx")
        assert pm.exactmatch is False

        pm.match(self.cmp("a[bcd]+"), "abc")
        assert pm.exactmatch is True

        pm.match(self.cmp("a[abcd]+"), "abx")
        assert pm.exactmatch is False

        pm.match(self.cmp("as"), "abx")
        assert pm.exactmatch is False

        pm.match(self.cmp("[abc]"), "aclass")
        assert pm.exactmatch is True

        pm.match(self.cmp("abc|abcde"), "abcde")
        assert pm.exactmatch is True

        pm.match(self.cmp("abcde|abc"), "abcde")
        assert pm.exactmatch is True

        pm.match(self.cmp("abcx|abcde"), "abcx")
        assert pm.exactmatch is True

        pm.match(self.cmp("abcde|abcx"), "abcx")
        assert pm.exactmatch is True

        pm = PatternMatcher()
        assert pm.match(self.cmp("[a-z]*"), 'abc1') == "abc"
        assert pm.la == 4

        pm = PatternMatcher()
        assert pm.match(self.cmp("a[b]*a"), 'abbbaa') == "abbba"
        assert pm.la == 5

        pm = PatternMatcher()
        assert pm.match(self.cmp('"[^"]*"'), '"abc') is None
        assert pm.la == 5

from incparser.astree import TextNode, BOS, EOS, AST
from grammar_parser.gparser import Terminal, Nonterminal, MagicTerminal
from incparser.syntaxtable import FinishSymbol

class Test_Lexer(object):

    def test_simple(self):
        l = Lexer([("name", "[a-z]+"), ("num", "[0-9]+")])
        assert l.lex("abc123") == [("abc", "name", 1), ("123", "num", 1)]
        assert l.lex("456foobar9") == [("456", "num", 1), ("foobar", "name", 1), ("9", "num", 1)]

    def test_lookahead(self):
        l = Lexer([("cls", "class"), ("as", "as"), ("chr", "[a-z]")])
        assert l.lex("aclasxy") == [("a", "chr", 1), ("c", "chr", 4), ("l", "chr", 0), \
                                    ("as", "as", 0), ("x", "chr", 0), ("y", "chr", 0)]

    def test_lookahead2(self):
        l = Lexer([("one", "abcdef"), ("two", "abc")])
        assert l.lex("abcdexyz") == [("abc", "two", 3), ("dexyz", None, 0)]

    def test_lookahead3(self):
        l = Lexer([("MLS", '\"\"\"[^\"]*\"\"\"'), ("sstring", '\"[^\"\r]*\"')])
        assert l.lex('"""abc""d') == [('""', "sstring", 7), ('"abc"', "sstring", 0), ('"d', None, 0)]

    def test_leftover(self):
        l = Lexer([("test", "abcde|abcx")])
        assert l.lex("abcx") == [("abcx", "test", 0)]

        l = Lexer([("test", "abcde|abc")])
        assert l.lex("abcx") == [("abc", "test", 0), ("x", None, 0)]

        l = Lexer([("test", "abc|abcde")])
        assert l.lex("abcx") == [("abc", "test", 0), ("x", None, 0)]

    def test_nodes(self):
        root = TextNode(Nonterminal("Root"))
        bos = BOS(Terminal(""))
        eos = EOS(FinishSymbol())
        a = TextNode(Terminal("a"))
        b = TextNode(Terminal("b"))
        nB = TextNode(Nonterminal("B"))
        nB.set_children([b])
        root.set_children([bos, a, nB, eos])

        a.next_term = b
        b.next_term = eos

        l = Lexer([("name", "[a-z]+")])
        assert l.treelex(a) == [("ab", "name", 0)]

class Test_IncrementalLexing(object):

    def setup_class(cls):
        rules = []
        rules.append(("INT", "[0-9]+"))
        rules.append(("plus", "\\+"))
        rules.append(("mul", "\\*"))
        rules.append(("string", "\'[^\']*\'"))
        cls.lexer = Lexer(rules)

    def test_token_iter(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1+2*3"))
        bos.insert_after(new)

        it = self.lexer.get_token_iter(new)
        assert next(it) == ("1", "INT", 1, [TextNode(Terminal("1+2*3"))], -4)
        assert next(it) == ("+", "plus", 0, [TextNode(Terminal("1+2*3"))], -3)
        assert next(it) == ("2", "INT", 1, [TextNode(Terminal("1+2*3"))], -2)
        assert next(it) == ("*", "mul", 0, [TextNode(Terminal("1+2*3"))], -1)
        assert next(it) == ("3", "INT", 1, [TextNode(Terminal("1+2*3"))], 0)
        with pytest.raises(StopIteration):
            next(it)

    def test_lexingerror(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("1b"))
        bos.insert_after(new)

        it = self.lexer.get_token_iter(new)
        assert next(it) == ("1", "INT", 1, [TextNode(Terminal("1b"))], -1)
        with pytest.raises(LexingError):
            next(it)

    def test_token_iter_lbox(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("12"))
        new2 = TextNode(MagicTerminal("<SQL>"))
        new3 = TextNode(Terminal("34"))
        bos.insert_after(new)
        new.insert_after(new2)
        new2.insert_after(new3)

        it = self.lexer.get_token_iter(new)
        assert next(it) == ("12", "INT", 1, [TextNode(Terminal("12"))], 0)
        assert next(it) == (lbph, "", 0, [TextNode(MagicTerminal("<SQL>"))], 0)
        assert next(it) == ("34", "INT", 1, [TextNode(Terminal("34"))], 0)
        with pytest.raises(Exception):
            next(it)

    def test_token_iter_lbox2(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new = TextNode(Terminal("12"))
        new2 = TextNode(Terminal("'string with"))
        new3 = TextNode(MagicTerminal("<SQL>"))
        new4 = TextNode(Terminal("inside'"))
        bos.insert_after(new)
        new.insert_after(new2)
        new2.insert_after(new3)
        new3.insert_after(new4)

        it = self.lexer.get_token_iter(new)
        assert next(it) == ("12", "INT", 1, [TextNode(Terminal("12"))], 0)
        assert next(it) == (["'string with", lbph, "inside'"], "string", 0, [TextNode(Terminal("'string with")), TextNode(MagicTerminal("<SQL>")), TextNode(Terminal("inside'"))], 0)
        with pytest.raises(StopIteration):
            next(it)

    def test_token_iter_lbox3(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("'a"))
        new2 = TextNode(MagicTerminal("<SQL>"))
        new3 = TextNode(Terminal("b"))
        new4 = TextNode(MagicTerminal("<SQL>"))
        new5 = TextNode(Terminal("c'"))
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)
        new3.insert_after(new4)
        new4.insert_after(new5)

        it = self.lexer.get_token_iter(new1)
        assert next(it) == (["'a", lbph, "b", lbph, "c'"], "string", 0, [TextNode(Terminal("'a")), TextNode(MagicTerminal("<SQL>")), TextNode(Terminal("b")), TextNode(MagicTerminal("<SQL>")), TextNode(Terminal("c'"))], 0)
        with pytest.raises(StopIteration):
            next(it)

    def test_token_iter_newline(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("'a"))
        new2 = TextNode(Terminal("\r"))
        new3 = TextNode(Terminal("b'"))
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)

        it = self.lexer.get_token_iter(new1)
        assert next(it) == (["'a", "\r", "b'"], "string", 0, [TextNode(Terminal("'a")), TextNode(Terminal("\r")), TextNode(Terminal("b'"))], 0)
        with pytest.raises(StopIteration):
            next(it)

    def test_token_iter_newline_lbox(self):
        ast = AST()
        ast.init()
        bos = ast.parent.children[0]
        new1 = TextNode(Terminal("'a"))
        new2 = TextNode(Terminal("\r"))
        new3 = TextNode(Terminal("b"))
        new4 = TextNode(MagicTerminal("<SQL>"))
        new5 = TextNode(Terminal("c'"))
        bos.insert_after(new1)
        new1.insert_after(new2)
        new2.insert_after(new3)
        new3.insert_after(new4)
        new4.insert_after(new5)

        it = self.lexer.get_token_iter(new1)
        assert next(it) == (["'a", "\r", "b", lbph, "c'"], "string", 0, [TextNode(Terminal("'a")), TextNode(Terminal("\r")), TextNode(Terminal("b")), TextNode(MagicTerminal("<SQL>")), TextNode(Terminal("c'"))], 0)
        with pytest.raises(StopIteration):
            next(it)

class Test_TripleQuote(object):

    def setup_class(cls):
        rules = []
        rules.append(("MLS", '\"\"\"[^\"]*\"\"\"'))
        rules.append(("sstring", "\'[^\'\r]*\'"))
        rules.append(("dstring", '\"[^\"\r]*\"'))
        cls.lexer = Lexer(rules)

    def test_simple(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('"""abc"""'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('"""abc"""', "MLS", 0, [TextNode(Terminal('"""abc"""'))], 0)

    def test_simple2(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('""'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('""', "dstring", 1, [TextNode(Terminal('""'))], 0)

    def test_simple3(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('"""'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('""', "dstring", 2, [TextNode(Terminal('"""'))], -1)

    def test_simple4(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('"""abc""d'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('""', "dstring", 7, [TextNode(Terminal('"""abc""d'))], -7)
        assert next(it) == ('"abc"', "dstring", 0, [TextNode(Terminal('"""abc""d'))], -2)

class Test_Keyword(object):

    def setup_class(cls):
        rules = []
        rules.append(("as", "as"))
        rules.append(("NAME", "[a-z]+"))
        cls.lexer = Lexer(rules)

    def test_simple(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal("asd"))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ("asd", "NAME", 1, [TextNode(Terminal("asd"))], 0)

class Test_LuaComments(object):

    def setup_class(cls):
        rules = []
        rules.append(("mcomment", r'--\[\[.*?\]\]'))
        rules.append(("minus", '-'))
        rules.append(("scomment", '--[^\r]*'))
        cls.lexer = Lexer(rules)

    def test_simple(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('--[[testtest]]'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('--[[testtest]]', "mcomment", 0, [TextNode(Terminal('--[[testtest]]'))], 0)

    def test_lookahead(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('--[[test\rtest'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == ('--[[test', "scomment", 6, [TextNode(Terminal('--[[test\rtest'))], -5)

    def test_multi(self):
        ast = AST()
        ast.init()
        new = TextNode(Terminal('--[[test\rtest]]'))
        ast.parent.children[0].insert_after(new)
        it = self.lexer.get_token_iter(new)
        assert next(it) == (['--[[test', '\r', 'test]]'], "mcomment", 0, [TextNode(Terminal('--[[test\rtest]]'))], 0)
