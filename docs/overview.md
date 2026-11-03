# Package overview

PyFWAT is organized by the stage of a SpecFWAT inversion each module serves.
This page describes what every module does and which command exposes it; the
{doc}`cli` lists the options of each command and the {doc}`api` documents the
Python functions and classes.

(project-layout)=
## Project layout

The `fwat_*` commands run from the root of a SpecFWAT project and read or
write files at fixed relative paths:

| Path | Content |
| ---- | ------- |
| `DATA/fwat_params.yml` | SpecFWAT parameters (iterations, optimization, joint-inversion weights). |
| `DATA/meshfem3D_files/Mesh_Par_file` | Mesh region, depth and UTM settings. |
| `DATA/STATIONS` | Station list: `station network lat lon elevation burial`. |
| `DATA/FKMODEL` | Template FK model used to generate virtual events. |
| `DATA/tomo_files/tomography_model.h5` | Gridded model used to build the mesh. |
| `src_rec/sources_<set>.dat` | Event list of a source set: `evtid evla evlo evdp evbur weight`. |
| `src_rec/FKmodel_<evtid>`, `STATIONS_<evtid>` | FK model (layers, `BACK_AZIMUTH`, `TAKE_OFF`, ...) and stations of each teleseismic event. |
| `src_rec/FKtimes_<evtid>`, `STF_<evtid>.sac` | FK arrival times and source time functions. |
| `solver/<model>.<set>/<evtid>/OUTPUT_FILES/` | Observed and synthetic waveforms of a simulation. |
| `misfits/` | Window misfit tables `M<it>.<evtid>*_<band>_window_chi`. |
| `optimize/` | Models `model_M<it>.h5`, gradients `gradient_M<it>.h5` and line-search trial models. |
| `figures/` | Default output directory of the plotting commands. |

## Preprocessing — {mod}`pyfwat.preproc`

Tools that prepare sources, stations and models before an inversion.

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.preproc.gen_virt_fkevts` | `fwat_gen_virt_fkevts` | Generate virtual FK plane-wave events on a grid of back-azimuths and ray parameters. Writes `FKmodel_<evtid>`, `STATIONS_<evtid>` and the source lists in `src_rec/` from the `DATA/FKMODEL` and `DATA/STATIONS` templates. |
| {mod}`~pyfwat.preproc.ch_fkmodel` | `fwat_ch_fkmodel` | Change one parameter in every `src_rec/FKmodel_*` file. |
| {mod}`~pyfwat.preproc.cal_fk_times` | `fwat_cal_fk_times` | Compute the arrival time of the FK plane wave at each station of an event in the layered FK model and write `src_rec/FKtimes_<evtid>`. |
| {mod}`~pyfwat.preproc.geo_weighting` | `fwat_assign_weight` | Weight events by the inverse of their density in back-azimuth/ray-parameter space or in epicentral location, and write the weights to the source list. See {doc}`guides/event_weighting`. |
| {mod}`~pyfwat.preproc.gen_gauss_stf` | `fwat_gen_gauss_stf` | Write Gaussian source time functions `src_rec/STF_<evtid>.sac` for the events of a set. |
| {mod}`~pyfwat.preproc.create_crustmodel` | `fwat_createmodel` | Build an initial gridded model over the mesh region from CRUST1.0 (bundled) or a user model, with optional smoothing and boundary taper; write HDF5 or xyz. |
| {mod}`~pyfwat.preproc.checkerboard` | `fwat_checkerboard` | Add checkerboard perturbations to a gridded HDF5 model for resolution tests. |
| {mod}`~pyfwat.preproc.dis2inc` | — | P-wave ray parameter and incidence angle at a given depth from the source depth and epicentral distance, using TauP with ak135. Run as `python -m pyfwat.preproc.dis2inc dep evdp dis`. |

## Visualization — {mod}`pyfwat.plot`

PyGMT figures for checking inputs, models and the progress of an inversion.
Figures are written to `./figures` unless `-o` is given.

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.plot.plot_stations` | `fwat_plot_stations` | Map of the stations in the mesh region. |
| {mod}`~pyfwat.plot.plot_rf_evts` | `fwat_plot_rf_evts` | Back-azimuth and ray parameter of receiver-function events in polar coordinates, optionally colored by weight. |
| {mod}`~pyfwat.plot.plot_evt_weight` | `fwat_plot_evt_weight` | Event distribution colored by weight: back-azimuth/ray-parameter polar plot and azimuthal equidistant map of epicenters. |
| {mod}`~pyfwat.plot.plot_vel_sec` | `fwat_plot_vel_sec` | Cross sections of Vp, Vs or density from a gridded model. |
| {mod}`~pyfwat.plot.plot_dv_sec` | `fwat_plot_dv_sec` | Cross sections of velocity perturbations (%) relative to the depth-averaged model or an initial model. |
| {mod}`~pyfwat.plot.plot_dlnv` | — | Cross sections of the relative perturbation of a model with respect to an initial model. |
| {mod}`~pyfwat.plot.plot_kernel_sec` | `fwat_plot_kernel_sec` | Cross sections of sensitivity kernels. |
| {mod}`~pyfwat.plot.plot_misfit` | `fwat_plot_misfit` | Normalized misfit versus iteration for a period band. |
| {mod}`~pyfwat.plot.plot_misfit_multifreq` | `fwat_plot_misfit_multifreq` | Misfit versus iteration for each period band, optionally with their average. |
| {mod}`~pyfwat.plot.plot_misfit_multistage` | `fwat_plot_misfit_multistage` | Misfit across several inversion stages (iteration ranges). |
| {mod}`~pyfwat.plot.plot_misfit_linesearch` | — | Misfit versus step length of a line search; also used by `fwat_optimize_ls`. |
| {mod}`~pyfwat.plot.plot_res` | `fwat_plot_residual` | Histograms of the measurement residuals at two iterations. |
| {mod}`~pyfwat.plot.plot_tele_fit` | `fwat_plot_tele_fit` | Observed and synthetic teleseismic waveforms of an event. |
| {mod}`~pyfwat.plot.plot_rf_fit` | `fwat_plot_rf_fit` | Observed and synthetic receiver functions of an event. |
| {mod}`~pyfwat.plot.plot_waveform_fit` | `fwat_plot_waveform_fit` | Observed and synthetic ambient-noise or local-earthquake waveforms of an event. |
| {mod}`~pyfwat.plot.plot_surf_data` | `fwat_plot_surf_data` | Record section of the surface-wave data of an event in a period band, with reference-velocity lines. |

