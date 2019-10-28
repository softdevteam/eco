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

import logging
import os
import os.path
import tempfile
import subprocess

from PyQt5.QtCore import QSettings
from incparser.astree import EOS
from export.jruby import JRubyCallgraphProcessor
from grammar_parser.gparser import MagicTerminal, IndentationTerminal


class JRubyJavaScriptExporter(object):
    def __init__(self, tm):
        self.tm = tm  # TreeManager object.
        self.js_functions = dict()
        self._js_output = list()
        self._wrappers = list()
        self._output = list()
        self._js_functions = list()

    def export(self, path=None, run=False, profile=False):
        if path is not None:
            self._export_as_text(path)
            return
        if run:
            return self._run()
        elif profile:
            return self._profile()

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
        output = "Truffle::Interop.eval('application/javascript', %{\n"
        output += "".join(self._js_output)
        for func in self._js_functions:
            output += "Interop.export('%s', %s.bind(this));\n" % (func, func)
        output += "})\n\n"
        output += "\n".join(self._wrappers)
        output += "\n\n"
        rb_code = "".join(self._output)
        output += rb_code
        with open(path, "w") as fp:
            fp.write("".join(output))

    def _run(self):
        f = tempfile.mkstemp(suffix=".rb")
        settings = QSettings("softdev", "Eco")
        graalvm_bin = str(settings.value("env_graalvm", "").toString())
        jruby_bin = str(settings.value("env_jruby", "").toString())
        js_jar = str(settings.value("env_js_jar", "").toString())
        truffle_jar = str(settings.value("env_truffle_jar", "").toString())
        jars = js_jar + ":" + truffle_jar

        self._export_as_text(f[1])
        if graalvm_bin:
            return subprocess.Popen([jruby_bin, "-X+T",
                                     "-J-classpath", jars, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0,
                                    env={"JAVACMD":graalvm_bin})
        else:
            return subprocess.Popen([jruby_bin, "-X+T",
                                     "-J-classpath", jars, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0)

    def _profile(self):
        callgraph_processor = JRubyCallgraphProcessor(self.tm)

        _, src_file_name = tempfile.mkstemp(suffix=".rb")
        self._export_as_text(src_file_name)

        log_file_name = os.path.join("/",
                                     "tmp",
                                     next(tempfile._get_candidate_names()) + ".txt")
        logging.debug("Placing callgraph trace in", log_file_name)

        # Run this command:
        #  $ jruby -X+T ... -Xtruffle.callgraph=true -Xtruffle.callgraph.write=test.txt -Xtruffle.dispatch.cache=2 FILE
        settings = QSettings("softdev", "Eco")
        graalvm_bin = str(settings.value("env_graalvm", "").toString())
        jruby_bin = str(settings.value("env_jruby", "").toString())
        js_jar = str(settings.value("env_js_jar", "").toString())
        truffle_jar = str(settings.value("env_truffle_jar", "").toString())
        jars = js_jar + ":" + truffle_jar
        pic_size = str(settings.value("graalvm_pic_size", "").toString())
        cmd = [jruby_bin, "-X+T", "-J-classpath", jars,
               "-Xtruffle.callgraph=true",
               "-Xtruffle.callgraph.write=" + log_file_name,
               "-Xtruffle.dispatch.cache=" + pic_size,
               src_file_name]
        logging.debug("Running command: " + " ".join(cmd))
        settings = QSettings("softdev", "Eco")
        graalvm_bin = str(settings.value("env_graalvm", "").toString())
        subprocess.call(cmd, env={"JAVACMD":graalvm_bin})

        return callgraph_processor.annotate_tree(src_file_name, log_file_name)
