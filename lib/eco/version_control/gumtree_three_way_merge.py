import collections, difflib, bisect
from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import Nonterminal, Terminal, MagicTerminal, IndentationTerminal
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol

from treemanager import TreeManager
from jsonmanager import JsonManager

from . import gumtree_filter, gumtree_diff3, gumtree_diffop, gumtree_driver

from lspace_ext.lspace import Pres, ApplyStyleSheet, Text, Row, Column, Flow, Colour, viewer, TextWeight, TextSlant


def diff2_tree_managers(tm_a, tm_b):
    exporter = gumtree_filter.GumtreeExporter([tm_a, tm_b], compact=True)

    gt_a = exporter.export_gumtree(tm_a)
    gt_b = exporter.export_gumtree(tm_b)

    return gumtree_driver.gumtree_diff(gt_a, gt_b)


def merge3_tree_managers(base_tm, derived_1_tm, derived_2_tm, lspace_root, visualise=False):
    exporter = gumtree_filter.GumtreeExporter([base_tm, derived_1_tm, derived_2_tm], compact=True)

    if visualise:
        base_eco_node_to_gt_node = {}
        d1_eco_node_to_gt_node = {}
        d2_eco_node_to_gt_node = {}
        merged_eco_node_to_gt_node = {}
    else:
        base_eco_node_to_gt_node = None
        d1_eco_node_to_gt_node = None
        d2_eco_node_to_gt_node = None
        merged_eco_node_to_gt_node = None

    base_gt = exporter.export_gumtree(base_tm, eco_node_to_gt_node=base_eco_node_to_gt_node)
    derived_1_gt = exporter.export_gumtree(derived_1_tm, eco_node_to_gt_node=d1_eco_node_to_gt_node)
    derived_2_gt = exporter.export_gumtree(derived_2_tm, eco_node_to_gt_node=d2_eco_node_to_gt_node)

    merged_gt, diffs, conflicts = gumtree_diff3.gumtree_diff3(base_gt, derived_1_gt, derived_2_gt)

    if len(conflicts) > 0:
        print 'WARNING: {0} conflicts detected; conflicting diffs will be ignored'.format(len(conflicts))
        print 'CONFLICTS:'
        for i, conflict in enumerate(conflicts):
            print 'conflict {0}: {1}'.format(i, conflict)

    root_merged, merged_language_boxes = gumtree_filter.import_gumtree(merged_gt,
                                                                       eco_node_to_gt_node=merged_eco_node_to_gt_node)

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

    if visualise:
        _visualise_merge3_in_lspace(base_tm, derived_1_tm, derived_2_tm, merged_tm,
                          base_eco_node_to_gt_node, d1_eco_node_to_gt_node, d2_eco_node_to_gt_node,
                          merged_eco_node_to_gt_node, diffs, conflicts, lspace_root)

    return merged_tm




def load_tm(filename):
    manager = JsonManager()
    language_boxes = manager.load(filename)

    tm = TreeManager()
    tm.load_file(language_boxes)

    return tm





class MergeVisToken (object):
    """
    Token to export to LSpace via JSON
    """
    def __init__(self, text):
        self.text = text

    def __present__(self):
        return Text(self.text)


class MergeVisStyle (object):
    def __init__(self, style_attrs):
        self.children = []
        self.style_attrs = style_attrs

    def append(self, x):
        self.children.append(x)

    def __present__(self):
        return ApplyStyleSheet(Row(self.children), **self.style_attrs)


class MergeVisLine (object):
    """
    Line to export to LSpace via JSON
    """
    def __init__(self):
        self.children = []

    def append(self, x):
        self.children.append(x)

    def __present__(self):
        return Row(self.children)


class MergeVisDoc (object):
    """
    Document to export to LSpace via JSON
    """
    def __init__(self, title):
        self.title = title
        self.children = []

    def append(self, x):
        self.children.append(x)

    def __present__(self):
        title = ApplyStyleSheet(Text(self.title), text_size=18.0, text_weight='bold', text_colour=Colour(0.0, 0.3, 0.4))
        content = Column(self.children)
        content = ApplyStyleSheet(content, text_font_family='Courier New', text_colour=Colour(0.4, 0.4, 0.4))
        return ApplyStyleSheet(Column([title, content]), column_y_spacing=20.0)


