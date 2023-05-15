import pygmt
import numpy as np
import glob
import argparse


def _read_misfit(it, filtstr, col=28):
    misfit = np.array([])
    fs = glob.glob('misfits/M{:02d}.set*_{}_window_chi'.format(it, filtstr))
    for f in fs:
        chi = np.loadtxt(f, usecols=[col], unpack=True)
        misfit = np.append(misfit, chi)
    misfit = misfit[misfit != 0.0]
    return misfit

class PlotRes():
    def __init__(self, iter_start, filtstr, iter_end=None, col=28):
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.col = col
        self.filtstr = filtstr
        self.iters = [self.iter_start, self.iter_end]
        self.read_misfit()
    
    def read_misfit(self):
        self.misfit_start = _read_misfit(self.iter_start, self.filtstr, col=self.col)
        if self.iter_end is not None:
            self.misfit_end = _read_misfit(self.iter_end, self.filtstr, col=self.col)

    def plot(self, outpath='./figures', bar_scale=70):
        fig = pygmt.Figure()
        mismax = np.max(np.abs(self.misfit_start))
        nummax = 2*self.misfit_start.size/bar_scale
        fig.histogram(
            data=self.misfit_start,
            series = mismax/bar_scale,
            fill='red',
            projection='X6c/4c',
            histtype=0,
            transparency=60,
            region=[-int(mismax+0.5), int(mismax+0.5), 0, nummax]
        )
        if self.iter_end is not None:
            fig.histogram(data=self.misfit_end, 
                        series = mismax/bar_scale,
                        fill='blue',
                        histtype=0,
                        transparency=60)
        fig.basemap(frame=['WSne', 'xaf+l"Residual"', 'yaf+l"Number"'])
        if self.iter_end is not None:
            fig.savefig('{}/residual_M{:02d}_M{:02d}_{}.png'.format(outpath, self.iter_start, self.iter_end, self.filtstr))
        else:
            fig.savefig('{}/residual_M{:02d}_{}.png'.format(outpath, self.iter_start, self.filtstr))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/10', metavar='iter_start/iter_end')
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050', default='*')
    parser.add_argument('-n', help='number of bars', default=40, type=int)
    # parser.add_argument('-c', help='Color of markers, defaults to 255/25/25', metavar='color', default='255/25/25')
    parser.add_argument('-l', help='Column in misfit to plot, defaults to 12', metavar='col_num', type=int, default=12)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    try:
        its = [int(v) for v in args.m.split('/')]
        pm = PlotRes(its[0], args.f, its[1], col=args.l)
    except:
        its = [int(args.m)]
        pm = PlotRes(its[0], args.f, col=args.l)
    
    pm.plot(args.o, bar_scale=args.n)