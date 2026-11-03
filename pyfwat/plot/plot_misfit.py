"""Normalized misfit versus iteration for a period band.

Command-line tool: ``fwat_plot_misfit``.
"""

import pygmt
import glob
import numpy as np
import argparse
from ..io.misfit import PeriodBandMisfit
import os


class PlotMisfit():
    """Mean window misfit of a period band over a range of iterations."""
    def __init__(self, iter_start, iter_end, filtstr, col=28) -> None:
        """Read the mean misfit of each iteration and print the total misfit.

        :param iter_start: First iteration
        :type iter_start: int
        :param iter_end: Last iteration
        :type iter_end: int
        :param filtstr: Period band name in the misfit file names, ``'*'`` for all
        :type filtstr: str
        :param col: Not used, defaults to 28
        :type col: int, optional
        """
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.col = col
        self.filtstr = filtstr
        self.iters = np.arange(self.iter_start, self.iter_end+1)
        self.misfits = np.zeros(self.iters.size)
        for it in self.iters:
            pbm = PeriodBandMisfit(it, self.filtstr)
            print(f'A total misfit of {pbm.sum_chi:.6f} for {it}th iter')
            self.misfits[it-self.iter_start] = pbm.mean_chi
    
    def plot(self, outpath='./figures', color='255/25/25'):
        """Plot the misfit normalized by its maximum versus iteration.

        The figure is ``<outpath>/misfit_M<start>_M<end>_<filtstr>.png``.

        :param outpath: Output directory, defaults to ``./figures``
        :type outpath: str, optional
        :param color: Marker color in GMT format, defaults to ``'255/25/25'``
        :type color: str, optional
        """
        self.misfits /= np.max(self.misfits)
        fig = pygmt.Figure()
        bound = (self.iter_end-self.iter_start)*0.1
        bound_ms = (np.max(self.misfits)-np.min(self.misfits))*0.1
        fig.basemap(region=[self.iter_start-bound, self.iter_end+bound, np.min(self.misfits)-bound_ms, 1+bound_ms],
                    projection="X10c/5c",
                    frame=['WSrt', 'xa1f1+lIteration', 'yaf+lMisfit'])
        fig.plot(x=self.iters, y=self.misfits, pen='0.5p')
        fig.plot(x=self.iters, y=self.misfits, style='c0.25c', fill=color, pen='0.1p')
        os.makedirs(outpath, exist_ok=True)
        fig.savefig('{}/misfit_M{:02d}_M{:02d}_{}.png'.format(outpath, self.iter_start, self.iter_end, self.filtstr))


def main():
    """Command-line entry point of ``fwat_plot_misfit``."""
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/10', metavar='iter_start/iter_end')
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050', default='*')
    parser.add_argument('-c', help='Color of markers, defaults to 255/25/25', metavar='color', default='255/25/25')
    parser.add_argument('-l', help='Column in misfit to plot, defaults to 28', metavar='col_num', type=int, default=28)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    os.makedirs(args.o, exist_ok=True)
    its = [int(v) for v in args.m.split('/')]
    pm = PlotMisfit(its[0], its[1], args.f, args.l)
    pm.plot(args.o, args.c)

