# Command-line tools

Installing PyFWAT puts the `fwat_*` commands on your `PATH`. Unless noted,
they run from the root of a SpecFWAT project and use the paths described in
{ref}`project-layout`. Every command prints the options below with `-h`.

## Preprocessing

### `fwat_gen_virt_fkevts`

Generate virtual FK events for every combination of back-azimuth (`-b`) and
ray parameter (`-r`, s/km), using `DATA/FKMODEL` and `DATA/STATIONS` as
templates.

```{fwat-cli} fwat_gen_virt_fkevts
```

### `fwat_ch_fkmodel`

Set a parameter to the same value in every `src_rec/FKmodel_*`, for example
`fwat_ch_fkmodel FREQUENCY_MAX 1.0`.

```{fwat-cli} fwat_ch_fkmodel
```

### `fwat_cal_fk_times`

Compute the FK arrival time at each station for the events of a set and write
`src_rec/FKtimes_<evtid>`.

```{fwat-cli} fwat_cal_fk_times
```

### `fwat_assign_weight`

Weight the events in `src_rec/sources_<set>.dat` by the inverse of their
density and write the weights to the last column. `-s` is needed only when
`src_rec/` holds more than one `sources_*.dat`. See
{doc}`guides/event_weighting`.

```{fwat-cli} fwat_assign_weight
```

### `fwat_gen_gauss_stf`

Write Gaussian source time functions `src_rec/STF_<evtid>.sac` for the events
of a set.

```{fwat-cli} fwat_gen_gauss_stf
```

### `fwat_createmodel`

Create an initial gridded model over the region in `Mesh_Par_file` from
CRUST1.0 or from a text model with depth, latitude, longitude, Vp and Vs
columns.

```{fwat-cli} fwat_createmodel
```

### `fwat_checkerboard`

Add checkerboard perturbations of relative amplitude `-p` to a gridded HDF5
model.

```{fwat-cli} fwat_checkerboard
```

## Visualization

### `fwat_plot_stations`

Map of the stations in the mesh region.

```{fwat-cli} fwat_plot_stations
```

### `fwat_plot_rf_evts`

Polar plot of the back-azimuth and ray parameter of receiver-function events.

```{fwat-cli} fwat_plot_rf_evts
```

### `fwat_plot_evt_weight`

Event distribution colored by weight. See {doc}`guides/event_weighting`.

```{fwat-cli} fwat_plot_evt_weight
```

### `fwat_plot_vel_sec`

Cross sections of Vp, Vs or density. `sections` is either a single line
`lat1/lon1/lat2/lon2` or a file with one line per row.

```{fwat-cli} fwat_plot_vel_sec
```

### `fwat_plot_dv_sec`

Cross sections of velocity perturbations (%).

```{fwat-cli} fwat_plot_dv_sec
```

### `fwat_plot_kernel_sec`

Cross sections of sensitivity kernels.

```{fwat-cli} fwat_plot_kernel_sec
```

### `fwat_plot_misfit`

Normalized misfit versus iteration.

```{fwat-cli} fwat_plot_misfit
```

### `fwat_plot_misfit_multifreq`

Misfit versus iteration for each period band.

```{fwat-cli} fwat_plot_misfit_multifreq
```

### `fwat_plot_misfit_multistage`

Misfit across several inversion stages.

```{fwat-cli} fwat_plot_misfit_multistage
```

### `fwat_plot_residual`

Histograms of the measurement residuals at the first and last iterations of
`-m`.

```{fwat-cli} fwat_plot_residual
```

### `fwat_plot_tele_fit`

Observed and synthetic teleseismic waveforms of an event.

```{fwat-cli} fwat_plot_tele_fit
```

### `fwat_plot_rf_fit`

Observed and synthetic receiver functions of an event.

```{fwat-cli} fwat_plot_rf_fit
```

### `fwat_plot_waveform_fit`

Observed and synthetic ambient-noise or local-earthquake waveforms of an event.

```{fwat-cli} fwat_plot_waveform_fit
```

### `fwat_plot_surf_data`

Record section of the surface-wave data of an event in a period band.

```{fwat-cli} fwat_plot_surf_data
```

## Post-processing

### `fwat_model_update`

Update model `-m` with step length `-l` and write the new model to
`DATA/tomo_files/tomography_model.h5`.

```{fwat-cli} fwat_model_update
```

### `fwat_joint_kernel`

Combine the gradients of different data types for model `-m`.

```{fwat-cli} fwat_joint_kernel
```

### `fwat_optimize_ls`

Select the step length with the lowest line-search misfit.

```{fwat-cli} fwat_optimize_ls
```

### `fwat_clean`

Remove the outputs of previous runs. Asks for confirmation unless `-f` is
given.

```{fwat-cli} fwat_clean
```

## Interactive picking

These commands need PySide6, which the `pyfwat` distribution installs.

### `fwat_pick_tele`

Pick and review teleseismic waveforms in a data directory.

```{fwat-cli} fwat_pick_tele
```

### `fwat_pick_waveform`

Pick and review ambient-noise or local-earthquake waveforms in a data
directory.

```{fwat-cli} fwat_pick_waveform
```

### `fwat_pick_rf`

Review and delete receiver functions of an event.

```{fwat-cli} fwat_pick_rf
```

## Utilities

### `fwat_setpar`

Set a parameter in a SPECFEM `Par_file` or `Mesh_Par_file`, an FK model or
`fwat_params.yml`. Nested YAML keys are joined with dots, for example
`fwat_setpar DATA/fwat_params.yml MODEL_UPDATE.ITER_START 0`.

```{fwat-cli} fwat_setpar
```

### `fwat_create_xmf`

Write an XDMF file next to an HDF5 grid model so that ParaView can open it.

```{fwat-cli} fwat_create_xmf
```
