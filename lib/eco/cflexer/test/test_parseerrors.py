import py
from cflexer.parsing import PackratParser, Rule, Nonterminal
from cflexer.parsing import Symbol, ParseError
from cflexer.ebnfparse import parse_ebnf, make_parse_function
from cflexer.deterministic import LexerError
from cflexer.tree import RPythonVisitor

class TestDictError(object):
    dictebnf = """
        QUOTED_STRING: "'[^\\']*'";
        IGNORE: " |\n";
        data: <dict> | <QUOTED_STRING> | <list>;
        dict: ["{"] (dictentry [","])* dictentry ["}"];
        dictentry: QUOTED_STRING [":"] data;
        list: ["["] (data [","])* data ["]"];
    """

    def setup_class(cls):
        regexs, rules, ToAST = parse_ebnf(cls.dictebnf)
        cls.ToAST = ToAST
        parse = make_parse_function(regexs, rules, eof=True)
        cls.parse = staticmethod(parse)

    def test_lexererror(self):
        py.test.skip("inclexer doesn't raise errors")
        excinfo = py.test.raises(LexerError, self.parse, """
{
    'type': 'SCRIPT',$#
    'funDecls': '',
    'length': '1',
}""")
        msg = excinfo.value.nice_error_message("<stdin>")
        print msg
        assert msg == """\
  File <stdin>, line 2
    'type': 'SCRIPT',$#
                     ^
LexerError"""

    def test_parseerror(self):
        source = """
{
    'type': 'SCRIPT',
    'funDecls': '',
    'length':: '1',
}"""
        excinfo = py.test.raises(ParseError, self.parse, source)
        error = excinfo.value.errorinformation
        source_pos = excinfo.value.source_pos
        assert source_pos.lineno == 4
        assert source_pos.columnno == 13
        msg = excinfo.value.nice_error_message("<stdin>", source)
        print msg
        assert msg == """\
  File <stdin>, line 4
    'length':: '1',
             ^
ParseError: expected '{', 'QUOTED_STRING' or '['"""
