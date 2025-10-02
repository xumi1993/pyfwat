import pygmt
import glob
import numpy as np
import argparse
from ..io.misfit import PeriodBandMisfit
import os


def read_misfit(it, filtstr, col=28):
    fs = glob.glob('misfits/M{:02d}.*_{}_window_chi'.format(it, filtstr))
    misfit = 0
    count = 0
    sum_chi = 0.
    for f in fs:
        try:
            chi = np.loadtxt(f, usecols=[col], unpack=True)
        except Exception as e:
            raise ValueError(f'error in reading {f}: {e}')
        chi = chi[chi!=0.0]
        count += chi.size
        misfit += np.mean(chi)
        sum_chi += np.sum(chi)
    print('A total misfit of {:.6f} for {}th iter'.format(sum_chi, it))
    return misfit/len(fs)

class PlotMisfit():
    def __init__(self, iter_start, iter_end, filtstr, col=28) -> None:
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
        self.misfits /= np.max(self.misfits)
        fig = pygmt.Figure()
        bound = (self.iter_end-self.iter_start)*0.1
        bound_ms = (np.max(self.misfits)-np.min(self.misfits))*0.1
        fig.basemap(region=[self.iter_start-bound, self.iter_end+bound, np.min(self.misfits)-bound_ms, 1+bound_ms],
                    projection="X10c/5c",
                    frame=['WSrt', 'xa1f1+lIteration', 'yaf+lMisfit'])
        fig.plot(x=self.iters, y=self.misfits, pen='0.5p')
        fig.plot(x=self.iters, y=self.misfits, style='c0.25c', fill=color, pen='0.1p')
        fig.savefig('{}/misfit_M{:02d}_M{:02d}_{}.png'.format(outpath, self.iter_start, self.iter_end, self.filtstr))


def main():
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

