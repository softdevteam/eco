import sys
sys.path.append("../")

from state import State, StateSet, LR1Element
from production import Production
from gparser import Terminal, Nonterminal, Epsilon
from syntaxtable import FinishSymbol

epsilon = Epsilon()


def first(grammar, symbol):

    if isinstance(symbol, Terminal) or isinstance(symbol, FinishSymbol):
        return set([symbol])

    if isinstance(symbol, list):
        alternatives = [symbol]
        symbol = None
    else:
        alternatives = grammar[symbol].alternatives

    result = set()

    for a in alternatives:
        if a == []:
            result.add(epsilon)

    # repeat steps until first set doesn't change anymore
    # this is necessary because later alternatives may change the outcome of
    # earlier alternatives
    changed = True
    while changed:
        former_result = result.copy()
        for a in alternatives:
            for element in a:
                if element == symbol:
                    f = set(result) # copy
                else:
                    f = first(grammar, element)
                result = result.union(f.difference(set([epsilon])))

                if not epsilon in f:
                    break

                if element is a[-1]: # reached last element
                    result.add(epsilon)
        if former_result == result:
            changed = False
    return result

def old_first(grammar, symbol):
    """
    1) If symbol is terminal, return {symbol}
    2) If there exists a production 'symbol ::= None', add 'None'
    3) If there is a production 'symbol ::= X1 X2 X3' add every FIRST(Xi)
       (without None) until one Xi has no None-alternative. Only add None if all
       of them have the None-alternative
    """
    print("find first of:", symbol)
    result = set()

    # 0) If symbol consists of multiple symbols join all of their first sets as
    #    long as they have epsilon rules
    if isinstance(symbol, list): # XXX or set?
        for s in symbol:
            f = first(grammar, s)
            print("first of", s, "=", f)
            if not epsilon in f:
                result |= f
                break
            else:
                f.remove(epsilon)
                result |= f
            # all symbols had epsilon rules
            if s == symbol[-1]:
                result.add(epsilon)
        return result

    # 1)
    if isinstance(symbol, Terminal) or isinstance(symbol, FinishSymbol):
        return set([symbol])


    has_epsilon = False
    for a in grammar[symbol].alternatives:
        if a == []:
            result.add(epsilon)
            has_epsilon = True

    for a in grammar[symbol].alternatives:
        print("looking at alternative", a)
        # 2)
        if a == []:
            # already treated
            continue

        # 3)
        all_none = True
        for e in a:
            # avoid recursion
            if e == symbol:
                # skip recursive symbol and continue with next terminal if rule has an epsilon alternative
                if has_epsilon:
                    continue
                else:
                    all_none = False
                    break
            f = first(grammar, e)
            try:
                f.remove(epsilon)
            except KeyError:
                all_none = False
            result |= f
            if all_none == False:
                break
        if all_none:
            result.add(epsilon)
    return result

def follow(grammar, symbol):
    #XXX can be optimized to find all FOLLOW sets at once
    """
        1) Add final symbol ($) to follow(Startsymbol)
        2) If there is a production 'X ::= symbol B' add first(B) \ {None} to follow(symbol)
        3) a) if production 'X ::= A symbol'
           b) if production 'X ::= A symbol X' and X ::= None (!!! X can be more than one Nonterminal)
           ==> add follow(X) to follow(symbol)
    """
    result = set()
    for rule in grammar.values():
        for alternative in rule.alternatives:
            for i in range(len(alternative)):
                # skip all symbols until we find the symbol we want to build the follow set from
                if alternative[i] == symbol:
                    following_symbols = alternative[i+1:]
                    f = first(grammar, following_symbols)
                    # 3)
                    if following_symbols == [] or epsilon in f:
                        result |= follow(grammar, rule.symbol)
                    else:
                        # 2)
                        f.discard(epsilon)
                        result |= f
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
                # create epsilon symbol if alternative is empty
                if a == []:
                    a = [epsilon]
                p = Production(symbol, a)
                s = State(p, 0)
                if a == [epsilon]:
                    s.d = 1
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

def closure_1(grammar, state_set):
    result = StateSet()
    # Step 1
    for state in state_set.elements:
        result.add(state)
    # Step 2
    for state in result:
        symbol = state.next_symbol()
        if isinstance(symbol, Nonterminal):
            f = set()
            for l in state.lookahead:
                betaL = []
                betaL.extend(state.remaining_symbols())
                betaL.append(l)
                f |= first(grammar, betaL)

            alternatives = grammar[symbol].alternatives
            for a in alternatives:
                # create epsilon symbol if alternative is empty
                if a == []:
                    a = [Epsilon()]
                p = Production(symbol, a)
                s = LR1Element(p, 0, f)
                if a == [epsilon]:
                    s.d = 1
                result.add(s)
    # merge states that only differ in their lookahead
    result.merge()
    return result

def goto_1(grammar, state_set, symbol):
    result = StateSet()
    for state in state_set:
        s = state.next_symbol()
        if s == symbol:
            new_state = state.clone()
            new_state.d += 1
            result.add(new_state)
    return closure_1(grammar, result)
