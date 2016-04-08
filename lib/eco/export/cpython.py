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

from mocks import MockPopen
from incparser.annotation import Annotation, Heatmap, Footnote, ToolTip
import copy, os, os.path, subprocess, tempfile

class CPythonFuncProfileMsg(Annotation):
    def __init__(self, annotation):
        self._hints = [ToolTip(), Footnote()]
        super(CPythonFuncProfileMsg, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class CPythonFuncProfileVal(Annotation):
    def __init__(self, annotation):
        self._hints = [Heatmap()]
        super(CPythonFuncProfileVal, self).__init__(annotation)

    def get_hints(self):
        return self._hints


class CPythonExporter(object):
    def __init__(self, tm):
        self.tm = tm

    def export(self, path, run, profile):
        if profile:
            return self._profile()
        elif run:
            return self._run()
        else:
            f = tempfile.mkstemp()
            self.tm.export_as_text(f[1])

    def _run(self):
        f = tempfile.mkstemp()
        self.tm.export_as_text(f[1])
        return subprocess.Popen(["python2", f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)


    def _profile(self):
        f = tempfile.mkstemp()
        self.tm.export_as_text(f[1])
        # Delete any stale profile info
        self.tm.profile_is_dirty = False
        self.tm.profile_map = dict()
        self.tm.profile_data = dict()
        # python -m cProfile [-o output_file] [-s sort_order] myscript.py
        proc = subprocess.Popen(["python2", "-m", "cProfile", f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        stdout_value, stderr_value = proc.communicate()
        # Mock Popen here, so that we can return a Popen-like object.
        # This allows Eco to append the output of the profiler
        # to the console.
        mock = MockPopen(copy.copy(stdout_value), copy.copy(stderr_value))
        # Lex profiler output:
        # ncalls  tottime  percall  cumtime  percall fname:lineno(fn)
        table = False
        temp_cursor = self.tm.cursor.copy()
        ncalls_dict = dict()
        for line in stdout_value.split('\n'):
            tokens = line.strip().split()
            if not tokens:
                continue
            elif len(tokens) < 6:
                continue
            elif not table:
                if tokens[0] == 'ncalls':
                    table = True
            else:
                if not ':' in tokens[5]:
                    continue
                fname, loc = tokens[5].split(':')
                if not (fname == os.path.basename(f[1]) or fname == f[1]):
                    continue
                ncalls = tokens[0]
                lineno = int(loc.split('(')[0])
                func = loc.split('(')[1][:-1]
                # Move cursor to correct line and character
                msg = ('%s: called %s times ran at %ss / call' % (func, ncalls, tokens[2]))
                temp_cursor.line = lineno - 1
                temp_cursor.move_to_x(0)
                node = temp_cursor.find_next_visible(temp_cursor.node)
                if node.lookup == "<ws>":
                    node = node.next_term
                node.remove_annotations_by_class(CPythonFuncProfileMsg)
                node.add_annotation(CPythonFuncProfileMsg(msg))
                ncalls_dict[node] = float(ncalls)

        # Normalise profiler information.
        vals = ncalls_dict.values()
        val_min = float(min(vals))
        val_max = float(max(vals))
        val_diff = val_max - val_min
        for node in ncalls_dict:
            ncalls_dict[node] = (ncalls_dict[node] - val_min) / val_diff
        for node in ncalls_dict:
            node.remove_annotations_by_class(CPythonFuncProfileVal)
            node.add_annotation(CPythonFuncProfileVal(ncalls_dict[node]))

        return mock
