from mocks import MockPopen
import copy, os, os.path, subprocess, tempfile


class CPythonExporter(object):

    def __init__(self, tm):
        self.tm = tm

    def export(self, path, run, profile):
        f = tempfile.mkstemp()
        self.tm.export_as_text(f[1])
        if profile:
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
                    temp_cursor.move_to_x(0, self.tm.lines)
                    #temp_cursor.right()
                    node = temp_cursor.find_next_visible(temp_cursor.node)
                    if node.lookup == "<ws>":
                        node = node.next_term
                    self.tm.profile_map[node] = msg
                    self.tm.profile_data[lineno] = (float(ncalls), node)
            return mock
        elif run:
            return subprocess.Popen(["python2", f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
