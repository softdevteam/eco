

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

