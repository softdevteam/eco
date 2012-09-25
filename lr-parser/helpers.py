import sys
sys.path.append("../")

from gparser import Terminal

def first(grammar, symbol):
    """
    1) If symbol is terminal, return {symbol}
    2) If there exists a production 'symbol ::= None', add 'None'
    3) If there is a production 'symbol ::= X1 X2 X3' add every FIRST(Xi)
       (without None) until one Xi has no None-alternative. Only add None if all
       of them have the None-alternative
    """
    # 1)
    if isinstance(symbol, Terminal):
        return set([symbol])

    result = set()
    for a in grammar[symbol].alternatives:
        # 2)
        if a == [None]:
            result.add(None)

        # 3)
        all_none = True
        for e in a:
            # avoid recursion
            if e == symbol:
                continue
            f = first(grammar, e)
            try:
                f.remove(None)
            except KeyError:
                all_none = False
            result |= f
            if all_none == False:
                break
        if all_none:
            result.add(None)

    return result

def follow(grammar, symbol):
    result = set()
    for rule in grammar.values():
        for alternative in rule.alternatives:
            found_symbol = False
            for a in alternative:
                # skip all symbols until we find the symbol we want to build the follow set from
                if a == symbol:
                    found_symbol = True
                    continue
                if found_symbol:
                    f = first(grammar, a)
                    # continue with other elements only if current has an empty alternative
                    if not None in f:
                        result |= f
                        break
                    f.discard(None)
                    result |= f

                    # reached end?
                    if rule.alternatives[-1] == a:
                        if rule.symbol != symbol:
                            result |= follow(grammar, rule.symbol)
    return result

def follow_old(grammar, symbol):
    #XXX can be optimized to find all FOLLOW sets at once
    """
        1) Add final symbol ($) to follow(Startsymbol)
        2) If there is a production 'X ::= symbol B' add first(B) \ {None} to follow(symbol)
        3) a) if production 'X ::= bla symbol'
           b) if production 'X ::= bla symbol X' and X ::= None (!!! X can be more than one Nonterminal)
           ==> add follow(X) to follow(symbol)
    """
    # 1)
    result = set()
    for s in grammar.keys():
        alternatives = grammar[s].alternatives

        for a in alternatives:
            # 2)
            prev = None
            for e in a:
                if prev == symbol:
                    f = first(grammar, e)
                    f.discard(None)
                    result |= f
                prev = e
            # 3a) if last element equals symbol
            if a[-1] == symbol and s != symbol:
                result |= follow(grammar, s)
                continue
            # 3b) if all elements after symbol are empty
            found_symbol = False
            all_empty = True
            for e in a:
                if e == symbol:
                    found_symbol = True
                    continue
                if found_symbol:
                    if not None in first(grammar, e):
                        all_empty = False
                        break
            if all_empty and s != symbol:
                result |= follow(grammar, s)

def closure():
    pass

def goto():
    pass
