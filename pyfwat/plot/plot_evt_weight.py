#!/usr/bin/env python
"""Plot the distribution of events colored by their weights in src_rec/sources_<set_name>.dat."""
import argparse
from os import makedirs
from os.path import join
from pathlib import Path

import numpy as np
import pygmt

from ..preproc.geo_weighting import find_set_name, read_fkmodel, read_sources
from ..utils.distaz import distaz
from ..utils.geo import deg2km, latlon_from
from .plot_stations import read_sta

PANEL = 8.0  # panel width in cm
GAP = 2.5    # gap between panels in cm
EVT_STYLE = 'c0.25c'
EVT_PEN = '0.25p,gray20'
TEXT_FONT = '7p,Helvetica,gray30'


def weight_cpt(weight, cmap='batlow'):
    """Make the cpt spanning the weight range."""
    vmin, vmax = float(weight.min()), float(weight.max())
    if vmin == vmax:
        vmin, vmax = vmin - 0.1, vmax + 0.1
    pygmt.makecpt(cmap=cmap, series=[vmin, vmax])


def plot_baz_rayp(fig, baz, rayp, weight, order, label_angle=22.5, step=0.01):
    """Polar plot with back-azimuth as angle and ray parameter (s/km) as radius."""
    rmin = max(0.0, np.floor((rayp.min() - step / 2) / step) * step)
    rmax = np.ceil((rayp.max() + step / 2) / step) * step
    fig.basemap(region=[0, 360, rmin, rmax], projection=f'P{PANEL}c+a',
                frame=['xa45f15g45', f'yg{step}', '+tBack-azimuth & ray parameter'])
    rings = np.arange(rmin, rmax + step / 2, step)
    fig.text(x=np.full(rings.size, label_angle), y=rings,
             text=[f'{r:.2f}' for r in rings[:-1]] + [f'{rings[-1]:.2f} s/km'],
             font=TEXT_FONT, fill='white', no_clip=True)
    fig.plot(x=baz[order], y=rayp[order], fill=weight[order], cmap=True,
             style=EVT_STYLE, pen=EVT_PEN)


def plot_epicenters(fig, evla, evlo, weight, order, center):
    """Azimuthal equidistant map of epicenters centered on the study region."""
    clat, clon = center
    dist = np.atleast_1d(distaz(clat, clon, evla, evlo).delta)
    horizon = min(180, max(100, np.ceil(dist.max() / 10) * 10 + 10))
    fig.basemap(region='g', projection=f'E{clon}/{clat}/{horizon}/{PANEL}c',
                frame='WSEN+tEpicenters')
    # GMT always warns that -G may fail on azimuthal projections; only show errors.
    fig.coast(land='gray90', shorelines='0.1p,gray60', resolution='c', verbose='e')
    for d in range(30, int(horizon), 30):
        fig.plot(x=[clon], y=[clat], style=f'E-{2 * deg2km(d):.0f}', pen='0.4p,gray50,-')
        lat, lon = latlon_from(clat, clon, 0, d)
        fig.text(x=lon, y=lat, text=f'{d}@.', font=TEXT_FONT, fill='white', justify='CM')
    fig.plot(x=[clon], y=[clat], style='t0.3c', fill='gray30')
    fig.plot(x=evlo[order], y=evla[order], fill=weight[order], cmap=True,
             style=EVT_STYLE, pen=EVT_PEN)


