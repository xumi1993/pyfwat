"""Sphinx configuration for the PyFWAT documentation."""
import sys
import tomllib
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DOCS / '_ext'))

with open(ROOT / 'pyproject.toml', 'rb') as f:
    _project = tomllib.load(f)['project']

# -- Project information -----------------------------------------------------
project = 'PyFWAT'
author = 'Mijian Xu'
copyright = author
release = _project['version']
version = '.'.join(release.split('.')[:2])

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.mathjax',
    'myst_parser',
    'sphinx_copybutton',
    'fwat_cli',
]
# Pages are written in MyST Markdown; reST is kept for the API stubs that
# autosummary generates.
source_suffix = {'.md': 'markdown', '.rst': 'restructuredtext'}
myst_enable_extensions = ['dollarmath', 'deflist']
templates_path = ['_templates']
exclude_patterns = ['_build']

# Dependencies that need system libraries or a GUI are mocked, so the docs
# build with only the packages in docs/requirements.txt.
autodoc_mock_imports = [
    'pygmt',
    'obspy',
    'PySide6',
    'matplotlib.backends.backend_qtagg',
    'xarray',
    'seispy',
]
autosummary_generate = True
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
napoleon_google_docstring = False

copybutton_prompt_text = r'\$ '
copybutton_prompt_is_regexp = True

# -- HTML output -------------------------------------------------------------
html_theme = 'furo'
html_title = f'PyFWAT {release}'
html_logo = '../pyfwat/data/icon.svg'
html_favicon = '../pyfwat/data/icon.svg'
