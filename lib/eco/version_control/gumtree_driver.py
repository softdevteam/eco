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



class EcoTreeNodeClass (object):
    def __init__(self, type_id, type_label):
        self.type_id = type_id
        self.type_label = type_label


    def full_node(self, position, length, value, children):
        return EcoTreeNode(self.type_id, self.type_label, position, length, value, children)

    def node(self, value, children=None):
        if children is None:
            children = []
        return EcoTreeNode(self.type_id, self.type_label, None, None, value, children)



class EcoTreeNode (object):
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
            if not isinstance(child, EcoTreeNode):
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



class EcoTreeDocument (object):
    def __init__(self, root):
        self.root = root
        self.index_to_node = {}

        self.root.walk_structure(0, 0, self.index_to_node)


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
        if isinstance(node, EcoTreeNode):
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



class GumTreeMerger (object):
    def __init__(self, tree_base):
        """
        Construct a GumTree merger

        :param tree_base: tree in the base version
        """
        if isinstance(tree_base, EcoTreeNode):
            tree_base = EcoTreeDocument(tree_base)

        if not isinstance(tree_base, EcoTreeDocument):
            raise TypeError('tree_base should be an instance of EcoTreeDocument or EcoTreeNode')

        self.tree_base = tree_base

        self.merge_id_to_node = {}
        self.__merge_id_counter = 0

        # Assign merge IDs to nodes
        for node_index, node in self.tree_base.index_to_node.items():
            merge_id = self.__merge_id_counter
            self.__merge_id_counter += 1

            node.merge_id = merge_id
            self.merge_id_to_node[merge_id] = node


    def diff(self, tree_derived, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
        """
        Invoke the external `Gumtree` tool to compare two trees `tree_a` and `tree_b`, each of which should be an
        instance of `EcoTreeDocument`.
        :param tree_derived: tree; derived version
        :return: the merged sequence, with possible conflicts. Conflicting regions are represented as `Diff3ConflictRegion`
        instances.
        """
        if isinstance(tree_derived, EcoTreeNode):
            tree_derived = EcoTreeDocument(tree_derived)

        if not isinstance(tree_derived, EcoTreeDocument):
            raise TypeError('tree_derived should be an instance of EcoTreeDocument or EcoTreeNode')

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

            json.dump(self.tree_base.as_json(), a_f)
            json.dump(tree_derived.as_json(), b_f)

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

        a_to_b = {}
        b_to_a = {}
        for m in matches_js:
            src = m['src']
            dest = m['dest']
            a_to_b[src] = dest
            b_to_a[dest] = src

        # Walk all nodes in `tree_derived` and assign merge IDs
        for node_index, node in tree_derived.index_to_node.items():
            # Use matches to translate index so that its relative to the base version tree
            base_index = b_to_a.get(node_index)

            if base_index is None:
                # The node in question is NOT present in the base version; need to assign a new merge ID
                merge_id = self.__merge_id_counter
                self.__merge_id_counter += 1

                node.merge_id = merge_id
                self.merge_id_to_node[merge_id] = node
            else:
                # Assign it the mapped merge_id
                node.merge_id = self.tree_base.index_to_node[base_index].merge_id


        diffs = []
        for action_js in actions_js:
            action = action_js['action']
            if action == 'update':
                # Update actions reference the node from tree A that is being modified
                node = self.tree_base.index_to_node[action_js['tree']]
                diffs.append(GumtreeDiffUpdate(node, action_js['label']))
            elif action == 'delete':
                # Delete actions reference the node from tree A that is being deleted
                node = self.tree_base.index_to_node[action_js['tree']]
                diffs.append(GumtreeDiffDelete(node))
            elif action == 'insert':
                # Insert actions reference the node from tree B, that is being inserted as a child of
                # a parent node - also from tree B - at a specified index
                node = tree_derived.index_to_node[action_js['tree']]
                parent = tree_derived.index_to_node[action_js['parent']]
                diffs.append(GumtreeDiffInsert(node, parent, action_js['at']))
            elif action == 'move':
                node = self.tree_base.index_to_node[action_js['tree']]
                parent = tree_derived.index_to_node[action_js['parent']]
                diffs.append(GumtreeDiffMove(node, parent, action_js['at']))

        print err

        return diffs

def gumtree_swingdiff(tree_a, tree_b, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
    """
    Invoke the external `Gumtree` tool to compare two trees `tree_a` and `tree_b`, each of which should be an
    instance of `EcoTreeDocument`.
    :param tree_a: tree version A
    :param tree_b: tree version B
    :return: the merged sequence, with possible conflicts. Conflicting regions are represented as `Diff3ConflictRegion`
    instances.
    """
    if isinstance(tree_a, EcoTreeNode):
        tree_a = EcoTreeDocument(tree_a)
    if isinstance(tree_b, EcoTreeNode):
        tree_b = EcoTreeDocument(tree_b)

    if not isinstance(tree_a, EcoTreeDocument):
        raise TypeError('tree_a should be an instance of EcoTreeDocument')
    if not isinstance(tree_b, EcoTreeDocument):
        raise TypeError('tree_b should be an instance of EcoTreeDocument')

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

        proc = subprocess.Popen([gumtree_executable_path, 'swingdiff', a_path, b_path],
                                cwd=gumtree_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate()
    finally:
        os.remove(a_path)
        os.remove(b_path)
