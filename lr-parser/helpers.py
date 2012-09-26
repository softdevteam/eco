import sys
sys.path.append("../")

from state import State, StateSet
from production import Production
from gparser import Terminal, Nonterminal

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
    #XXX can be optimized to find all FOLLOW sets at once
    """
        1) Add final symbol ($) to follow(Startsymbol)
        2) If there is a production 'X ::= symbol B' add first(B) \ {None} to follow(symbol)
        3) a) if production 'X ::= bla symbol'
           b) if production 'X ::= bla symbol X' and X ::= None (!!! X can be more than one Nonterminal)
           ==> add follow(X) to follow(symbol)
    """
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

def closure_0(grammar, state_set):
    result = StateSet()
    # 1) Add state_set to it's own closure
    for state in state_set.elements:
        result.add(state)
    # 2) If there exists an LR-element with a Nonterminal as its next symbol
    #    add all production with this symbol on the left side to the closure
    for state in result:
        symbol = state.next_symbol()
        if isinstance(symbol, Nonterminal):
            alternatives = grammar[symbol].alternatives
            for a in alternatives:
                p = Production(symbol, a)
                s = State(p, 0)
                result.add(s)
    return result

def goto_0(grammar, state_set, symbol):
    result = StateSet()
    for state in state_set:
        s = state.next_symbol()
        if s == symbol:
            new_state = state.clone()
            new_state.d += 1
            result.add(new_state)
    return closure_0(grammar, result)
