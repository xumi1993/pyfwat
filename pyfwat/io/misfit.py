import pandas as pd
import numpy as np
import glob
from .. import MISFIT_PATH

class PeriodBandMisfit():
    def __init__(self, it, band_name, evtid='*') -> None:
        fs = glob.glob(f'{MISFIT_PATH}/M{it:02d}.{evtid}*_{band_name}_window_chi')
        self.sum_chi = 0.
        self.misfits = []
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
        self.sum_chi = self.misfits[self.misfits['imeas']!=0]['misfit'].sum()
        self.mean_chi = self.misfits[self.misfits['imeas']!=0]['misfit'].mean()