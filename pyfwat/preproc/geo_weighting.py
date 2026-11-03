"""Assign weights to teleseismic / receiver-function events.

Events clustered in back-azimuth/ray-parameter space (``baz``) or in epicentral
location (``loc``) are down-weighted by the inverse of a Gaussian-kernel
density. The raw weights are then linearly rescaled to ``[wmin, wmax]`` and
written to the last column of ``src_rec/sources_<set_name>.dat``.
"""
import argparse
from pathlib import Path

import numpy as np

from ..utils.distaz import distaz
from ..utils.geo import sind, skm2srad
from ..utils.pario import readfkpar

DEFAULT_COEF = {'baz': 0.5, 'loc': 0.25}
SOURCE_COLUMNS = 'evtid evla evlo evdp evbur weight'


def _check_inputs(x, y, names, coef):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or x.size == 0 or y.shape != x.shape:
        raise ValueError(f'{names} must be nonempty 1-D arrays of equal length')
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError(f'{names} must be finite')
    if not np.isfinite(coef) or coef <= 0:
        raise ValueError('coef must be finite and positive')
    return x, y


def _density_weight(dis_mat, delta_ref):
    """Inverse Gaussian-kernel density of each event; equal weights if all events coincide."""
    if delta_ref == 0:
        return np.full(dis_mat.shape[0], 1.0 / dis_mat.shape[0])
    return 1.0 / np.sum(np.exp(-(dis_mat / delta_ref)**2), axis=1)


def gen_weight(baz, rayp, coef=0.5):
    """Raw density weights from back-azimuth (deg) and ray parameter (s/km).

    The back-azimuth difference wraps around 360 deg, so events at 355 and
    5 deg are treated as neighbours. The kernel width is ``coef`` times the
    mean inter-event distance.
    """
    baz, rayp = _check_inputs(baz, rayp, 'baz and rayp', coef)
    dbaz = np.abs(baz[:, None] - baz[None, :]) % 360
    dbaz = np.minimum(dbaz, 360 - dbaz)
    rayp = skm2srad(rayp)
    dis_mat = np.hypot(dbaz, rayp[:, None] - rayp[None, :])
    return _density_weight(dis_mat, np.mean(dis_mat) * coef)


def gen_weight_loc(evla, evlo, coef=0.25):
    """Raw density weights from event latitude and longitude (deg).

    The kernel width is ``coef`` times the standard deviation of the
    inter-event epicentral distances.
    """
    evla, evlo = _check_inputs(evla, evlo, 'evla and evlo', coef)
    dis_mat = np.array([distaz(la, lo, evla, evlo).delta for la, lo in zip(evla, evlo)])
    return _density_weight(dis_mat, np.std(dis_mat) * coef)


def rescale_weight(weight, wmin=0.3, wmax=1.0):
    """Linearly map raw weights to [wmin, wmax]; uniform weights map to wmax."""
    weight = np.asarray(weight, dtype=float)
    if not np.isfinite([wmin, wmax]).all() or wmin > wmax:
        raise ValueError('weight bounds must be finite and wmin <= wmax')
    span = np.ptp(weight)
    if span > 0:
        return wmin + (wmax - wmin) * (weight - weight.min()) / span
    return np.full_like(weight, wmax)


def read_fkmodel(path):
    """Return back-azimuth (deg) and ray parameter (s/km) of an FKmodel.

    The ray parameter is computed from TAKE_OFF and the velocity of the
    half space (the last LAYER), using Vp or Vs according to INCIDENT_WAVE.
    """
    model = readfkpar(path, 'LAYER')
    if model.shape[0] == 0:
        raise ValueError(f'{path}: no LAYER found')
    wave = readfkpar(path, 'INCIDENT_WAVE').lower()
    if wave not in ('p', 's'):
        raise ValueError(f'{path}: INCIDENT_WAVE must be p or s, got {wave}')
    vel = model[-1, 2] if wave == 'p' else model[-1, 3]  # m/s
    baz = readfkpar(path, 'BACK_AZIMUTH')
    rayp = sind(readfkpar(path, 'TAKE_OFF')) / (vel / 1000)
    return baz, rayp


def read_sources(fname):
    """Read a sources file as lists of string fields, keeping the original text."""
    rows = []
    with open(fname) as f:
        for lineno, line in enumerate(f, 1):
            fields = line.split()
            if not fields:
                continue
            if len(fields) != 6:
                raise ValueError(f'{fname}:{lineno}: expected 6 columns '
                                 f'({SOURCE_COLUMNS}), got {len(fields)}')
            rows.append(fields)
    if not rows:
        raise ValueError(f'{fname}: no events found')
    return rows


