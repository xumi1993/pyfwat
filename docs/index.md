# PyFWAT

PyFWAT is the Python toolkit for [SpecFWAT](https://github.com/xumi1993/SpecFWAT),
a SPECFEM3D-based full-waveform adjoint tomography (FWAT) tool for multiple
seismic data. PyFWAT prepares the inputs of an inversion, updates the model
between iterations, and plots models, kernels, misfits and data fits. See the
[SpecFWAT documentation](https://specfwat.xumijian.me) for running the
inversion itself.

Most functionality is exposed as `fwat_*` commands that run from the root of a
SpecFWAT project (the directory containing `DATA/` and `src_rec/`):

```bash
fwat_gen_virt_fkevts -b 0/360/30 -r 0.04/0.08/0.01   # virtual FK events
fwat_assign_weight                                    # weight events by density
fwat_plot_evt_weight                                  # check the weights
fwat_model_update -m M03 -l 0.02                      # update the model
fwat_plot_misfit -m 0/3                               # misfit reduction
```

The same functions can be imported from Python, for example
{func}`pyfwat.preproc.geo_weighting.assign_weight`.

## What's in the package

- **Preprocessing** ({mod}`pyfwat.preproc`): virtual FK plane-wave events, FK
  travel times, source time functions, event weights, initial and
  checkerboard models.
- **Visualization** ({mod}`pyfwat.plot`): PyGMT figures of velocity and kernel
  cross sections, misfit evolution, residual histograms, waveform and
  receiver-function fits, stations and event distributions.
- **Post-processing** ({mod}`pyfwat.postproc`): steepest-descent and L-BFGS
  model updates, joint kernels from several data types, step-length selection
  and project cleanup.
- **Interactive picking** ({mod}`pyfwat.picker`): Qt (PySide6) GUIs to review
  teleseismic, ambient-noise / local-earthquake waveforms and receiver
  functions.
- **I/O and utilities** ({mod}`pyfwat.io`, {mod}`pyfwat.utils`): readers and
  writers of SPECFEM GLL models, gridded HDF5 models, XDMF files and misfit
  tables; parameter-file editing; geodesy helpers.

```{toctree}
:maxdepth: 2
:caption: User guide

installation
overview
cli
guides/event_weighting
```

```{toctree}
:maxdepth: 1
:caption: Reference

api
```
