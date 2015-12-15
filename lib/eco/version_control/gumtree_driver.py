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
    def __init__(self, type_id, type_label, position, length, value, children, merge_id=None):
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
        self.parent = None
        self.children = children
        for child in children:
            child.parent = self
        self.index = None
        self.merge_id = merge_id

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

    def predecessor_of_child(self, child):
        i = self.children.index(child)
        return self.children[i - 1] if i > 0 else None

    def successor_of_child(self, child):
        i = self.children.index(child)
        return self.children[i + 1] if i < len(self.children) - 1 else None

    def insertion_index(self, predecessor_merge_id, successor_merge_id):
        pred_index = succ_index = None
        for i, node in enumerate(self.children):
            if predecessor_merge_id == node.merge_id:
                pred_index = i
            elif successor_merge_id == node.merge_id:
                succ_index = i
        if len(self.children) == 0:
            return 0
        else:
            if pred_index is None and succ_index is not None:
                # Successor available, no predecessor
                if succ_index < len(self.children):
                    return succ_index
            elif pred_index is not None and succ_index is None:
                # Predecessor available, no successor
                if pred_index < len(self.children):
                    return pred_index + 1
            elif pred_index is not None and succ_index is not None:
                # Predecessor and successor available
                i = pred_index + 1
                j = succ_index
                if i == j:
                    return i
                else:
                    return i, j
            return None

    def remove_child(self, child):
        self.children.remove(child)
        child.parent = None

    def insert_child(self, index, child):
        self.children.insert(index, child)
        child.parent = self

    def index_of_child_by_id(self, child_merge_id):
        for i, child in enumerate(self.children):
            if child.merge_id == child_merge_id:
                return i
        raise ValueError('No child with merge_id {0}'.format(child_merge_id))

    def copy(self, children=None):
        if children is None:
            children = []
        return GumtreeNode(self.type_id, self.type_label, self.position, self.length, self.value, children,
                           self.merge_id)

    def clone_subtree(self, merge_id_to_node):
        children = [node.clone_subtree(merge_id_to_node) for node in self.children]
        node = GumtreeNode(self.type_id, self.type_label, self.position, self.length, self.value, children,
                           self.merge_id)
        merge_id_to_node[node.merge_id] = node
        return node

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

    def __len__(self):
        return len(self.children)

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

    def __eq__(self, other):
        if isinstance(other, GumtreeNode):
            return self.value == other.value and self.type_id == other.type_id and \
                   self.type_label == other.type_label and self.children == other.children
        else:
            return False

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


    def clone_subtree(self, merge_id_to_node):
        return GumtreeDocument(self.root.clone_subtree(merge_id_to_node))

    def as_json(self):
        return {
            'root': self.root.as_json()
        }

    def as_str(self):
        return json.dumps(self.as_json())

    def node_by_id(self, node_id):
        return self.index_to_node[node_id]

    def __eq__(self, other):
        if isinstance(other, GumtreeDocument):
            return self.root == other.root
        elif isinstance(other, GumtreeNode):
            return self.root == other
        else:
            return False




class GumtreeDiff (object):
    def __init__(self, source):
        self.source = source

    def merge_op(self):
        raise NotImplementedError('abstract for {0}'.format(type(self)))

    @staticmethod
    def _node_and_id(node):
        if node is None:
            return None, None
        elif isinstance(node, GumtreeNode):
            return node, node.merge_id
        else:
            raise TypeError('node must be an GumtreeNode instance, not an {0}'.format(type(node)))

    @staticmethod
    def _find_predecessor(parent, index_in_parent, ignore_merge_id):
        if len(parent) == 0:
            return None, None
        else:
            i = index_in_parent - 1
            pred_node = parent[i]
            while pred_node.merge_id == ignore_merge_id:
                i -= 1
                if i < 0:
                    return None, None
                pred_node = parent[i]
            return pred_node, pred_node.merge_id

    @staticmethod
    def _find_successor(parent, index_in_parent, ignore_merge_id):
        if len(parent) == 0 or index_in_parent == len(parent):
            return None, None
        else:
            i = index_in_parent
            succ_node = parent[i]
            while succ_node.merge_id == ignore_merge_id:
                i += 1
                if i >= len(parent):
                    return None, None
                succ_node = parent[i]
            return succ_node, succ_node.merge_id



