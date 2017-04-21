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

    def detect_autoremove(self, lbox):
        outer_root = lbox.get_root()
        outer_lang = outer_root.name
        outer_parser, outer_lexer = self.langs[outer_lang]
        r = IncrementalRecognizer(outer_parser.syntaxtable, outer_lexer.lexer, outer_lang)
        return r.parse(outer_root, lbox)

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
        self.reached_eos = False

    def parse(self, startnode, valid_override=False):
        self.tokeniter = self.lexer.get_token_iter(StringWrapper(startnode, startnode))
        token = self.next_token()
        if not valid_override and not self.valid_start(token):
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
                return self.last_read
            else:
                if not isinstance(token, FinishSymbol):
                    self.last_read = self.last_read.prev_term
                    token = FinishSymbol()
                    continue
                return None

    def next_token(self):
        try:
            t = self.tokeniter()
            self.last_read = t[3][-1]
            return Terminal(t[1])
        except StopIteration:
            self.reached_eos = True
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
            self.last_read = tok1[3][-1]
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

class IncrementalRecognizer(Recognizer):
    def parse(self, outer_root, lbox):
        # Start parsing incrementally from BOS. Parsing was successful if we
        # reached and parsed the last node of the language box.
        path_to_lbox = set()
        parent = lbox.parent
        while parent is not None:
            path_to_lbox.add(parent)
            parent = parent.parent

        # setup parser to the state just before lbox
        node = outer_root.children[1]
        while True:
            if node is lbox:
                # Reached lbox
                break
            if node not in path_to_lbox:
                # Skip/Shift nodes that are not parents of the language box
                goto = self.syntaxtable.lookup(self.state[-1], node.symbol)
                if goto:
                    self.state.append(goto.action)
                else:
                    return False
                node  = node.right
            else:
                if node.children:
                    node = node.children[0]
                else:
                    node = node.right

        # try parsing lbox content in outer language
        lbox_start = lbox.symbol.ast.children[0].next_term
        result = Recognizer.parse(self, lbox_start, valid_override=True)
        if self.reached_eos:
            after_lbox = lbox.next_term
            # XXX validate language box by checking if the next token after the
            # language box has been shifted is valid (reduce/shift)
            return True
        return False

