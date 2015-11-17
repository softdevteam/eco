import collections, difflib, bisect
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, IndentationTerminal, Terminal
from version_control import diff3_driver

from treemanager import TreeManager
from jsonmanager import JsonManager




class VCSTreeWalker (object):
    def __init__(self, root_node, exporter):
        self.buf = []
        self.terminal_positions = {}
        self.terminals = []
        self.root_node = root_node
        self.exporter = exporter

    def pp(self, node):
        # Clear the buffer first
        self.buf = []
        # Walk the tree
        self.walk(node)
        # Return the buffer
        return self.buf

    def walk(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            if isinstance(node, EOS):
                break
            assert isinstance(node, TextNode)
            if isinstance(sym, MagicTerminal):
                self.language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                pass
            elif sym.name == "\r":
                self.text("\n", node)
            else:
                self.text(sym.name, node)

    def language_box(self, name, node):
        self.terminal_positions[id(node)] = len(self.buf)
        # Export the contents of the language box
        ref, box_content = self.exporter._export_node(node)
        # Append the reference text to the buffer
        self.buf.append(ref)
        self.terminals.append(node)

    def text(self, text, node):
        self.terminal_positions[id(node)] = len(self.buf)
        self.buf.append(text)
        self.terminals.append(node)


    def _compute_node_bounds(self):
        """
        Compute the bounds of every node in a parse tree, where the bounds describe the region of
        a flattened token sequence that is contained within the subtree rooted at each node.

        :param tree_walker: a `VCSTreeWalker` that has walked the parse tree
        :return: a dictionary mapping node ID `id(node)` to bounds `(start,end)`
        """
        # Initialise the `node_id_to_bounds` dictionary with the bounds of the terminals/leaves
        node_id_to_bounds = {}
        # Build a queue of nodes that we must handle as we go
        node_queue = collections.deque()
        for i, node in enumerate(self.terminals):
            node_id_to_bounds[id(node)] = (i, i+1)
            node_queue.append(node)

        # For each node in the queue, propagate its bounds to its parent, one level up, adding newly discovered
        # parent nodes. This should results in bounds for every node in the tree.
        while len(node_queue) > 0:
            # Get node from queue and get its bounds (should already have been computed)
            n = node_queue.popleft()
            n_bounds = node_id_to_bounds[id(n)]

            # Get the parent node and its ID
            parent = n.parent
            if parent is not None:
                parent_id = id(parent)

                if parent_id in node_id_to_bounds:
                    # Already encountered this node; enlarge its bounds to encompass those of `n` if necessary
                    p_bounds = node_id_to_bounds[parent_id]
                    p_bounds = (min(p_bounds[0], n_bounds[0]), max(p_bounds[1], n_bounds[1]))
                    node_id_to_bounds[parent_id] = p_bounds
                else:
                    # Newly discovered node; propagate bounds from child (`n`)
                    node_id_to_bounds[parent_id] = n_bounds
                    # Add the parent node to the queue
                    node_queue.append(parent)

        return node_id_to_bounds


    @staticmethod
    def three_way_merge(base, derived_local, derived_main):
        """
        Perform a three-way merge from three VCS tree walkers

        :param base: VCSTreeWalker from the base revision document
        :param derived_local: VCSTreeWalker from the locally modified document
        :param derived_main: VCSTreeWalker from the main line modified document
        :return:
        """

        # STEP 1: perform 3-way merge on token sequences
        merged = diff3_driver.diff3(base.buf, derived_local.buf, derived_main.buf,
                                    automerge_two_way_conflicts=True)

        print('MERGED: {0}'.format(merged))

        # STEP 2: compute changes from `derived_local` to merged sequence; use difflib for this
        sm = difflib.SequenceMatcher(a=derived_local.buf, b=merged)
        changes = sm.get_opcodes()

        print('CHANGES: {0}'.format(changes))

        # STEP 3: walk the list of opcodes from difflib and determine the minimum set of subtrees that encompass
        # the changes

        # List of nodes that are the roots of the modified subtrees
        modified_subtrees = set()
        # List of nodes encountered so far, to ensure we don't walk nodes multiple times
        visited_nodes = set()

        # For each change region
        for tag, i1, i2, j1, j2 in changes:
            # Ignore any region that is a match; start with regions that represent changes
            if tag != 'equal':
                if tag == 'insert':
                    # Expand the range of insert options so that it is not zero-length
                    i1 = max(i1 - 1, 0)
                    i2 = min(i2 + 1, len(derived_local.terminals))
                # Start with the set of terminals in the changed region
                node_set = set(derived_local.terminals[i1:i2])
                # Mark the nodes as visited
                visited_nodes = visited_nodes.union(node_set)

                # Until we reach the node that is the subtree root
                while len(node_set) > 1:
                    # Get the set of the parent nodes; as we go up the tree this set should decrease in size
                    # until we get to one parent
                    parents = set([node.parent for node in node_set])
                    try:
                        parents.remove(None)
                    except KeyError:
                        pass

                    # Remove any nodes that have been previously visited
                    parents = parents.difference(visited_nodes)
                    # Mark remaining nodes as visited
                    visited_nodes = visited_nodes.union(parents)
                    # Remove the nodes in `parents` from `modified_subtrees`, so that `modified_subtrees`
                    # will not contain nodes that within the subtrees of other nodes
                    modified_subtrees = modified_subtrees.difference(parents)
                    # Next iteration
                    node_set = parents

                # If one node remains (could be 0 if this part of the tree has already been visited)...
                if len(node_set) == 1:
                    # Add into `modified_subtrees`
                    modified_subtrees = modified_subtrees.union(node_set)

        # Convert to list
        modified_subtrees = list(modified_subtrees)

        print('SUBTREES TO UPDATE: {0}'.format([subtree.symbol.name for subtree in modified_subtrees]))

        # STEP 4: compute the replacement content for each modified subtree

        # Compute the bounds of the nodes
        node_id_to_bounds = derived_local._compute_node_bounds()
        start_indices = [i1 for tag, i1, i2, j1, j2 in changes]
        subtrees_with_content = []

        for subtree in modified_subtrees:
            # The the sub-tree bounds
            bounds = node_id_to_bounds[id(subtree)]

            # Locate the change regions that are underneath the start and end of the subtree
            start_op_ndx = bisect.bisect_left(start_indices, bounds[0])
            end_op_ndx = bisect.bisect_left(start_indices, bounds[1])
            if start_op_ndx >= len(changes) or bounds[0] < changes[start_op_ndx][1]:
                start_op_ndx = max(start_op_ndx - 1, 0)
            if end_op_ndx >= len(changes) or bounds[1] < changes[end_op_ndx][1]:
                end_op_ndx = max(end_op_ndx - 1, 0)
            st_tag, st_i1, st_i2, st_j1, st_j2 = changes[start_op_ndx]
            en_tag, en_i1, en_i2, en_j1, en_j2 = changes[end_op_ndx]

            if bounds[0] == st_i1:
                subtree_start_index = st_j1
            else:
                if st_tag == 'equal':
                    # Offset the start point into the index-space of the merged token list
                    subtree_start_index = bounds[0] - st_i1 + st_j1
                else:
                    subtree_start_index = st_j1

            if bounds[1] == en_i1:
                subtree_end_index = en_j1
            else:
                if st_tag == 'equal':
                    # Offset the start point into the index-space of the merged token list
                    subtree_end_index = bounds[1] - en_i1 + en_j1
                else:
                    subtree_end_index = en_j1

            print('The subtree {0} will have the content:'.format(subtree.symbol.name))
            print(merged[subtree_start_index:subtree_end_index])

            subtrees_with_content.append((subtree, merged[subtree_start_index:subtree_end_index]))

        return subtrees_with_content



class VCSDocument (object):
    NODE_REF_START = u'\ue000'
    NODE_REF_END = u'\ue001'

    def __init__(self):
        self.node_id_to_walker = {}
        self.root_node_id = None


    def handle_node(self, node):
        # Set the ID of the root node to `node`
        node_id = id(node)
        self.root_node_id = node_id
        # Export content
        self._export_node(node)

    def _export_node(self, node):
        # Get the node ID and see if we have already exported it
        node_id = id(node)
        if node_id != self.root_node_id:
            raise NotImplementedError('Language boxes cannot be exported for version control purposes yet')
        try:
            walker = self.node_id_to_walker[node_id]
        except KeyError:
            # We haven't handled this node / language box yet; create a new buffer
            walker = VCSTreeWalker(node, self)
            # Register it
            self.node_id_to_walker[node_id] = walker
            # Export its content
            tokens = walker.pp(node)
        else:
            # Node already exported; just get the content
            tokens = walker.buf

        # Generate the control sequence for a reference to this node
        ref = self.node_ref_control_sequence(node_id)
        return ref, tokens


    def node_ref_control_sequence(self, node_id):
        return self.NODE_REF_START + str(node_id) + self.NODE_REF_END




def three_way_merge(base_tm, derived_local_tm, derived_main_tm):
    base_doc = VCSDocument()
    base_doc.handle_node(base_tm.get_bos())

    derived_local_doc = VCSDocument()
    derived_local_doc.handle_node(derived_local_tm.get_bos())

    derived_main_doc = VCSDocument()
    derived_main_doc.handle_node(derived_main_tm.get_bos())

    if len(base_doc.node_id_to_walker) > 1:
        raise NotImplementedError('Language boxes cannot be used for version control purposes yet')
    if len(derived_local_doc.node_id_to_walker) > 1:
        raise NotImplementedError('Language boxes cannot be used for version control purposes yet')
    if len(derived_main_doc.node_id_to_walker) > 1:
        raise NotImplementedError('Language boxes cannot be used for version control purposes yet')

    base_walker = base_doc.node_id_to_walker[base_doc.root_node_id]
    derived_local_walker = derived_local_doc.node_id_to_walker[derived_local_doc.root_node_id]
    derived_main_walker = derived_main_doc.node_id_to_walker[derived_main_doc.root_node_id]

    subtrees_with_content = VCSTreeWalker.three_way_merge(base_walker, derived_local_walker, derived_main_walker)

    print 'Updating subtrees...'

    for subtree, content in subtrees_with_content:
        for x in content:
            if isinstance(x, diff3_driver.Diff3ConflictRegion):
                raise NotImplementedError('Conflicts not yet correctly handled by three-way merge')
        text = ''.join(content)

        print 'Giving subtree {0} the text {1}'.format(subtree.symbol.name, repr(text))

        subtree.replace_content(text)

        print 'Relexing...'

        derived_local_tm.relex(subtree)
        print 'Reparsing...'
        derived_local_tm.reparse(subtree)



def load_tm(filename):
    manager = JsonManager()
    language_boxes = manager.load(filename)

    tm = TreeManager()
    tm.load_file(language_boxes)

    return tm
