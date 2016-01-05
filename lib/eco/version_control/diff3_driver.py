import subprocess, tempfile, os, ast


class Diff3ConflictRegion (object):
    """
    `Diff3ConflictRegion` represents a merge conflict. A `Diff3ConflictRegion` instance has 3 attributes; `base`,
    `derived_local` and `derived_main`. Each one will either contain None, or a (possibly empty) list that contains
    the content of the conflicting region from that version of the document; e.g. `base` will contain the content
    from the conflicting region in the base document.
    """
    def __init__(self, base=None, derived_local=None, derived_main=None):
        if base is not None and not isinstance(base, list):
            raise TypeError('base should either be None or a list')
        if derived_local is not None and not isinstance(derived_local, list):
            raise TypeError('derived_local should either be None or a list')
        if derived_main is not None and not isinstance(derived_main, list):
            raise TypeError('derived_main should either be None or a list')
        self.base = base
        self.derived_local = derived_local
        self.derived_main = derived_main

    @property
    def is_three_way(self):
        return self.base is not None and self.derived_local is not None and self.derived_main is not None

    def __eq__(self, other):
        if isinstance(other, Diff3ConflictRegion):
            return self.base == other.base and self.derived_local == other.derived_local and \
                   self.derived_main == other.derived_main
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, Diff3ConflictRegion):
            return self.base != other.base or self.derived_local != other.derived_local or \
                   self.derived_main != other.derived_main
        else:
            return True

    def __hash__(self):
        return hash((type(self),
                     tuple(self.base) if self.base is not None else None,
                     tuple(self.derived_local) if self.derived_local is not None else None,
                     tuple(self.derived_main) if self.derived_main is not None else None))



def _back_to_string(x):
    return ast.literal_eval(x)

def diff3(base, derived_local, derived_main, automerge_two_way_conflicts=False):
    """
    Invoke the external `diff3` tool to merge three sequences; the base sequence `base` or parent sequence and two
    sequences derived from it; a local derived version and a main derived version. The changes from `base` to
    `derived_main` are applied to `derived_local` to generate the final merged result.
    :param base: [str] the base version
    :param derived_local: [str] local derived version
    :param derived_main: [str] main-line derived version
    :param automerge_two_way_conflicts: the diff3 tool reports situations where elements from `base` are changed
    in both `derived_local` and `derived_main` to the same thing as a conflict. If `automerge_two_way_conflicts`
    is True, then these conflicts will be resolved automatically.
    :return: the merged sequence, with possible conflicts. Conflicting regions are represented as `Diff3ConflictRegion`
    instances.
    """
    for x in base:
        if not isinstance(x, (str, unicode)):
            raise TypeError('base should be a list of strings; should not contain a {0}'.format(type(x)))
    for x in derived_local:
        if not isinstance(x, (str, unicode)):
            raise TypeError('derived_local should be a list of strings; should not contain a {0}'.format(type(x)))
    for x in derived_main:
        if not isinstance(x, (str, unicode)):
            raise TypeError('derived2 should be a list of strings; should not contain a {0}'.format(type(x)))

    base_fd, base_path = tempfile.mkstemp()
    dlocal_fd, dlocal_path = tempfile.mkstemp()
    dmain_fd, dmain_path = tempfile.mkstemp()

    try:
        base_f = os.fdopen(base_fd, 'w')
        dlocal_f = os.fdopen(dlocal_fd, 'w')
        dmain_f = os.fdopen(dmain_fd, 'w')

        base_f.write('\n'.join([repr(x) for x in base]) + '\n')
        dlocal_f.write('\n'.join([repr(x) for x in derived_local]) + '\n')
        dmain_f.write('\n'.join([repr(x) for x in derived_main]) + '\n')

        base_f.close()
        dlocal_f.close()
        dmain_f.close()

        proc = subprocess.Popen(['diff3', '-m', dlocal_path, base_path, dmain_path], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()

    finally:
        os.remove(base_path)
        os.remove(dlocal_path)
        os.remove(dmain_path)

    out_lines = out.split('\n')

    merged = []

    file_path_to_name = {
        base_path: 'base',
        dlocal_path: 'derived_local',
        dmain_path: 'derived_main',
    }

    i = 0
    while i < len(out_lines):
        line = out_lines[i]
        if line == '':
            pass
        elif line.startswith('<<<'):
            # handle the conflict
            conflict = []
            conflict_part_start = i + 1
            conflict_file = file_path_to_name[line[8:]]

            while not line.startswith('>>>'):
                if out_lines[i].startswith('|||'):
                    conflict_part_end = i
                    conflict_content = out_lines[conflict_part_start:conflict_part_end]
                    conflict.append((conflict_file, conflict_content))

                    conflict_part_start = i + 1
                    conflict_file = file_path_to_name[line[8:]]
                elif out_lines[i].startswith('==='):
                    conflict_part_end = i
                    conflict_content = out_lines[conflict_part_start:conflict_part_end]
                    conflict.append((conflict_file, conflict_content))

                    conflict_part_start = i + 1
                    conflict_file = None

                i += 1
                line = out_lines[i]

            conflict_part_end = i
            conflict_file = file_path_to_name[line[8:]]
            conflict_content = out_lines[conflict_part_start:conflict_part_end]
            conflict.append((conflict_file, conflict_content))

            conflict = Diff3ConflictRegion(**{conflict_file: [_back_to_string(x) for x in conflict_content]
                                              for conflict_file, conflict_content in conflict})

            if automerge_two_way_conflicts and conflict.derived_local is None:
                # Collapse this conflict
                merged.extend(conflict.derived_main)
            else:
                merged.append(conflict)
        else:
            merged.append(_back_to_string(line))
        i += 1

    return merged
