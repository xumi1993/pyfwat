"""Histograms of the measurement residuals at two iterations.

Command-line tool: ``fwat_plot_residual``.
"""

import pygmt
import numpy as np
import glob
import argparse
from ..io.misfit import PeriodBandMisfit
import os


class PlotRes():
    """Histograms of the measurement residuals at two iterations."""
    def __init__(self, iter_start, iter_end, filtstr):
        """Read the residuals of the measured windows at both iterations.

        :param iter_start: First iteration
        :type iter_start: int
        :param iter_end: Second iteration
        :type iter_end: int
        :param filtstr: Period band name in the misfit file names
        :type filtstr: str
        """
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.filtstr = filtstr
        self.read_res()
    
    def read_res(self):
        """Read the residuals of the measured windows into ``misfit_start`` and ``misfit_end``."""
        pbm = PeriodBandMisfit(self.iter_start, self.filtstr)
        self.misfit_start = pbm.misfits['residual'][pbm.misfits['imeas']!=0]
        pbm = PeriodBandMisfit(self.iter_end, self.filtstr)
        self.misfit_end = pbm.misfits['residual'][pbm.misfits['imeas']!=0]

    def plot(self, outpath='./figures', bar_scale=70):
        """Plot both histograms and save ``<outpath>/residual_M<start>_M<end>_<filtstr>.png``.

        :param outpath: Output directory, defaults to ``./figures``
        :type outpath: str, optional
        :param bar_scale: Number of bins across the largest absolute residual of
            the first iteration, defaults to 70
        :type bar_scale: int, optional
        """
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
    """Command-line entry point of ``fwat_plot_residual``."""
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/10', metavar='iter_start/iter_end')
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050', default='*')
    parser.add_argument('-n', help='number of bars', default=40, type=int)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    its = [int(v) for v in args.m.split('/')]
    pm = PlotRes(its[0],  its[1], args.f)
    pm.plot(args.o, bar_scale=args.n)
