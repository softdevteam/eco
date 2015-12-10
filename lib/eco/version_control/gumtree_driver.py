import json, subprocess, tempfile, os

# Gumtree's EcoTree handler handles trees of the form:
#
# {
#     "__type__": "EcoTree",
#     "tree": <tree>
# }
#
# where <tree> is an ordered tree of nodes, of the form:
#
# {
#     "__type__": "TreeNode",
#     "label": string,
#     "type": integer,
#     "type_label": string,
#     "pos": integer,
#     "length": integer,
#     "children": [array of child nodes]
# }



class GumtreeNodeClass (object):
    def __init__(self, type_id, type_label):
        self.type_id = type_id
        self.type_label = type_label


    def full_node(self, position, length, value, children):
        return GumtreeNode(self.type_id, self.type_label, position, length, value, children)

    def node(self, value, children=None):
        if children is None:
            children = []
        return GumtreeNode(self.type_id, self.type_label, None, None, value, children)



class GumtreeNode (object):
    def __init__(self, type_id, type_label, position, length, value, children):
        if value is None:
            value = ''
        if not isinstance(type_id, int):
            raise TypeError('type_id must be an int')
        if not isinstance(type_label, str):
            raise TypeError('type_label must be a str')
        if position is not None and not isinstance(position, int):
            raise TypeError('position must be None or an int')
        if length is not None and not isinstance(length, int):
            raise TypeError('length must be None or an int')
        if not isinstance(value, str):
            raise TypeError('value must be None or a str')
        for child in children:
            if not isinstance(child, GumtreeNode):
                raise TypeError('children must be a sequence of EcoTreeNode instances')
        self.type_id = type_id
        self.type_label = type_label
        self.position = position
        self.length = length
        self.value = value
        self.children = children
        self.index = None
        self.merge_id = None

    def walk_structure(self, index, leaf_count, index_to_node):
        if self.position is None:
            self.position = leaf_count
        cur_index = index
        cur_leaf_count = leaf_count

        if self.children is None  or  len(self.children) == 0:
            # Leaf node
            cur_leaf_count += 1
        else:
            # Branch node
            for child in self.children:
                cur_index, cur_leaf_count = child.walk_structure(cur_index, cur_leaf_count, index_to_node)

        if self.length is None:
            self.length = cur_leaf_count - leaf_count

        self.index = cur_index
        index_to_node[self.index] = self

        return cur_index + 1, cur_leaf_count

    def clear_merge_ids(self):
        self.merge_id = None
        for child in self.children:
            child.clear_merge_ids()


    def as_json(self):
        return {
            'label': self.value,
            'type': self.type_id,
            'type_label': self.type_label,
            'pos': self.position,
            'length': self.length,
            'children': [child.as_json() for child in self.children] if self.children is not None else [],
        }

    def __getitem__(self, index):
        return self.children[index]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    @property
    def label_str(self):
        return '{0}:{1}'.format(self.type_label, self.value)

    @property
    def id_label_str(self):
        return '{0}:{1}:{2}'.format(self.merge_id, self.type_label, self.value)

    def __str__(self):
        if len(self.children) == 0:
            return '{0}'.format(self.label_str)
        else:
            return '{0}({1})'.format(self.label_str, ', '.join([str(x) for x in self.children]))

    def __repr__(self):
        if len(self.children) == 0:
            return '{0}'.format(self.label_str)
        else:
            return '{0}({1})'.format(self.label_str, ', '.join([str(x) for x in self.children]))



class GumtreeDocument (object):
    def __init__(self, root):
        self.root = root
        self.index_to_node = {}

        self.root.walk_structure(0, 0, self.index_to_node)


    def clear_merge_ids(self):
        self.root.clear_merge_ids()


    def as_json(self):
        return {
            'root': self.root.as_json()
        }

    def as_str(self):
        return json.dumps(self.as_json())

    def node_by_id(self, node_id):
        return self.index_to_node[node_id]




