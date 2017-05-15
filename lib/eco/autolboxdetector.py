from grammars.grammars import lang_dict
from incparser.astree import BOS, EOS
from grammar_parser.gparser import MagicTerminal, Terminal, Nonterminal, IndentationTerminal
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
        r.preparse(outer_root, lbox)
        return r.parse(lbox.symbol.ast.children[0].next_term)

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
            if type(term) is EOS:
                term = term.prev_term
                continue
            if  term.lookup == "<return>":
                break

            #XXX check if term is valid in any of the langs first? If not we don't need to increc
            outer_root = term.get_root()
            outer_lang = outer_root.name
            outer_parser, outer_lexer = self.langs[outer_lang]
            r = IncrementalRecognizer(outer_parser.syntaxtable, outer_lexer.lexer, outer_lang)
            result = r.preparse(outer_root, term)
            if result:
                # Check if first token is valid in one of the autobox grammars
                for langname in self.langs:
                    if r.is_valid(MagicTerminal("<%s>" % (langname,))):
                        end = self.detect_end(langname, term)
                        if end and self.contains_errornode(term, end, node):
                            return (term, end, langname)
                    else:
                        #print("Language box {} not valid at position {} in {}\n".format(langname, term, outer_lang))
                        pass
            term = term.prev_term

    def detect_end(self, lang, start):
        parser, lexer = self.langs[lang]
        #print("Language box valid. Find lbox end")
        if lexer.indentation_based:
            r = RecognizerIndent(parser.syntaxtable, lexer.lexer, lang)
        else:
            r = Recognizer(parser.syntaxtable, lexer.lexer, lang)
        end = r.parse(start)
        end = self.adjust_end(end)
        return end

    def adjust_end(self, end):
        """Remove newlines/whitespace from end"""
        if end is None:
            return None
        while True:
            if end.lookup not in ["<ws>", "<return>"]:
                break
            end = end.prev_term
        return end

    def contains_errornode(self, start, end, error):
        while True:
            if start is error:
                return True
            if start is end:
                break
            start = start.next_term
        return False

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
        if self.lang == "Python + PHP":
            return token.name in ["def"]
        elif self.lang == "SQL":
            return token.name in ["SELECT"]
        elif self.lang == "SQL Statement":
            return token.name in ["SELECT"]
        elif self.lang == "Python expression":
            return token.name in ["[", "NUMBER"]
        elif self.lang == "SimpleLanguage":
            return token.name in ["function"]
        elif self.lang == "HTML":
            return token.name.startswith("<") and token.name not in ["<ws>", "<return>"]
        elif self.lang.find("Python") > -1: # other Python derivatives
            return token.name in ["def"]
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
            # use NEWLINE to reduce everything, shift newline then try to shift
            # DEDENT
            if self.is_finished():
                while self.indents:
                    self.todo.append(Terminal("DEDENT"))
                    self.indents.pop()
                self.todo.append(Terminal("NEWLINE"))
                self.last_read = tok1[3][-1]
                return Terminal(tok1[1])
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

    def is_finished(self):
        states = list(self.state)
        if self.temp_parse(states, Terminal("NEWLINE")):
            # XXX need to test ALL dedents not just one
            # XXX also can just check for shift which should be enough
            if self.temp_parse(states, Terminal("DEDENT")):
                return True
        return False

    def temp_parse(self, states, terminal):
        while True:
            element = self.syntaxtable.lookup(states[-1], terminal)
            if type(element) is Shift:
                states.append(element.action)
                return True
            elif type(element) is Reduce:
                i = 0
                while i < element.amount():
                   states.pop()
                   i += 1
                goto = self.syntaxtable.lookup(states[-1], element.action.left)
                assert isinstance(goto, Goto)
                states.append(goto.action)
                continue
            else:
                return False

class IncrementalRecognizer(Recognizer):

    def preparse(self, outer_root, stop):
        """Puts the recogniser into the state just before `stop`."""
        #print("Preparsing {} upto {}".format(outer_root, stop))
        path_to_stop = set()
        parent = stop.parent
        while parent is not None:
            path_to_stop.add(parent)
            parent = parent.parent

        # setup parser to the state just before lbox
        node = outer_root.children[1]
        while True:
            if node.deleted:
                node = node.right
                continue
            if node is stop:
                # Reached stop node
                return True
            if node not in path_to_stop:
                # Skip/Shift nodes that are not parents of the language box
                lookup = self.get_lookup(node)
                element = self.syntaxtable.lookup(self.state[-1], lookup)
                if type(element) is Goto:
                    self.state.append(element.action)
                elif type(element) is Shift:
                    self.state.append(element.action)
                elif type(element) is Reduce:
                    i = 0
                    while i < element.amount():
                       self.state.pop()
                       i += 1
                    goto = self.syntaxtable.lookup(self.state[-1], element.action.left)
                    assert isinstance(goto, Goto)
                    self.state.append(goto.action)
                    continue
                else:
                    return False
                node  = node.right
            else:
                if node.children:
                    node = node.children[0]
                else:
                    node = node.right

    def is_valid(self, token):
        """Checks if a token is valid in the current state."""
        state = list(self.state)
        while True:
            element = self.syntaxtable.lookup(state[-1], token)
            #print("Checking validity of {} in state {}: {}".format(token, state, element))
            if type(element) is Shift:
                state.append(element.action)
                return True
            elif type(element) is Reduce:
                i = 0
                while i < element.amount():
                   state.pop()
                   i += 1
                goto = self.syntaxtable.lookup(state[-1], element.action.left)
                assert isinstance(goto, Goto)
                state.append(goto.action)
            else:
                #print("Error on", token, state)
                return False
        return False

    def get_lookup(self, la):
        """Get the lookup symbol of a node. If no such lookup symbol exists use
        the nodes symbol instead."""
        if la.lookup != "":
            lookup_symbol = Terminal(la.lookup)
        else:
            lookup_symbol = la.symbol
        if isinstance(lookup_symbol, IndentationTerminal):
            #XXX hack: change parsing table to accept IndentationTerminals
            lookup_symbol = Terminal(lookup_symbol.name)
        return lookup_symbol

    def parse(self, node):
        """Parse normally starting at `node`."""

        # try parsing lbox content in outer language
        result = Recognizer.parse(self, node, valid_override=True)
        if self.reached_eos:
            #after_lbox = lbox.next_term
            # XXX validate language box by checking if the next token after the
            # language box has been shifted is valid (reduce/shift)
            return True
        return False

