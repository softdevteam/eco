import re

class TokenLexer(object):
    def __init__(self, regexlist):
        self.regexlist = regexlist
        self.compiled_regexes = {}
        for regex in self.regexlist:
            self.compiled_regexes[regex] = re.compile(regex)

    def match(self, token):
        matches = []
        remaining = token
        any_match_found = False
        while remaining != "":
            longest_match = ("", "", 999999)
            for regex in self.regexlist:
                m = self.compiled_regexes[regex].match(remaining)
                if m:
                    result = m.group(0)
                    if len(result) > len(longest_match[0]):
                        new_priority = self.regexlist[regex][0]
                        regex_name = self.regexlist[regex][1]
                        longest_match = (result, regex_name, new_priority)
                    if len(result) == len(longest_match[0]):
                        new_priority = self.regexlist[regex][0]
                        old_priority = longest_match[2]
                        if new_priority < old_priority: # use token with higher priority (smaller numbers have higher priority)
                            regex_name = self.regexlist[regex][1]
                            longest_match = (result, regex_name, new_priority)
            if longest_match[0] != "":
                any_match_found = True
                remaining = remaining[len(longest_match[0]):]
                matches.append(longest_match)
            else:
                matches.append((remaining, ""))
                break
        if any_match_found:
            return matches
        else:
            return None
