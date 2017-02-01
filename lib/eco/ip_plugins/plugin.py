import pkgutil, importlib

class PluginManager:

    def __init__(self):
        self.loaded = []

    def loadplugins(self, caller):
        modules = [name for _, name, _ in pkgutil.iter_modules(['ip_plugins'])]
        modules.remove("plugin")
        for m in modules:
            m = importlib.import_module("." + m, "ip_plugins")
            p = m.load(caller)
            if p:
                self.loaded.append(p)

    def __getattr__(self, attr, *args, **kwargs):

        funcs = []
        if attr.startswith("do_"):
            fname = attr[3:]
            for p in self.loaded:
                try:
                    f = p.__getattribute__(fname)
                    funcs.append(f)
                except AttributeError:
                    print("WARNING: Plugin %s has no method '%s'" % (type(p), fname))
            def func(*args, **kwargs):
                for f in funcs:
                    return f(*args, **kwargs)
            return func
        else:
            return object.__getattribute__(self, attr)
