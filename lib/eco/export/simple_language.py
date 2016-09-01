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

from PyQt4.QtCore import QSettings


class SimpleLanguageExporter(object):
    def __init__(self, tm):
        self.tm = tm  # TreeManager object.

    def export(self, path=None, run=False):
        if path is not None:
            self._export_as(path)
            return
        if run:
            return self._run()

    def _export_as(self, path):
        self.tm.export_as_text(path)

    def _run(self):
        f = tempfile.mkstemp(suffix=".sl")
        self.tm.export_as_text(f[1])
        settings = QSettings('softdev', 'Eco')
        graalvm_bin = str(settings.value('env_graalvm', '').toString())
        sl_jar = str(settings.value('env_sl_jar', '').toString())
        truffle_jar = str(settings.value('env_truffle_jar', '').toString())
        jars = sl_jar + ':' + truffle_jar
        main = 'com.oracle.truffle.sl.SLLanguage'
        if graalvm_bin:
            return subprocess.Popen(['java', '-cp', jars, main, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0,
                                    env={'JAVACMD':graalvm_bin})
        else:
            return subprocess.Popen(['java', '-cp', jars, main, f[1]],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    bufsize=0)