def plot_evt_weight(set_name=None, panels='both', center=None, outpath='./figures',
                    src_rec='src_rec', stafile='DATA/STATIONS', label_angle=22.5, cmap='batlow'):
    """Plot events in ``<src_rec>/sources_<set_name>.dat`` colored by weight.

    :param set_name: Set name of the sources file, defaults to the only
        ``sources_*.dat`` in ``src_rec``
    :param panels: ``'baz'`` for back-azimuth/ray-parameter from FKmodel,
        ``'loc'`` for epicenters, or ``'both'``
    :param center: (lat, lon) of the map center, defaults to the mean location of ``stafile``
    :param outpath: Output directory of the figure
    :param src_rec: Directory of the sources and FKmodel files
    :param stafile: Station file used for the default map center
    :param label_angle: Back-azimuth where ray-parameter labels are drawn
    :param cmap: GMT color map for weights
    :return: Path to the figure
    """
    if panels not in ('both', 'baz', 'loc'):
        raise ValueError("panels must be 'both', 'baz' or 'loc'")
    if set_name is None:
        set_name = find_set_name(src_rec)
    rows = read_sources(Path(src_rec) / f'sources_{set_name}.dat')
    weight = np.array([row[5] for row in rows], dtype=float)
    # Draw low weights (dense clusters) last so their colors stay visible.
    order = np.argsort(-weight, kind='stable')

    fig = pygmt.Figure()
    pygmt.config(FORMAT_GEO_MAP='+D', FONT_ANNOT_PRIMARY='8p,Helvetica,gray20',
                 FONT_TITLE='11p,Helvetica,black', FONT_LABEL='9p,Helvetica,gray20',
                 MAP_TITLE_OFFSET='8p',
                 MAP_FRAME_PEN='0.6p,gray30', MAP_GRID_PEN_PRIMARY='0.25p,gray75',
                 MAP_TICK_PEN_PRIMARY='0.5p,gray30')
    weight_cpt(weight, cmap)
    if panels in ('both', 'baz'):
        baz, rayp = np.array([read_fkmodel(Path(src_rec) / f'FKmodel_{row[0]}') for row in rows]).T
        plot_baz_rayp(fig, baz, rayp, weight, order, label_angle)
    if panels == 'both':
        fig.shift_origin(xshift=f'{PANEL + GAP}c')
    if panels in ('both', 'loc'):
        if center is None:
            if not Path(stafile).exists():
                raise FileNotFoundError(f'{stafile} not found for the map center, '
                                        'specify center_la/center_lo with -c or plot baz only with -m baz')
            _, _, stla, stlo, _ = read_sta(stafile)
            center = (float(np.mean(stla)), float(np.mean(stlo)))
        evla, evlo = np.array([row[1:3] for row in rows], dtype=float).T
        plot_epicenters(fig, evla, evlo, weight, order, center)
    # Center the colorbar under all panels.
    xcbar = -GAP / 2 if panels == 'both' else PANEL / 2
    fig.colorbar(position=f'x{xcbar}c/-1.3c+w{PANEL}c/0.3c+h+jTC',
                 frame=['xa0.1f0.05+lWeight'])

    makedirs(outpath, exist_ok=True)
    figpath = join(outpath, f'evt_weight_{set_name}.png')
    fig.savefig(figpath, dpi=300)
    return figpath


def main():
    parser = argparse.ArgumentParser(
        description='Plot the distribution of events in src_rec/sources_<set_name>.dat colored by '
                    'weight: back-azimuth and ray parameter from src_rec/FKmodel_<evtid> (baz), '
                    'and epicenters on an azimuthal equidistant map (loc).')
    parser.add_argument('-s', help='Set name, required only if there are multiple '
                        'src_rec/sources_*.dat', metavar='set_name', default=None)
    parser.add_argument('-m', help='Panels to plot, defaults to both',
                        choices=['both', 'baz', 'loc'], default='both')
    parser.add_argument('-c', help='Center of the epicenter map, defaults to the mean '
                        'location of DATA/STATIONS', metavar='center_la/center_lo', default=None)
    parser.add_argument('-a', help='Back-azimuth for drawing ray-parameter labels, defaults to 22.5',
                        type=float, metavar='angle', default=22.5)
    parser.add_argument('-C', help='GMT color map for weights, defaults to batlow',
                        metavar='cmap', default='batlow')
    parser.add_argument('-o', help='Figure output path, defaults to ./figures',
                        metavar='output_path', default='./figures')
    args = parser.parse_args()
    center = None
    if args.c is not None:
        try:
            center = tuple(float(v) for v in args.c.split('/'))
            assert len(center) == 2
        except (ValueError, AssertionError):
            parser.error('-c must be in the format of center_la/center_lo')
    set_name = args.s
    if set_name is None:
        try:
            set_name = find_set_name()
        except ValueError as e:
            parser.error(str(e))
    figpath = plot_evt_weight(set_name, panels=args.m, center=center,
                              outpath=args.o, label_angle=args.a, cmap=args.C)
    print(f'Saved {figpath}')


if __name__ == '__main__':
    main()
