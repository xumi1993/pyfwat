# Weighting teleseismic events

Teleseismic and receiver-function events are unevenly distributed: most come
from a few source regions, so clusters of similar events dominate the misfit
and the kernels. `fwat_assign_weight` gives each event a weight that decreases
with the number of similar events around it, and writes it to the last column
of `src_rec/sources_<set>.dat`.

## Method

Event similarity is measured in one of two spaces, chosen with `-m`:

`baz` (default)
: Back-azimuth $\phi$ and ray parameter $p$. For each event, `BACK_AZIMUTH` and
  `TAKE_OFF` $\theta$ are read from `src_rec/FKmodel_<evtid>`, and
  $p = \sin\theta / v$, where $v$ is the Vp (or Vs if `INCIDENT_WAVE` is `s`)
  of the half space, the last `LAYER`. The distance between events $i$ and $j$
  is

  $$
  d_{ij} = \sqrt{\Delta\phi_{ij}^2 + (p_i - p_j)^2},
  $$

  with $\Delta\phi_{ij}$ in degrees, wrapped to $[0^\circ, 180^\circ]$ so that
  events at 355° and 5° are neighbours, and $p$ in s/rad so that its spread is
  comparable to that of the back-azimuth.

`loc`
: Epicenter. $d_{ij}$ is the epicentral distance in degrees between the
  `evla`/`evlo` of events $i$ and $j$ in the source list.

The density around each event is the sum of a Gaussian kernel over all events,
and the raw weight is its inverse:

$$
w_i = \left[\sum_j \exp\left(-\frac{d_{ij}^2}{\delta^2}\right)\right]^{-1},
\qquad
\delta = c \cdot \begin{cases}
\operatorname{mean}(d_{ij}) & \text{baz} \\
\operatorname{std}(d_{ij}) & \text{loc}
\end{cases}
$$

The coefficient $c$ (`-c`) defaults to 0.5 for `baz` and 0.25 for `loc`. A
larger $c$ widens the kernel, so the weights follow the large-scale event
distribution; a smaller $c$ only counts close neighbours.

Finally the weights are mapped linearly to $[w_{\min}, w_{\max}]$ (`-w`,
default `0.3/1.0`):

$$
w_i' = w_{\min} + (w_{\max} - w_{\min})\,
\frac{w_i - \min_k w_k}{\max_k w_k - \min_k w_k}.
$$

The most isolated event gets $w_{\max}$ and the one in the densest cluster
gets $w_{\min}$. If all raw weights are equal, every event gets $w_{\max}$.

## Assign weights

Run from the project root. When `src_rec/` holds a single `sources_*.dat`, no
set name is needed:

```console
$ fwat_assign_weight
Using src_rec/sources_tele.dat
Assigned weights to 50 events: min=0.3000, max=1.0000
```

With several source lists, choose one with `-s`. Other options select the
method, the kernel width and the weight range, or write to another file
instead of overwriting the source list:

```bash
fwat_assign_weight -s rf -m loc -c 0.3 -w 0.5/1.0
fwat_assign_weight -s rf -o preview.dat
```

Only the weight column is rewritten, with four decimals; the other columns are
kept as they are.

## Check the weights

`fwat_plot_evt_weight` plots the events colored by weight, in
back-azimuth/ray-parameter space (from the FK models) and on an azimuthal
equidistant map centered on the mean station location of `DATA/STATIONS`:

```bash
fwat_plot_evt_weight            # writes figures/evt_weight_<set>.png
fwat_plot_evt_weight -m baz     # polar plot only, no DATA/STATIONS needed
fwat_plot_evt_weight -c 35/-100 -C viridis
```

```{figure} ../images/evt_weight_example.png
:alt: Synthetic events colored by weight in a polar back-azimuth/ray-parameter plot and on an azimuthal equidistant map.

Synthetic example with 50 events. The cluster to the north-west gets the
lowest weights and the isolated events the highest.
```

## From Python

{func}`~pyfwat.preproc.geo_weighting.assign_weight` does the same as the
command and returns the weights:

```python
from pyfwat.preproc.geo_weighting import assign_weight

weight = assign_weight('rf', method='baz', coef=0.5, wmin=0.3, wmax=1.0)
```

The building blocks work on arrays directly:
{func}`~pyfwat.preproc.geo_weighting.gen_weight` (back-azimuth and ray
parameter), {func}`~pyfwat.preproc.geo_weighting.gen_weight_loc` (epicenters)
and {func}`~pyfwat.preproc.geo_weighting.rescale_weight`.
