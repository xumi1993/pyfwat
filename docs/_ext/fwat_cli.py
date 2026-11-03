"""Render the ``-h`` help of pyfwat console scripts in the documentation.

Usage in MyST Markdown::

    ```{fwat-cli} fwat_assign_weight
    ```

The command is looked up in ``[project.scripts]`` of ``pyproject.toml``. Its
entry function is called with :meth:`argparse.ArgumentParser.parse_args`
intercepted, so only the argument parser is built and no work is done. Heavy
dependencies are mocked with ``autodoc_mock_imports``. The usage line shows the
command name, and the parser description is dropped because each command is
described in the surrounding text.

When the build starts, every console script missing from ``cli.md`` is
reported as a warning.
"""
import argparse
import importlib
import os
import re
import tomllib
from pathlib import Path

from docutils import nodes
from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
HELP_WIDTH = '88'


class _Captured(Exception):
    def __init__(self, parser):
        super().__init__()
        self.parser = parser


def load_scripts():
    with open(ROOT / 'pyproject.toml', 'rb') as f:
        return tomllib.load(f)['project']['scripts']


def capture_parser(entry, mock_modules):
    """Call the entry point ``module:function`` and return the parser it builds."""
    modname, funcname = entry.split(':')

    def capture(parser, *args, **kwargs):
        raise _Captured(parser)

    original = argparse.ArgumentParser.parse_args
    argparse.ArgumentParser.parse_args = capture
    try:
        with mock(mock_modules):
            getattr(importlib.import_module(modname), funcname)()
    except _Captured as captured:
        return captured.parser
    else:
        raise RuntimeError(f'{entry} returned without parsing arguments')
    finally:
        argparse.ArgumentParser.parse_args = original


def format_help(parser, command):
    parser.prog = command
    parser.description = None
    parser.epilog = None
    parser.color = False  # Python >= 3.14 may colorize help on a terminal.
    columns = os.environ.get('COLUMNS')
    os.environ['COLUMNS'] = HELP_WIDTH
    try:
        return parser.format_help()
    finally:
        if columns is None:
            del os.environ['COLUMNS']
        else:
            os.environ['COLUMNS'] = columns


class FwatCliDirective(SphinxDirective):
    required_arguments = 1

    def run(self):
        command = self.arguments[0]
        scripts = load_scripts()
        if command not in scripts:
            logger.warning(f'{command} is not a console script in pyproject.toml',
                           location=self.get_location())
            return []
        try:
            parser = capture_parser(scripts[command], self.config.autodoc_mock_imports)
            text = format_help(parser, command)
        except Exception as e:
            logger.warning(f'cannot render the help of {command}: {e!r}',
                           location=self.get_location())
            return []
        block = nodes.literal_block(text, text)
        block['language'] = 'none'
        return [block]


def check_documented(app):
    cli_md = Path(app.srcdir) / 'cli.md'
    documented = set(re.findall(r'^```\{fwat-cli\} *(\S+)', cli_md.read_text(), re.MULTILINE))
    for command in sorted(set(load_scripts()) - documented):
        logger.warning(f'console script {command} is not documented in cli.md')


def setup(app):
    app.add_directive('fwat-cli', FwatCliDirective)
    app.connect('builder-inited', check_documented)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
