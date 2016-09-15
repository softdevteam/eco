# Copyright (c) 2012--2013 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from lexer import Lexer

class Rule(object):

    def __init__(self, symbol=None):
        self.symbol = symbol
        self.alternatives = []
        self.annotations = []
        self.precs = []
        self.inserts = {}

    def add_alternative(self, alternative, annotation=None, prec=None):
        # create symbol for empty alternative
        self.alternatives.append(alternative)
        self.annotations.append(annotation)
        self.precs.append(prec)

    def __repr__(self):
        return "Rule(%s => %s)" % (self.symbol, self.alternatives)

class Symbol(object):
    def __init__(self, name="", folding=None):
        self.name = name
        self.folding = folding

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        #XXX unsafe hashfunction
        return hash(self.__class__.__name__ + self.name)

    def copy(self):
        return self.__class__(self.name, self.folding)

    

class Terminal(Symbol):
    def __repr__(self):
        return "Terminal('%s')" % (repr(self.name),)

class MagicTerminal(Terminal):
    def __repr__(self):
        return "MagicTerminal('%s')" % (repr(self.name),)

class IndentationTerminal(Terminal):
    def __repr__(self):
        return "IndentationTerminal('%s')" % (repr(self.name),)

class Nonterminal(Symbol):
    def __repr__(self):
        return "Nonterminal('%s')" % (self.name,)

class Epsilon(Symbol):

    def __eq__(self, other):
        return isinstance(other, Epsilon)

    def __repr__(self):
        return self.__class__.__name__

    def __hash__(self):
        #XXX why doesn't Epsilon inherit this method from Symbol!?
        return hash(self.__class__.__name__ + self.name)

class ExtendedSymbol(object):

    def __init__(self, name, children):
        self.children = children
        self.name = name

    def __repr__(self):
        return "%s(%s)" % (self.name, self.children)