class GumtreeDiffUpdate (GumtreeDiff):
    def __init__(self, source, node, value):
        super(GumtreeDiffUpdate, self).__init__(source)
        self.value = value
        self.node, self.node_id = self._node_and_id(node)

    def merge_op(self):
        return GumtreeMerge3Update(self)

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
    def __init__(self, source, node):
        super(GumtreeDiffDelete, self).__init__(source)
        self.node, self.node_id = self._node_and_id(node)

    def merge_op(self):
        return GumtreeMerge3Delete(self)

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
    def __init__(self, source, node, parent, index_in_parent):
        super(GumtreeDiffInsert, self).__init__(source)
        self.node, self.node_id = self._node_and_id(node)
        self.parent_node, self.parent_id = self._node_and_id(parent)
        self.pred_node, self.pred_id = self._find_predecessor(parent, index_in_parent, self.node_id)
        self.succ_node, self.succ_id = self._find_successor(parent, index_in_parent, self.node_id)
        self.index_in_parent = index_in_parent

    def merge_op(self):
        return GumtreeMerge3Insert(self)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffInsert):
            return self.parent_id == other.parent_id and self.index_in_parent == other.index_in_parent and \
                   self.node_id == other.node_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffInsert, self.parent_id, self.index_in_parent, self.node_id))

    def __str__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.node.id_label_str,
                                                            self.parent_node.id_label_str, self.index_in_parent)

    def __repr__(self):
        return 'insert(src {0}, parent {1}, at {2})'.format(self.node.id_label_str,
                                                            self.parent_node.id_label_str, self.index_in_parent)


class GumtreeDiffMove (GumtreeDiff):
    def __init__(self, source, node, parent, index_in_parent):
        super(GumtreeDiffMove, self).__init__(source)
        self.node, self.node_id = self._node_and_id(node)
        self.parent_node, self.parent_id = self._node_and_id(parent)
        self.pred_node, self.pred_id = self._find_predecessor(parent, index_in_parent, self.node_id)
        self.succ_node, self.succ_id = self._find_successor(parent, index_in_parent, self.node_id)
        self.index_in_parent = index_in_parent

    def merge_op(self):
        return GumtreeMerge3Move(self)

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



class GumtreeMerge3Op (object):
    def __init__(self, diff):
        if not isinstance(diff, GumtreeDiff):
            raise TypeError('diff should be an instance of GumtreeDiff')
        self.conflicts = []
        self.source = diff.source

    def deletes_node(self, node_id):
        return False

    def get_updated_node_value(self, node_id):
        return None

    def moves_node(self, node_id):
        return False

    def inserts_node_before(self, node_id):
        return False

    def inserts_node_after(self, node_id):
        return False

    def get_one_way_conflict_with(self, op):
        return None

    def apply(self, src_merge_id_to_node, dst_merge_id_to_node):
        raise NotImplementedError('abstract for {0}'.format(type(self)))

    def get_conflict_with(self, op):
        conflict = self.get_one_way_conflict_with(op)
        if conflict is None:
            conflict = op.get_one_way_conflict_with(self)
        return conflict

    @staticmethod
    def coerce(x):
        if isinstance(x, GumtreeMerge3Op):
            return x
        elif isinstance(x, GumtreeDiff):
            return x.merge_op()
        else:
            raise TypeError('Cannot coerce {0} to GumtreeMerge3Op'.format(type(x)))





class GumtreeMerge3Delete (GumtreeMerge3Op):
    def __init__(self, diff):
        super(GumtreeMerge3Delete, self).__init__(diff)
        if not isinstance(diff, GumtreeDiffDelete):
            raise TypeError('diff should be an instance of GumtreeDiffDelete')
        self.node_id = diff.node_id

    def deletes_node(self, node_id):
        return node_id == self.node_id

    def get_one_way_conflict_with(self, op):
        return None

    def apply(self, src_merge_id_to_node, dst_merge_id_to_node):
        dst_node = dst_merge_id_to_node[self.node_id]
        dst_node.parent.remove_child(dst_node)

    def __eq__(self, other):
        if isinstance(other, GumtreeMerge3Delete):
            return self.node_id == other.node_id
        else:
            return False

    def __str__(self):
        return 'delete({0})'.format(self.node_id)

    def __repr__(self):
        return 'delete({0})'.format(self.node_id)