class GumtreeDiff (object):
    @staticmethod
    def _node_and_id(node):
        if isinstance(node, GumtreeNode):
            return node, node.merge_id
        else:
            raise TypeError('node must be an EcoTreeNode instance')


class GumtreeDiffUpdate (GumtreeDiff):
    def __init__(self, node, value):
        self.value = value
        self.node, self.node_id = self._node_and_id(node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffUpdate):
            return self.node_id == other.node_id and self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffUpdate, self.node_id, self.value))

    def __str__(self):
        return 'update({0}, value={1})'.format(self.node.id_label_str, self.value)

    def __repr__(self):
        return 'update({0}, value={1})'.format(self.node.id_label_str, self.value)


class GumtreeDiffDelete (GumtreeDiff):
    def __init__(self, node):
        self.node, self.node_id = self._node_and_id(node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffDelete):
            return self.node_id == other.node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffDelete, self.node_id))

    def __str__(self):
        return 'delete({0})'.format(self.node.id_label_str)

    def __repr__(self):
        return 'delete({0})'.format(self.node.id_label_str)


class GumtreeDiffInsert (GumtreeDiff):
    def __init__(self, src_node, parent, index_in_parent):
        self.parent_node, self.parent_id = self._node_and_id(parent)
        self.index_in_parent = index_in_parent
        self.src_node, self.src_node_id = self._node_and_id(src_node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffInsert):
            return self.parent_id == other.parent_id and self.index_in_parent == other.index_in_parent and \
                   self.src_node_id == other.src_node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffInsert, self.parent_id, self.index_in_parent, self.src_node_id))

    def __str__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.src_node.id_label_str,
                                                            self.parent_node.id_label_str, self.index_in_parent)

    def __repr__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.src_node.id_label_str,
                                                            self.parent_node.id_label_str, self.index_in_parent)


class GumtreeDiffMove (GumtreeDiff):
    def __init__(self, node, parent, index_in_parent):
        self.parent_node, self.parent_id = self._node_and_id(parent)
        self.index_in_parent = index_in_parent
        self.node, self.node_id = self._node_and_id(node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffMove):
            return self.parent_id == other.parent_id and self.index_in_parent == other.index_in_parent and \
                   self.node_id == other.node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffMove, self.parent_id, self.index_in_parent, self.node_id))

    def __str__(self):
        return 'move(src {0}, parent {1}, at {2})'.format(self.node.id_label_str,
                                                          self.parent_node.id_label_str, self.index_in_parent)

    def __repr__(self):
        return 'move(src {0}, parent {1}, at {2})'.format(self.node.id_label_str,
                                                          self.parent_node.id_label_str, self.index_in_parent)


DEFAULT_GUMTREE_PATH = os.path.expanduser('~/kcl/bin_gumtree/dist-2.1.0-SNAPSHOT/bin')



