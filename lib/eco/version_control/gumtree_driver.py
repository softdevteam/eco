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
    """
    Gumtree diff node class used to represent the nodes in a tree that is to be used for differencing or 3-way merge.

    Attributes:

    The constructor arguments are directly copied into attributes of the same name. In addition, the following
    attributes are available:

    :var parent: a reference to the parent node; note this attribute is set by the constructor, so that children
    passed to the constructor have their parent references set.
    :var merge_id: the ID used to identify this node during 3-way merge operations; nodes that have the
    same `merge_id` are matched with one another.
    """
    def __init__(self, type_id, type_label, position, length, value, children, _merge_id=None):
        """
        Constructor. Each node has a type, a position and length, a value and children. The type would roughly
        correspond to the class of the node, or the grammar rule in the case of a parse tree. Nodes of the same type
        can be matched.
        The position and length specify the region of text that the node covers. The value is a textual value,
        changes to which can be detected as update operations.

        :param type_id: A unique ID for the type named by `type_label`.
        :param type_label: the name of the type
        :param position: the position of the node within the text document (use 0 if not used)
        :param length: the length of the text in the document covered by the node (use 0 if not used)
        :param value: the textual value of the node
        :param children: a list of nodes that are the children of this node
        :param _merge_id: unique merge ID; used internally
        :return:
        """
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
        self._gumtree_index = None
        self.merge_id = _merge_id

    @property
    def parent_merge_id(self):
        """
        Return the merge ID of the parent node, or `Node` if `self` has no parent.
        """
        return self.parent.merge_id if self.parent is not None else None

    def build_gumtree_index_to_node_table(self):
        """
        Walk the tree rooted at `self`, assigning Gumtree indices to nodes as they are encountered.
        This allows Gumtree and the driver to have a consistent indexing scheme for identifying nodes.

        :return: `{gumtree_index: node}`; a dictionary mapping Gumtree indices to nodes
        """
        gumtree_index_to_node = {}
        self._walk_subtree_internal(gumtree_index_to_node, 0, 0)
        return gumtree_index_to_node

    def _walk_subtree_internal(self, gumtree_index_to_node, _index, _leaf_count):
        if self.position is None:
            self.position = _leaf_count
        cur_index = _index
        cur_leaf_count = _leaf_count

        if self.children is None  or  len(self.children) == 0:
            # Leaf node
            cur_leaf_count += 1
        else:
            # Branch node
            for child in self.children:
                cur_index, cur_leaf_count = child._walk_subtree_internal(gumtree_index_to_node, cur_index, cur_leaf_count)

        if self.length is None:
            self.length = cur_leaf_count - _leaf_count

        self._gumtree_index = cur_index
        gumtree_index_to_node[self._gumtree_index] = self

        return cur_index + 1, cur_leaf_count


    def clear_merge_ids(self):
        """
        Reset merge IDs of nodes in the subtree rooted at `self`.
        """
        self.merge_id = None
        for child in self.children:
            child.clear_merge_ids()

    def get_ancestry_merge_ids(self):
        """
        Get a list of node merge IDs along the path to the root
        :return: list of node merge IDs
        """
        merge_ids = []
        node = self
        while node is not None:
            merge_ids.append(node.merge_id)
            node = node.parent
        return merge_ids

    def predecessor_of_child(self, child):
        """
        Get the child node that is the left sibling of `child`.

        :param child: the reference point child node
        :return: the predecessor of `child` or `None` if `child` is the first child in `self.children`.
        """
        i = self.children.index(child)
        return self.children[i - 1] if i > 0 else None

    def successor_of_child(self, child):
        """
        Get the child node that is the right sibling of `child`.

        :param child: the reference point child node
        :return: the successor of `child` or `None` if `child` is the last child in `self.children`.
        """
        i = self.children.index(child)
        return self.children[i + 1] if i < len(self.children) - 1 else None

    def insertion_index(self, predecessor_merge_id, successor_merge_id):
        """
        Compute the index at which a node should be inserted such that it is between the child nodes identified by
        the merge IDs `predecessor_merge_id` and `successor_merge_id`. This is used during 3-way merge to determine
        where to insert a node by specifying the position relative to its surroundings, rather than using an
        absolute value.

        If no position could be found, `None` is returned. If the predecessor and successor nodes are both present
        but not neighbours, then a tuple of two positions is returned; `(i, j)` where `i` is the position after
        the predecessor and `j` is the position of the successor. If a single insertion point was found, it is
        returned as an integer index.

        :param predecessor_merge_id: The merge ID of the predecessor node
        :param successor_merge_id: The merge ID of the successor node
        :return: `None`, or `i` or `(i, j)`
        """
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
                return succ_index
            elif pred_index is not None and succ_index is None:
                # Predecessor available, no successor
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
        """
        Remove a child node
        :param child: child to remove
        """
        self.children.remove(child)
        child.parent = None

    def insert_child(self, index, child):
        """
        Insert a child node
        :param index: the position at which to insert `child`
        :param child: child to remove
        """
        self.children.insert(index, child)
        child.parent = self

    def detach_from_parent(self):
        """
        Remove from the child list of the parent.
        """
        if self.parent is not None:
            self.parent.remove_child(self)

    def copy(self, children=None):
        """
        Create a copy of `self`, with children specified as a parameter

        :param children:
        :return: the copy of `self`
        """
        if children is None:
            children = []
        return GumtreeNode(self.type_id, self.type_label, self.position, self.length, self.value, children,
                           self.merge_id)

    def clone_subtree(self, merge_id_to_node):
        """
        Clone the subtree rooted at self.

        :param merge_id_to_node: a dictionary mapping node merge ID to node that is filled in as clone nodes are created.
        :return: the cloned subtree
        """
        children = [node.clone_subtree(merge_id_to_node) for node in self.children]
        node = GumtreeNode(self.type_id, self.type_label, self.position, self.length, self.value, children,
                           self.merge_id)
        merge_id_to_node[node.merge_id] = node
        return node

    def as_json(self):
        """
        Create a Gumtree compatible JSON representation of the subtree rooted at `self`.

        :return: JSON data
        """
        return {
            'label': self.value,
            'type': self.type_id,
            'type_label': self.type_label,
            'pos': self.position,
            'length': self.length,
            'children': [child.as_json() for child in self.children] if self.children is not None else [],
        }

    def __getitem__(self, index):
        """
        Get the child at position `index`.

        :param index: index of child
        :return: child node
        """
        return self.children[index]

    def __len__(self):
        """
        Get the number of children

        :return: number of children
        """
        return len(self.children)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    @property
    def label_str(self):
        """
        :return: A string giving the type and value of self of the form '<type>:<value>'.
        """
        return '{0}:{1}'.format(self.type_label, self.value)

    @property
    def id_label_str(self):
        """
        :return: A string giving the type and value of self of the form '<merge_id>:<type>:<value>'.
        """
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
    """
    A document for use with Gumtree. Contains a tree built of `GumtreeNode` instances.
    """
    def __init__(self, root):
        self.root = root
        self.gumtree_index_to_node = self.root.build_gumtree_index_to_node_table()


    def clear_merge_ids(self):
        """
        Clear the merge IDs of the node in the tree.
        """
        self.root.clear_merge_ids()


    def clone_subtree(self, merge_id_to_node):
        """
        Create a clone of the document.
        :return: the clone
        """
        return GumtreeDocument(self.root.clone_subtree(merge_id_to_node))

    def as_json(self):
        """
        Create a Gumtree compatible JSON representation of the subtree rooted at `self`.

        :return: JSON data
        """
        return {
            'root': self.root.as_json()
        }

    def __eq__(self, other):
        if isinstance(other, GumtreeDocument):
            return self.root == other.root
        elif isinstance(other, GumtreeNode):
            return self.root == other
        else:
            return False




