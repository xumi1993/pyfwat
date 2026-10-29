# PyFWAT

[![PyPI version](https://badge.fury.io/py/pyfwat.svg)](https://badge.fury.io/py/pyfwat)
[![Python](https://img.shields.io/pypi/pyversions/pyfwat.svg)](https://pypi.org/project/pyfwat/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Downloads](https://static.pepy.tech/badge/pyfwat)](https://pepy.tech/project/pyfwat)
[![GitHub stars](https://img.shields.io/github/stars/xumi1993/pyfwat.svg?style=social&label=Star)](https://github.com/xumi1993/pyfwat)

Python interface for SpecFWAT (Full Waveform Adjoint Tomography)

## Overview

PyFWAT is a comprehensive Python toolkit designed for full waveform inversion (FWI) and adjoint tomography workflows. It provides a complete set of tools for preprocessing seismic data, running inversions, post-processing results, and visualizing various aspects of the tomographic models and data fits.

## Features

- **Preprocessing Tools**: Data preparation and model setup utilities
- **Plotting Utilities**: Comprehensive visualization tools for velocity models, kernels, misfits, and data fits
- **Post-processing**: Model updates, kernel operations, and optimization routines
- **Data I/O**: Support for various seismic data formats and model representations
- **Interactive Picking**: GUI-based phase picking interface for teleseismic data

## Installation

### Install from PyPI (recommended)

Install PyFWAT with the PySide6 GUI tools:

```bash
pip install pyfwat
```

For servers or environments that do not need the GUI, install the core package:

```bash
pip install pyfwat-core
```

Both packages provide the same `pyfwat` Python imports and `fwat_*` commands.
`pyfwat-core` owns the implementation and its command-line entry points;
`pyfwat` is a small package that installs the matching core version with its GUI
dependencies. The code is installed only once.

### Install from source

```bash
git clone https://github.com/xumi1993/pyfwat.git
cd pyfwat
pip install -e ".[gui]"
```

To install from source without GUI dependencies:

```bash
pip install -e .
```

To add the GUI later, install `pyfwat` or `pyfwat-core[gui]`.

Use a clean environment when switching an existing GUI installation to core-only;
installing `pyfwat-core` does not remove an installed `pyfwat` wrapper or PySide6.
For upgrades from older releases that bundled the implementation directly in
`pyfwat`, use a clean environment or uninstall the old `pyfwat` package before
installing the new distributions. This avoids overlapping ownership of installed
files during the packaging transition.

### Requirements

- Python >= 3.9
- ObsPy >= 1.2.0
- NumPy >= 1.19.0
- SciPy >= 1.1.0
- Matplotlib >= 3.5.0
- pandas >= 1.0.0
- PyGMT
- h5py
- pyproj
- ruamel.yaml
- PySide6 >= 6.2 (included with `pyfwat`; optional for `pyfwat-core`)

## Command-line Tools

PyFWAT provides numerous command-line utilities for various tasks:

### Visualization Tools

- `fwat_plot_vel_sec` - Plot velocity cross-sections
- `fwat_plot_dv_sec` - Plot velocity perturbation cross-sections
- `fwat_plot_kernel_sec` - Plot sensitivity kernel cross-sections
- `fwat_plot_residual` - Visualize data residuals
- `fwat_plot_misfit` - Plot misfit evolution
- `fwat_plot_misfit_multifreq` - Plot misfit for multiple frequencies
- `fwat_plot_misfit_multistage` - Plot misfit across multiple inversion stages
- `fwat_plot_misfit_linesearch` - Visualize line search optimization
- `fwat_plot_stations` - Display station distributions
- `fwat_plot_rf_evts` - Plot receiver function events
- `fwat_plot_rf_fit` - Show receiver function data fits
- `fwat_plot_waveform_fit` - Visualize ambient noise / local earthquake data fits
- `fwat_plot_tele_fit` - Display teleseismic waveform fits

### Preprocessing Tools

- `fwat_gen_virt_fkevts` - Generate virtual FK events
- `fwat_gen_gauss_stf` - Generate Gaussian source time functions
- `fwat_ch_fkmodel` - Modify FK models
- `fwat_cal_fk_times` - Calculate FK travel times
- `fwat_checkerboard` - Create checkerboard resolution tests
- `fwat_createmodel` - Generate initial crustal models
- `fwat_setpar` - Setup parameters of FWAT and Specfem3D

### Post-processing Tools

- `fwat_optimize_ls` - Perform line search optimization
- `fwat_clean` - Clean up working directories
- `fwat_joint_kernel` - Combine kernels from different data types
- `fwat_model_update` - Update velocity models

### Interactive Tools for data quality control

- `fwat_pick_tele` - Interactive GUI for teleseismic waveform with phase picking
- `fwat_pick_waveform` - Interactive GUI for ambient noise / local earthquake waveform picking
- `fwat_pick_rf` - Interactive GUI for receiver function picking

## Module Structure

```
pyfwat/
├── io/           # Input/output utilities
├── picker/       # Phase picking tools
├── plot/         # Visualization modules
├── postproc/     # Post-processing routines
├── preproc/      # Preprocessing utilities
├── utils/        # General utility functions
├── cpt/          # Color palette files
└── data/         # Data resources (e.g., CRUST1.0 model)
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Building and publishing

The version in the root `pyproject.toml` is the single version source for both
distributions. Before a release, set it to a new version that has not already
been published; PyPI does not allow replacing an existing release file.

Build and check both packages from a source checkout using Python 3.11 or newer:

```bash
python -m pip install build twine setuptools wheel
python -m unittest discover -s tests -p test_packaging.py -v
python scripts/build_distributions.py
python -m twine check dist/*
```

The build produces wheels and source distributions for `pyfwat-core` and
`pyfwat`. The wrapper depends on the matching core version with its `gui` extra.
Publishing a GitHub release runs the same tests and build, uploads the core
distribution first, and then uploads the GUI wrapper.

Configure PyPI Trusted Publishing for both project names using this repository
and `.github/workflows/publish-to-pypi.yml`. For the first `pyfwat-core` release,
create a pending publisher as described in the
[PyPI guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
The existing `pyfwat` project's publisher must remain configured as well.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).

## Author

Mijian Xu (mijian.xu@utoronto.ca)

