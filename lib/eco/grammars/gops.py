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


def extract(new_name, old_lang, rule_name):
    rules = _parse_grm(old_lang.grammar)
    rd = {}
    for r in rules:
        rd[r[0]] = r
    stack = [rule_name]
    inc = set() # All rules which need to be in the extract
    while len(stack) > 0:
        rn = stack.pop()
        if rn in inc:
            continue
        inc.add(rn)
        for alt in rd[rn][1:]:
            for e in alt:
                if len(e) == 0:
                    continue
                if e[0] in "\"<":
                    continue
                stack.append(e)

    new_rules = [rd[rule_name]]
    for rn in inc:
        if rn == rule_name:
            continue
        new_rules.append(rd[rn])

    return Language(new_name, _rules_to_str(new_rules), old_lang.priorities)