class MergeVis (object):
    def __init__(self, base, d1, d2, merged, title='3-way merge'):
        self.base = base
        self.d1 = d1
        self.d2 = d2
        self.merged = merged
        self.title = title

    def __present__(self):
        title = ApplyStyleSheet(Text(self.title), text_size=24.0, text_weight='bold', text_colour=Colour(0.4, 0.0, 0.4))
        content = Column([Row([self.base, self.merged]), Row([self.d1, self.d2])])
        content = ApplyStyleSheet(content, row_x_spacing=25.0, column_y_spacing=25.0)
        return ApplyStyleSheet(Column([title, content]), column_y_spacing=35.0)



def _join_style_stack(style_stack):
    style = {}
    for s in style_stack:
        style.update(s)
    return style


def _populate_vis_doc_from_commands(doc, commands):
    style_stack = []
    current_line = None
    current_dest = None

    for cmd, args in commands:
        if cmd == 'token':
            token_text = args[0]
            if current_line is None:
                # Start a new line and append it
                current_line = MergeVisLine()
                doc.append(current_line)
            if current_dest is None:
                if len(style_stack) == 0:
                    # No active styles; put tokens in current line
                    current_dest = current_line
                else:
                    # Build style node
                    current_dest = MergeVisStyle(_join_style_stack(style_stack))
                    current_line.children.append(current_dest)
            current_dest.append(MergeVisToken(token_text))
        elif cmd == 'push_style':
            style_attrs = args[0]
            style_stack.append(style_attrs)
            current_dest = None
        elif cmd == 'pop_style':
            style_stack.pop()
            current_dest = None
        elif cmd == 'newline':
            current_dest = None
            current_line = None



def _tree_manager_to_commands(commands, tree_manager, node_to_style_fn=None):
    root = tree_manager.get_bos().get_root()
    _eco_node_to_commands(commands, root, node_to_style_fn=node_to_style_fn)



def _eco_node_to_commands(commands, node, node_to_style_fn=None):
    style = node_to_style_fn(node) if node_to_style_fn is not None else None
    if style is not None:
        commands.append(('push_style', [style]))
    if isinstance(node.symbol, Nonterminal):
        for child_node in node.children:
            _eco_node_to_commands(commands, child_node, node_to_style_fn=node_to_style_fn)
    elif isinstance(node.symbol, MagicTerminal):
        _eco_node_to_commands(commands, node.symbol.ast, node_to_style_fn=node_to_style_fn)
    elif isinstance(node.symbol, (Terminal, FinishSymbol)):
        if isinstance(node.symbol, IndentationTerminal):
            pass
        elif isinstance(node, EOS):
            pass
        elif node.symbol.name == "\r":
            commands.append(('newline', []))
        else:
            commands.append(('token', [node.symbol.name]))
    if style is not None:
        commands.append(('pop_style', []))


def _tree_manager_to_vis_doc(doc, tree_manager, node_to_style_fn=None):
    commands = []
    _tree_manager_to_commands(commands, tree_manager, node_to_style_fn=node_to_style_fn)
    _populate_vis_doc_from_commands(doc, commands)



