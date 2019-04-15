import random, json, glob, os
from grammars.grammars import lang_dict, EcoFile
from treemanager import TreeManager
from grammar_parser.gparser import Nonterminal, Terminal
from incparser.astree import MultiTextNode

# helper functions

debug = False
MAX_FILES = 200

def next_node(node):
    while(node.right is None):
        node = node.parent
    return node.right

def prev_node(node):
    while(node.left is None):
        node = node.parent
    return node.left

def subtree_to_text(subtree):
    l = []
    if subtree.children:
        for child in subtree.children:
            l.append(subtree_to_text(child))
    elif type(subtree.symbol) is Terminal:
        l.append(subtree.symbol.name)
    return "".join(l).replace("\r", "").replace("\t", "").replace("\n", "")

def truncate(string):
    if len(string) > 40:
        return repr(string[:20] + "..." + string[-20:])
    else:
        return repr(string)

def validnonterm(node, symbol):
    if node.symbol.name == "class_statement": # PHP func
        return node.children[1].symbol.name == "function"
    elif node.symbol.name == "expr_without_variable": ] # PHP expr
        return node.children[0].symbol.name == "expr"
    elif node.symbol.name == "testlist": # Python expr
        # Only replace RHS of expressions, because there's currently a bug that
        # keeps indentation terminals from being inserted before language boxes
        return node.left_sibling() is not None
    elif n.symbol.name == "stat": # Lua func
        if n.children:
            if n.children[0].symbol.name == "function":
                return True
            if n.children[0].symbol.name == "local" and n.children[2].symbol.name == "function":
                return True
        return False
    else:
        return node.symbol.name == symbol

