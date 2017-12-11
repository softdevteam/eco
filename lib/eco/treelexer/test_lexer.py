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
        assert PatternMatcher().match(RE_CHAR("a"), "a") == "a"
        assert PatternMatcher().match(RE_CHAR("."), "c") == "c"
        assert PatternMatcher().match(RE_CHAR("x"), "c") is None
        assert PatternMatcher().match(None, "c") == "c"
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

    def test_match_plus(self):
        assert PatternMatcher().match(self.cmp("a+"), "aaaaaa") == "aaaaaa"
        assert PatternMatcher().match(self.cmp("a+"), "bbbbb") is None
        assert PatternMatcher().match(self.cmp("ab+"), "abbbbbb") == "abbbbbb"
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaabbbbbbbbbb") == "aaaaaabbbbbbbbbb"
        assert PatternMatcher().match(self.cmp("a+b+"), "bbbbbbbbbb") is None
        assert PatternMatcher().match(self.cmp("a+b+"), "aaaaaaa") is None
        assert PatternMatcher().match(self.cmp("(ab)+"), "abababab") == "abababab"
        assert PatternMatcher().match(self.cmp("(ab)+"), "aaabbb") is None

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

    def test_negatedcharrange(self):
        assert PatternMatcher().match(self.cmp("[^abcd]"), "a") is None
        assert PatternMatcher().match(self.cmp("[^abcd]"), "e") == "e"
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "ABCD") == "ABCD"
        assert PatternMatcher().match(self.cmp("[^a-z]+"), "abcd") is None

    def test_escaped(self):
        assert PatternMatcher().match(self.cmp("[a-z]"), "-") is None
        assert PatternMatcher().match(self.cmp("[a\-z]"), "-") == "-"
        assert PatternMatcher().match(self.cmp("#[^\-]*"), "-") is None
        assert PatternMatcher().match(self.cmp("[\[]*"), "[") == "["
        assert PatternMatcher().match(self.cmp("[\.]"), ".") == "."
        assert PatternMatcher().match(self.cmp("\."), ".") == "."
        assert PatternMatcher().match(self.cmp("\["), "[") == "["
        assert PatternMatcher().match(self.cmp("\[\]"), "[]") == "[]"

    def test_realworld_examples(self):
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "abc123_") == "abc123_"
        assert PatternMatcher().match(self.cmp("[a-zA-Z_][a-zA-Z_0-9]*"), "123abc123_") is None

        assert PatternMatcher().match(self.cmp("#[^\\r]*"), "# abc") == "# abc"
        assert PatternMatcher().match(self.cmp("#[^\r]*"), "# abc \r") == "# abc "

        assert PatternMatcher().match(self.cmp("([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "123.456") == "123.456"
        assert PatternMatcher().match(self.cmp("([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?"), "1e23") == "1e23"
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a string 123!'") == "'this is a string 123!'"
        assert PatternMatcher().match(self.cmp("\'[^\'\r]*\'"), "'this is a with a newline \r string 123!'") is None

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

class Test_Lexer(object):

    def test_simple(self):
        l = Lexer([("name", "[a-z]+"), ("num", "[0-9]+")])
        assert l.lex("abc123") == [("abc", "name", 1), ("123", "num", 0)]
        assert l.lex("456foobar9") == [("456", "num", 1), ("foobar", "name", 1), ("9", "num", 0)]

    def test_lookahead(self):
        l = Lexer([("cls", "class"), ("as", "as"), ("chr", "[a-z]")])
        assert l.lex("aclasxy") == [("a", "chr", 1), ("c", "chr", 4), ("l", "chr", 0), \
                                    ("as", "as", 0), ("x", "chr", 0), ("y", "chr", 0)]
    def test_leftover(self):
        l = Lexer([("test", "abcde|abcx")])
        assert l.lex("abcx") == [("abcx", "test", 0)]

        l = Lexer([("test", "abcde|abc")])
        assert l.lex("abcx") == [("abc", "test", 0), ("x", None, 0)]

        l = Lexer([("test", "abc|abcde")])
        assert l.lex("abcx") == [("abc", "test", 0), ("x", None, 0)]
