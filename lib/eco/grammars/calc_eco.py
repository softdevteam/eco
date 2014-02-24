from grammars import EcoGrammar


grammar = """
            E ::= T             {#0}
                | E "plus" T    {Plus(arg1=#0,arg2=#2)}
                ;
            T ::= P             {#0}
                | T "mul" P     {Mul(arg1=#0,arg2=#2)}
                ;
            P ::= "INT"         {#0}
                ;
        %%

            INT:"[0-9]+"
            plus:"\+"
            mul:"\*"
            <ws>:"[ \\t]+"
            <return>:"[\\n\\r]"
"""

calc_eco = EcoGrammar("Basic Calculator (Eco)", grammar)
