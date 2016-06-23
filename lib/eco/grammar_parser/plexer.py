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

import re

class PriorityLexer(object):

    terminal = ""

    def __init__(self, code):
        self.code = code
        self.pos = 0
        self.rule_count = 0
        self.rules = {}

        self.eat_all_regex()

        self.test_rules()

        # compile regex
        self.compiled_regex = {}
        for k in self.rules:
            c = re.compile("^"+k+"$")
            self.compiled_regex[k] = c

    def test_rules(self):
        import re
        for rule in self.rules:
            try:
                m = re.match(rule, "")
            except re.error:
                print("Not a regular expression:", rule)

    def priority(self, text):
        for k in self.rules.keys():
            m = re.match("^"+k+"$", text)
            if m:
                return self.rules[k][0]
        return ""

    def name(self, text):
        rules = []
        for k in self.rules.keys():
            regex = k
            lookup = self.rules[k][1]
            pos = self.rules[k][0]
            rules.append((pos, regex, lookup))

        # sort by priority
        rules = sorted(rules, key=lambda node: node[0])
        for k in rules:
            m = re.match("^("+k[1]+")$", text)
            if m:
                return k[2]
        return ""

    def regex(self, text):
        for k in self.rules.keys():
            m = self.compiled_regex[k].match(text)
            if m:
                return k
        return ""

    def matches(self, text, cls):
        for k in self.rules.keys():
            #m = re.match("^("+k+")$", text)
            m = self.compiled_regex[k].match(text)
            if m:
                return True
        return False

    def eat_all(self):
        while self.pos < len(self.code):
            self.eat_whitespace()
            self.eat_rule()
            self.eat_whitespace()

    def eat_rule(self):
        terminal = self.eat_terminal()
        self.eat_char(":")
        name = self.eat_name()
        self.rules[terminal] = (self.rule_count, name)
        self.rule_count += 1

    def eat_all_regex(self):
        for x in self.code.split("\n"):
            self.eat_rule_regex(x)

    def eat_rule_regex(self, x):
        m = re.match("\"(.*)\":(.*)", x)
        if m:
            regex = m.group(1)
            name = m.group(2)
            self.rules[regex] = (self.rule_count, name)
            self.rule_count += 1

    def eat_terminal(self):
        self.eat_char("\"")
        m = re.match("[^\"]*", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)
        self.eat_char("\"")
        return result

    def eat_name(self):
        m = re.match("[^\n]*", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)
            return result

    def eat_char(self, char):
        if self.code[self.pos] == char:
            self.pos += 1
        else:
            raise Exception("Couldn't find char:", char, ". Found instead:", self.code[self.pos], "at", self.code[self.pos-10:self.pos+10])

    def eat_whitespace(self):
        m = re.match("\s*", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)

    def get_all_possible_chars(self, terminal):
        import string
        chars = set()
        if len(re.findall("\[.*a-z.*\]", terminal)) > 0:
            chars |= set(list(string.ascii_lowercase))
        if len(re.findall("\[.*A-Z.*\]", terminal)) > 0:
            chars |= set(list(string.ascii_lowercase))
        if len(re.findall("\[.*0-9.*\]", terminal)) > 0:
            chars |= set(list(string.ascii_lowercase))
