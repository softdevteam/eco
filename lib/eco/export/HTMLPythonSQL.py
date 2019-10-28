# Copyright (c) 2014 King's College London
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
from . import helper


class Outer_HTML(helper.Generic):
    def __init__(self):
        helper.Generic.__init__(self)
        self.buf_html = []

    def pp(self, node):
        self.walk(node)
        self.flush_html()
        o = "".join(self.buf)
        # XXX the way we search for a variable and generate a function with a
        # fixed name is obviously fragile. This should use a name which we know
        # isn't bound in any other way.
        m = re.search("([a-zA-Z_][a-zA-Z_0-9]*) = sqlite3.connect", o)
        if m:
            o = """
def gen_exec(query):
    try:
        _c = %s.cursor()
        _c.execute(query)
        while True:
            o = _c.fetchone()
            if o == None:
                break
            yield o
    finally:
        _c.close()

%s
""" % (m.group(1), o)
        return o

    def language_box(self, name, node):
        self.flush_html()
        if name == "<Python + HTML + SQL>":
            self.buf.append(Python().pp(node))
            self.buf.append("\n")
        elif name == "<Image>":
            self.buf.append(Image().pp(node))
        else:
            helper.bad_node(name)

    def text(self, text):
        self.buf_html.append(text)

    def flush_html(self):
        j = "".join(self.buf_html)
        if len(j) > 0:
            self.buf.append("print \"\"\"%s\"\"\"\n" % _escape(j))
        self.buf_html = []


class Python(helper.Generic):
    def language_box(self, name, node):
        if name == "<SQL>":
            self.buf.append("gen_exec(\"\"\"%s\"\"\")" % _escape(SQL().pp(node)))
        elif name == "<HTML>":
            self.buf.append(Nested_HTML().pp(node))
        else:
            helper.bad_node(name)

class Image(helper.Generic):
    def pp(self, node):
        self.walk(node)
        return "print \"%s\"\n" % "".join(self.buf)

class SQL(helper.Generic):
    pass


class Nested_HTML(helper.Generic):
    def pp(self, node):
        self.walk(node)
        return "\"\"\"%s\"\"\"" % _escape("".join(self.buf))


def _escape(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'")


def export(node):
    return Outer_HTML().pp(node)
