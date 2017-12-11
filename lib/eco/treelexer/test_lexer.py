from lexer import Lexer, PatternMatcher, RegexParser, RE_CHAR, RE_OR, RE_STAR, RE_PLUS
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
        assert PatternMatcher().match(RE_CHAR("a"), "a") is True
        assert PatternMatcher().match(RE_CHAR("."), "c") is True
        assert PatternMatcher().match(RE_CHAR("x"), "c") is False
        assert PatternMatcher().match(None, "c") is True
        assert PatternMatcher().match(RE_CHAR("c"), "") is False

    def test_match_more(self):
        assert PatternMatcher().match(self.cmp("aa"), "aa") is True
        assert PatternMatcher().match(self.cmp("a.b"), "axb") is True

    def test_match_question(self):
        assert PatternMatcher().match(self.cmp("ab?"), "a") is True
        assert PatternMatcher().match(self.cmp("ab?"), "ab") is True
        assert PatternMatcher().match(self.cmp("ab?"), "ac") is True # but 'c' is left over
        assert PatternMatcher().match(self.cmp("ab(cdef)?"), "ab") is True
        assert PatternMatcher().match(self.cmp("ab(cdef)?"), "abcdef") is True

    def test_match_or(self):
        assert PatternMatcher().match(self.cmp("a|b"), "a") is True
        assert PatternMatcher().match(self.cmp("a|b"), "b") is True
        assert PatternMatcher().match(self.cmp("a|bd|c"), "a") is True
        assert PatternMatcher().match(self.cmp("a|bd|c"), "bd") is True
        assert PatternMatcher().match(self.cmp("a|bd|c"), "c") is True
        assert PatternMatcher().match(self.cmp("ab|ac"), "ac") is True

    def test_match_star(self):
        assert PatternMatcher().match(self.cmp("a*"), "") is True
        assert PatternMatcher().match(self.cmp("a*"), "aaaaaa") is True
        assert PatternMatcher().match(self.cmp("a*"), "bbbbb") is True
        assert PatternMatcher().match(self.cmp("ab*"), "abbbbbb") is True
        assert PatternMatcher().match(self.cmp("a*b*"), "aaaaaabbbbbbbbbb") is True
        assert PatternMatcher().match(self.cmp(".*"), "absakljsadklajd") is True

    def test_match_plus(self):
        assert PatternMatcher().match(self.cmp("a+"), "aaaaaa") is True
        assert PatternMatcher().match(self.cmp("a+"), "bbbbb") is False
        assert PatternMatcher().match(self.cmp("ab+"), "abbbbbb") is True
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaabbbbbbbbbb") is True
        assert PatternMatcher().match(self.cmp("a+b+"), "bbbbbbbbbb") is False
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaaa") is False
        assert PatternMatcher().match(self.cmp("(ab)+"), "abababab") is True
        assert PatternMatcher().match(self.cmp("(ab)+"), "aaabbb") is False

    def test_mixed(self):
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbc") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbdd") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aadd") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aabbc") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aac") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "aad") is True
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "cdd") is False
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "bbcdd") is False
        assert PatternMatcher().match(self.cmp("a+b*(c|d+)"), "abc") is True # but 'd' left over

    def test_charrange(self):
        assert PatternMatcher().match(self.cmp("[a-z]"), "b") is True
        assert PatternMatcher().match(self.cmp("[a-z]"), "x") is True
        assert PatternMatcher().match(self.cmp("[a-z]+"), "123") is False
        assert PatternMatcher().match(self.cmp("[a-z]+"), "foobar") is True
        assert PatternMatcher().match(self.cmp("[a-zA-Z0-9]+"), "fooBAR123") is True
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z0-9_]"), "_fooBAR123_") is True
        pm = PatternMatcher()
        assert pm.match(self.cmp("[a-z]"), "abc") is True
        assert pm.pos == 1

    def test_negatedcharrange(self):
        assert PatternMatcher().match(self.cmp("[^abcd]"), "a") is False
        assert PatternMatcher().match(self.cmp("[^abcd]"), "e") is True
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "ABCD") is True
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "abcd") is False

    def test_escaped(self):
        assert PatternMatcher().match(self.cmp("[a-z]"), "-") is False
        assert PatternMatcher().match(self.cmp("[a\-z]"), "-") is True
        assert PatternMatcher().match(self.cmp("#[^\-]*"), "-") is False
        assert PatternMatcher().match(self.cmp("[\[]*"), "[") is True
        assert PatternMatcher().match(self.cmp("[\.]"), ".") is True
        assert PatternMatcher().match(self.cmp("\."), ".") is True
        assert PatternMatcher().match(self.cmp("\["), "[") is True

    def test_realworld_examples(self):
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "abc123_") is True
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "123abc123_") is False

        p = PatternMatcher()
        assert p.match(self.cmp("#[^\\r]*"), "# abc") is True
        assert p.pos == 5

        p = PatternMatcher()
        assert p.match(self.cmp("#[^\r]*"), "# abc \r") is True
        assert p.pos == 6


        assert PatternMatcher().match(self.cmp("([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "123.456") is True
        assert PatternMatcher().match(self.cmp("([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "1e23") is True
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a string 123!'") is True
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a with a newline \r string 123!'") is False

    def test_exactmatch(self):
        pm = PatternMatcher()
        pm.match(self.cmp("abc"), "abcd")
        assert pm.exactmatch is True

        pm.reset()
        pm.match(self.cmp("[abcd]+"), "abcdx")
        assert pm.exactmatch is False

        pm.reset()
        pm.match(self.cmp("a[bcd]+"), "abc")
        assert pm.exactmatch is True

        pm.reset()
        pm.match(self.cmp("a[abcd]+"), "abx")
        assert pm.exactmatch is False

        pm.reset()
        pm.match(self.cmp("as"), "abx")
        assert pm.exactmatch is False

        pm.reset()
        pm.match(self.cmp("[abc]"), "aclass")
        assert pm.exactmatch is True

class Test_Lexer(object):

    def test_simple(self):
        l = Lexer([("name", "[a-z]+"), ("num", "[0-9]+")])
        assert l.lex("abc123") == [("abc", "name", 1), ("123", "num", 0)]
        assert l.lex("456foobar9") == [("456", "num", 1), ("foobar", "name", 1), ("9", "num", 0)]

    def test_lookahead(self):
        l = Lexer([("cls", "class"), ("as", "as"), ("chr", "[a-z]")])
        assert l.lex("aclasxy") == [("a", "chr", 1), ("c", "chr", 4), ("l", "chr", 0), \
                                    ("as", "as", 0), ("x", "chr", 0), ("y", "chr", 0)]
