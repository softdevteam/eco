# Grammar operations

import re
from languages import Language


def add_alt(new_name, old_lang, rule, alt):
    old_grm = old_lang.grammar
    m = re.search(r"%s\s*::=" % rule, old_grm)
    assert m is not None
    rest = old_grm[m.end():]
    if rest.find("::=") == -1:
        btwn = rest
    else:
        btwn = old_grm[m.end():rest.find("::=")]
    btwn = btwn.strip()
    if btwn == "":
        assert False
    else:
        new_grm = "".join([old_grm[:m.end()], "%s | " % alt, old_grm[m.end():]])
    return Language(new_name, new_grm, old_lang.priorities)
