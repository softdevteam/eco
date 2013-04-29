# Grammar operations

import re
from languages import Language




def _rules_to_str(rules):
    s = []
    for r in rules:
        s.extend([r[0], "::="])
        i = 0
        for alt in r[1:]:
            if i > 0:
                s.append("|")
            i += 1
            s.extend(alt)
        s.append("\n")
    return " ".join(s)


RE_RULE = re.compile(r"([^\s]+)\s*::=\s*")
RE_WORD = re.compile(r"([^\s|]+)")

def _parse_grm(grm):
    rules = []
    i = 0

    def _skip_ws(i):
        while i < len(grm) and grm[i] in " \t\r\n":
            i += 1
        return i

    while i < len(grm):
        i = _skip_ws(i)
        if i == len(grm):
            break
        m = RE_RULE.match(grm, i)
        assert m is not None
        rule = [m.group(1)]
        alt  = []
        i = m.end()
        while i < len(grm):
            i = _skip_ws(i)
            if i == len(grm):
                break
            if RE_RULE.match(grm, i):
                break
            if grm[i] == "|":
                rule.append(alt)
                alt = []
                i += 1
                continue
            m = RE_WORD.match(grm, i)
            assert m is not None
            alt.append(m.group(1))
            i = m.end()
        rule.append(alt)
        rules.append(rule)

    return rules


def add_alt(new_name, old_lang, rule, alt):
    rules = _parse_grm(old_lang.grammar)
    for r in rules:
        if r[0] == rule:
            r.append([alt])
    return Language(new_name, _rules_to_str(rules), old_lang.priorities)
