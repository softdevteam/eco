from astree import FinishSymbol, BOS, EOS
from syntaxtable import Goto
import logging

class RecoveryManager(object):

    def __init__(self, previous_version, root, stack, syntaxtable):
        self.previous_version = previous_version
        self.root = root
        self.stack = stack
        self.syntaxtable = syntaxtable
        self.rejects = set()

        self.new_state = None
        self.iso_node = None

    def recover(self, error_node):
        """Takes a node causing a parsing error as input and attempts
        to find a subtree containing that nodes that can be reverted to allow
        the parsing algorithm to continue."""

        logging.debug("\x1b[31mRecovering\x1b[0m %s (%s)", error_node, id(error_node))

        ancestors_to_ignore = set()

        self.new_state = None
        self.iso_node = None

        if isinstance(self.stack[-1].symbol, FinishSymbol):
            # Can't recover if there's nothing on the stack
            return False
        if isinstance(error_node, EOS):
            # Can't recover if EOS caused the error. But why?
            return False

        # Get the character offset of the top node on the stack
        error_offset = self.stack_offset(len(self.stack))

        node = self.stack[-1]
        while not isinstance(node, EOS):
            if node.new:
                # Can't recover a newly created subtree
                self.stack.pop()
                node = self.stack[-1]
                continue

            # Check if current node can be isolated
            if self.is_valid_iso_subtree(node, error_offset):
                return True

            # Couldn't isolate current node. Try it's parents of the last
            # successfully parsed tree (including recent changes)
            while node.get_attr("parent", self.previous_version):
                node = node.get_attr("parent", self.previous_version)
                if node is self.root:
                    break
                if node in ancestors_to_ignore:
                    continue
                # Check if current node can be isolated
                if self.is_valid_iso_subtree(node, error_offset):
                    return True
                else:
                    ancestors_to_ignore.add(node)

            # Couldn't find elegible parent. Now try more previously parsed subtrees
            # on the stack
            self.stack.pop()
            node = self.stack[-1]
        return False

    def is_valid_iso_subtree(self, node, error_offset):
        if node in self.rejects:
            # Node has already been rejected as a candidate for recovery
            return False

        self.rejects.add(node)

        # There is no point in isolating nodes that don't have changes, even if
        # they are valid isolation trees. Ultimately the parse will fail again
        # as no changes have been isolated, and a bigger isolation area will be
        # picked. This is a deviation from Wagner's algorithm, which doesn't seem
        # to check for this.
        if not node.has_changes(self.previous_version):
            return False

        if len(node.children) == 0:
            return False

        cut = self.get_cut(node)
        if cut == -1:
            return False

        left_offset = self.stack_offset(cut) # offset of the stack node at position `cut`
        if left_offset > error_offset:
            # The node offset is after the error
            return False

        last_offset = self.offset(node, self.previous_version) # character offset of the isolation node

        # because I am using get_cut on all nodes, get_cut would fail before
        # this check. Wagner doesn't use get_cut on stack nodes which is why he
        # needed this check
        if left_offset != last_offset:
            # Offsets don't align
            return False

        # Get the subtrees character length as in the previous version
        nlen = node.textlength(version = self.previous_version)
        if last_offset + nlen < error_offset:
            # The offset range of the isolation tree doesn't meet or exceed the
            # location of the error
            return False

        # Reaching this point means we found a candidate for isolation. Now we
        # need to check if we can continue parsing if we isolate this subtree

        # Check if the isolation candidate can be shifted at the point to which
        # we need to cut down the stack.
        element = self.syntaxtable.lookup(self.stack[cut].state, node.symbol)
        if not element:
            # Couldn't shift candidate at this point. Try to adjust for empty
            # Nonterminals, before giving up.
            temp_cp = cut + 1
            if temp_cp >= len(self.stack):
                # Reached end of stack. Isolation tree can't be pushed here.
                return False

            while len(self.stack[temp_cp].children) == 0:
                element = self.syntaxtable.lookup(self.stack[temp_cp].state, node.symbol)
                if isinstance(element, Goto):
                    cut = temp_cp
                    break
                temp_cp += 1
                if temp_cp > len(self.stack) - 1:
                    # Reached the end of the stack.
                    break

        if isinstance(element, Goto):
            # Found a valid isolation subtree. Now cut back the stack to the
            # position where we can push the subtree and setup the parser so
            # parsing can continue.
            self.stack[:] = self.stack[:cut+1]
            self.new_state = element.action
            self.iso_node = node
            self.iso_node.state = self.new_state
            self.iso_offset = last_offset
            self.error_offset = error_offset
            logging.debug("   Found valid isolation node %s (%s)", node, id(node))
            return True

        return False

    def get_cut(self, node):
        """Get the stack index at which the character offset is equal to the
        character offset of `node` in the previous version of the tree."""
        old_offset = self.offset(node, self.previous_version)
        index = 0
        length = 0
        last_index = -1
        for n in self.stack:
            length += n.textlength()
            if length == old_offset:
                return index
            if length > old_offset:
                return -1
            index += 1
        return -1

    def find_cut_point(self, offset):
        """Finds the position on the stack to which we need to reset the parser
        to to continue parsing after isolating a subtree."""
        cut_point = 0
        length = 0
        while cut_point < len(self.stack):
            cur_node = self.stack[cut_point]
            length += cur_node.textlength()
            if length == offset:
                last_valid_cutpoint = cut_point
                return cut_point
            if length > offset:
                # We are already past the target offset. Abort!
                break
            cut_point += 1
        assert False

    def stack_offset(self, cut):
        """Get the character offset of the stack node at the position `cut`."""
        offset = 0
        i = 0
        for n in self.stack:
            offset += n.textlength()
            if i == cut:
                break
            i += 1
        return offset

    def offset(self, node, version = None):
        """Calculates the character offset of `node`. This is an optimised
        version that goes backwards through the tree starting at the node,
        instead of starting at BOS which requires looking into each subtree to
        find `node`."""
        offset = 0
        while True:
            if isinstance(node, BOS):
                # Reached the beginning of the parse tree
                break
            left = node.get_attr("left", version)
            if left:
                node = left
                offset += node.textlength(version = version)
            else:
                node = node.get_attr("parent", version)
        return offset
