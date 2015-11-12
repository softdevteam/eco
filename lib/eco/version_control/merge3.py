import difflib

from version_control.diff3_driver import diff3


def merge3_with_mapping(base, derived_local, derived_main, automerge_two_way_conflicts=False):
    """
    Performs a three-way merge on the three sequences; the base sequence `base` or parent sequence and two
    sequences derived from it; a local derived version and a main derived version. The changes from `base` to
    `derived_main` are applied to `derived_local` to generate the final merged result.
    This functions returns the resulting merged sequence along with an index mapping that is used to
    map indices relative to the content in `derived_local` to become relative to the merged content.
    The mapping takes the form of a list of integers of length `len(derived_local)` where the integer `j` at
    position `i` in the mapping states that the item at position `i` in `derived_local` can be found at position
    `j` in the merged list. If `j` is `None`, it indicates that the item is not present in the merged list.

    :param base: [str] the base version
    :param derived_local: [str] local derived version
    :param derived_main: [str] main-line derived version
    :param automerge_two_way_conflicts: the diff3 tool reports situations where elements from `base` are changed
    in both `derived_local` and `derived_main` to the same thing as a conflict. If `automerge_two_way_conflicts`
    is True, then these conflicts will be resolved automatically.
    :return: `(merged, index_mapping)`, where `merged` is the merged sequence, with possible conflicts and
    `index_mapping` is the index mapping explained above. Conflicting regions are represented as
    `diff3_driver.Diff3ConflictRegion` instances.
    """
    # Perform 3-way merge
    dm = diff3(base, derived_local, derived_main, automerge_two_way_conflicts=automerge_two_way_conflicts)

    # Use difflib to compute the differences applied to `derived_local` to get it into the merged state
    sm = difflib.SequenceMatcher(a=derived_local, b=dm)

    # Initialse the index mapping to identity
    index_mapping = list(range(len(derived_local)))

    # Modify index_mapping using opcodes
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for i in xrange(i1, i2):
                index_mapping[i] = j1 + i - i1
        elif tag == 'delete':
            for i in xrange(i1, i2):
                index_mapping[i] = None
        elif tag == 'insert':
            pass
        elif tag == 'replace':
            for i in xrange(i1, i2):
                index_mapping[i] = None
        else:
            raise ValueError('Unrecognised tag \'{0}\' in opcode list acquired from difflib'.format(tag))

    return dm, index_mapping
