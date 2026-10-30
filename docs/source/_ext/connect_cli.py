# connect_cli.py
"""Sphinx extension that documents a connect_* program in the same style as the
support tools functions (signature box + Parameters list), using the program's
own argparse parser so the manual always matches ``-h``.

Usage in an .rst file::

    .. connect-cli:: wsuconnect.connect_fmriprep
"""

import argparse
import importlib

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.domains.python import PyFunction


class PyCliProgram(PyFunction):
    """py:function that accepts a program name such as connect_recon-all.py."""

    def handle_signature(self, sig, signode):
        name, _, args = sig.partition(' ')
        signode += addnodes.desc_name(name, name)
        if args:
            # one option per line, like the multi-line function signatures
            plist = addnodes.desc_parameterlist()
            plist['multi_line_parameter_list'] = True
            for arg in args.split(' || '):
                plist += addnodes.desc_parameter(arg, arg)
            signode += plist
        return name, ''

    def add_target_and_index(self, name_cls, sig, signode):
        pass


def _type(action):
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        t = 'flag'
    elif action.nargs in ('+', '*'):
        t = 'list'
    elif action.type is int:
        t = 'int'
    elif action.type is float:
        t = 'float'
    else:
        t = 'str'
    t += ', required' if action.required else ', optional'
    return t


def _usage_args(parser):
    parts = []
    for a in parser._actions:
        if isinstance(a, argparse._HelpAction):
            continue
        flag = a.option_strings[0] if a.option_strings else a.dest
        if a.option_strings and a.nargs != 0:
            flag += ' ' + (a.metavar or a.dest)
            if a.nargs in ('+', '*'):
                flag += ' ...'
        parts.append(flag if a.required or not a.option_strings else '[' + flag + ']')
    return ' || '.join(parts)


class ConnectCli(Directive):
    required_arguments = 1

    def run(self):
        modname = self.arguments[0]
        mod = importlib.import_module(modname)
        parser = mod.parser
        prog = modname.split('.')[-1] + '.py'

        lines = [f'.. py:cliprogram:: {prog} {_usage_args(parser)}', '']
        if parser.description:
            lines += ['   ' + parser.description, '']
        for a in parser._actions:
            if isinstance(a, argparse._HelpAction):
                continue
            key = '/'.join(a.option_strings) if a.option_strings else a.dest
            helptext = (a.help or '').replace('\n', ' ')
            if a.choices:
                helptext += ' Choices: ' + ', '.join(str(c) for c in a.choices) + '.'
            lines += [f'   :param {key}: {helptext}', f'   :type {key}: {_type(a)}']
        lines.append('')

        node = nodes.container()
        self.state.nested_parse(StringList(lines, source=modname), self.content_offset, node)
        return node.children


def setup(app):
    app.add_directive_to_domain('py', 'cliprogram', PyCliProgram)
    app.add_directive('connect-cli', ConnectCli)
    return {'parallel_read_safe': True}
