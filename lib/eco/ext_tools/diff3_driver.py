import subprocess, tempfile, os, ast


def extract_conflict_lines_from_iter(it):
    lines = []
    line = next(it)
    while not line.startswith('<<<<<<<') and not line.startswith('|||||||') and not line.startswith('=======') and not line.startswith('>>>>>>>'):
        lines.append(line)
        line = next(it)
    return lines, line


def diff3(base, derived1, derived2):
    """
    Invoke the external `diff3` tool to merge three sequences; the base sequence `base` and two derived sequences
    `derived1` and `derived2`.
    :param base: [str] the base version
    :param derived1: [str] derived version
    :param derived2: [str] derived version
    :return:
    """
    for x in base:
        if not isinstance(x, (str, unicode)):
            raise TypeError('base should be a list of strings; should not contain a {0}'.format(type(x)))
    for x in derived1:
        if not isinstance(x, (str, unicode)):
            raise TypeError('derived1 should be a list of strings; should not contain a {0}'.format(type(x)))
    for x in derived2:
        if not isinstance(x, (str, unicode)):
            raise TypeError('derived2 should be a list of strings; should not contain a {0}'.format(type(x)))

    base_fd, base_path = tempfile.mkstemp()
    base_f = os.fdopen(base_fd, 'w')

    d1_fd, d1_path = tempfile.mkstemp()
    d1_f = os.fdopen(d1_fd, 'w')

    d2_fd, d2_path = tempfile.mkstemp()
    d2_f = os.fdopen(d2_fd, 'w')

    base_f.write('\n'.join([repr(x) for x in base]) + '\n')
    d1_f.write('\n'.join([repr(x) for x in derived1]) + '\n')
    d2_f.write('\n'.join([repr(x) for x in derived2]) + '\n')

    base_f.close()
    d1_f.close()
    d2_f.close()

    proc = subprocess.Popen(['diff3', '-m', d1_path, base_path, d2_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    os.remove(base_path)
    os.remove(d1_path)
    os.remove(d2_path)

    out_lines = out.split('\n')

    merged = []

    file_path_to_name = {
        base_path: 'base',
        d1_path: 'derived1',
        d2_path: 'derived2',
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
