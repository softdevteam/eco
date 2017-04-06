from grammars.grammars import lang_dict
from incparser.astree import BOS, EOS
from grammar_parser.gparser import MagicTerminal, Terminal
from incparser.syntaxtable import Shift, Reduce, Goto, Accept

class AutoLBoxDetector(object):

    def __init__(self):
        self.langs = {}

    def init_language(self, langname):
        if langname in self.langs:
            return

        main = lang_dict[langname]
        self.langs[langname] = main.load()

        for sub in main.included_langs:
            self.init_language(sub)

    def detect_languagebox(self, node):
        # Get current language
        mainlang = node.get_root().name
        parser, _ = self.langs[mainlang]

        # Find beginning terminal
        term = node
        while True:
            # get most left terminal
            if type(term) is BOS:
                break

            # Check if first token is valid in one of the autobox grammars
            for langname in self.langs:
                p, l = self.langs[langname]
                state = term.prev_term.state
                result = parser.is_valid_symbol(state, MagicTerminal("<%s>" % (langname,)))
                if result:
                    end = self.detect_end(langname, term)
                    if end:
                       return (term, end, langname)
            term = term.prev_term

    def detect_end(self, lang, start):
        if type(start) is EOS:
            return None
        parser, lexer = self.langs[lang]
        if lexer.indentation_based:
            r = RecognizerIndent(parser.syntaxtable, lexer.lexer, lang)
        else:
            r = Recognizer(parser.syntaxtable, lexer.lexer, lang)
        end = r.parse(start)
        return end

from inclexer.inclexer import StringWrapper
from cflexer.lexer import LexingError
from incparser.incparser import FinishSymbol

class Recognizer(object):
    """A parser that simulates parsing some input without actually creating a
    parse tree. Used to test if some input is valid in some language."""

    def __init__(self, syntaxtable, lexer, lang):
        self.syntaxtable = syntaxtable
        self.lexer = lexer
        self.lang = lang
        self.state = [0]

    def parse(self, startnode):
        self.tokeniter = self.lexer.get_token_iter(StringWrapper(startnode, startnode))
        token = self.next_token()
        if not self.valid_start(token):
            return None
        while True:
            element = self.syntaxtable.lookup(self.state[-1], token)
            if isinstance(element, Shift):
                self.state.append(element.action)
                token = self.next_token()
                continue
            elif isinstance(element, Reduce):
                i = 0
                while i < element.amount():
                   self.state.pop()
                   i += 1
                goto = self.syntaxtable.lookup(self.state[-1], element.action.left)
                assert isinstance(goto, Goto)
                self.state.append(goto.action)
                continue
            elif isinstance(element, Accept):
                return self.last_read[-1]
            else:
                return None

    def next_token(self):
        try:
            t = self.tokeniter()
            self.last_read = t[3]
            return Terminal(t[1])
        except StopIteration:
           return FinishSymbol() # No more tokens to read
        except LexingError:
           return FinishSymbol() # Couldn't continue lexing with given language

    def valid_start(self, token):
        if self.lang.find("Python") > -1:
            if token.name in ["def"]:
                return True
        elif self.lang == "SQL":
            return token.name in ["SELECT"]
        elif self.lang == "Python expression":
            return token.name in ["["]
        return False

class RecognizerIndent(Recognizer):

    def __init__(self, syntaxtable, lexer, lang):
        Recognizer.__init__(self, syntaxtable, lexer, lang)
        self.todo = []
        self.indents = [0]

    def get_token_iter(self):
        try:
            return self.tokeniter()
        except StopIteration:
            return None
        except LexingError:
            return None

    def next_token(self):

        if self.todo:
           return self.todo.pop()

        tok1 = self.get_token_iter()
        if tok1 is None:
            # XXX generate remaining dedents?
            self.todo.append(FinishSymbol())
            self.todo.append(Terminal("NEWLINE"))
            while self.indents[-1] != 0:
                self.todo.append(Terminal("DEDENT"))
                self.indents.pop()
            return self.todo.pop()
        elif tok1[1] != "<return>":
            self.last_read = tok1[3]
            return Terminal(tok1[1])
        else:
            tok2 = self.get_token_iter()
            if tok2 is None:
                # non logical line -> parse <return> normally
                return Terminal(tok1[1])
            # XXX get tok3 and check it's not whitespace/comment
            ws_len = 0
            if tok2[1] == "<ws>":
                ws_len = len(tok2[0])

            if ws_len > self.indents[-1]:
                # create NEWLINE INDENT
                self.todo.append(Terminal("INDENT"))
                self.todo.append(Terminal("NEWLINE"))
                self.indents.append(ws_len)
            elif ws_len == self.indents[-1]:
                self.todo.append(Terminal("NEWLINE"))
            else:
                while ws_len < self.indents[-1]:
                    self.todo.append(Terminal("DEDENT"))
                    self.indents.pop()
                self.todo.append(Terminal("NEWLINE"))
            return Terminal(tok1[1]) # parse <return> token first

