import json, subprocess, tempfile, os
from gumtree_tree import GumtreeNode, GumtreeDocument
from gumtree_diffop import GumtreeDiffDelete, GumtreeDiffUpdate, GumtreeDiffInsert, GumtreeDiffMove



if 'GUMTREE_PATH' in os.environ:
    GUMTREE_PATH = os.environ['GUMTREE_PATH']
else:

    GUMTREE_PATH = os.path.expanduser(os.path.join(
        '~', 'kcl', 'bin_gumtree', 'dist-2.1.0-SNAPSHOT', 'bin', 'dist'))



def gumtree_diff_raw(tree_a, tree_b):
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
    gumtree_dir = os.path.split(GUMTREE_PATH)[0]

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

        proc = subprocess.Popen([GUMTREE_PATH, 'jsondiff', a_path, b_path],
                                cwd=gumtree_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def convert_js_actions_to_diffs(tree_base, tree_derived, source, actions_js):
    """
    Convert a list of actions in Javascript form from the Gumtree tool, returned by `_raw_diff` into
    a list of `GumtreeDiff` instances.
    :param tree_base: tree, base version
    :param tree_derived: tree, derived version
    :param source: the value for the source field in all diffs generated
    :param actions_js: action list, JS form, see `_raw_diff` for explanation
    :return: list of `GumtreeDiff` instances
    """
    delete_by_parent_and_index = {}
    inserts_by_parent_and_index = {}

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
            # Get the merge ID of the parent node and the index of the child being deleted
            parent_id = id(node.parent)
            index_in_parent = node.parent.children.index(node)
            cur_key = parent_id, index_in_parent

            # See if there is a delete operation that deletes `node`'s previous sibling
            prev_key = parent_id, index_in_parent - 1
            op = delete_by_parent_and_index.get(prev_key)
            if op is not None:
                # Add `node` to the delete operation
                assert isinstance(op, GumtreeDiffDelete)
                op.append_node(node)
                delete_by_parent_and_index[cur_key] = op

            # See if there is a delete operation that deletes `node`'s next sibling
            next_key = parent_id, index_in_parent + 1
            next_op = delete_by_parent_and_index.get(next_key)
            if next_op is not None:
                raise NotImplementedError('Delete operations out of order')

            if op is None:
                op = GumtreeDiffDelete(source, [node])
                delete_by_parent_and_index[cur_key] = op
                diffs.append(op)
        elif action == 'insert':
            # Insert actions reference the node from tree B, that is being inserted as a child of
            # a parent node - also from tree B - at a specified index
            node = tree_derived.gumtree_index_to_node[action_js['tree']]
            parent = tree_derived.gumtree_index_to_node[action_js['parent']]

            # Get the merge ID of the parent node and the index where the child node is being inserted
            parent_id = id(parent)
            index_in_parent = action_js['at']
            cur_key = parent_id, index_in_parent

            # See if there is a delete operation that deletes `node`'s previous sibling
            prev_key = parent_id, index_in_parent - 1
            op = inserts_by_parent_and_index.get(prev_key)
            if op is not None:
                # Add `node` to the insert operation
                assert isinstance(op, GumtreeDiffInsert)
                temp_op = GumtreeDiffInsert(source, [node], parent, action_js['at'])
                op.append_insert_op(temp_op)
                inserts_by_parent_and_index[cur_key] = op

            # See if there is a delete operation that deletes `node`'s next sibling
            next_key = parent_id, index_in_parent + 1
            next_op = inserts_by_parent_and_index.get(next_key)
            if next_op is not None:
                raise NotImplementedError('Insert operations out of order')

            if op is None:
                op = GumtreeDiffInsert(source, [node], parent, action_js['at'])
                inserts_by_parent_and_index[cur_key] = op
                diffs.append(op)
        elif action == 'move':
            node = tree_base.gumtree_index_to_node[action_js['tree']]
            parent = tree_derived.gumtree_index_to_node[action_js['parent']]
            diffs.append(GumtreeDiffMove(source, node, parent, action_js['at']))

    return diffs


def gumtree_diff(tree_base, tree_derived):
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
    matches_js, actions_js = gumtree_diff_raw(tree_base, tree_derived)

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
    return convert_js_actions_to_diffs(tree_base, tree_derived, None, actions_js)

