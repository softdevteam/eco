connect4 = """class Connect4(object):
    UI_DEPTH = 5 # lookahead for minimax

    def __init__(self, p1_is_ai, p2_is_ai):
        self.top = tk.Tk()
        self.top.title("Unipycation: Connect 4 GUI (Python)")

        self.pl_engine = uni.Engine()

        # controls cpu/human players
        self.turn = None # True for p1, False for p2
        self.ai_players = { True : p1_is_ai, False : p2_is_ai }

        self.cols = []
        self.insert_buttons = []
        for colno in range(COLS):
            col = []
            b = tk.Button(self.top, text=str(colno), command=token_click_closure(self, colno))
            b.grid(column=colno, row=0)
            self.insert_buttons.append(b)

            for rowno in range(ROWS):
                b = tk.Button(self.top, state=tk.DISABLED)
                b.grid(column=colno, row=rowno + 1)
                col.append(b)
            self.cols.append(col)

        self.new_game_button = tk.Button(self.top, text="Start New Game", command=self._new)
        self.new_game_button.grid(column=COLS, row=0)

        self.status_text = tk.Label(self.top, text="---")
        self.status_text.grid(column=COLS, row=1)

    def _set_status_text(self, text):
        self.status_text["text"] = text

    def _update_from_pos_one_colour(self, pylist, colour):
        assert colour in ["red", "yellow"]

        for c in pylist:
            assert c.name == "c"
            (x, y) = c
            self.cols[x][y]["background"] = colour

    def _turn(self):
        # Not pretty, but works...
        while True:
            self.turn = not self.turn # flip turn
            if self.ai_players[self.turn]:
                self._set_status_text("%s AI thinking" % (self._player_colour().title()))
                self._ai_turn()
                if self._check_win(): break # did the AI player win
            else:
                self._set_status_text("%s human move" % (self._player_colour().title()))
                break # allow top loop to deal with human turn

    def _end(self, winner_colour=None):
        for i in self.insert_buttons:
            i["state"] = tk.DISABLED

        if winner_colour is not None:
            self.new_game_button["background"] = winner_colour
            self._set_status_text("%s wins" % winner_colour)"""

phpclass = """class PHP {

}"""

pythonsmall = """class X:
    def helloworld(x, y, z):
        for x in range(0, 10):
            if x == 1:
                return 1
            else:
                return 12
        return 13

    def foo(x):
        x = 1
        y = 2
        foo()
        return 12"""
