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

import sys
import re

whitespace = "( |\n|\r|\t)+"
nonterminal = "[a-zA-Z_0-9]+(\^\^\^|\^\^|\^|<)?"  # e.g. E, T, Nonterminal
magicterminal = "\<[a-zA-Z_0-9 \.]+\>"  # <sql>
terminal = "\"([0-9]+|[a-zA-Z_]+|\+|-|\*|\/|\&|{|}|\t| |\n|\r|,|;)\""  # e.g. a, b, +, -
terminal = "\"[^\"]*\"(\^\^\^|\^\^|\^|<)?"  # everthing except ticks
mapsto = "::="
alternative = "\|"
option_start = "\["
option_end = "\]"
loop_start = "\{"
loop_end = "\}"
group_start = "\("
group_end = "\)"

def make_groups(expressions):
    regex = []
    for name in expressions:
        s = "(?P<%s>%s)" % (name, expressions[name])
        regex.append(s)
    return r"|".join(regex)

regex = make_groups({"Nonterminal":nonterminal, "Terminal":terminal, "MagicTerminal":magicterminal, "Mapsto":mapsto,
                    "Whitespace":whitespace, "Alternative":alternative, "Option_Start":option_start,
                    "Option_End":option_end, "Loop_Start":loop_start, "Loop_End":loop_end,
                    "Group_Start":group_start, "Group_End": group_end})

class Token(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return "%s(%s)" % (self.name, self.value)

class Lexer(object):
    """
    A lexer that can be stared with a call the lex.
    """

    def __init__(self, code):
        """
        Create a lexer
        :param code: Code to lex
        """
        self.tokens = []
        self.code = code
        self.pos = 0
        self.regex = regex

    def set_regex(self, expressions):
        """
        Set the regular expressions for the various kinds of tokens to lex
        :param expressions: A Named capturing group regular expression that can lex te code
        """
        self.regex = make_groups(expressions)

    def lex(self):
        """
        Convert input stream (given at construction) to tokens.
        The lexing reuslt can be found a Lexer.tokens
        :return: Boolean indicating succes
        """
        token = self.next()
        while token is not None:
            self.pos += len(token.value)
            if token.name != "Whitespace":
                self.tokens.append(token)
            token = self.next()
        if self.pos == len(self.code):
            return True
        return False

    def next(self):
        """
        :return: The next token that is matched as a Token with the name of the capture group that captured it and as
        value the effective token as string
        """
        m = re.match(self.regex, self.code[self.pos:])
        if m:
            result = m.groupdict()
            for r in result:
                value = result[r]
                if value is not None:
                    return Token(r, value)


if __name__ == "__main__":
    l = Lexer()
    l.lex(sys.argv[1])
