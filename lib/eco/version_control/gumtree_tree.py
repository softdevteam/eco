
class GumtreeNodeClass (object):
    """
    Helper class for constructing GumtreeNode instances. E.g. declare a node type:

    >>> MyType = GumtreeNodeClass(42, 'MyType')

    Then create nodes:

    >>> x = MyType(0, 11, 'hello world', [])
    >>> y = MyType(11, 7, 'the end', [])
    >>> xy = MyType(0, 18, '', [x, y])
    """
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
        elif predecessor_merge_id is None:
            # Inserting at start
            return 0
        elif successor_merge_id is None:
            # Inserting at end
            return len(self.children)
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

    def _populate_merge_id_to_node(self, merge_id_to_node):
        """
        Populate a dictionary mapping merge ID to node

        :param merge_id_to_node: a dictionary mapping node merge ID to node that is to be populated
        """
        for child in self.children:
            child._populate_merge_id_to_node(merge_id_to_node)

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

    def merge_id_string(self, indent=0):
        INDENT_SIZE = 3
        indent_str = ('|' + ' ' * (INDENT_SIZE-1))*indent
        return '\n'.join(['{0}{1}'.format(indent_str, self.merge_id)] + [x.merge_id_string(indent+1) for x in self.children])

    def pretty_string(self, indent=0):
        INDENT_SIZE = 3
        indent_str = ('|' + ' ' * (INDENT_SIZE-1))*indent
        return '\n'.join(['{0}{1}'.format(indent_str, self.id_label_str)] + [x.pretty_string(indent+1) for x in self.children])



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


    def clone_tree(self, merge_id_to_node):
        """
        Create a clone of the document.
        :return: the clone
        """
        return GumtreeDocument(self.root.clone_subtree(merge_id_to_node))

    def build_merge_id_to_node_table(self):
        """
        Build a merge ID to node table for all nodes in this tree
        :return: a dictionary mapping merge ID to node
        """
        merge_id_to_node = {}
        self.root._populate_merge_id_to_node(merge_id_to_node)
        return merge_id_to_node

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


class GumtreeNodeMergeIDTable (object):
    def __init__(self):
        self.__id_counter = 0
        self.__merge_id_to_node = {}


    def register_node(self, node):
        merge_id = self.__id_counter
        self.__id_counter += 1
        node.merge_id = merge_id
        self.__merge_id_to_node[merge_id] = node
        return merge_id


    def __getitem__(self, merge_id):
        return self.__merge_id_to_node[merge_id]

    def merge_ids_and_nodes(self):
        return self.__merge_id_to_node.items()



# Gumtree's JSON tree handler handles trees of the form:
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
