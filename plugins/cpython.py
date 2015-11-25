from plugins.api import Plugin
from incparser.annotation import Annotation, Footnote, Heatmap, ToolTip

import os
import os.path
import subprocess
import tempfile

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


class CPythonProfiler(Plugin):
    """CPython 2 prfofiler.
    Requires the Python standard library.
    """

    def __init__(self):
        super(CPythonProfiler, self).__init__("Python 2.7.5",
                                              "CPython profiler")

    def run_tool(self):
        f = tempfile.mkstemp()
        self.export(f[1])

        # python -m cProfile [-o output_file] [-s sort_order] myscript.py
        proc = subprocess.Popen(["python2",
                                 "-m",
                                 "cProfile",
                                 f[1]],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 bufsize=0)
        stdout_value, stderr_value = proc.communicate()

        # Lex profiler output:
        # ncalls  tottime  percall  cumtime  percall fname:lineno(fn)
        table = False
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
                if "/" in ncalls:
                    ncalls = ncalls.split("/")[0]
                lineno = int(loc.split('(')[0])
                func = loc.split('(')[1][:-1]
                msg = ('%s: called %s times ran at %ss / call' % (func, ncalls, tokens[2]))
                node = self.get_node_at_pos(lineno, 0)
                node.remove_annotations_by_class(CPythonFuncProfileMsg)
                node.add_annotation(CPythonFuncProfileMsg(msg))
                ncalls_dict[node] = float(ncalls)

        # Normalise profiler information.
        vals = ncalls_dict.values()
        if len(vals) == 1:
            for node in ncalls_dict:
                ncalls_dict[node] = 1.0
                node.remove_annotations_by_class(CPythonFuncProfileVal)
                node.add_annotation(CPythonFuncProfileVal(ncalls_dict[node]))
        elif len(vals) > 1:
            val_min = float(min(vals))
            val_max = float(max(vals))
            val_diff = val_max - val_min
            for node in ncalls_dict:
                ncalls_dict[node] = (ncalls_dict[node] - val_min) / val_diff
            for node in ncalls_dict:
                node.remove_annotations_by_class(CPythonFuncProfileVal)
                node.add_annotation(CPythonFuncProfileVal(ncalls_dict[node]))

# Create the plugin object that will be loaded by Eco.
cpython_profiler = CPythonProfiler()
