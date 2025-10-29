import pygmt
import numpy as np
import glob
import argparse
from ..io.misfit import PeriodBandMisfit
import os


class PlotRes():
    def __init__(self, iter_start, iter_end, filtstr):
        """Plot residual histogram for a given iteration.
        Parameters
        ----------
        iter_start : int
            Start iteration number.
        filtstr : str
            Period band name in the filename.
        """
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.filtstr = filtstr
        self.read_misfit()
    
    def read_misfit(self):
        pbm = PeriodBandMisfit(self.iter_start, self.filtstr)
        self.misfit_start = pbm.misfits['residual'][pbm.misfits['imeas']!=0]
        pbm = PeriodBandMisfit(self.iter_end, self.filtstr)
        self.misfit_end = pbm.misfits['residual'][pbm.misfits['imeas']!=0]

    def plot(self, outpath='./figures', bar_scale=70):
        fig = pygmt.Figure()
        mismax = np.max(np.abs(self.misfit_start))
        nummax = 4*self.misfit_end.size/bar_scale
        fig.histogram(
            data=self.misfit_start,
            series=mismax/bar_scale,
            fill='red',
            projection='X6c/4c',
            histtype=0,
            center=True,
            transparency=60,
            region=[-int(mismax+0.5), int(mismax+0.5), 0, nummax],
            label='M{:02d}'.format(self.iter_start)
        )
        fig.histogram(data=self.misfit_end, 
                    series=mismax/bar_scale,
                    fill='blue',
                    histtype=0,
                    center=True,
                    transparency=60,
                    label='M{:02d}'.format(self.iter_end))
        fig.legend()
        fig.basemap(frame=['WSne', 'xaf+lResidual (s)', 'yaf+lNumber'])
        if self.iter_end is not None:
            fig.savefig('{}/residual_M{:02d}_M{:02d}_{}.png'.format(outpath, self.iter_start, self.iter_end, self.filtstr))
        else:
            fig.savefig('{}/residual_M{:02d}_{}.png'.format(outpath, self.iter_start, self.filtstr))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/10', metavar='iter_start/iter_end')
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050', default='*')
    parser.add_argument('-n', help='number of bars', default=40, type=int)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    its = [int(v) for v in args.m.split('/')]
    pm = PlotRes(its[0],  its[1], args.f)
    pm.plot(args.o, bar_scale=args.n)