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

```bash
pip install pyfwat
```

### Install from source

```bash
git clone https://github.com/xumi1993/pyfwat.git
cd pyfwat
pip install -e .
```

### Requirements

- Python >= 3.9
- ObsPy >= 1.2.0
- NumPy >= 1.19.0
- SciPy >= 1.1.0
- Matplotlib >= 3.2.0
- pandas >= 1.0.0
- PyGMT
- h5py
- pyproj
- ruamel.yaml
- PyQt5 (optional, for GUI tools)

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

### Interactive Tools

- `fwat_pick_tele` - Interactive GUI for teleseismic phase picking
- `fwat_pick_waveform` - Interactive GUI for ambient noise / local earthquake waveform picking

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

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).

## Author

Mijian Xu (mijian.xu@utoronto.ca)

