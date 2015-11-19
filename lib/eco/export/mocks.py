import os

class MockFile(object):
    """Mock the readline() method of a file object.
    Used by MockPopen.
    """
    def __init__(self, text):
        if text:
            self.text = text.split(os.linesep)
        else:
            self.text = ""
        self.index = 0

    def read(self):
        return os.linesep.join(self.text)

    def readline(self):
        if self.index >= len(self.text):
            return ""
        line = self.text[self.index]
        self.index += 1
        return line


class MockPopen(object):
    """Mock a Popen object.
    Used by profilers which need to call communicate() on a real Popen object,
    but also need to return the same Popen, so that its contents can be
    appended to the Eco console.
    """
    def __init__(self, out, err=""):
        self.stdout = MockFile(out)
        self.stderr = MockFile(err)
        self.rc = 0
