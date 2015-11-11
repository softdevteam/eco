import subprocess, tempfile, os, ast


def extract_conflict_lines_from_iter(it):
    lines = []
    line = next(it)
    while not line.startswith('<<<<<<<') and not line.startswith('|||||||') and not line.startswith('=======') and not line.startswith('>>>>>>>'):
        lines.append(line)
        line = next(it)
    return lines, line


def diff3(base, derived_local, derived_main):
    """
    Invoke the external `diff3` tool to merge three sequences; the base sequence `base` or parent sequence and two
    sequences derived from it; a local derived version and a main derived version. The changes from `base` to
    `derived_local` are applied to `derived_main`.
    :param base: [str] the base version
    :param derived_local: [str] local derived version
    :param derived_main: [str] main-line derived version
    :return: the merged sequence, with possible conflicts. Conflict regions are represented as dictionaries
    `{version: sequence}` where `version` is one of `'base'`, `'derived_local'` or `'derived_main'` and `sequence` is
    a list of strings that represents the content in that version.
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
    base_f = os.fdopen(base_fd, 'w')

    dlocal_fd, dlocal_path = tempfile.mkstemp()
    dlocal_f = os.fdopen(dlocal_fd, 'w')

    dmain_fd, dmain_path = tempfile.mkstemp()
    dmain_f = os.fdopen(dmain_fd, 'w')

    base_f.write('\n'.join([repr(x) for x in base]) + '\n')
    dlocal_f.write('\n'.join([repr(x) for x in derived_local]) + '\n')
    dmain_f.write('\n'.join([repr(x) for x in derived_main]) + '\n')

    base_f.close()
    dlocal_f.close()
    dmain_f.close()

    proc = subprocess.Popen(['diff3', '-m', dlocal_path, base_path, dmain_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

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

            conflict = {conflict_file: [ast.literal_eval(x) for x in conflict_content] for conflict_file, conflict_content in conflict}
            merged.append(conflict)
        else:
            merged.append(ast.literal_eval(line))
        i += 1

    return merged