class FuzzyLboxStats:

    def __init__(self, main, sub):
        parser, lexer = main.load()
        self.lexer = lexer
        self.parser = parser
        self.ast = parser.previous_version
        self.treemanager = TreeManager()
        self.treemanager.add_parser(parser, lexer, main.name)
        self.treemanager.option_autolbox_insert = True
        self.langname = main.name

        parser.setup_autolbox(main.name)
        self.sub = sub

        self.inserted = 0

        self.faillog = []

    def load_main(self, filename):
        self.filename = filename
        f = open(filename, "r")
        self.content = f.read()
        f.close()
        self.content.replace("\n", "\r")
        self.treemanager.import_file(self.content)
        self.mainexprs = self.find_nonterms_by_name(self.treemanager, self.main_repl_str)
        self.minver = self.treemanager.version

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, self.langname)
        self.treemanager.import_file(self.content)
        self.mainexprs = self.find_nonterms_by_name(self.treemanager, self.main_repl_str)

    def load_expr(self, filename):
        f = open(filename, "r")
        content = f.read()
        f.close()
        self.replexprs = self.find_expressions(content, self.sub_repl_str)

    def load_expr_from_json(self, filename):
        import json
        with open(filename) as f:
            self.replexprs = json.load(f)

    def set_replace(self, main, sub):
        self.main_repl_str = main
        self.sub_repl_str = sub

    def find_nonterms_by_name(self, tm, name):
        l = []
        bos = tm.get_bos()
        eos = tm.get_eos()
        node = bos.right_sibling()
        while node is not eos:
            if validnonterm(node, name):
                l.append(node)
                node = next_node(node)
                continue
            if node.children:
                node = node.children[0]
            else:
                node = next_node(node)
        return l

    def find_expressions(self, program, expr):
        parser, lexer = self.sub.load()
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, self.sub.name)
        treemanager.import_file(program)

        # find all sub expressions
        l = self.find_nonterms_by_name(treemanager, expr)
        return [subtree_to_text(st).rstrip() for st in l]

    def insert_python_expression(self, expr):
        for c in expr:
            self.treemanager.key_normal(c)

    def delete_expr(self, expr):
        # find first term and last term
        # select + delete
        node = expr
        while type(node.symbol) is Nonterminal:
            if node.children:
                node = node.children[0]
            else:
                node = next_node(node)
        first = node
        if isinstance(first, MultiTextNode):
            first = first.children[0]

        node = expr
        while type(node.symbol) is Nonterminal:
            if node.children:
                node = node.children[-1]
            else:
                node = prev_node(node)
        while node.lookup == "<ws>" or node.lookup == "<return>":
            node = node.prev_term
        last = node
        if isinstance(last, MultiTextNode):
            last = last.children[-1]

        if first.deleted or last.deleted:
            return None

        self.treemanager.select_nodes(first, last)
        deleted = self.treemanager.copySelection()
        self.treemanager.deleteSelection()
        return deleted

    def run(self, main_samples=None, sub_samples=None):
        assert len(self.treemanager.parsers) == 1

        ops = self.main_repl_str, len([subtree_to_text(x) for x in self.mainexprs])
        preversion = self.treemanager.version

        inserted_error = 0
        inserted_valid = 0
        noinsert_error = 0
        noinsert_valid = 0
        noinsert_multi = 0

        # pick random exprs from main
        if not main_samples:
            samplesize = 10
            if len(self.mainexprs) < 10:
                samplesize = len(self.mainexprs)
            sample = random.sample(range(len(self.mainexprs)), samplesize) # store this for repeatability
            exprchoices = [self.mainexprs[i] for i in sample]
            self.main_samples = sample
        else:
            self.main_samples = main_samples

        if not sub_samples:
            # pick random exprs from sub
            sample = random.sample(range(len(self.replexprs)), len(exprchoices))
            replchoices = [self.replexprs[i] for i in sample]
            self.sub_samples = sample
        else:
            self.sub_samples = sub_samples

        for i, e in enumerate(exprchoices):
            if e.get_root() is None:
                continue
            deleted = self.delete_expr(e)
            before = len(self.treemanager.parsers)
            if deleted:
                choice = replchoices[i]
                if debug: print "  Replacing '{}' with '{}':".format(truncate(deleted), choice)
                self.insert_python_expression(choice)
                valid = self.parser.last_status
                if before == len(self.treemanager.parsers):
                    if len(self.parser.error_nodes) > 0 and self.parser.error_nodes[0].autobox and len(self.parser.error_nodes[0].autobox) > 1:
                        noinsert_multi += 1
                        result = "No box inserted (Multi)"
                        self.faillog.append(("multi", self.filename, repr(deleted), repr(choice)))
                    elif valid:
                        noinsert_valid += 1
                        result = "No box inserted (Valid)"
                        self.faillog.append(("valid", self.filename, repr(deleted), repr(choice)))
                    else:
                        noinsert_error += 1
                        result = "No box inserted (Error)"
                        self.faillog.append(("error", self.filename, repr(deleted), repr(choice)))
                else:
                    result = "Box inserted"
                    self.inserted += 1
                    if valid:
                        inserted_valid += 1
                    else:
                        inserted_error += 1
                        self.faillog.append(("inerr", self.filename, repr(deleted), repr(choice)))
                if debug: print "    => {} ({})".format(result, valid)
            else:
                if debug: print "Replacing '{}' with '{}':\n    => Already deleted".format(truncate(subtree_to_text(e)), truncate(choice))
            self.undo(self.minver)
        if debug:
            print("Boxes inserted: {}/{}".format(self.inserted, ops))
            print("Valid insertions:", inserted_valid)
            print("Invalid insertions:", inserted_error)
            print("No insertion (valid):", noinsert_valid)
            print("No insertion (error):", noinsert_error)
            print("No insertion (multi):", noinsert_multi)
        return (inserted_valid, inserted_error, noinsert_valid, noinsert_error, noinsert_multi)

    def undo(self, version):
        while self.treemanager.version != version:
            before = self.treemanager.version
            self.treemanager.version -= 1
            self.treemanager.recover_version("undo", self.treemanager.version + 1)
            self.treemanager.cursor.load(self.treemanager.version, self.treemanager.lines)
            if before == self.treemanager.version:
                exit("Error")

