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



def _coerce_js(js):
    if js is None or isinstance(js, (str, unicode, int, long, float, bool)):
        return js
    elif isinstance(js, (tuple, list)):
        return [_coerce_js(x) for x in js]
    elif isinstance(js, dict):
        return {key: _coerce_js(value) for key, value in js.items()}
    else:
        try:
            as_json = getattr(js, 'as_json', None)
        except AttributeError:
            raise TypeError('Cannot coerce {0} to JSON'.format(type(js)))
        else:
            return _coerce_js(as_json())

class JSONData (object):
    def __init__(self, **js):
        self.js = js

    def as_json(self):
        return self.js



class TextWeight (object):
    normal = 'normal'
    bold = 'bold'

    @staticmethod
    def check(x):
        if x not in {TextWeight.normal, TextWeight.bold}:
            raise ValueError('Invalid text weight {0}'.format(x))
        return x

class TextSlant (object):
    normal = 'normal'
    italic = 'italic'

    @staticmethod
    def check(x):
        if x not in {TextSlant.normal, TextSlant.italic}:
            raise ValueError('Invalid text slant {0}'.format(x))
        return x


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


class Colour (JSONData):
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        super(Colour, self).__init__(r=r, g=g, b=b, a=a)



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
    def __init__(self, children):
        super(Column, self).__init__(__type__='Column',
                children=[Pres.coerce(c).as_json() for c in children])


class Row (Pres):
    def __init__(self, children):
        super(Row, self).__init__(__type__='Row',
                children=[Pres.coerce(c).as_json() for c in children])


class Flow (Pres):
    def __init__(self, children):
        super(Flow, self).__init__(__type__='Flow',
                children=[Pres.coerce(c).as_json() for c in children])


class ApplyStyleSheet (Pres):
    def __init__(self, child, **kwargs):
        super(ApplyStyleSheet, self).__init__(__type__='ApplyStyleSheet',
                child=Pres.coerce(child).as_json(), **kwargs)


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

    json.dump(_coerce_js(Pres.coerce(pres)), proc.stdin)
    proc.stdin.close()

