import pygmt
import glob
import numpy as np
import argparse


def read_misfit(it, filtstr, col=28):
    fs = glob.glob('misfits/M{:02d}.set*_{}_window_chi'.format(it, filtstr))
    misfit = 0
    count = 0
    for f in fs:
        chi = np.loadtxt(f, usecols=[col], unpack=True)
        chi = chi[chi!=0.0]
        count += chi.size
        misfit += np.mean(chi)
    print('A total of {} traces for {}th iter'.format(count, it))
    return misfit/len(fs)

class PlotMisfit():
    def __init__(self, iter_start, iter_end, filtstr, col=26) -> None:
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.col = col
        self.filtstr = filtstr
        self.iters = np.arange(self.iter_start, self.iter_end+1)
        self.misfits = np.array([read_misfit(it, self.filtstr, col) for it in self.iters])
    
    def plot(self, outpath='./figures', color='255/25/25'):
        self.misfits /= np.max(self.misfits)
        fig = pygmt.Figure()
        bound = (self.iter_end-self.iter_start)*0.1
        bound_ms = (np.max(self.misfits)-np.min(self.misfits))*0.1
        fig.basemap(region=[self.iter_start-bound, self.iter_end+bound, np.min(self.misfits)-bound_ms, 1+bound_ms],
                    projection="X10c/5c",
                    frame=['WSrt', 'xa1f1+l"Iteration"', 'yaf+l"Misfit"'])
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
    its = [int(v) for v in args.m.split('/')]
    pm = PlotMisfit(its[0], its[1], args.f, args.l)
    pm.plot(args.o, args.c)