def _raw_diff(tree_a, tree_b, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
    """
    Invoke the external `Gumtree` tool to compare two trees `tree_a` and `tree_b`, each of which should be an
    instance of `GumtreeDocument` or `GumtreeNode`.
    :param tree_a: tree; version A
    :param tree_b: tree; version B
    :return: `(matches_js, actions_js)` where `matches_js` lists all of the nodes in the two trees
            that match one another and `actions_js` is a list of all the differences between `tree_a` and
            `tree_b`. `matches_js` takes the form `[[a0, b0], [a1, b1], ...]` where each `[an, bn]`
            pair describes a match between the node in `tree_a` of index `an` and the node in `tree_b` of
            index `bn`. `actions_js` takes the form of a list of actions: `[action0, action1, ...],
            where each action is one of the following:
            - UPDATE actions change the label of the node in `tree_a` whose index is `tree` to have
            the label `label`:
               `{'action': 'update', 'tree': <index of node in tree_a>, 'label': <new label>}
            - DELETE actions remove the node in `tree_a` whose index is `tree`:
               `{'action': 'delete', 'tree': <index of node in tree_a>}
            - INSERT actions insert a node from `tree_b` whose index is `tree` into a parent node
            from `tree_b` whose index is `parent` at the position `at`:
               `{'action': 'insert', 'tree': <index of inserted node in tree_b>,
                 'parent': <index of parent node in tree_b>, 'at': <position at which the node is inserted>}
            - MOVE actions move a node from `tree_a` whose index is `tree` into a parent node
            from `tree_b` whose index is `parent` at the position `at`:
               `{'action': 'move', 'tree': <index of moved node in tree_a>,
                 'parent': <index of parent node in tree_b>, 'at': <position at which the node is inserted>}
    instances.
    """
    if gumtree_path is None:
        gumtree_path = DEFAULT_GUMTREE_PATH
    if join_path:
        gumtree_executable_path = os.path.join(gumtree_path, gumtree_executable_name)
    else:
        gumtree_executable_path = gumtree_executable_name

    # Use the .ecotree file extension so that Gumtree knows which format to assume
    a_fd, a_path = tempfile.mkstemp(suffix='.jsontree')
    b_fd, b_path = tempfile.mkstemp(suffix='.jsontree')

    try:
        a_f = os.fdopen(a_fd, 'w')
        b_f = os.fdopen(b_fd, 'w')

        json.dump(tree_a.as_json(), a_f)
        json.dump(tree_b.as_json(), b_f)

        a_f.close()
        b_f.close()

        proc = subprocess.Popen([gumtree_executable_path, 'jsondiff', a_path, b_path],
                                cwd=gumtree_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()

        redefine_err_string = 'java.lang.RuntimeException: Redefining type'
        if 'java.lang.RuntimeException: Redefining type' in err:
            _, _, after = err.partition(redefine_err_string)
            after = after.strip()
            type_id, _, _ = after.partition(':')
            raise ValueError('Gumtree error, attempted to redefine type {0}'.format(type_id))
    finally:
        os.remove(a_path)
        os.remove(b_path)

    diff_js = json.loads(out)
    matches_js = diff_js['matches']
    actions_js = diff_js['actions']

    return matches_js, actions_js


def _convert_actions(tree_base, tree_derived, actions_js):
    """
    Convert a list of actions in Javascript form from the Gumtree tool, returned by `_raw_diff` into
    a list of `GumtreeDiff` instances.
    :param tree_base: tree, base version
    :param tree_derived: tree, derived version
    :param actions_js: action list, JS form, see `_raw_diff` for explanation
    :return: list of `GumtreeDiff` instances
    """
    # Go through each action in the action list and convert to `GumtreeDiff` instances.
    diffs = []
    for action_js in actions_js:
        action = action_js['action']
        if action == 'update':
            # Update actions reference the node from tree A that is being modified
            node = tree_base.index_to_node[action_js['tree']]
            diffs.append(GumtreeDiffUpdate(node, action_js['label']))
        elif action == 'delete':
            # Delete actions reference the node from tree A that is being deleted
            node = tree_base.index_to_node[action_js['tree']]
            diffs.append(GumtreeDiffDelete(node))
        elif action == 'insert':
            # Insert actions reference the node from tree B, that is being inserted as a child of
            # a parent node - also from tree B - at a specified index
            node = tree_derived.index_to_node[action_js['tree']]
            parent = tree_derived.index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffInsert(node, parent, action_js['at']))
        elif action == 'move':
            node = tree_base.index_to_node[action_js['tree']]
            parent = tree_derived.index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffMove(node, parent, action_js['at']))

    return diffs


