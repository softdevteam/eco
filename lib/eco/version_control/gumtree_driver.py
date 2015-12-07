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

    def node(self, value, children):
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

        cur_index += 1

        index_to_node[self.index] = self

        return cur_index, cur_leaf_count


    def as_json(self):
        return {
            '__type__': 'TreeNode',
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


class EcoTreeDocument (object):
    def __init__(self, root):
        self.root = root
        self.index_to_node = {}

        self.root.walk_structure(0, 0, self.index_to_node)

        print self.index_to_node


    def as_json(self):
        return {
            '__type__': 'EcoTree',
            'tree': self.root.as_json()
        }

    def as_str(self):
        return json.dumps(self.as_json())


class GumtreeDiff (object):
    @staticmethod
    def _node_and_id(doc, node):
        if isinstance(node, EcoTreeNode):
            return node, node.index
        elif isinstance(node, (int, long)):
            node_ref = doc.index_to_node[node] if doc is not None else None
            return node_ref, node
        else:
            raise TypeError('node must be an int, long or an EcoTreeNode instance')


class GumtreeDiffUpdate (GumtreeDiff):
    def __init__(self, dst_doc, node, value):
        self.dst_doc = dst_doc
        self.value = value
        self.node, self.node_id = self._node_and_id(dst_doc, node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffUpdate):
            return self.node_id == other.node_id and self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffUpdate, self.node_id, self.value))

    def __str__(self):
        return 'update({0}: value={1})'.format(self.node_id, self.value)

    def __repr__(self):
        return 'update({0}: value={1})'.format(self.node_id, self.value)


class GumtreeDiffDelete (GumtreeDiff):
    def __init__(self, dst_doc, node):
        self.dst_doc = dst_doc
        self.node, self.node_id = self._node_and_id(dst_doc, node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffDelete):
            return self.node_id == other.node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffDelete, self.node_id))

    def __str__(self):
        return 'delete({0})'.format(self.node_id)

    def __repr__(self):
        return 'delete({0})'.format(self.node_id)


class GumtreeDiffInsert (GumtreeDiff):
    def __init__(self, dst_doc, src_doc, parent, index_in_parent, src_node):
        self.dst_doc = dst_doc
        self.src_doc = src_doc
        self.parent_node, self.parent_id = self._node_and_id(dst_doc, parent)
        self.index_in_parent = index_in_parent
        self.src_node, self.src_node_id = self._node_and_id(src_doc, src_node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffInsert):
            return self.parent_id == other.parent_id and self.index_in_parent == other.index_in_parent and \
                   self.src_node_id == other.src_node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffInsert, self.parent_id, self.index_in_parent, self.src_node_id))

    def __str__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.src_node_id, self.parent_id, self.index_in_parent)

    def __repr__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.src_node_id, self.parent_id, self.index_in_parent)


class GumtreeDiffMove (GumtreeDiff):
    def __init__(self, dst_doc, parent, index_in_parent, node):
        self.dst_doc = dst_doc
        self.parent_node, self.parent_id = self._node_and_id(dst_doc, parent)
        self.index_in_parent = index_in_parent
        self.node, self.node_id = self._node_and_id(dst_doc, node)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffMove):
            return self.parent_id == other.parent_id and self.index_in_parent == other.index_in_parent and \
                   self.node_id == other.node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffMove, self.parent_id, self.index_in_parent, self.node_id))

    def __str__(self):
        return 'move({0}, parent {1}, at {2})'.format(self.node_id, self.parent_id, self.index_in_parent)

    def __repr__(self):
        return 'move({0}, parent {1}, at {2})'.format(self.node_id, self.parent_id, self.index_in_parent)


DEFAULT_GUMTREE_PATH = os.path.expanduser('~/kcl/bin_gumtree/dist-2.1.0-SNAPSHOT/bin')


def gumtree(tree_a, tree_b, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
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
    a_fd, a_path = tempfile.mkstemp(suffix='.ecotree')
    b_fd, b_path = tempfile.mkstemp(suffix='.ecotree')

    try:
        a_f = os.fdopen(a_fd, 'w')
        b_f = os.fdopen(b_fd, 'w')

        json.dump(tree_a.as_json(), a_f)
        json.dump(tree_b.as_json(), b_f)

        print json.dumps(tree_a.as_json())
        print json.dumps(tree_b.as_json())

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

    diffs_js = json.loads(out)

    diffs = []

    for d in diffs_js:
        action = d['action']
        if action == 'update':
            diffs.append(GumtreeDiffUpdate(tree_a, d['tree'], d['label']))
        elif action == 'delete':
            diffs.append(GumtreeDiffDelete(tree_a, d['tree']))
        elif action == 'insert':
            diffs.append(GumtreeDiffInsert(tree_a, tree_b, d['parent'], d['at'], d['tree']))
        elif action == 'move':
            diffs.append(GumtreeDiffMove(tree_a, d['parent'], d['at'], d['tree']))

    return diffs