class GumtreeMerge3Update (GumtreeMerge3Op):
    def __init__(self, diff):
        super(GumtreeMerge3Update, self).__init__(diff)
        if not isinstance(diff, GumtreeDiffUpdate):
            raise TypeError('diff should be an instance of GumtreeDiffUpdate')
        self.node_id = diff.node_id
        self.value = diff.value

    def get_updated_node_value(self, node_id):
        if node_id == self.node_id:
            return (self.value,)
        else:
            return None

    def get_one_way_conflict_with(self, op):
        if op.deletes_node(self.node_id):
            # Update-delete conflict
            return GumtreeMerge3ConflictDeleteUpdate(op, self)
        wrapped_val = op.get_updated_node_value(self.node_id)
        if wrapped_val is not None:
            if wrapped_val[0] != self.value:
                # Update-update conflict
                return GumtreeMerge3ConflictUpdateUpdate(op, self)
        return None

    def apply(self, src_merge_id_to_node, dst_merge_id_to_node):
        dst_node = dst_merge_id_to_node[self.node_id]
        dst_node.value = self.value

    def __eq__(self, other):
        if isinstance(other, GumtreeMerge3Update):
            return self.node_id == other.node_id and self.value == other.value
        else:
            return False

    def __str__(self):
        return 'update({0} to {1})'.format(self.node_id, self.value)

    def __repr__(self):
        return 'update({0} to {1})'.format(self.node_id, self.value)