class GumtreeAbstractDiff (object):
    """
    Difference operation abstract base class.

    Atrributes:

    :var source: an identifier used to identify where this diff came from, e.g. in 3-way merge the identifiers could
    be `'AB'` and `'AC'`.
    :var conflicts: a list of conflicts that involve this diff; thist list will be empty if this diff did not
    conflict with any other.
    """
    def __init__(self, source):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        """
        self.source = source
        self.conflicts = []


    def deletes_node(self, node_merge_id):
        """
        Return True if the node whose merge ID is `node_merge_id` is deleted by this diff, False otherwise
        """
        return False

    def get_updated_node_value_in_tuple(self, node_id):
        """
        If this diff updates the value of the node whose merge ID is `node_merge_id`, return the new value
        in a single-element tuple, otherwise return None.
        """
        return None

    def moves_node(self, node_id):
        """
        Return True if the node whose merge ID is `node_merge_id` is moved by this diff, False otherwise
        """
        return False

    def inserts_node_before(self, node_id):
        """
        Return True if this diff inserts a node before the node whose merge ID is `node_merge_id`, False otherwise
        """
        return False

    def inserts_node_after(self, node_id):
        """
        Return True if this diff inserts a node after the node whose merge ID is `node_merge_id`, False otherwise
        """
        return False

    def get_deleted_node_id(self):
        """
        Get the node merge ID of the node that is deleted by `self`, or `None` if this diff does not delete a node.
        """
        return None

    def get_moved_node_id(self):
        """
        Get the node merge ID of the node that is moved by `self`, or `None` if this diff does not move a node.
        """
        return None

    def required_target_node_id(self):
        """
        Get the node merge ID of the node that must exist in the destination tree for this diff to by successfully
        applied. For an update operation, this would be the node whose value is being updated. For an insert or move
        it would be the new parent.
        """
        return None

    def _detect_one_way_conflict_with(self, diff):
        """
        Detect a conflict with the diff passed as an argument. Only needs to detect the conflict one way
        as it is invoked in both directions by the `detect_conflict_with` method.
        A one way conflict is an 'op' -> 'self' conflict, e.g. if `self` is an update and `op` is a delete, then this
        would detect a delete-update conflict, but would not need to detect a update-delete.

        :return: a conflict if detected, or `None` for no conflict.
        """
        return None

    def detect_conflict_with(self, diff):
        """
        Detect a conflict with the diff passed as an argument.

        :return: a conflict if detected, or `None` for no conflict.
        """
        conflict = self._detect_one_way_conflict_with(diff)
        if conflict is None:
            conflict = diff._detect_one_way_conflict_with(self)
        return conflict

    def apply(self, merge_id_to_node):
        """
        Apply this diff to the destination tree, whose nodes are accessible via `merge_id_to_node`.
        :param merge_id_to_node: a dictionary that maps node merge ID to node
        """
        raise NotImplementedError('abstract for {0}'.format(type(self)))

    def get_description(self, node_id_to_node):
        """
        Get a textual description of this diff.
        """
        raise NotImplementedError('abstract for {0}'.format(type(self)))


    @staticmethod
    def _get_node_id(node):
        """
        Coerce `node` into a merge ID. If `node` is `None` returns `None`, if `node` is an int or long returns `node`,
        if it is a `GumtreeNode` returns its merge ID, otherwise raises `TypeError`.
        """
        if node is None:
            return None
        elif isinstance(node, GumtreeNode):
            return node.merge_id
        elif isinstance(node, (int, long)):
            return node
        else:
            raise TypeError('node must be an GumtreeNode instance, an int, or None; not an {0}'.format(type(node)))

    @staticmethod
    def _find_predecessor(parent, index_in_parent, ignore_merge_id):
        """
        Get the merge ID of the node that is the predecessor/left sibling to child `index_in_parent` of `parent`.
        `ignore_merge_id` is an optional merge ID of a node that should be passed over.

        :param parent: the parent node; `GumtreeNode` instance
        :param index_in_parent: the index of the child in `parent`
        :param ignore_merge_id: optional merge ID of a node to skip over when searching backwards from `index_in_parent`.
        :return: the merge ID of the predecessor or `None` if one could not be found.
        """
        if len(parent) == 0:
            return None
        else:
            i = index_in_parent - 1
            pred_node = parent[i]
            while pred_node.merge_id == ignore_merge_id:
                i -= 1
                if i < 0:
                    return None
                pred_node = parent[i]
            return pred_node.merge_id

    @staticmethod
    def _find_successor(parent, index_in_parent, ignore_merge_id):
        """
        Get the merge ID of the node that is the successor/right sibling to child `index_in_parent` of `parent`.
        `ignore_merge_id` is an optional merge ID of a node that should be passed over.

        :param parent: the parent node; `GumtreeNode` instance
        :param index_in_parent: the index of the child in `parent`
        :param ignore_merge_id: optional merge ID of a node to skip over when searching forwards from `index_in_parent`.
        :return: the merge ID of the successor or `None` if one could not be found.
        """
        if len(parent) == 0 or index_in_parent == len(parent):
            return None
        else:
            i = index_in_parent
            succ_node = parent[i]
            while succ_node.merge_id == ignore_merge_id:
                i += 1
                if i >= len(parent):
                    return None
                succ_node = parent[i]
            return succ_node.merge_id



class GumtreeDiffDelete (GumtreeAbstractDiff):
    """
    Delete diff operation

    Attributes:
        :var source: an identifier used to identify where this diff came from, e.g. in 3-way merge the identifiers could
        be `'AB'` and `'AC'`.
        :var conflicts: a list of conflicts that involve this diff; thist list will be empty if this diff did not
        conflict with any other.
        :var node_id: the merge ID of the node to delete.
    """
    def __init__(self, source, node):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node to be deleted, either as a `GumtreeNode` instance or as an integer node merge ID.
        """
        super(GumtreeDiffDelete, self).__init__(source)
        self.node_id = self._get_node_id(node)


    def deletes_node(self, node_merge_id):
        return node_merge_id == self.node_id

    def get_deleted_node_id(self):
        return self.node_id

    def _detect_one_way_conflict_with(self, diff):
        return None

    def apply(self, merge_id_to_node):
        dst_node = merge_id_to_node[self.node_id]
        dst_node.parent.remove_child(dst_node)


    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.node_id]
        return 'delete({0})'.format(node.id_label_str)


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


