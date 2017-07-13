from grammars.grammars import lang_dict
from treemanager import TreeManager
from utils import KEY_UP as UP, KEY_DOWN as DOWN, KEY_LEFT as LEFT, KEY_RIGHT as RIGHT
from optparse import OptionParser
import logging
import sys, os

class FuzzyMinimiser(object):

    def __init__(self, lang, program, test):
        grm = lang_dict[language]
        parser, lexer = grm.load()
        parser.init_ast()
        self.parser = parser
        self.lexer = lexer
        self.grm = grm
        self.treemanager = TreeManager()
        self.treemanager.add_parser(parser, lexer, grm.name)
        self.treemanager.version = 1
        self.treemanager.last_saved_version = 1

        self.program = program
        self.test = test
        self.pos = 0
        self.lastexception = None

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, self.grm)

    def auto(self):
        logging.info("Running auto-mode")
        # try to reduce snapshots first
        while True:
            self.original = self.test[:] # remember original tests
            self.reduce("snapshot")
            if self.test == self.original:
                logging.info("No more snapshot reductions possible.")
                break
        # try single reduce next
        while True:
            self.original = self.test[:] # remember original tests
            self.reduce("single")
            if self.test == self.original:
                logging.info("No more single reductions possible.")
                break

    def reduce(self, mode):
        self.pos = 0
        logging.info("Pos: {} Len: {} Start {}-reduce".format(self.pos, len(self.test), mode))
        try:
            # Run without changes to store exception
            self.run()
        except Exception as e:
            self.lastexception = e
        while self.pos < len(self.test):
            self.delete(mode)
            try:
                self.run() # check if first run causes error
                logging.info("Pos: {} Len: {} Fixed".format(self.pos, len(self.test)))
                self.revert()
            except Exception as e:
                if not self.same_exception(e):
                    logging.info("Pos: {} Len: {} Wrong exception: '{}'".format(self.pos, len(self.test), e))
                    self.revert()
                    continue
                else:
                    logging.info("Pos: {} Len: {} Still failing: '{}'".format(self.pos, len(self.test), e))
                    self.save() # save progress
        self.save()

    def same_exception(self, e):
        if not self.lastexception:
            self.lastexception = e
            return True
        if type(self.lastexception) is type(e) and \
                self.lastexception.args == e.args:
                    return True
        return False

    def delete(self, mode):
        self.old = self.test[:] # copy
        if mode == "single":
            del self.test[self.pos:self.pos+4] # remove one keystroke
            if self.pos < len(self.test) and \
                self.test[self.pos] == "self.treemanager.undo_snapshot()":
                    self.test.pop(self.pos)
        elif mode == "snapshot":
            # removes 1 snapshot consisting of 20 keystrokes (each 4 lines) and
            # a `self.treemanager.undo_snapshot()` line at the end
            del self.test[self.pos:self.pos+81]

    def revert(self):
        diff = len(self.old) - len(self.test)
        self.test = self.old[:] # revert changes
        self.pos += diff # and skip test lines that are needed

    def set_destination(self, dest):
        filename = dest + ".1"
        i = 1
        while os.path.isfile(filename):
            filename = dest + ".{}".format(i)
            i += 1
        self.dest = filename
        logging.info("Setting destination to '{}'".format(filename))

    def save(self):
        f = open(self.dest, "w")
        for l in self.test:
            f.write(l)
            f.write("\n")
        f.close()

    def run(self):
        self.reset()
        self.treemanager.import_file(self.program)
        for l in self.test:
            exec(l)

    def move(self, direction, times):
        for i in range(times): self.treemanager.cursor_movement(direction)

if __name__ == "__main__":
    optp = OptionParser(usage="usage: python2 %prog PROGRAM TEST LANG [options]\n\ne.g. python2 %prog program.txt tests.txt \"Python 2.7.5\"")
    optp.add_option("-l", "--log", action="store_true", default=False, help="Show logging information")
    optp.add_option("-m", "--mode", default="auto", help="Specify type of reduction (default: %default)")

    (options, args) = optp.parse_args()

    if len(args) < 3:
        optp.print_help()
        exit()

    with open(args[0], "r") as f:
        program = f.read()
        program = program[:-1]
    with open(args[1], "r") as f:
        test = f.read().splitlines()
    language = args[2]
    mode = options.mode

    # set logging
    if options.log:
        loglevel=logging.INFO
    else:
        loglevel=logging.WARNING
    logging.basicConfig(format='%(levelname)s: %(message)s', filemode='w', level=loglevel)

    # run
    r = FuzzyMinimiser(language, program, test)
    r.set_destination(sys.argv[2])
    if mode == "auto":
        r.auto()
    else:
        r.reduce(mode)
