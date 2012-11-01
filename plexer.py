import re

class PriorityLexer(object):

    terminal = ""

    def __init__(self, code):
        self.code = code
        self.pos = 0
        self.rule_count = 0
        self.rules = {}

        self.eat_all()

    def priority(self, name):
        return self.rules[name][0]

    def class_type(self, name):
        return self.rules[name][1]

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

    def eat_terminal(self):
        self.eat_char("\"")
        m = re.match("[^\"]*", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)
        self.eat_char("\"")
        return result

    def eat_name(self):
        m = re.match("[a-zA-Z0-9]+", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)
            return result

    def eat_char(self, char):
        if self.code[self.pos] == char:
            self.pos += 1
        else:
            raise Exception("Couldn't find char:", char)

    def eat_whitespace(self):
        m = re.match("\s*", self.code[self.pos:])
        if m:
            result = m.group(0)
            self.pos += len(result)
