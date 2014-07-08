import helper

class PHP(helper.Generic):
    def language_box(self, name, node):
        if name == "<Python + PHP>":
            buf = Python().pp(node)
            self.buf.append("embed_py_func(\"\"\"%s\"\"\")" % (_escape(buf)))

class Python(helper.Generic):
    def language_box(self, name, node):
        if name == "<PHP + Python>":
            buf = PHP().pp(node)
            self.buf.append("embed_php_func(\"\"\"%s\"\"\")" % (_escape(buf)))

def _escape(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("'", "\\'")

def export(node):
    return PHP().pp(node)
