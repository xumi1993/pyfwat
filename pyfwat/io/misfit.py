"""Read the window misfit tables in ``misfits/`` for an iteration and period band."""

import pandas as pd
import numpy as np
import glob
from .. import MISFIT_PATH

class PeriodBandMisfit():
    """Window misfits of an iteration and period band.

    Reads the ``M<it>.<evtid>*_<band_name>_window_chi`` tables. ``misfits`` is a
    DataFrame with the columns ``netwk``, ``stnm``, ``chan``, ``imeas``,
    ``tstart``, ``tend``, ``residual`` and ``misfit``; ``sum_chi`` and
    ``mean_chi`` are the sum and mean of the misfit over measured windows
    (``imeas != 0``).
    """
    def __init__(self, it, band_name, evtid='*', pathname=None) -> None:
        """:param it: Iteration number
        :type it: int
        :param band_name: Period band name in the file names, e.g. ``T005_T050``
        :type band_name: str
        :param evtid: Event id pattern, defaults to ``'*'`` (all events)
        :type evtid: str, optional
        :param pathname: Directory of the misfit tables, defaults to ``misfits``
        :type pathname: str, optional
        :raises FileNotFoundError: If no misfit table matches
        :raises ValueError: If ``pathname`` is not a string or a table cannot be read
        """
        if pathname is None:
            path = MISFIT_PATH
        elif isinstance(pathname, str):
            path = pathname
        else:
            raise ValueError(f'Path name should be string, but {type(pathname)} got.')
        fs = glob.glob(f'{path}/M{it:02d}.{evtid}*_{band_name}_window_chi')
        self.sum_chi = 0.
        self.misfits = []
        if not fs:
            raise FileNotFoundError(f'No misfit files found for iteration {it}, event {evtid}, band {band_name}')
        for f in fs:
            try:
                self.misfits.append(pd.read_csv(f, sep=r'\s+', header=None))
            except Exception as e:
                raise ValueError(f'error in reading {f}: {e}')
        self.misfits = pd.concat(self.misfits, axis=0)
        # define name of self.misfits columns
        self.misfits.columns = [
            'netwk', 'stnm', 'chan', 'imeas',
            'tstart', 'tend', 'residual', 'misfit',
        ]
        self.misfits = self.misfits.astype({
            'netwk': 'string',
            'stnm': 'string',
            'chan': 'string',
            'imeas': 'int64',
            'tstart': 'float64',
            'tend': 'float64',
            'residual': 'float64',
            'misfit': 'float64',
        })
        self.sum_chi = self.misfits[self.misfits['imeas']!=0]['misfit'].sum()
        self.mean_chi = self.misfits[self.misfits['imeas']!=0]['misfit'].mean()