def run_multi(name, main, sub, folder, ext, exprs, mrepl, srepl=None, config=None):
    if config:
        run_config(name, main, sub, config, exprs, mrepl)
        return
    print "Multi:", name 
    run_config = []
    results = []
    faillog = []
    files = [y for x in os.walk(folder) for y in glob.glob(os.path.join(x[0], ext))]
    if len(files) > MAX_FILES:
        # let's limit files to 200 for now
        files = random.sample(files, MAX_FILES)
    i = 0
    for filename in files:
        c, r, f = run_single(filename, main, sub, exprs, mrepl, srepl)
        if c is None:
            continue
        run_config.append(c)
        results.append(r)
        faillog.extend(f)
        i = i + sum(r)
        if i > 1000:
            # abort after 1000 insertions
            break
    with open("{}_run.json".format(name), "w") as f: json.dump(run_config, f, indent=0)
    with open("{}_log.json".format(name), "w") as f: json.dump(results, f)
    with open("{}_fail.json".format(name), "w") as f: json.dump(faillog, f, indent=0)
    print

def run_single(filename, main, sub, exprs, mrepl, srepl, msample=None, ssample=None):
    if debug: print("Runsingle:", filename)
    fuz = FuzzyLboxStats(main, sub)
    fuz.set_replace(mrepl, srepl)
    try:
        fuz.load_main(filename)
        fuz.load_expr_from_json(exprs)
        r = fuz.run(msample, ssample)
    except Exception, e:
        # We only care about files that parse initially
        sys.stdout.write("s")
        sys.stdout.flush()
        return None, None, None
    if r[1] > 0 or r[3] > 0:
        # insert_error and noinsert_error
        sys.stdout.write("x")
        sys.stdout.flush()
    else:
        sys.stdout.write(".")
        sys.stdout.flush()
    config = (filename, fuz.main_samples, fuz.sub_samples)
    return config, r, fuz.faillog

def run_config(name, main, sub, configdir, exprs, mrepl, srepl=None):
    print "Config:", name
    with open("{}/{}_run.json".format(configdir, name)) as f:
        log = []
        faillog = []
        config = json.load(f)
        for filename, msample, ssample in config:
            c, r, f = run_single(filename, main, sub, exprs, mrepl, srepl, msample, ssample)
            if c is None:
                continue
            log.append(r)
            faillog.extend(f)
        with open("{}_log.json".format(name), "w") as f: json.dump(results, f)
        with open("{}_fail.json".format(name), "w") as f: json.dump(faillog, f, indent=0)
        print

def create_composition(smain, ssub, mainexpr, gmain, gsub, subexpr=None):
    sub = EcoFile(ssub, "grammars/" + gsub, ssub)
    if subexpr:
        sub.name = sub.name + " expr"
        sub.change_start(subexpr)

    main = EcoFile(smain + " + " + ssub, "grammars/" + gmain, smain)
    main.auto_limit_new = True
    main.add_alternative(mainexpr, sub)
    lang_dict[main.name] = main
    lang_dict[sub.name] = sub

    return main

if __name__ == "__main__":
    import sys
    args = sys.argv
    wd = "/home/lukas/research/auto_lbox_experiments"

    if len(args) < 8:
        print("Missing arguments.\nUsage: python2 fuzzylboxstats.py MAINGRM MAINRULE SUBGRM SUBRULE FILES EXTENSION REPLACMENTS HISTORICTOKEN [RERUNDIR]")
        exit()

    maingrm = args[1]
    mainrule = args[2]
    subgrm = args[3]
    subrule = args[4]
    files = args[5]
    ext = args[6]
    repl = args[7]
    histtok = args[8]
    if len(args) > 9:
        rerunconfig = args[9]
    else:
        rerunconfig = None
    if subrule == "None":
        subrule = None

    comp = create_composition("Main", "Sub", mainrule, maingrm, subgrm, subrule)
    name = maingrm[:-4] + subgrm[:-4]
    run_multi(name, comp, None, "{}/{}/".format(wd, files), '*.{}'.format(ext), "{}/{}".format(wd, repl), mainrule, rerunconfig)
