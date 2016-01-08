import collections, difflib, bisect
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, IndentationTerminal, Terminal

from treemanager import TreeManager
from jsonmanager import JsonManager

from . import gumtree_filter, gumtree_diff3


def merge3_tree_managers(base_tm, derived_1_tm, derived_2_tm):
    exporter = gumtree_filter.GumtreeExporter([base_tm, derived_1_tm, derived_2_tm], compact=True)

    base_gt = exporter.export_gumtree(base_tm)
    derived_1_gt = exporter.export_gumtree(derived_1_tm)
    derived_2_gt = exporter.export_gumtree(derived_2_tm)

    merged_gt, diffs, conflicts = gumtree_diff3.gumtree_diff3(base_gt, derived_1_gt, derived_2_gt)

    if len(conflicts) > 0:
        print 'WARNING: {0} conflicts detected; conflicting diffs will be ignored'.format(len(conflicts))

    root_merged, merged_language_boxes = gumtree_filter.import_gumtree(merged_gt)

    merged_tm = TreeManager()
    merged_tm.load_file(merged_language_boxes)

    # for lb in merged_language_boxes:
    #     lb_root = lb[0]
    #     merged_tm.relex(lb_root)
    #
    # for lb in merged_language_boxes:
    #     lb_root = lb[0]
    #     merged_tm.reparse(lb_root)
    merged_tm.full_reparse()


    merged_tm.changed = True

    return merged_tm



def load_tm(filename):
    manager = JsonManager()
    language_boxes = manager.load(filename)

    tm = TreeManager()
    tm.load_file(language_boxes)

    return tm