class GumtreeDiffUpdate (GumtreeAbstractDiff):
    """
    Update diff operation

    Attributes:
        :var source: an identifier used to identify where this diff came from, e.g. in 3-way merge the identifiers could
        be `'AB'` and `'AC'`.
        :var conflicts: a list of conflicts that involve this diff; thist list will be empty if this diff did not
        conflict with any other.
        :var node_id: the merge ID of the node to update.
        :var value: the updated node value
    """
    def __init__(self, source, node, value):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node to be update, either as a `GumtreeNode` instance or as an integer node merge ID.
        :param value: the new value
        """
        super(GumtreeDiffUpdate, self).__init__(source)
        self.value = value
        self.node_id = self._get_node_id(node)

    def get_updated_node_value_in_tuple(self, node_id):
        if node_id == self.node_id:
            return (self.value,)
        else:
            return None

    def _detect_one_way_conflict_with(self, diff):
        if diff.deletes_node(self.node_id):
            # Update-delete conflict
            return GumtreeMerge3ConflictDeleteUpdate(diff, self)
        wrapped_val = diff.get_updated_node_value_in_tuple(self.node_id)
        if wrapped_val is not None:
            if wrapped_val[0] != self.value:
                # Update-update conflict
                return GumtreeMerge3ConflictUpdateUpdate(diff, self)
        return None

    def apply(self, merge_id_to_node):
        dst_node = merge_id_to_node[self.node_id]
        dst_node.value = self.value

    def required_target_node_id(self):
        return self.node_id

    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.node_id]
        return 'update({0}, value={1})'.format(node.id_label_str, self.value)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffUpdate):
            return self.node_id == other.node_id and self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffUpdate, self.node_id, self.value))

    def __str__(self):
        return 'update({0}, value={1})'.format(self.node_id, self.value)

    def __repr__(self):
        return 'update({0}, value={1})'.format(self.node_id, self.value)


class GumtreeDiffInsert (GumtreeAbstractDiff):
    """
    Insert diff operation

    Attributes:
        :var source: an identifier used to identify where this diff came from, e.g. in 3-way merge the identifiers could
        be `'AB'` and `'AC'`.
        :var conflicts: a list of conflicts that involve this diff; thist list will be empty if this diff did not
        conflict with any other.
        :var node_id: the merge ID of the node to insert.
        :var parent_id: the merge ID of the parent under which the new node that is to be inserted
        :var predecessor_id: the merge ID of the predecessor (left-sibling) of the new node that is to be inserted
        :var successor_id: the merge ID of the successor (right-sibling) of the new node that is to be inserted
        :var value: the updated node value
        :var src_node: a reference to the inserted node from the destination tree
    """
    def __init__(self, source, node, parent, index_in_parent):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node from the destination tree that is to be inserted
        :param parent: the node from the soruce tree that is to be the parent of the inserted node
        :param index_in_parent: the index at which the new node is to be inserted
        """
        super(GumtreeDiffInsert, self).__init__(source)
        self.node_id = self._get_node_id(node)
        self.parent_id = self._get_node_id(parent)
        self.predecessor_id = self._find_predecessor(parent, index_in_parent, self.node_id)
        self.successor_id = self._find_successor(parent, index_in_parent, self.node_id)
        self.value = node.value
        self.src_node = node

    def inserts_node_before(self, node_id):
        return node_id == self.successor_id

    def inserts_node_after(self, node_id):
        return node_id == self.predecessor_id

    def _detect_one_way_conflict_with(self, diff):
        if diff.deletes_node(self.parent_id) or \
                diff.deletes_node(self.predecessor_id) or \
                diff.deletes_node(self.successor_id):
            return GumtreeMerge3ConflictDeleteDestination(diff, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if diff.moves_node(self.predecessor_id) or \
                diff.moves_node(self.successor_id):
            return GumtreeMerge3ConflictMoveDestination(diff, self)
        if isinstance(diff, GumtreeDiffInsert) and \
                self.node_id == diff.node_id and \
                self.parent_id == diff.parent_id and \
                self.predecessor_id == diff.predecessor_id and \
                self.successor_id == diff.successor_id and \
                self.value != diff.value:
            return GumtreeMerge3ConflictInsertInsert(diff, self)
        if self.successor_id is not None and diff.inserts_node_before(self.successor_id):
            return GumtreeMerge3ConflictDestinationDestination(diff, self)
        if self.predecessor_id is not None and diff.inserts_node_after(self.predecessor_id):
            return GumtreeMerge3ConflictDestinationDestination(diff, self)
        return None

    def apply(self, merge_id_to_node):
        parent_node = merge_id_to_node[self.parent_id]
        node_to_insert = merge_id_to_node[self.node_id]
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting new node {0}'.format(self.node_id))
        if isinstance(index, tuple):
            raise RuntimeError('Could not get unique insertion index for inserting new node {0}'.format(self.node_id))
        parent_node.insert_child(index, node_to_insert)

    def required_target_node_id(self):
        return self.parent_id

    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.node_id]
        parent_node = node_id_to_node[self.parent_id]
        insertion_index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        return 'insert(src {0}, parent {1}, at {2})'.format(node.id_label_str,
                                                            parent_node.id_label_str, insertion_index)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffInsert):
            return self.parent_id == other.parent_id and self.predecessor_id == other.predecessor_id and \
                   self.successor_id == other.successor_id and self.node_id == other.node_id and \
                   self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffInsert, self.parent_id, self.predecessor_id, self.successor_id, self.node_id))

    def __str__(self):
        return 'insert(src {0}, parent {1}, between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                         self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'insert(src {0}, parent {1}, between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                         self.predecessor_id, self.successor_id)