class GumtreeMerge3Insert (GumtreeMerge3Op):
    def __init__(self, diff):
        super(GumtreeMerge3Insert, self).__init__(diff)
        if not isinstance(diff, GumtreeDiffInsert):
            raise TypeError('diff should be an instance of GumtreeDiffInsert')
        self.node_id = diff.node_id
        self.value = diff.node.value
        self.parent_id = diff.parent_id
        self.predecessor_id = diff.pred_id
        self.successor_id = diff.succ_id
        self.src_node = diff.node

    def inserts_node_before(self, node_id):
        return node_id == self.successor_id

    def inserts_node_after(self, node_id):
        return node_id == self.predecessor_id

    def get_one_way_conflict_with(self, op):
        if op.deletes_node(self.parent_id) or \
                op.deletes_node(self.predecessor_id) or \
                op.deletes_node(self.successor_id):
            return GumtreeMerge3ConflictDeleteDestination(op, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if op.moves_node(self.predecessor_id) or \
                op.moves_node(self.successor_id):
            return GumtreeMerge3ConflictMoveDestination(op, self)
        if isinstance(op, GumtreeMerge3Insert) and \
                self.node_id == op.node_id and \
                self.parent_id == op.parent_id and \
                self.predecessor_id == op.predecessor_id and \
                self.successor_id == op.successor_id and \
                self.value != op.value:
            return GumtreeMerge3ConflictInsertInsert(op, self)
        if self.successor_id is not None and op.inserts_node_before(self.successor_id):
            return GumtreeMerge3ConflictDestinationDestination(op, self)
        if self.predecessor_id is not None and op.inserts_node_after(self.predecessor_id):
            return GumtreeMerge3ConflictDestinationDestination(op, self)
        return None

    def apply(self, src_merge_id_to_node, dst_merge_id_to_node):
        parent_node = dst_merge_id_to_node[self.parent_id]
        dst_node = src_merge_id_to_node[self.node_id].copy()
        dst_merge_id_to_node[self.node_id] = dst_node
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting new node {0}'.format(self.node_id))
        if isinstance(index, tuple):
            raise RuntimeError('Could not get unique insertion index for inserting new node {0}'.format(self.node_id))
        parent_node.insert_child(index, dst_node)

    def __eq__(self, other):
        if isinstance(other, GumtreeMerge3Insert):
            return self.node_id == other.node_id and \
                   self.value == other.value and \
                   self.parent_id == other.parent_id and \
                   self.predecessor_id == other.predecessor_id and \
                   self.successor_id == other.successor_id
        else:
            return False

    def __str__(self):
        return 'insert({0} into {1} between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                 self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'insert({0} into {1} between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                 self.predecessor_id, self.successor_id)


class GumtreeMerge3Move (GumtreeMerge3Op):
    def __init__(self, diff):
        super(GumtreeMerge3Move, self).__init__(diff)
        if not isinstance(diff, GumtreeDiffMove):
            raise TypeError('diff should be an instance of GumtreeDiffMove')
        self.node_id = diff.node_id
        self.parent_id = diff.parent_id
        self.predecessor_id = diff.pred_id
        self.successor_id = diff.succ_id

    def moves_node(self, node_id):
        return node_id == self.node_id

    def get_dest_context(self):
        return self.parent_id, self.predecessor_id, self.successor_id

    def inserts_node_before(self, node_id):
        return node_id == self.successor_id

    def inserts_node_after(self, node_id):
        return node_id == self.predecessor_id

    def get_one_way_conflict_with(self, op):
        if op.deletes_node(self.node_id):
            return GumtreeMerge3ConflictDeleteMove(op, self)
        if op.deletes_node(self.parent_id) or \
                op.deletes_node(self.predecessor_id) or \
                op.deletes_node(self.successor_id):
            return GumtreeMerge3ConflictDeleteDestination(op, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if op.moves_node(self.predecessor_id) or \
                op.moves_node(self.successor_id):
            return GumtreeMerge3ConflictMoveDestination(op, self)
        if isinstance(op, GumtreeMerge3Move) and \
                self.node_id == op.node_id and \
                (self.parent_id != op.parent_id or \
                self.predecessor_id != op.predecessor_id or \
                self.successor_id != op.successor_id):
            return GumtreeMerge3ConflictMoveMove(op, self)
        if self.successor_id is not None and op.inserts_node_before(self.successor_id):
            return GumtreeMerge3ConflictDestinationDestination(op, self)
        if self.predecessor_id is not None and op.inserts_node_after(self.predecessor_id):
            return GumtreeMerge3ConflictDestinationDestination(op, self)
        return None

    def apply(self, src_merge_id_to_node, dst_merge_id_to_node):
        parent_node = dst_merge_id_to_node[self.parent_id]
        dst_node = dst_merge_id_to_node[self.node_id]
        dst_node.parent.remove_child(dst_node)
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting moved node {0}'.format(self.node_id))
        if isinstance(index, tuple):
            raise RuntimeError('Could not get unique insertion index for inserting moved node {0}'.format(self.node_id))
        parent_node.insert_child(index, dst_node)

    def __eq__(self, other):
        if isinstance(other, GumtreeMerge3Move):
            return self.node_id == other.node_id and \
                   self.parent_id == other.parent_id and \
                   self.predecessor_id == other.predecessor_id and \
                   self.successor_id == other.successor_id
        else:
            return False

    def __str__(self):
        return 'move({0} into {1} between {2} and {3})'.format(self.node_id, self.parent_id,
                                                               self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'move({0} into {1} between {2} and {3})'.format(self.node_id, self.parent_id,
                                                               self.predecessor_id, self.successor_id)


class GumtreeMerge3Conflict (object):
    def __init__(self, op1, op2):
        self.op1 = GumtreeMerge3Op.coerce(op1)
        self.op2 = GumtreeMerge3Op.coerce(op2)
        self.register_op(self.op1)
        self.register_op(self.op2)

    def register_op(self, op):
        op.conflicts.append(self)

    @property
    def ops(self):
        return [self.op1, self.op2]


class GumtreeMerge3ConflictDeleteUpdate (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictUpdateUpdate (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictInsertInsert (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictMoveMove (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictDeleteMove (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictDeleteDestination (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictMoveDestination (GumtreeMerge3Conflict):
    pass

class GumtreeMerge3ConflictDestinationDestination (GumtreeMerge3Conflict):
    pass


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


def _convert_actions(tree_base, tree_derived, source, actions_js):
    """
    Convert a list of actions in Javascript form from the Gumtree tool, returned by `_raw_diff` into
    a list of `GumtreeDiff` instances.
    :param tree_base: tree, base version
    :param tree_derived: tree, derived version
    :param source: the value for the source field in all diffs generated
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
            diffs.append(GumtreeDiffUpdate(source, node, action_js['label']))
        elif action == 'delete':
            # Delete actions reference the node from tree A that is being deleted
            node = tree_base.index_to_node[action_js['tree']]
            diffs.append(GumtreeDiffDelete(source, node))
        elif action == 'insert':
            # Insert actions reference the node from tree B, that is being inserted as a child of
            # a parent node - also from tree B - at a specified index
            node = tree_derived.index_to_node[action_js['tree']]
            parent = tree_derived.index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffInsert(source, node, parent, action_js['at']))
        elif action == 'move':
            node = tree_base.index_to_node[action_js['tree']]
            parent = tree_derived.index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffMove(source, node, parent, action_js['at']))

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
    return _convert_actions(tree_base, tree_derived, None, actions_js)


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
    diffs_ab = _convert_actions(tree_base, tree_derived_1, 'ab', ab_actions_js)
    diffs_ac = _convert_actions(tree_base, tree_derived_2, 'ab', ac_actions_js)

    # We process the operations in the following order, so that any operation will affect nodes that
    # by that point will exist due to being in the base version tree to start with or having been introduced by
    # a previous operation:
    # Deletes - delete nodes that exist in the base version
    # Updates - update the values of nodes that exist in the base version
    # Inserts - insert new nodes into parents from the base tree or into parents that were inserted by prior
    #   insert operations. Gumtree generates insert operations in an order that ensures that the parent and
    #   predecessor nodes will already exist. Performing the inserts from the base -> derived 1 diffs
    #   followed by the inserts from the base -> derived 2 diffs should work as the insert operations from
    #   the base -> derived 2 diffs will refer to nodes that are in the base tree
    # Moves - moves existing nodes into new positions that may be within parents from the base tree or parents
    #   that were inserted by insert operations

    # Operation conflict pairings:
    #
    # Delete - delete; RESOLVABLE: node deleted in both change sets; delete it once
    # Update - delete; CONFLICT: node updated in one change set, deleted in another
    # Update - update; MOSTLY CONFLICT: node update in each change set, resolvable IF the updated values are
    #                                   the same in each change set
    # Insert - delete/update/move; CANNOT HAPPEN: a node that is inserted in one change set cannot be deleted,
    #                                             updated or moved in the other since it will not yet exist
    #                                             in the other
    # Insert - insert; MOSTlY CONFLICT: each change set inserts a node into the tree. Gumtree matches these
    #                                   inserted nodes to one another when comparing derived 1 and derived 2.
    #                                   Can be resolved if the values of the inserted nodes are identical
    #                                   and if they are inserted into the same position.
    # Insert context - delete; CONFLICT: a node is inserted beneath a parent node or adjacent to a sibling node
    #                                    where the parent or sibling nodes are deleted in the other change set
    # Insert context - update; RESOLVABLE: the context nodes (parent/sibling) are updated
    # Insert parent - move; RESOLVABLE; a node is inserted as a child of a parent node where the parent node
    #                                   is moved in the other change set
    # Move - delete; CONFLICT: node X moved in one change set, X deleted in another
    # Move - update; RESOLVABLE: move the node and update its value
    # Move - move; MOSTLY CONFLICT: node moved in both change sets, resolvable IF the destination position is
    #                               the same in each change set
    # Move context - delete; CONFLICT: node moved into position whose parent/siblings are deleted in the other
    # Move context - update; RESOLVABLE: node moved into position whose parent/siblings are updated in the other
    # Move parent - move; RESOLVABLE: node moved into child list of node that is moved elsewhere by the other
    #                                 change set
    # Move siblings - move; CONFLICT: node moved adjacent to node that is moved elsewhere in the other change set
    # Insert/move siblings - move; CONFLICT: node inserted/moved adjacent to sibling node that is moved elsewhere
    #                                        in the other change set
    # Insert/move siblings - move/insert dest; CONFLICT: node inserted/moved into position, where a
    #                                                    move/insert in the other change set inserts a node between
    #                                                    the predecessor and successor of the first insert operation

    merge3_ops_ab = [d.merge_op() for d in diffs_ab]
    merge3_ops_ac = [d.merge_op() for d in diffs_ac]

    # Detect and remove operations in `merge3_ops_ac` that are duplicates of ops from `merge3_ops_ab`
    for i, ac_op_i in reversed(list(enumerate(merge3_ops_ac))):
        remove = False
        for ab_op in merge3_ops_ab:
            if ac_op_i == ab_op:
                remove = True
                break
        if remove:
            del merge3_ops_ac[i]

    # Detect conflicts
    merge3_conflicts = []
    for ac_op in merge3_ops_ac:
        for ab_op in merge3_ops_ab:
            conflict = ab_op.get_conflict_with(ac_op)
            if conflict is not None:
                merge3_conflicts.append(conflict)

    # Create combined op list
    merge3_ops = merge3_ops_ab + merge3_ops_ac

    # Create destination tree
    merged_merge_id_to_node = {}
    tree_merged = tree_base.root.clone_subtree(merged_merge_id_to_node)

    # Apply ops that are not involved in conflicts
    for op in merge3_ops:
        if len(op.conflicts) == 0:
            op.apply(merge_id_to_node, merged_merge_id_to_node)

    return tree_merged, merge3_ops, merge3_conflicts
