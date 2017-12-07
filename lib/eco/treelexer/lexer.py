class PatternMatcher(object):

    def match_one(self, pattern, text):
        if not pattern:
            # Empty pattern always matches
            return True
        if not text:
            # Existing pattern can't match empty input
            return False
        if pattern[0] == ".":
            # Wild card always matches
            return True
        return pattern[0] == text[0]

    def match_question(self, pattern, text):
        if not text:
            # No more text, so ? is automatically true
            return True
        if self.match_one(pattern, text):
            # character appears 1 time. Remove question pattern and continue
            return self.match(pattern[2:], text[1:])
        # character appears zero times
        return self.match(pattern[2:], text)

    def match_star(self, pattern, text):
        if self.match_one(pattern, text):
            # matched one, continue matching *
            return self.match(pattern, text[1:])
        # couldn't match star, remove star regex and continue
        return self.match(pattern[2:], text)

    def match(self, pattern, text):
        if not pattern:
            return True
        if len(pattern) > 1 and pattern[1] == "?":
            return self.match_question(pattern, text)
        if len(pattern) > 1 and pattern[1] == "*":
            return self.match_star(pattern, text)
        if len(pattern) > 1 and pattern[1] == "+":
            if self.match_one(pattern, text):
                # rewrite pattern from + to *
                return self.match_star(pattern[0] + "*" + pattern[2:], text[1:])
            return False
        return self.match_one(pattern, text) and self.match(pattern[1:], text[1:])