def _visualise_merge3_in_lspace(base_tm, derived_1_tm, derived_2_tm, merged_tm,
                      base_eco_node_to_gt_node, d1_eco_node_to_gt_node, d2_eco_node_to_gt_node,
                      merged_eco_node_to_gt_node, diffs, conflicts, lspace_root):
    deleted_nodes = {}
    updated_nodes = {}
    moved_nodes = {}
    inserted_nodes = {}
    conflict_nodes = {}

    for op in diffs:
        if isinstance(op, gumtree_diffop.GumtreeDiffDelete):
            for node_id in op.node_ids:
                deleted_nodes[node_id] = op.source
        elif isinstance(op, gumtree_diffop.GumtreeDiffUpdate):
            updated_nodes[op.__node_id] = op.source
        elif isinstance(op, gumtree_diffop.GumtreeDiffInsert):
            inserted_nodes[op.__node_id] = op.source
        elif isinstance(op, gumtree_diffop.GumtreeDiffMove):
            moved_nodes[op.__node_id] = op.source
        else:
            raise TypeError('Unknown diff type {0}'.format(type(op)))
        if len(op.conflicts) > 0:
            conflict_nodes[op.__node_id] = op.source

    def base_merge_id_to_style(eco_node_to_gt_node, eco_node, sources):
        gt_node = eco_node_to_gt_node.get(eco_node)
        if gt_node is not None:
            merge_id = gt_node.merge_id
            src = deleted_nodes.get(merge_id)
            if src in sources:
                style = {}
                if conflict_nodes.get(merge_id) in sources:
                    style.update({'text_weight': TextWeight.BOLD})
                if src == 'ab':
                    style.update({'text_colour': Colour(0.7, 0.4, 0.0)})
                elif src == 'ac':
                    style.update({'text_colour': Colour(0.7, 0.0, 0.4)})
                else:
                    raise ValueError('Deleted node op source \'{0}\' unknown'.format(src))
                if len(style) > 0:
                    return style
        return None

    def merge_id_to_style(eco_node_to_gt_node, eco_node, sources):
        gt_node = eco_node_to_gt_node.get(eco_node)
        if gt_node is not None:
            merge_id = gt_node.merge_id
            style = {}
            if conflict_nodes.get(merge_id) in sources:
                style.update({'text_weight': TextWeight.BOLD})
            if deleted_nodes.get(merge_id) in sources:
                style.update({'text_colour': Colour(0.6, 0.0, 0.6)})
            elif updated_nodes.get(merge_id) in sources:
                style.update({'text_colour': Colour(0.6, 0.6, 0.0)})
            elif inserted_nodes.get(merge_id) in sources:
                style.update({'text_colour': Colour(0.0, 0.6, 0.0)})
            elif moved_nodes.get(merge_id) in sources:
                style.update({'text_colour': Colour(0.0, 0.6, 0.6)})
            if len(style) > 0:
                return style
        return None


    base_node_to_style_fn = lambda eco_node: base_merge_id_to_style(base_eco_node_to_gt_node, eco_node, ['ab', 'ac'])
    d1_node_to_style_fn = lambda eco_node: merge_id_to_style(d1_eco_node_to_gt_node, eco_node, ['ab'])
    d2_node_to_style_fn = lambda eco_node: merge_id_to_style(d2_eco_node_to_gt_node, eco_node, ['ac'])
    merged_node_to_style_fn = lambda eco_node: merge_id_to_style(merged_eco_node_to_gt_node, eco_node, ['ab', 'ac'])

    base_doc = MergeVisDoc('Base')
    derived_1_doc = MergeVisDoc('A')
    derived_2_doc = MergeVisDoc('B')
    merged_doc = MergeVisDoc('Merged')

    _tree_manager_to_vis_doc(base_doc, base_tm, node_to_style_fn=base_node_to_style_fn)
    _tree_manager_to_vis_doc(derived_1_doc, derived_1_tm, node_to_style_fn=d1_node_to_style_fn)
    _tree_manager_to_vis_doc(derived_2_doc, derived_2_tm, node_to_style_fn=d2_node_to_style_fn)
    _tree_manager_to_vis_doc(merged_doc, merged_tm, node_to_style_fn=merged_node_to_style_fn)

    vis = MergeVis(base_doc, derived_1_doc, derived_2_doc, merged_doc,
                   title='3-way merge; {0} diffs, {1} del, {2} upd, {3} ins, {4} mov, {5} conf'.format(
                       len(diffs), len(deleted_nodes), len(updated_nodes), len(inserted_nodes), len(moved_nodes),
                       len(conflict_nodes)
                   ))
    return viewer(vis, lspace_root=lspace_root)