def gumtree_diff(tree_base, tree_derived, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
    """
    Compute the difference actions required to mutate the tree `tree_base` into `tree_derived`.
    :param tree_base: tree; base version
    :param tree_derived: tree; derived version
    :return: list of actions, each of which is a `GumtreeDiff` instance.
    """
    # Coerce the trees into `GumtreeDocument` instances
    if isinstance(tree_base, GumtreeNode):
        tree_base = GumtreeDocument(tree_base)
    if isinstance(tree_derived, GumtreeNode):
        tree_derived = GumtreeDocument(tree_derived)

    if not isinstance(tree_base, GumtreeDocument):
        raise TypeError('tree_base should be an instance of GumtreeDocument or GumtreeNode')
    if not isinstance(tree_derived, GumtreeDocument):
        raise TypeError('tree_derived should be an instance of GumtreeDocument or GumtreeNode')

    tree_base.clear_merge_ids()
    tree_derived.clear_merge_ids()


    # This dictionary maps node ID to node, where if a node is deemed by Gumtree to appear in both `tree_base`
    # and `tree_derived`, the node from `tree_base` is used. In otherwise, nodes from `tree_derived` that match
    # nodes in `tree_based` are in effect 'merged' away.
    merge_id_to_node = {}
    merge_id_counter = 0

    # Assign merge IDs to nodes from `tree_base`.
    for derived_node_index, derived_node in tree_base.index_to_node.items():
        merge_id = merge_id_counter
        merge_id_counter += 1

        derived_node.merge_id = merge_id
        merge_id_to_node[merge_id] = derived_node


    # Get the matches and diff actions from Gumtree
    matches_js, actions_js = _raw_diff(tree_base, tree_derived, gumtree_path=gumtree_path,
                                            gumtree_executable_name=gumtree_executable_name, join_path=join_path)

    # Build a mapping from index in derived tree to index in base tree
    derived_index_to_base_index = {m['dest']: m['src'] for m in matches_js}

    # Walk all nodes in `tree_derived` and assign merge IDs
    for derived_node_index, derived_node in tree_derived.index_to_node.items():
        # Use `b_to_a` to translate index so that its relative to the base version tree
        base_index = derived_index_to_base_index.get(derived_node_index)

        if base_index is None:
            # The node in question is NOT matched to any node in the base tree; need to assign it a new merge ID
            merge_id = merge_id_counter
            merge_id_counter += 1

            derived_node.merge_id = merge_id
            merge_id_to_node[merge_id] = derived_node
        else:
            # Assign it the merge ID of the matching node from the base tree
            derived_node.merge_id = tree_base.index_to_node[base_index].merge_id

    # Convert actions to `GumtreeDiff` instances
    return _convert_actions(tree_base, tree_derived, actions_js)


def gumtree_diff3(tree_base, tree_derived_1, tree_derived_2, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
    """
    :param tree_derived_1: tree; derived version
    :return: the actions required to modified `self.tree_base` until it matches `tree_derived`.
    """
    # Coerce the trees into `GumtreeDocument` instances
    if isinstance(tree_base, GumtreeNode):
        tree_base = GumtreeDocument(tree_base)
    if isinstance(tree_derived_1, GumtreeNode):
        tree_derived_1 = GumtreeDocument(tree_derived_1)
    if isinstance(tree_derived_2, GumtreeNode):
        tree_derived_2 = GumtreeDocument(tree_derived_2)

    if not isinstance(tree_base, GumtreeDocument):
        raise TypeError('tree_base should be an instance of GumtreeDocument or GumtreeNode')
    if not isinstance(tree_derived_1, GumtreeDocument):
        raise TypeError('tree_derived_a should be an instance of GumtreeDocument or GumtreeNode')
    if not isinstance(tree_derived_2, GumtreeDocument):
        raise TypeError('tree_derived_b should be an instance of GumtreeDocument or GumtreeNode')


    tree_base.clear_merge_ids()
    tree_derived_1.clear_merge_ids()
    tree_derived_2.clear_merge_ids()


    # This dictionary maps node ID to node. If Gumtree deems that nodes from multiple versions of the tree match,
    # the node from *one* of these versions is used. In preference, the node from `tree_base` will be used,
    # with the node from `tree_derived_1` being chosen if there is a match between `tree_derived_1` and
    # `tree_derived_2` but not with `tree_base`.
    merge_id_to_node = {}
    merge_id_counter = 0

    # Assign merge IDs to nodes from `tree_base`.
    for B_node_index, B_node in tree_base.index_to_node.items():
        merge_id = merge_id_counter
        merge_id_counter += 1

        B_node.merge_id = merge_id
        merge_id_to_node[merge_id] = B_node


    # Get the matches and diff actions from Gumtree betwee `tree_base` and `tree_derived_a`
    ab_matches_js, ab_actions_js = _raw_diff(tree_base, tree_derived_1, gumtree_path=gumtree_path,
                                       gumtree_executable_name=gumtree_executable_name, join_path=join_path)
    ac_matches_js, ac_actions_js = _raw_diff(tree_base, tree_derived_2, gumtree_path=gumtree_path,
                                       gumtree_executable_name=gumtree_executable_name, join_path=join_path)
    bc_matches_js, bc_actions_js = _raw_diff(tree_derived_1, tree_derived_2, gumtree_path=gumtree_path,
                                       gumtree_executable_name=gumtree_executable_name, join_path=join_path)

    # Build index mappings from derived_1 to base, derived_2 to base and derived_2 to derived_1
    B_ndx_to_A_ndx = {m['dest']: m['src'] for m in ab_matches_js}
    C_ndx_to_A_ndx = {m['dest']: m['src'] for m in ac_matches_js}
    C_ndx_to_B_ndx = {m['dest']: m['src'] for m in bc_matches_js}


    # Walk all nodes in `tree_derived_1` and assign merge IDs using matches with `tree_base`
    for B_node_index, B_node in tree_derived_1.index_to_node.items():
        # Use `B_ndx_to_A_ndx` to translate index so that its relative to the base version tree
        A_index = B_ndx_to_A_ndx.get(B_node_index)

        if A_index is None:
            # The node in question is NOT matched to any node in the base tree; need to assign it a new merge ID
            merge_id = merge_id_counter
            merge_id_counter += 1

            B_node.merge_id = merge_id
            merge_id_to_node[merge_id] = B_node
        else:
            # Assign it the merge ID of the matching node from the base tree
            B_node.merge_id = tree_base.index_to_node[A_index].merge_id


    # Walk all nodes in `tree_derived_2` and assign merge IDs using matches with `tree_base`
    for C_node_index, C_node in tree_derived_2.index_to_node.items():
        # Use `C_ndx_to_A_ndx` to translate index so that its relative to the base version tree
        A_index = C_ndx_to_A_ndx.get(C_node_index)

        if A_index is not None:
            # Assign it the merge ID of the matching node from the base tree
            C_node.merge_id = tree_base.index_to_node[A_index].merge_id
        else:
            # Use `C_ndx_to_B_ndx` to translate index so that its relative to the derived 1 version tree
            B_index = C_ndx_to_B_ndx.get(C_node_index)

            if B_index is not None:
                # Assign it the merge ID of the matching node from the derived 1 tree
                C_node.merge_id = tree_derived_1.index_to_node[B_index].merge_id
            else:
                # The node in question is NOT matched to any node in the base tree or the derived 1 tree;
                # need to assign it a new merge ID
                merge_id = merge_id_counter
                merge_id_counter += 1

                C_node.merge_id = merge_id
                merge_id_to_node[merge_id] = C_node


    # Convert actions to `GumtreeDiff` instances
    diffs_ab = _convert_actions(tree_base, tree_derived_1, ab_actions_js)
    diffs_ac = _convert_actions(tree_base, tree_derived_2, ac_actions_js)
    diffs_bc = _convert_actions(tree_derived_1, tree_derived_2, ac_actions_js)


    raise NotImplementedError('Not finished yet')