## Post-processing — {mod}`pyfwat.postproc`

Steps between two iterations of an inversion.

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.postproc.model_update` | `fwat_model_update` | Update the model with steepest descent or L-BFGS from the models and gradients in `optimize/`, and write `DATA/tomo_files/tomography_model.h5`. |
| {mod}`~pyfwat.postproc.joint_kernel` | `fwat_joint_kernel` | Combine the gradients of different data types, each normalized and weighted by `POSTPROC.JOINT_WEIGHT`. |
| {mod}`~pyfwat.postproc.optimize_ls` | `fwat_optimize_ls` | Pick the step length with the lowest line-search misfit and promote its trial model to the next iteration. |
| {mod}`~pyfwat.postproc.clean` | `fwat_clean` | Remove `solver/`, `optimize/`, `misfits/` and `output_*.log`. |

## Interactive picking — {mod}`pyfwat.picker`

PySide6 GUIs for reviewing data before an inversion. They require the
`pyfwat` distribution (or `pyfwat-core[gui]`).

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.picker.picker_ui_tele` | `fwat_pick_tele` | Align teleseismic waveforms, pick arrivals and delete bad traces. |
| {mod}`~pyfwat.picker.picker_ui_waveform` | `fwat_pick_waveform` | The same for ambient-noise and local-earthquake waveforms. |
| {mod}`~pyfwat.picker.picker_ui_rf` | `fwat_pick_rf` | Review receiver functions of an event and delete bad ones. |
| {mod}`~pyfwat.picker.picker_fig_tele`, {mod}`~pyfwat.picker.picker_fig_waveform` | — | Data loading, plotting and saving behind the teleseismic and waveform pickers. |
| {mod}`~pyfwat.picker.mccc` | — | Multi-channel cross-correlation of waveforms for relative time delays. |

## Input/output — {mod}`pyfwat.io`

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.io.gllio` | — | Read and write SPECFEM binary mesh and GLL model files. |
| {mod}`~pyfwat.io.grid_model` | — | Gridded HDF5 models (`x`, `y`, `z` and model arrays): trimming, UTM-to-geographic conversion and perturbations relative to a reference. |
| {mod}`~pyfwat.io.misfit` | — | Read the window misfit tables in `misfits/` for an iteration and period band. |
| {mod}`~pyfwat.io.xdmf` | `fwat_create_xmf` | Write an XDMF descriptor of an HDF5 grid model to open it in ParaView. |

## Utilities — {mod}`pyfwat.utils`

| Module | Command | Purpose |
| ------ | ------- | ------- |
| {mod}`~pyfwat.utils.pario` | `fwat_setpar` | Read and change parameters in SPECFEM `Par_file`/`Mesh_Par_file`, FK models and `fwat_params.yml`. |
| {mod}`~pyfwat.utils.geo` | — | Trigonometry in degrees, distance and slowness unit conversions, and destination points from an azimuth and distance. |
| {mod}`~pyfwat.utils.distaz` | — | Distance, azimuth and back-azimuth between points on the Earth. |
| {mod}`~pyfwat.utils.utils` | — | Paths of the bundled color tables, density from Vp, and filling NaNs in 3-D arrays. |
