from time import sleep
import telnetlib

from PyQt4 import QtCore
from PyQt4.QtCore import QObject


class Debugger(QObject):
    def __init__(self, window):
        QObject.__init__(self)
        self.window = window
        # used from outside debugger
        self.signal_command = QtCore.SIGNAL("command")
        self.signal_start = QtCore.SIGNAL("start")
        # signals that will be emitted from debugger
        self.signal_done = QtCore.SIGNAL("finished")
        self.signal_output = QtCore.SIGNAL("output")
        self.signal_toggle_buttons = QtCore.SIGNAL("disablebuttons")

    def start_pdb(self):   
        self.bps = {'keep': [], 'del': []}         
        self.proc = self.window.getEditor().tm.export(debug=True)
        if not self.proc:
            self.emit(self.signal_output, "Cannot run debugger.")
            self.exit()
            return
        self.tn = False
        while not self.tn:
            sleep(0.5)
            self.tn = telnetlib.Telnet("localhost", 8210)                
        output = False     
        while not output:
            sleep(0.1)
            output = self.tn.read_until("(Pdb)") 
        self.emit(self.signal_toggle_buttons, True)           
        self.emit(self.signal_output, output)             

    # Run command and wait for response
    def run_command(self, command):
        self.emit(self.signal_toggle_buttons, False)
        try:
            self.tn.write(command + "\n")             
        except AttributeError:
            return None
        # If user quits then don't wait for (Pdb)
        if (command == "q"):
            self.exit()
            return None
        ot = self.output_debug()
        # If ot is empty then debugging is finished
        if ot and self.window.debugging:
            self.emit(self.signal_toggle_buttons, True)
            self.window.getEditorTab().set_breakpoints(self.get_breakpoints())
        return ot

    def output_debug(self):
        try:
            output = self.tn.read_until("(Pdb)")             
        except EOFError:
            self.exit() 
            return None               
        if "(Pdb)" not in output:
            self.exit()
            return None
        self.emit(self.signal_output, output) 
        return output

    def get_breakpoints(self, temp=False, number=0, get_all=True):
        # Returns only the type of breakpoint specified (temp or not)        
        try:
            self.tn.write("b\n")
            output = self.tn.read_until("(Pdb)")             
        except (EOFError, AttributeError):
            return None
        type_wanted = 'keep'
        if temp:
            type_wanted = 'del'

        # The third word in the line will be either 'keep' or 'del'
        # This tells you whether or not it's a temporary breakpoint
        lines = output.split('\n')
        headers_skipped = False
        self.bps['del'] = []
        self.bps['keep'] = []
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
                self.bps[words[2]].append(words[5].split(":")[1])
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
            return self.bps
        return 0

    def exit(self): 
        if self.window.debugging:
            if self.tn:     
                self.tn.close()
            self.emit(self.signal_output, "Debug finished.")  
            self.emit(self.signal_done)  
