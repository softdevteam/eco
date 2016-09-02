import abc


class Hint(object):
    """A Hint tells Eco how a particular annotation  might be visualised.

    Each annotation may have a number of hints (e.g. textual information
    might be displayed as a footnote or a tooltip) and Eco will automatically
    select a visualisation strategy for each annotation type.

    Hints are implemented as a hierarchy of classes, because Python 2 does
    not have enumerations.
    """
    pass


class Heatmap(Hint):
    """Annotations which can be displayed on a heatmap.
    For this hint, annotations must be numerical data (for example a floats).
    """
    pass


class Railroad(Hint):
    """Annotations which can be displayed as railroad lines between tokens.
    Annotations should be dicts of tuples, e.g. { (10, 'foo'): (20, 'bar')}
    requests that Eco should draw a line between token 'foo' on line 10
    and token 'bar' on line 20.
    """
    pass


class Footnote(Hint):
    """Annotations which can be displayed as a footnote.
    A footnote (in Eco) is a line of text underneath a node.
    """
    pass


class ToolTip(Hint):
    """Annotations which can be displayed on a tooltip.
    """
    pass


class HUDEval(Hint):
    """Annotations displayed when the HUD eval() strings button is down.
    """
    pass


class HUDTypes(Hint):
    """Annotations displayed when the HUD types button is down.
    """
    pass


class HUDHeatmap(Hint):
    """Annotations displayed when the HUD heatmap button is down.
    """
    pass


class HUDCallgraph(Hint):
    """Annotations displayed when the HUD call graph button is down.
    """
    pass

class Annotation(object):
    """An Annotation is a piece of information related to a node.
    Annotations are used to instrument the AST with runtime information about
    the code which is currently being edited (for example, coverage, profile,
    or type information might be visualised).
    """

    def __init__(self, annotation):
        self._annotation = annotation

    @property
    def annotation(self):
        return self._annotation

    @annotation.setter
    def annotation(self, annotation):
        self._annotation = annotation

    @abc.abstractmethod
    def has_hint(self, klass):
        """Returns True if annotation contains the given hint, else False.
        Eco will use these hints to determine how annotations of this type
        will be visualised in the editor.
        """
        msg = "has_hint(klass) must be implemented in subclasses of Annotation."
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def get_hints(self):
        """Returns a list of Hints (must be subclasses of annotations.Hint).
        Eco will use these hints to determine how annotations of this type
        will be visualised in the editor.
        """
        msg = "get_hints() must be implemented in subclasses of Annotation."
        raise NotImplementedError(msg)
