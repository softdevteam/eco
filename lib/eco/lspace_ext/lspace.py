import os, json, subprocess


class CannotFindLSpaceRootError (Exception):
    pass

class CannotLaunchLSpaceError (Exception):
    pass


def _valid_lspace_root(lspace_root=None):
    if not os.path.exists(lspace_root):
        raise CannotFindLSpaceRootError("Cannot find LSpace directory; you "
                "can set the LSpace root using the settings dialog")
    return lspace_root

def _get_lspace_viewer_path(lspace_root=None):
    lspace_root = _valid_lspace_root(lspace_root)
    return os.path.join(lspace_root, 'target', 'release', 'examples', 'json_viewer')



class JSONData (object):
    def __init__(self, **js):
        self.js = js

    def as_json(self):
        return self.js


class FlowIndent (JSONData):
    @staticmethod
    def no_indent():
        return FlowIndent(indent_type='no_indent')

    @staticmethod
    def first(indent):
        return FlowIndent(indent_type='first', indent=indent)

    @staticmethod
    def except_first(indent):
        return FlowIndent(indent_type='except_first', indent=indent)



class Pres (JSONData):
    @staticmethod
    def coerce(x):
        if isinstance(x, Pres):
            return x
        else:
            present = getattr(x, '__present__', None)
            if present is None:
                return Text(repr(x))
            return present()



class Text (Pres):
    def __init__(self, text):
        super(Text, self).__init__(__type__='Text', text=text)


class Column (Pres):
    def __init__(self, children, y_spacing=0.0):
        super(Column, self).__init__(__type__='Column', y_spacing=y_spacing,
                children=[Pres.coerce(c).as_json() for c in children])


class Row (Pres):
    def __init__(self, children, x_spacing=0.0):
        super(Row, self).__init__(__type__='Row', x_spacing=x_spacing,
                children=[Pres.coerce(c).as_json() for c in children])


class Flow (Pres):
    def __init__(self, children, x_spacing=0.0, y_spacing=0.0, indentation=None):
        if indentation is None:
            indentation = FlowIndent.no_indent()
        super(Flow, self).__init__(__type__='Flow', x_spacing=x_spacing,
                y_spacing=y_spacing, indentation=indentation.as_json(),
                children=[Pres.coerce(c).as_json() for c in children])


def viewer(pres, lspace_root=None):
    """
    Start the LSpace eco_viewer external tool

    pres: a `Pres` instance to show or another object that will be coerced
    into a `Pres`.

    lspace_root: [optional] the root directory of the LSpace repo
    """
    lspace_viewer_path = _get_lspace_viewer_path(lspace_root)
    lspace_viewer_dir = os.path.split(lspace_viewer_path)[0]

    try:
        proc = subprocess.Popen([lspace_viewer_path], cwd=lspace_viewer_dir,
                                stdin=subprocess.PIPE)
    except OSError:
        raise CannotLaunchLSpaceError("Could not execute LSpace viewer at "
            "{0}, you can set the LSpace root using the settings "
            "dialog".format(lspace_viewer_path))

    json.dump(Pres.coerce(pres).as_json(), proc.stdin)
    proc.stdin.close()

