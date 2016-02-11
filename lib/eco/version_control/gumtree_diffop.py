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

    def get_deleted_node_ids(self):
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

    def get_short_description(self):
        """
        Get a short textual description of this diff.
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
    def _find_predecessor(parent, index_in_parent, ignore_merge_ids):
        """
        Get the merge ID of the node that is the predecessor/left sibling to child `index_in_parent` of `parent`.
        `ignore_merge_id` is an optional set of merge IDs of nodes that should be passed over.

        :param parent: the parent node; `GumtreeNode` instance
        :param index_in_parent: the index of the child in `parent`
        :param ignore_merge_ids: optional set of merge IDs of nodes to skip over when searching backwards from `index_in_parent`.
        :return: the merge ID of the predecessor or `None` if one could not be found.
        """
        if len(parent) == 0 or index_in_parent == 0:
            return None
        else:
            i = index_in_parent - 1
            pred_node = parent[i]
            while pred_node.merge_id in ignore_merge_ids:
                i -= 1
                if i < 0:
                    return None
                pred_node = parent[i]
            return pred_node.merge_id

    @staticmethod
    def _find_successor(parent, index_in_parent, ignore_merge_ids):
        """
        Get the merge ID of the node that is the successor/right sibling to child `index_in_parent` of `parent`.
        `ignore_merge_id` is an optional set of merge IDs of nodes that should be passed over.

        :param parent: the parent node; `GumtreeNode` instance
        :param index_in_parent: the index of the child in `parent`
        :param ignore_merge_ids: optional set of merge ID of nodes to skip over when searching forwards from `index_in_parent`.
        :return: the merge ID of the successor or `None` if one could not be found.
        """
        if len(parent) == 0 or index_in_parent == len(parent):
            return None
        else:
            i = index_in_parent
            succ_node = parent[i]
            while succ_node.merge_id in ignore_merge_ids:
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
    def __init__(self, source, nodes):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node to be deleted, either as a `GumtreeNode` instance or as an integer node merge ID.
        """
        super(GumtreeDiffDelete, self).__init__(source)
        assert isinstance(nodes, list)
        self.__node_ids = [self._get_node_id(node) for node in nodes]


    @property
    def node_ids(self):
        return self.__node_ids

    def deletes_node(self, node_merge_id):
        return node_merge_id in self.__node_ids

    def get_deleted_node_ids(self):
        return self.__node_ids

    def _detect_one_way_conflict_with(self, diff):
        return None

    def apply(self, merge_id_to_node):
        dst_nodes = [merge_id_to_node[node_id] for node_id in self.__node_ids]
        parent = dst_nodes[0].parent
        for dst_node in dst_nodes:
            parent.remove_child(dst_node)


    def append_node(self, node):
        self.__node_ids.append(self._get_node_id(node))


    def get_description(self, node_id_to_node):
        return 'delete({0})'.format([node_id_to_node[node_id].id_label_str for node_id in self.__node_ids])

    def get_short_description(self):
        return 'delete({0} source {1})'.format(self.__node_ids, self.source)


    def __eq__(self, other):
        if isinstance(other, GumtreeDiffDelete):
            return self.__node_ids == other.__node_ids
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffDelete, tuple(self.__node_ids)))

    def __str__(self):
        return 'delete({0}; {1})'.format(self.source, self.__node_ids)

    def __repr__(self):
        return 'delete({0}; {1})'.format(self.source, self.__node_ids)


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
        self.__node_id = self._get_node_id(node)

    @property
    def node_ids(self):
        return [self.__node_id]

    def get_updated_node_value_in_tuple(self, node_id):
        if node_id == self.__node_id:
            return (self.value,)
        else:
            return None

    def _detect_one_way_conflict_with(self, diff):
        if diff.deletes_node(self.__node_id):
            # Update-delete conflict
            return gumtree_conflict.GumtreeMerge3ConflictDeleteUpdate(diff, self)
        wrapped_val = diff.get_updated_node_value_in_tuple(self.__node_id)
        if wrapped_val is not None:
            if wrapped_val[0] != self.value:
                # Update-update conflict
                return gumtree_conflict.GumtreeMerge3ConflictUpdateUpdate(diff, self)
        return None

    def apply(self, merge_id_to_node):
        dst_node = merge_id_to_node[self.__node_id]
        dst_node.value = self.value

    def required_target_node_id(self):
        return self.__node_id

    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.__node_id]
        return 'update({0}, value={1})'.format(node.id_label_str, self.value)

    def get_short_description(self):
        return 'update({0} source {1})'.format(self.__node_id, self.source)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffUpdate):
            return self.__node_id == other.__node_id and self.value == other.value
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffUpdate, self.__node_id, self.value))

    def __str__(self):
        return 'update({0}; {1}, value={2})'.format(self.source, self.__node_id, self.value)

    def __repr__(self):
        return 'update({0}; {1}, value={2})'.format(self.source, self.__node_id, self.value)


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
    def __init__(self, source, nodes, parent, index_in_parent):
        """
        Constructor

        :param source: an identifier used to identify where this diff came from, e.g. in 3-way merge the
        identifiers could be `'AB'` and `'AC'`.
        :param node: the node from the destination tree that is to be inserted
        :param parent: the node from the soruce tree that is to be the parent of the inserted node
        :param index_in_parent: the index at which the new node is to be inserted
        """
        super(GumtreeDiffInsert, self).__init__(source)
        assert isinstance(nodes, list)
        self.__node_ids = [self._get_node_id(node) for node in nodes]
        self.parent_id = self._get_node_id(parent)
        self.predecessor_id = self._find_predecessor(parent, index_in_parent, set(self.__node_ids))
        self.successor_id = self._find_successor(parent, index_in_parent + len(nodes) - 1, set(self.__node_ids))
        self.__values = [node.value for node in nodes]

    @property
    def node_ids(self):
        return self.__node_ids

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
                self.__node_ids == diff.__node_ids and \
                self.parent_id == diff.parent_id and \
                self.predecessor_id == diff.predecessor_id and \
                self.successor_id == diff.successor_id and \
                self.__values != diff.__values:
            return gumtree_conflict.GumtreeMerge3ConflictInsertInsert(diff, self)
        if self.successor_id is not None and diff.inserts_node_before(self.successor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
        if self.predecessor_id is not None and diff.inserts_node_after(self.predecessor_id):
            return gumtree_conflict.GumtreeMerge3ConflictDestinationDestination(diff, self)
        return None

    def apply(self, merge_id_to_node):
        parent_node = merge_id_to_node[self.parent_id]
        nodes_to_insert = [merge_id_to_node[node_id] for node_id in self.__node_ids]
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting new nodes {0}'.format(self.__node_ids))
        if isinstance(index, tuple):
            if index[0] > index[1]:
                error_msg = 'Could not get unique position for inserting nodes {0} under parent {1} between {2} and {3};' \
                            'children of parent={4}, source={5}, got indices {6}'.format(
                    self.__node_ids, self.parent_id, self.predecessor_id, self.successor_id,
                    [n.merge_id for n in parent_node.children], self.source, index)
                raise RuntimeError(error_msg)
            else:
                # the first index is smaller than second; this indicates that in the destination tree the
                # predecessor and successor were immediate neighbours but they are separated in the tree
                # in its current state, and that future operations are likely to remove the nodex between them
                index = index[0]
        parent_node.insert_children(index, nodes_to_insert)

    def required_target_node_id(self):
        return self.parent_id


    def append_insert_op(self, op):
        assert isinstance(op, GumtreeDiffInsert)
        self.__node_ids.extend(op.__node_ids)
        self.successor_id = op.successor_id
        self.__values.extend(op.__values)


    def get_description(self, node_id_to_node):
        node_id_label_strs = [node_id_to_node[node_id].id_label_str for node_id in self.__node_ids]
        parent_node = node_id_to_node[self.parent_id]
        insertion_index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        return 'insert(src {0}, parent {1}, at {2})'.format(node_id_label_strs,
                                                            parent_node.id_label_str, insertion_index)

    def get_short_description(self):
        return 'insert({0} under {1} between {2} and {3} source {4})'.format(self.__node_ids, self.parent_id,
                                                                             self.predecessor_id, self.successor_id, self.source)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffInsert):
            return self.parent_id == other.parent_id and self.predecessor_id == other.predecessor_id and \
                   self.successor_id == other.successor_id and self.__node_ids == other.__node_ids and \
                   self.__values == other.__values
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffInsert, self.parent_id, self.predecessor_id, self.successor_id,
                     tuple(self.__node_ids), tuple(self.__values)))

    def __str__(self):
        return 'insert({0}; src {1}, parent {2}, between {3} and {4})'.format(self.source, self.__node_ids, self.parent_id,
                                                                              self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'insert({0}; src {1}, parent {2}, between {3} and {4})'.format(self.source, self.__node_ids, self.parent_id,
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
        self.__node_id = self._get_node_id(node)
        self.parent_id = self._get_node_id(parent)
        self.predecessor_id = self._find_predecessor(parent, index_in_parent, {self.__node_id})
        self.successor_id = self._find_successor(parent, index_in_parent, {self.__node_id})

    @property
    def node_ids(self):
        return [self.__node_id]

    def moves_node(self, node_id):
        return node_id == self.__node_id

    def get_dest_context(self):
        return self.parent_id, self.predecessor_id, self.successor_id

    def inserts_node_before(self, node_id):
        return node_id == self.successor_id

    def inserts_node_after(self, node_id):
        return node_id == self.predecessor_id

    def _detect_one_way_conflict_with(self, diff):
        if diff.deletes_node(self.__node_id):
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
                self.__node_id == diff.__node_id and \
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
        return self.__node_id

    def apply(self, merge_id_to_node):
        parent_node = merge_id_to_node[self.parent_id]
        node_to_move = merge_id_to_node[self.__node_id]
        node_to_move.detach_from_parent()
        index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        if index is None:
            raise RuntimeError('Could not get insertion index for inserting moved node {0}'.format(self.__node_id))
        if isinstance(index, tuple):
            error_msg = 'Could not get unique position for moving node {0} to parent {1} between {2} and {3};' \
                        'children of parent={4}, source={5}, got indices {6}'.format(
                self.__node_id, self.parent_id, self.predecessor_id, self.successor_id,
                [n.merge_id for n in parent_node.children], self.source, index)
            raise RuntimeError(error_msg)
        parent_node.insert_child(index, node_to_move)

    def required_target_node_id(self):
        return self.parent_id

    def get_description(self, node_id_to_node):
        node = node_id_to_node[self.__node_id]
        parent_node = node_id_to_node[self.parent_id]
        insertion_index = parent_node.insertion_index(self.predecessor_id, self.successor_id)
        return 'move(src {0}, to parent {1}, at {2})'.format(node.id_label_str,
                                                            parent_node.id_label_str, insertion_index)

    def get_short_description(self):
        return 'move({0} under {1} between {2} and {3} source {4})'.format(self.__node_id, self.parent_id,
                                                                           self.predecessor_id, self.successor_id, self.source)

    def __eq__(self, other):
        if isinstance(other, GumtreeDiffMove):
            return self.parent_id == other.parent_id and self.__node_id == other.__node_id and \
                   self.predecessor_id == other.predecessor_id and self.successor_id == other.successor_id
        else:
            return False

    def __hash__(self):
        return hash((GumtreeDiffMove, self.parent_id, self.predecessor_id, self.successor_id, self.__node_id))

    def __str__(self):
        return 'move({0}; src {1}, to parent {2}, between {3} and {4})'.format(self.source, self.__node_id, self.parent_id,
                                                                               self.predecessor_id, self.successor_id)

    def __repr__(self):
        return 'move({0}; src {1}, to parent {2}, between {3} and {4})'.format(self.source, self.__node_id, self.parent_id,
                                                                               self.predecessor_id, self.successor_id)

