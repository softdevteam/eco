import subprocess
import tempfile

class CPythonExporter(object):
    def __init__(self, tm):
        self.tm = tm

    def export(self, path, run):
        if run:
            return self._run()
        else:
            f = tempfile.mkstemp()
            self.tm.export_as_text(f[1])

    def _run(self):
        f = tempfile.mkstemp()
        self.tm.export_as_text(f[1])
        return subprocess.Popen(["python2", f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