class GumtreeDiffMove (GumtreeAbstractDiff):
    """
    Move diff operation

    Attributes:
        :var source: an identifier used to identify where this diff came from, e.g. in 3-way merge the identifiers could
        be `'AB'` and `'AC'`.
        :var conflicts: a list of conflicts that involve this diff; thist list will be empty if this diff did not
        conflict with any other.
        :var node_id: the merge ID of the node to move.
        :var parent_id: the merge ID of the parent of the destination position
        :var predecessor_id: the merge ID of the predecessor (left-sibling) of the destination position
        :var successor_id: the merge ID of the successor (right-sibling) of the destination position
    """
    def __init__(self, source, node, parent, index_in_parent):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node from the source tree that is to be moved
        :param parent: the node from the soruce tree that under which `node` should be positioned
        :param index_in_parent: the index of the new position of `node`
        """
        super(GumtreeDiffMove, self).__init__(source)
        self.node_id = self._get_node_id(node)
        self.parent_id = self._get_node_id(parent)
        self.predecessor_id = self._find_predecessor(parent, index_in_parent, self.node_id)
        self.successor_id = self._find_successor(parent, index_in_parent, self.node_id)

    def moves_node(self, node_id):
        return node_id == self.node_id

    def get_dest_context(self):
        return self.parent_id, self.predecessor_id, self.successor_id

    def inserts_node_before(self, node_id):
        return node_id == self.successor_id

    def inserts_node_after(self, node_id):
        return node_id == self.predecessor_id

    def _detect_one_way_conflict_with(self, diff):
        if diff.deletes_node(self.node_id):
            return GumtreeMerge3ConflictDeleteMove(diff, self)
        if diff.deletes_node(self.parent_id) or \
                diff.deletes_node(self.predecessor_id) or \
                diff.deletes_node(self.successor_id):
            return GumtreeMerge3ConflictDeleteDestination(diff, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if diff.moves_node(self.predecessor_id) or \
                diff.moves_node(self.successor_id):
            return GumtreeMerge3ConflictMoveDestination(diff, self)
        if isinstance(diff, GumtreeDiffMove) and \
                self.node_id == diff.node_id and \
                (self.parent_id != diff.parent_id or \
                self.predecessor_id != diff.predecessor_id or \
                self.successor_id != diff.successor_id):
            return GumtreeMerge3ConflictMoveMove(diff, self)
        if self.successor_id is not None and diff.inserts_node_before(self.successor_id):
            return GumtreeMerge3ConflictDestinationDestination(diff, self)
        if self.predecessor_id is not None and diff.inserts_node_after(self.predecessor_id):
            return GumtreeMerge3ConflictDestinationDestination(diff, self)
        return None

    def get_moved_node_id(self):
        return self.node_id

    def apply(self, merge_id_to_node):
        parent_node = merge_id_to_node[self.parent_id]
        node_to_move = merge_id_to_node[self.node_id]
        node_to_move.detach_from_parent()
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting moved node {0}'.format(self.node_id))
        if isinstance(index, tuple):
            raise RuntimeError('Could not get unique insertion index for inserting moved node {0}'.format(self.node_id))
        parent_node.insert_child(index, node_to_move)

    def required_target_node_id(self):
        return self.parent_id

    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.node_id]
        parent_node = node_id_to_node[self.parent_id]
        insertion_index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        return 'move(src {0}, to parent {1}, at {2})'.format(node.id_label_str,
                                                            parent_node.id_label_str, insertion_index)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffMove):
            return self.parent_id == other.parent_id and self.node_id == other.node_id and \
                   self.predecessor_id == other.predecessor_id and self.successor_id == other.successor_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffMove, self.parent_id, self.predecessor_id, self.successor_id, self.node_id))

    def __str__(self):
        return 'move(src {0}, to parent {1}, between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                       self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'move(src {0}, to parent {1}, between {2} and {3})'.format(self.node_id, self.parent_id,
                                                                       self.predecessor_id, self.successor_id)



class GumtreeMerge3Conflict (object):
    """
    Three-way merge conflict base class. Represents a conflict between two difference operations.

    Attributes:
        :var op1: the first diff
        :var op2: the second diff

    Class attributes:
        :var COMMUTATIVE: this class attribute determines if the operation is commutative; if so, then
         the operations `op1` and `op2` can be swapped without changing the meaning of the operation.
         This helps when comparing conflicts for equality.
    """
    COMMUTATIVE = False

    def __init__(self, op1, op2):
        self.op1 = op1
        self.op2 = op2
        self.register_op(self.op1)
        self.register_op(self.op2)

    def register_op(self, op):
        op.conflicts.append(self)

    @property
    def ops(self):
        return [self.op1, self.op2]

    def __eq__(self, other):
        if isinstance(other, type(self)):
            if self.COMMUTATIVE:
                return self.op1 == other.op1 and self.op2 == other.op2 or \
                    self.op1 == other.op2 and self.op2 == other.op1
            else:
                return self.op1 == other.op1 and self.op2 == other.op2
        else:
            return False

    def __repr__(self):
        return str(self)


class GumtreeMerge3ConflictDeleteUpdate (GumtreeMerge3Conflict):
    """
    Delete-update conflict: `op1` deletes the node that is updated by `op2`.
    """
    def __str__(self):
        return 'DeleteUpdateConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictUpdateUpdate (GumtreeMerge3Conflict):
    """
    Update-update conflict: `op1` and `op2` both update the same node to have different values.
    """
    COMMUTATIVE = True

    def __str__(self):
        return 'UpdareUpdateConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictInsertInsert (GumtreeMerge3Conflict):
    """
    Insert-insert conflict: `op1` and `op2` both insert a node at the same position, but with different values
    """
    COMMUTATIVE = True

    def __str__(self):
        return 'InsertInsertConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictMoveMove (GumtreeMerge3Conflict):
    """
    Move-move conflict: `op1` and `op2` both move the same node to different destinations
    """
    COMMUTATIVE = True

    def __str__(self):
        return 'MoveMoveConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictDeleteMove (GumtreeMerge3Conflict):
    """
    Delete-move conflict: `op1` deletes the node that is moved by `op2`.
    """
    def __str__(self):
        return 'DeleteMoveConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictDeleteDestination (GumtreeMerge3Conflict):
    """
    Delete-destination conflict: `op1` deletes a node that surrounds - either as a parent, a predecessor or successor -
    of an insert destination or move destination.
    """
    def __str__(self):
        return 'DeleteDestConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictMoveDestination (GumtreeMerge3Conflict):
    """
    Move-destination conflict: `op1` moves away a node that surrounds - either as a predecessor or successor -
    of an insert destination or move destination.

    Note that it is not a conflict to move the parent of an insert or move destination, as the destination will
    move with the parent in such cases.
    """
    def __str__(self):
        return 'MoveDestConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictDestinationDestination (GumtreeMerge3Conflict):
    """
    Destination-destination conflict: `op1` inserts or moves a node into a position between the destination of `op2`
    and its predecessor or successor.
    """
    COMMUTATIVE = True

    def __str__(self):
        return 'DestDestConflict({0}, {1})'.format(self.op1, self.op2)

class GumtreeMerge3ConflictDeleteAncestry (GumtreeMerge3Conflict):
    """
    Delete-ancestry conflict: `op1` deletes a node that lies on the path between the root and a node required
    by `op2`, where the required node is either the node that is to be modified in the case of an update, or
    the parent the destination in the case of a move or insert.
    """
    def __str__(self):
        return 'DeleteAncestryConflict({0}, {1})'.format(self.op1, self.op2)



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
            node = tree_base.gumtree_index_to_node[action_js['tree']]
            diffs.append(GumtreeDiffUpdate(source, node, action_js['label']))
        elif action == 'delete':
            # Delete actions reference the node from tree A that is being deleted
            node = tree_base.gumtree_index_to_node[action_js['tree']]
            diffs.append(GumtreeDiffDelete(source, node))
        elif action == 'insert':
            # Insert actions reference the node from tree B, that is being inserted as a child of
            # a parent node - also from tree B - at a specified index
            node = tree_derived.gumtree_index_to_node[action_js['tree']]
            parent = tree_derived.gumtree_index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffInsert(source, node, parent, action_js['at']))
        elif action == 'move':
            node = tree_base.gumtree_index_to_node[action_js['tree']]
            parent = tree_derived.gumtree_index_to_node[action_js['parent']]
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
    for derived_node_index, derived_node in tree_base.gumtree_index_to_node.items():
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
    for derived_node_index, derived_node in tree_derived.gumtree_index_to_node.items():
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
            derived_node.merge_id = tree_base.gumtree_index_to_node[base_index].merge_id

    # Convert actions to `GumtreeDiff` instances
    return _convert_actions(tree_base, tree_derived, None, actions_js)


def _remove_redundant_delete_diffs(ops, merge_id_to_node):
    """
    Remove redundant delete operations; remove all operations that delete a node whose parent is also deleted; only
    delete operations that delete notes that are at the root of deleted subtrees will remain

    :param ops: the list of operations to filter
    :param merge_id_to_node: a table mapping node merge ID to node
    :return: filtered operation list
    """
    delete_ops = []
    non_delete_ops = []
    for op in ops:
        if isinstance(op, GumtreeDiffDelete):
            delete_ops.append(op)
        else:
            non_delete_ops.append(op)

    delete_node_ids = set()
    for op in delete_ops:
        deleted_id = op.get_deleted_node_id()
        if deleted_id is not None:
            delete_node_ids.add(deleted_id)

    # Remove any delete operations that delete nodes that are children of nodes that are also deleted
    delete_ops = [op for op in delete_ops
                           if merge_id_to_node[op.node_id].parent_merge_id not in delete_node_ids]
    return delete_ops + non_delete_ops


def gumtree_diff3(tree_base, tree_derived_1, tree_derived_2, gumtree_path=None, gumtree_executable_name='dist', join_path=True):
    """
    Perform a three-way merge and diff between a base version tree and two derived versions.
    :param tree_base: the base version of the tree, as a `GumtreeNode` or a `GumtreeDocument`.
    :param tree_derived_1: the first derived version of the tree, as a `GumtreeNode` or a `GumtreeDocument`.
    :param tree_derived_2: the second derived version of the tree, as a `GumtreeNode` or a `GumtreeDocument`.

    :return: a tuple of `(merged_tree, merged_diffs, conflicts)` where `merged_tree` is the merged tree,
    `merged_diffs` is a list of difference operations as instances of subclasses of `GumtreeAbstractDiff`
    and `conflicts` is a list of detected conflicts.
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
    for B_node_index, B_node in tree_base.gumtree_index_to_node.items():
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
    for B_node_index, B_node in tree_derived_1.gumtree_index_to_node.items():
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
            B_node.merge_id = tree_base.gumtree_index_to_node[A_index].merge_id


    # Walk all nodes in `tree_derived_2` and assign merge IDs using matches with `tree_base`
    for C_node_index, C_node in tree_derived_2.gumtree_index_to_node.items():
        # Use `C_ndx_to_A_ndx` to translate index so that its relative to the base version tree
        A_index = C_ndx_to_A_ndx.get(C_node_index)

        if A_index is not None:
            # Assign it the merge ID of the matching node from the base tree
            C_node.merge_id = tree_base.gumtree_index_to_node[A_index].merge_id
        else:
            # Use `C_ndx_to_B_ndx` to translate index so that its relative to the derived 1 version tree
            B_index = C_ndx_to_B_ndx.get(C_node_index)

            if B_index is not None:
                # Assign it the merge ID of the matching node from the derived 1 tree
                C_node.merge_id = tree_derived_1.gumtree_index_to_node[B_index].merge_id
            else:
                # The node in question is NOT matched to any node in the base tree or the derived 1 tree;
                # need to assign it a new merge ID
                merge_id = merge_id_counter
                merge_id_counter += 1

                C_node.merge_id = merge_id
                merge_id_to_node[merge_id] = C_node


    # Convert actions to `GumtreeDiff` instances
    diffs_ab = _convert_actions(tree_base, tree_derived_1, 'ab', ab_actions_js)
    diffs_ac = _convert_actions(tree_base, tree_derived_2, 'ac', ac_actions_js)

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

    # Detect and remove diffs in `diffs_ac` that are duplicates of diffs from `diffs_ab`
    diffs_ab_set = set(diffs_ab)
    diffs_ac = [diff for diff in diffs_ac if diff not in diffs_ab_set]

    # Mark all delete operations that delete a node that is a child of a node that is also deleted.
    # Since deleteing a node will also detach its children from the tree, there is no need to delete all
    # nodes in the subtree.
    # This will also help with conflict resolution, as further down we detect if a delete operation deletes a
    # node that is an ancestor of a node that is required by another operation, e.g. an update. By only deleting
    # subtree root nodes, we avoid the situation where the conflict prevents delete operations that lie on the
    # path between the subtree root and the node required by the conflicting operation, with all sibling nodes being
    # deleted. This way, the subtree is either deleted or it stays.
    diffs_ab = _remove_redundant_delete_diffs(diffs_ab, merge_id_to_node)
    diffs_ac = _remove_redundant_delete_diffs(diffs_ac, merge_id_to_node)

    # Detect node-node conflicts
    merge3_conflicts = []
    for ac_op in diffs_ac:
        for ab_op in diffs_ab:
            conflict = ab_op.detect_conflict_with(ac_op)
            if conflict is not None:
                merge3_conflicts.append(conflict)

    # Create combined diff list
    merge3_diffs = diffs_ab + diffs_ac

    # Split into delete, update, insert and move operations and join so that they are in that order
    merge3_delete_diffs = []
    merge3_update_diffs = []
    merge3_insert_diffs = []
    merge3_move_diffs = []
    for op in merge3_diffs:
        if isinstance(op, GumtreeDiffDelete):
            merge3_delete_diffs.append(op)
        elif isinstance(op, GumtreeDiffUpdate):
            merge3_update_diffs.append(op)
        elif isinstance(op, GumtreeDiffInsert):
            merge3_insert_diffs.append(op)
        elif isinstance(op, GumtreeDiffMove):
            merge3_move_diffs.append(op)
    merge3_diffs = merge3_delete_diffs + merge3_update_diffs + merge3_insert_diffs + merge3_move_diffs

    # The conflict detection approach used up until now has one major weakness that we now address.
    # When a subtree S is deleted and a conflict is detected between the deletion of a node N further down the subtree
    # and another operation that requires that N should still exist - e.g. an update - the approach used up until
    # now will detect the conflict between the deletion of N and the update of N, while the deletion of ancestors
    # of N will not be reported as conflicts. As a consequence, the tree that results from performing all operations
    # that do not conflict will not contain N as N will be detached.
    # We address this by asking all operations to provide the IDs of nodes that should exist in the final tree
    # for them not to conflict. We then mark conflicts for all delete operations that affect nodes that are ancestors
    # of N.

    # Note, that if a required node N is a descendant of a node M that is moved and the moved node M is a descendant
    # of a deleted node D, then this can be okay, as the move operation moves the subtree containing N out of the
    # region that is deleted.
    # Take node of all nodes that are moved:
    moved_nodes = set()
    for op in merge3_move_diffs:
        moved_id = op.get_moved_node_id()
        if moved_id is not None:
            moved_nodes.add(moved_id)

    # Now, generate a map that maps any ancestor of a required node to a list of operations that require it
    required_ancestors = {}
    for op in merge3_diffs:
        req_node_id = op.required_target_node_id()
        if req_node_id is not None:
            # Walk the tree from the parent of the required node to the root
            node_id = merge_id_to_node[req_node_id].parent_merge_id
            while node_id is not None:
                # If we encounter a moved node, no need to continue
                if node_id in moved_nodes:
                    break

                # Get the ops that require the existence of the node identified by `node_id` and add `op`
                requiring_ops = required_ancestors.setdefault(node_id, list())
                requiring_ops.append(op)

                # Go to parent
                node_id = merge_id_to_node[node_id].parent_merge_id

    # Check all delete operations against the required node lists and report conflicts as necessary
    for op in merge3_delete_diffs:
        deleted_id = op.get_deleted_node_id()
        requiring_ops = required_ancestors.get(deleted_id)
        if requiring_ops is not None:
            for req_op in requiring_ops:
                merge3_conflicts.append(GumtreeMerge3ConflictDeleteAncestry(op, req_op))

    # Create destination tree by cloning the base version tree
    merged_merge_id_to_node = {}
    tree_merged = tree_base.root.clone_subtree(merged_merge_id_to_node)
    for key, value in merge_id_to_node.items():
        if key not in merged_merge_id_to_node:
            merged_merge_id_to_node[key] = value.copy()

    # Apply diffs that are not involved in conflicts
    for op in merge3_diffs:
        if len(op.conflicts) == 0:
            op.apply(merged_merge_id_to_node)

    return tree_merged, merge3_diffs, merge3_conflicts