def find_set_name(src_rec='src_rec'):
    """Return the set name of the only ``sources_<set_name>.dat`` in ``src_rec``."""
    names = sorted(p.name[len('sources_'):-len('.dat')]
                   for p in Path(src_rec).glob('sources_*.dat'))
    if len(names) == 1:
        return names[0]
    if not names:
        raise ValueError(f'No sources_*.dat found in {src_rec}')
    raise ValueError(f'Multiple sources files found in {src_rec}, '
                     f'specify a set name from: {", ".join(names)}')


def assign_weight(set_name=None, method='baz', coef=None, wmin=0.3, wmax=1.0,
                  src_rec='src_rec', outfile=None):
    """Compute weights of events in ``<src_rec>/sources_<set_name>.dat`` and write them.

    :param set_name: Set name of the sources file, defaults to the only
        ``sources_*.dat`` in ``src_rec``
    :param method: ``'baz'`` uses BACK_AZIMUTH and TAKE_OFF in ``<src_rec>/FKmodel_<evtid>``;
        ``'loc'`` uses evla and evlo in the sources file
    :param coef: Kernel width coefficient, defaults to 0.5 for baz and 0.25 for loc
    :param wmin: Minimum of output weights
    :param wmax: Maximum of output weights
    :param src_rec: Directory of the sources and FKmodel files
    :param outfile: Output path, defaults to overwrite the input sources file
    :return: Rescaled weights in the order of events in the sources file
    """
    if method not in DEFAULT_COEF:
        raise ValueError(f'method must be one of {list(DEFAULT_COEF)}')
    if coef is None:
        coef = DEFAULT_COEF[method]
    if set_name is None:
        set_name = find_set_name(src_rec)
    src_rec = Path(src_rec)
    srcfile = src_rec / f'sources_{set_name}.dat'
    rows = read_sources(srcfile)
    if method == 'baz':
        baz, rayp = np.array([read_fkmodel(src_rec / f'FKmodel_{row[0]}') for row in rows]).T
        weight = gen_weight(baz, rayp, coef)
    else:
        evla, evlo = np.array([row[1:3] for row in rows], dtype=float).T
        weight = gen_weight_loc(evla, evlo, coef)
    weight = rescale_weight(weight, wmin=wmin, wmax=wmax)
    with open(srcfile if outfile is None else outfile, 'w') as f:
        for row, w in zip(rows, weight):
            f.write(' '.join(row[:5] + [f'{w:.4f}']) + '\n')
    return weight


def main():
    parser = argparse.ArgumentParser(
        description='Assign weights to events in src_rec/sources_<set_name>.dat according to '
                    'their density in back-azimuth/ray-parameter (baz) or epicentral location (loc). '
                    'Weights are written to the last column.')
    parser.add_argument('-s', help='Set name, required only if there are multiple '
                        'src_rec/sources_*.dat', metavar='set_name', default=None)
    parser.add_argument('-m', help='Weighting method, baz reads BACK_AZIMUTH and TAKE_OFF from '
                        'src_rec/FKmodel_<evtid>, loc uses evla and evlo, defaults to baz',
                        choices=list(DEFAULT_COEF), default='baz')
    parser.add_argument('-c', help='Coefficient of the Gaussian kernel width relative to the mean (baz) '
                        'or std (loc) of inter-event distances, defaults to 0.5 for baz and 0.25 for loc',
                        type=float, default=None, metavar='coef')
    parser.add_argument('-w', help='Range of output weights, defaults to 0.3/1.0',
                        default='0.3/1.0', metavar='wmin/wmax')
    parser.add_argument('-o', help='Output file, defaults to overwrite src_rec/sources_<set_name>.dat',
                        default=None, metavar='outfile')
    args = parser.parse_args()
    try:
        wmin, wmax = [float(v) for v in args.w.split('/')]
    except ValueError:
        parser.error('-w must be in the format of wmin/wmax')
    set_name = args.s
    if set_name is None:
        try:
            set_name = find_set_name()
        except ValueError as e:
            parser.error(str(e))
        print(f'Using src_rec/sources_{set_name}.dat')
    weight = assign_weight(set_name, method=args.m, coef=args.c, wmin=wmin, wmax=wmax, outfile=args.o)
    print(f'Assigned weights to {weight.size} events: min={weight.min():.4f}, max={weight.max():.4f}')


if __name__ == '__main__':
    main()
