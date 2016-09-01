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
import sys

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

    def export(self, path, run, profile, debug):
        if profile:
            return self._profile()
        elif run:
            return self._run()
        elif debug:
            return self._debug()
        else:
            f = tempfile.mkstemp()
            self.tm.export_as_text(f[1])

    def _run(self):
        f = tempfile.mkstemp()
        self.tm.export_as_text(f[1])
        return subprocess.Popen(["python2", f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)

    def _debug(self):
        f = tempfile.mkstemp(suffix='.py')
        code = self.tm.export_as_text(f[1])

        # Check if remote pdb installed
        try:
            import remote_pdb
        except ImportError:
            sys.stderr.write("""Error: can't import the remote_pdb module. Typically this can be installed with:
          pip install python-remote-pdb

        More detailed install instructions for remote_pdb can be found at:
          https://pypi.python.org/pypi/remote-pdb
        """)
            return None

        # These are the lines for remotepdb
        pdb_lines = """from remote_pdb import RemotePdb
if hasattr(RemotePdb, 'DefaultConfig'):
    RemotePdb.DefaultConfig.prompt='(Pdb)'
    RemotePdb.DefaultConfig.highlight=False
RemotePdb('localhost', 8210).set_trace();"""

        with open(f[1], "w") as f2:
            f2.write("".join(code))

        """ The pdb lines are passed in as a command line statement to python,
        and the actual file is imported in that statement.
        Alternatively the pdb lines could be added to the source code, but
        that causes other problems with line numbers and breakpoints"""

        # get only filename
        import_file = f[1].split("/tmp/")[1]
        import_file = import_file.split(".py")[0]
        shell_command = ['python2', '-u', '-c', pdb_lines + "import " + import_file]
        return subprocess.Popen(shell_command,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, cwd=tempfile.gettempdir())

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
                if '/' in ncalls:
                    ncalls_dict[node] = float(ncalls.split('/')[0])
                else:
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