class Parser(object):

    def __init__(self, code, whitespaces=False):
        self.lexer = Lexer(code)
        self.lexer.lex()
        self.curtok = 0
        self.start_symbol = None
        self.rules = {}
        self.whitespaces = whitespaces

    def __repr__(self):
        s = []
        for r in self.rules:
            s.append(r.__repr__())
        return "\n".join(s)

    def parse(self):
        while self.curtok < len(self.lexer.tokens):
            rule = self.parse_rule()

            if not self.start_symbol:
                self.start_symbol = rule.symbol

            self.rules[rule.symbol] = rule
            self.transform_ebnf(rule)

        # add whitespace rule
        if self.whitespaces:
            ws_rule = Rule()
            ws_rule.symbol = Nonterminal("WS")
            ws_rule.add_alternative([Terminal("<ws>", "^"), Nonterminal("WS", "^")])
            ws_rule.add_alternative([Terminal("<return>", "^"), Nonterminal("WS", "^")])
            ws_rule.add_alternative([]) # or empty
            self.rules[ws_rule.symbol] = ws_rule

            self.start_symbol.folding = "^^"
            # allow whitespace/comments at beginning of file
            start_rule = Rule()
            start_rule.symbol = Nonterminal("Startrule")
            start_rule.add_alternative([Nonterminal("WS", "^"), self.start_symbol])
            self.rules[start_rule.symbol] = start_rule
            self.start_symbol = start_rule.symbol

    def transform_ebnf(self, original_rule):
        # XXX can be made faster by setting a flag if there is a ebnf token
        # in the rule or not (can be done in first parse)
        new_rules = []
        for a in original_rule.alternatives:
            i = 0
            for s in a:
                if isinstance(s, ExtendedSymbol):
                    if s.name == "loop":
                        # Example: A ::= a {b} c
                        remaining_tokens = a[i+1:] # [c]
                        loop_symbol = Nonterminal("%s_loop" % (original_rule.symbol.name,))
                        a[i:] = [loop_symbol] # A ::= a A_loop

                        newrule = Rule()
                        newrule.symbol = loop_symbol
                        newrule.add_alternative(s.children + [loop_symbol]) # A_loop ::= b A_loop
                        newrule.add_alternative(remaining_tokens)           #          | c (or epsilon)
                        new_rules.append(newrule)
                    if s.name == "option":
                        # Example: A ::= a [b] c
                        remaining_tokens = a[i+1:] # [c]
                        option_symbol = Nonterminal("%s_option" % (original_rule.symbol.name,))
                        a[i:] = [option_symbol] # A ::= a A_option

                        newrule = Rule()
                        newrule.symbol = option_symbol
                        newrule.add_alternative(s.children + remaining_tokens) # A_option ::= b c
                        newrule.add_alternative(remaining_tokens)              #            | c
                        new_rules.append(newrule)
                    if s.name == "group":
                        # Example: A ::= a [b | c] d
                        remaining_tokens = a[i+1:] # [c]
                        group1_symbol = Nonterminal("%s_group1" % (original_rule.symbol.name,))
                        group2_symbol = Nonterminal("%s_group2" % (original_rule.symbol.name,))
                        a[i:] = [group1_symbol] # A ::= a A_group

                        newrule = Rule()
                        newrule.symbol = group1_symbol
                        for c in s.children:
                            newrule.add_alternative([c, group2_symbol]) # A_option ::= b A_option2 | c A_option2
                        new_rules.append(newrule)

                        newrule = Rule()
                        newrule.symbol = group2_symbol
                        newrule.add_alternative(remaining_tokens)              # A_option2 ::= d
                        new_rules.append(newrule)
                i += 1
        for rule in new_rules:
            self.rules[rule.symbol] = rule
            self.transform_ebnf(rule)

    def inc(self):
        self.curtok += 1

    def next_token(self):
        t = self.lexer.tokens[self.curtok]
        return t

    def parse_rule(self):
        symbols_level = []
        rule = Rule()
        rule.symbol = self.parse_nonterminal()

        self.parse_mappingsymbol()

        # find beginning of next rule
        i = self.curtok
        while i < len(self.lexer.tokens):
            if self.lexer.tokens[i].name == "Mapsto":
                i = i - 1 # go back to end of last rule
                break
            i += 1

        tokenlist = self.lexer.tokens[self.curtok:i]

        # skip to next rule for further parsing
        self.curtok += len(tokenlist)

        # parse right side of rule
        # XXX rewrite Loop, Option, Group into separate methods (getting rid of
        # the symbols_level and adding the pipe check to group
        symbols_level.append([]) # first symbols level
        mode = None
        i = 0
        for t in tokenlist:
            if t.name == "Nonterminal":
                if t.value.endswith("^^^"):
                    nt = Nonterminal(t.value[:-3], "^^^")
                elif t.value.endswith("^^"):
                    nt = Nonterminal(t.value[:-2], "^^")
                elif t.value.endswith("^"):
                    nt = Nonterminal(t.value[:-1], "^")
                elif t.value.endswith("<"):
                    nt = Nonterminal(t.value[:-1], "<")
                    rule.inserts[len(rule.alternatives)] = (i, nt)
                    continue
                else:
                    nt = Nonterminal(t.value)
                symbols_level[-1].append(nt)
                i = i + 1
            elif t.name == "Terminal":
                if t.value.endswith("^^^"):
                    stripped = t.value[:-3].strip("\"")
                    terminal = Terminal(stripped, "^^^")
                elif t.value.endswith("^^"):
                    stripped = t.value[:-2].strip("\"")
                    terminal = Terminal(stripped, "^^")
                elif t.value.endswith("^"):
                    stripped = t.value[:-1].strip("\"")
                    terminal = Terminal(stripped, "^")
                else:
                    stripped = t.value.strip("\"")
                    terminal = Terminal(stripped)
                symbols_level[-1].append(terminal)
                i = i + 1
                if self.whitespaces:
                    symbols_level[-1].append(Nonterminal("WS", "^"))
                    i = i + 1
            elif t.name == "MagicTerminal":
                symbols_level[-1].append(MagicTerminal(t.value))
                i = i + 1
                if self.whitespaces:
                    symbols_level[-1].append(Nonterminal("WS", "^"))
            elif t.name == "Alternative":
                if mode == None:
                    rule.add_alternative(symbols_level.pop())
                    symbols_level.append([])
                    i = 0
            elif t.name in ["Loop_Start", "Option_Start", "Group_Start"]:
                symbols_level.append([])
                if t.name == "Group_Start":
                    mode = "group"
            elif t.name == "Loop_End":
                symbols = symbols_level.pop()
                token = ExtendedSymbol("loop", symbols)
                symbols_level[-1].append(token)
            elif t.name == "Option_End":
                symbols = symbols_level.pop()
                token = ExtendedSymbol("option", symbols)
                symbols_level[-1].append(token)
            elif t.name == "Group_End":
                symbols = symbols_level.pop()
                token = ExtendedSymbol("group", symbols)
                symbols_level[-1].append(token)
                mode = None


        assert symbols_level[0] is symbols_level[-1]
        rule.add_alternative(symbols_level[-1])
        return rule

    def parse_nonterminal(self):
        t = self.next_token()
        assert t.name == "Nonterminal"
        self.inc()
        return Nonterminal(t.value)

    def parse_mappingsymbol(self):
        t = self.next_token()
        assert t.name == "Mapsto"
        self.inc()
