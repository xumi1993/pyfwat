# Installation

PyFWAT is published as two distributions that provide the same `pyfwat`
package and `fwat_*` commands:

| Distribution  | Content                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| `pyfwat`      | The full installation, including the PySide6 GUI used by the pickers.   |
| `pyfwat-core` | The implementation without GUI dependencies, for servers and clusters.  |

## Install from PyPI

```bash
pip install pyfwat        # with GUI tools
pip install pyfwat-core   # without GUI tools
```

`pyfwat` only depends on the matching `pyfwat-core` version plus PySide6, so
the code is installed once. To add the GUI to a core installation later,
install `pyfwat` or `pyfwat-core[gui]`.

When switching an existing GUI installation to core-only, use a clean
environment: installing `pyfwat-core` does not remove an installed `pyfwat`
wrapper or PySide6. When upgrading from older releases that bundled the code
directly in `pyfwat`, also use a clean environment or uninstall the old
`pyfwat` first.

## Install from source

```bash
git clone https://github.com/xumi1993/pyfwat.git
cd pyfwat
pip install -e ".[gui]"   # or "pip install -e ." without the GUI
```

## Dependencies

- ObsPy, NumPy, SciPy, pandas, Matplotlib
- PyGMT (which requires the GMT library), used by all plotting commands
- h5py, pyproj, ruamel.yaml
- PySide6 >= 6.2, only for the picking GUIs

## Build this documentation

The documentation does not need GMT, ObsPy or PySide6; these are mocked during
the build.

```bash
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser.
