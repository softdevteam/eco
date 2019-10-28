from time import sleep
import telnetlib

from PyQt5.QtCore import QObject, pyqtSignal
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK
from socket import error as socket_error

class Debugger(QObject):

    # incoming signals
    signal_command = pyqtSignal(str)
    signal_start = pyqtSignal()
    # outgoing signals
    signal_done = pyqtSignal()
    signal_output = pyqtSignal(str)
    signal_toggle_buttons = pyqtSignal(bool)
    signal_execute_fail = pyqtSignal()

    def __init__(self, window):
        QObject.__init__(self)
        self.window = window
        self.telnet = None

    def start_pdb(self):
        self.breakpoints = {'keep': [], 'del': []}
        self.line_read_until = '(Pdb)'
        self.process = self.window.getEditor().tm.export(debug=True)
        if not self.process:
            self.signal_execute_fail.emit()
            self.exit()
            return
        flags = fcntl(self.process.stdout, F_GETFL)
        fcntl(self.process.stdout, F_SETFL, flags | O_NONBLOCK)
        self.telnet = None
        attempt = 0
        while not self.telnet:
            sleep(0.5)
            try:
                self.telnet = telnetlib.Telnet("localhost", 8210)
            except socket_error:
                if attempt > 3:
                    self.signal_output.emit("Telnet connection failed, cannot debug")
                    self.exit()
                    return None
                attempt += 1
        output = False
        while not output:
            sleep(0.1)
            output = self.telnet.read_until(self.line_read_until)
        self.signal_toggle_buttons.emit(True)
        self.signal_output.emit(output)

    # Run command and wait for response
    def run_command(self, command):
        command = command.encode("ascii", "ignore")
        self.signal_toggle_buttons.emit(False)
        try:
            self.telnet.write(command + "\n")
        except AttributeError:
            return None
        # If user quits then don't wait for (Pdb)
        if (command == "q"):
            self.exit()
            return None
        ot = self.output_debug()
        # If ot is empty then debugging is finished
        if ot and self.window.debugging:
            self.signal_toggle_buttons.emit(True)
            self.window.getEditorTab().set_breakpoints(self.get_breakpoints())
        return ot

    def output_debug(self):
        try:
            output = self.telnet.read_until(self.line_read_until)
        except (AttributeError, EOFError):
            self.exit()
            return None
        if self.line_read_until not in output:
            self.exit()
            return None
        if "--Return--" in output:
            if self.is_program_finished():
                self.exit()
                return None
        self.print_program_output()
        self.signal_output.emit(output)
        return output

    def print_program_output(self):
        try:
            if self.process:
                program_output = self.process.stdout.read()
                self.signal_output.emit(program_output.strip())
        except (OSError, IOError):
            pass
        return

    def is_program_finished(self):
        try:
            # 'w' is the 'where' command. It tells you where you are in the program
            self.telnet.write("w\n")
            output = self.telnet.read_until(self.line_read_until)
        except (AttributeError, EOFError):
            return True

        if output:
            # Only look at first line of output
            place = output.split("\n")[0]
            if "<string>" in place and "None" in place:
                return True
        return False

    def get_breakpoints(self, temp=False, number=0, get_all=True):
        # Returns only the type of breakpoint specified (temp or not)
        try:
            self.telnet.write("b\n")
            output = self.telnet.read_until(self.line_read_until)
        except (EOFError, AttributeError):
            return None
        type_wanted = 'keep'
        if temp:
            type_wanted = 'del'

        # The third word in the line will be either 'keep' or 'del'
        # This tells you whether or not it's a temporary breakpoint
        lines = output.split('\n')
        headers_skipped = False
        self.breakpoints['del'] = []
        self.breakpoints['keep'] = []
        for l in lines:
            if not headers_skipped:
                headers_skipped = True
                continue
            # No parameter for split - split by any whitespace
            words = l.split()
            # In all the lines needed, the first part is an integer
            try:
                int(words[0])
            except ValueError:
                continue
            # Breakpoints are numbered from 1 and goes up
            bp_number = words[0]
            is_type = False
            if get_all:
                # just add to the list
                self.breakpoints[words[2]].append(words[5].split(":")[1])
            else:
                # check if it matches
                for w in words:
                    if w == type_wanted:
                        is_type = True
                    if is_type:
                        # Line number comes after colon
                        if words[5].split(":")[1] == str(number):
                            return bp_number
        if get_all:
            return self.breakpoints
        return 0

    def exit(self):
        self.print_program_output()
        try:
            if self.process:
                self.process.kill()
        except OSError:
            pass
        if self.window.debugging:
            if self.telnet:
                self.telnet.close()
                self.signal_output.emit("Debugging finished.")
            self.signal_done.emit()
