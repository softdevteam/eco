from gumtree_tree import GumtreeNode, GumtreeDocument
from gumtree_diffop import GumtreeDiffDelete, GumtreeDiffUpdate, GumtreeDiffInsert, GumtreeDiffMove
from gumtree_conflict import GumtreeMerge3ConflictDeleteAncestry
from gumtree_driver import gumtree_diff_raw, convert_js_actions_to_diffs


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


def gumtree_diff3(tree_base, tree_derived_1, tree_derived_2):
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
    ab_matches_js, ab_actions_js = gumtree_diff_raw(tree_base, tree_derived_1)
    ac_matches_js, ac_actions_js = gumtree_diff_raw(tree_base, tree_derived_2)
    bc_matches_js, bc_actions_js = gumtree_diff_raw(tree_derived_1, tree_derived_2)

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
    diffs_ab = convert_js_actions_to_diffs(tree_base, tree_derived_1, 'ab', ab_actions_js)
    diffs_ac = convert_js_actions_to_diffs(tree_base, tree_derived_2, 'ac', ac_actions_js)

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

    doc_merged = GumtreeDocument(tree_merged)

    return doc_merged, merge3_diffs, merge3_conflicts
