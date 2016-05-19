# Copyright (c) 2015--2016 King's College London
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

import tempfile
import subprocess

from incparser.annotation import Annotation, ToolTip, Heatmap

from PyQt4.QtCore import QSettings
from incparser.astree import EOS
from grammar_parser.gparser import MagicTerminal, IndentationTerminal


class JRubyCoverageCounterMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip()]
        super(JRubyCoverageCounterMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyCoverageCounterVal(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(JRubyCoverageCounterVal, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class JRubyJavaScriptExporter(object):
    def __init__(self, tm):
        self.tm = tm  # TreeManager object.
        self.js_functions = dict()
        self._js_output = list()
        self._wrappers = list()
        self._output = list()
        self._js_functions = list()

    def export(self, path=None, run=False):
        if path is not None:
            self._export_as_text(path)
            return
        if run:
            return self._run()

    def _language_box(self, name, node):
        if name == "<Ruby + JavaScript>":
            self._walk_rb(node)
        elif name == "<JavaScript>":
            self._walk_js(node)

    def _walk_js(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            if isinstance(sym, MagicTerminal):
                self._language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                self._js_output.append(sym)
            elif sym.name == "function":
                self._js_functions.append(node.next_term.next_term.symbol.name)
                self._js_output.append(sym.name)
            elif sym.name == "\r":
                self._js_output.append("\n")
            else:
                self._js_output.append(sym.name)

    def _walk_rb(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            if isinstance(sym, MagicTerminal):
                self._language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                self._output.append(sym)
            elif sym.name == "\r":
                self._output.append("\n")
            else:
                self._output.append(sym.name)

    def _apply_template(self, name):
        return "Truffle::Interop.import_method(:%s)" % name

    def _export_as_text(self, path):
        node = self.tm.lines[0].node # first node
        self._walk_rb(node)
        for func in self._js_functions:
            self._wrappers.append(self._apply_template(func))
        output = "Truffle::Interop.eval('application/x-javascript', %{\n"
        output += "".join(self._js_output)
        output += "})\n\n"
        output += "\n".join(self._wrappers)
        output += "\n\n"
        rb_code = "".join(self._output)
        output += rb_code
        with open(path, "w") as fp:
            fp.write("".join(output))

    def _run(self):
        f = tempfile.mkstemp(suffix=".rb")
        settings = QSettings('softdev', 'Eco')
        graalvm_bin = str(settings.value('env_graalvm', '').toString())
        jruby_bin = str(settings.value('env_jruby', '').toString())
        js_jar = str(settings.value('env_js_jar', '').toString())
        truffle_jar = str(settings.value('env_truffle_jar', '').toString())
        jars = js_jar + ':' + truffle_jar

        self._export_as_text(f[1])
        if graalvm_bin:
            return subprocess.Popen([jruby_bin, "-X+T",
                                     "-J-classpath", jars, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0,
                                    env={'JAVACMD':graalvm_bin})
        else:
            return subprocess.Popen([jruby_bin, "-X+T",
                                     "-J-classpath", jars, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0)
