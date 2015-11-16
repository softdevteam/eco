import difflib

from version_control.diff3_driver import diff3


def merge3_with_change_regions(base, derived_local, derived_main, automerge_two_way_conflicts=False):
    """
    Performs a three-way merge on the three sequences; the base sequence `base` or parent sequence and two
    sequences derived from it; a local derived version and a main derived version. The changes from `base` to
    `derived_main` are applied to `derived_local` to generate the final merged result.
    This function returns the resulting merged sequence along with a list of regions from `derived_local`
    that were altered by the merge. The modified regions take the form of 4-tuples of the form
    `(i1, i2, j1, j2)`, where `i1:i2` is the modified range in `derived_local` and `j1:j2` is the equivalent
     modified range in the merged list.

    :param base: [str] the base version
    :param derived_local: [str] local derived version
    :param derived_main: [str] main-line derived version
    :param automerge_two_way_conflicts: the diff3 tool reports situations where elements from `base` are changed
    in both `derived_local` and `derived_main` to the same thing as a conflict. If `automerge_two_way_conflicts`
    is True, then these conflicts will be resolved automatically.
    :return: `(merged, change_regions)`, where `merged` is the merged sequence, with possible
    conflicts and `change_regions` lists the changed regions as explained above. Conflicting regions in `merged` are
    represented as `diff3_driver.Diff3ConflictRegion` instances.
    """
    # Perform 3-way merge
    dm = diff3(base, derived_local, derived_main, automerge_two_way_conflicts=automerge_two_way_conflicts)

    # Use difflib to compute the differences applied to `derived_local` to get it into the merged state
    sm = difflib.SequenceMatcher(a=derived_local, b=dm)

    # Initialse the index mapping to identity
    change_regions = []

    # Modify index_mapping using opcodes
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            # No change
            pass
        elif tag == 'delete':
            change_regions.append((tag, i1, i2, j1, j2))
        elif tag == 'insert':
            change_regions.append((tag, i1, i2, j1, j2))
        elif tag == 'replace':
            change_regions.append((tag, i1, i2, j1, j2))
        else:
            raise ValueError('Unrecognised tag \'{0}\' in opcode list acquired from difflib'.format(tag))

    return dm, change_regions
