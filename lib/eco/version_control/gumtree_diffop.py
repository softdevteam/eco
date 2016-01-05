from gumtree_tree import GumtreeNode
import gumtree_conflict


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
            return gumtree_conflict.GumtreeMerge3ConflictDeleteUpdate(diff, self)
        wrapped_val = diff.get_updated_node_value_in_tuple(self.node_id)
        if wrapped_val is not None:
            if wrapped_val[0] != self.value:
                # Update-update conflict
                return gumtree_conflict.GumtreeMerge3ConflictUpdateUpdate(diff, self)
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
            return gumtree_conflict.GumtreeMerge3ConflictDeleteDestination(diff, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if diff.moves_node(self.predecessor_id) or \
                diff.moves_node(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictMoveDestination(diff, self)
        if isinstance(diff, GumtreeDiffInsert) and \
                self.node_id == diff.node_id and \
                self.parent_id == diff.parent_id and \
                self.predecessor_id == diff.predecessor_id and \
                self.successor_id == diff.successor_id and \
                self.value != diff.value:
            return gumtree_conflict.GumtreeMerge3ConflictInsertInsert(diff, self)
        if self.successor_id is not None and diff.inserts_node_before(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
        if self.predecessor_id is not None and diff.inserts_node_after(self.predecessor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
        return None

    def apply(self, merge_id_to_node):
        parent_node = merge_id_to_node[self.parent_id]
        node_to_insert = merge_id_to_node[self.node_id]
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting new node {0}'.format(self.node_id))
        if isinstance(index, tuple):
            raise RuntimeError('Could not get unique insertion index for inserting new node {0}; got {1}'.format(self.node_id, index))
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
            return gumtree_conflict.GumtreeMerge3ConflictDeleteMove(diff, self)
        if diff.deletes_node(self.parent_id) or \
                diff.deletes_node(self.predecessor_id) or \
                diff.deletes_node(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDeleteDestination(diff, self)
        # Don't worry if the parent node has been moved, as all children will just move with it.
        # Its only a conflict if sibling nodes get moved as that prevents us from determining where in
        # the child list this node should go
        if diff.moves_node(self.predecessor_id) or \
                diff.moves_node(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictMoveDestination(diff, self)
        if isinstance(diff, GumtreeDiffMove) and \
                self.node_id == diff.node_id and \
                (self.parent_id != diff.parent_id or \
                self.predecessor_id != diff.predecessor_id or \
                self.successor_id != diff.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictMoveMove(diff, self)
        if self.successor_id is not None and diff.inserts_node_before(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
        if self.predecessor_id is not None and diff.inserts_node_after(self.predecessor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
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

