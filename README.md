# PyFWAT

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

### Install from source

```bash
git clone https://github.com/xumi1993/pyfwat.git
cd pyfwat
pip install -e .
```

## Command-line Tools

PyFWAT provides numerous command-line utilities for various tasks:

### Visualization Tools

- `plot_vel_sec` - Plot velocity cross-sections
- `plot_dv_sec` - Plot velocity perturbation cross-sections
- `plot_kernel_sec` - Plot sensitivity kernel cross-sections
- `plot_residual` - Visualize data residuals
- `plot_misfit` - Plot misfit evolution
- `plot_misfit_multifreq` - Plot misfit for multiple frequencies
- `plot_misfit_multistage` - Plot misfit across multiple inversion stages
- `plot_misfit_linesearch` - Visualize line search optimization
- `plot_stations` - Display station distributions
- `plot_rf_evts` - Plot receiver function events
- `plot_rf_fit` - Show receiver function data fits
- `plot_noise_fit` - Visualize ambient noise data fits
- `plot_surf_data` - Plot surface wave data
- `plot_tele_fit` - Display teleseismic waveform fits

### Preprocessing Tools

- `gen_virt_fkevts` - Generate virtual FK events
- `gen_gauss_stf` - Generate Gaussian source time functions
- `ch_fkmodel` - Modify FK models
- `cal_fk_times` - Calculate FK travel times
- `fwat_checkerboard` - Create checkerboard resolution tests
- `fwat_createmodel` - Generate initial crustal models
- `setpar_fwat` - Configure FWAT parameters

### Post-processing Tools

- `optimize_ls` - Perform line search optimization
- `fwat_clean` - Clean up working directories
- `fwat_joint_kernel` - Combine kernels from different data types
- `fwat_model_update` - Update velocity models
- `create_xmf` - Create XDMF files for visualization (under development)

### Interactive Tools

- `pick_tele` - Interactive GUI for teleseismic phase picking

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

