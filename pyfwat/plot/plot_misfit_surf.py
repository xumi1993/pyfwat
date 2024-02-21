import pygmt
import glob
import numpy as np
import argparse
from ..pario import readfwatpar


def read_misfit(it, filtstr, col=28):
    fs = glob.glob('misfits/M{:02d}.set*_{}_window_chi'.format(it, filtstr))
    if len(fs) == 0:
        return np.nan
    misfit = 0
    for f in fs:
        chi = np.loadtxt(f, usecols=[col], unpack=True)
        chi = chi[chi!=0]
        misfit += np.mean(chi)
    return misfit/len(fs)

class PlotMisfit():
    def __init__(self, iter_start, iter_end, col=28, all_band=True, norm=False, rf=False) -> None:
        self.iter_start = iter_start
        self.iter_end = iter_end
        self.col = col
        self.all_band = all_band
        if self.all_band:
            self.norm = False
        else:
            self.norm = norm
        self.colors = ['47/127/193', '150/195/125', '196/151/178', '73/108/136', 'olivedrab', 'burlywood', 'thistle']
        if rf:
            self.read_gaus()
        else:
            self.read_freq()
        self.read_misfit_all()

    def read_freq(self):
        self.periodmin = readfwatpar('fwat_params/FWAT.PAR', 'NOISE_SHORT_P')
        self.periodmax = readfwatpar('fwat_params/FWAT.PAR', 'NOISE_LONG_P')
        self.bandname = ['T{:03.0f}_T{:03.0f}'.format(pmin, pmax) for pmin, pmax in zip(self.periodmin, self.periodmax)]
        self.iters = np.arange(self.iter_start, self.iter_end+1)
        # self.misfits = np.array([read_misfit(it, self.filtstr, col) for it in self.iters])

    def read_gaus(self):
        self.gaus = readfwatpar('fwat_params/FWAT.PAR', 'RF_F0')
        self.bandname = ['F{:.1f}'.format(ff) for ff in self.gaus]
        self.iters = np.arange(self.iter_start, self.iter_end+1)

    def read_misfit_all(self):
        self.misfits = np.zeros([len(self.bandname), self.iters.size])
        for i, it in enumerate(self.iters):
            for j, band in enumerate(self.bandname):
                print(it, band, read_misfit(it, band, self.col))
                self.misfits[j, i] = read_misfit(it, band, self.col)
        self.misfit_mean = np.nanmean(self.misfits, axis=0)

    def plot(self, outpath='./figures', color='218/56/58', avg=False):
        # self.misfits /= np.max(self.misfits)
        fig = pygmt.Figure()
        bound = (self.iter_end-self.iter_start)*0.1
        if self.all_band:
            bound_ms = (np.nanmax(self.misfits)-np.nanmin(self.misfits))*0.1
            ylim = [np.nanmin(self.misfits)-bound_ms, np.nanmax(self.misfits)+bound_ms]
        else:
            if self.norm:
                self.misfit_mean /= np.max(self.misfit_mean)
            bound_ms = (np.max(self.misfit_mean)-np.min(self.misfit_mean))*0.1
            ylim = [np.min(self.misfit_mean)-bound_ms, np.max(self.misfit_mean)+bound_ms]
        fig.basemap(region=[self.iter_start-bound, self.iter_end+bound, *ylim],
                    projection="X10c/7c",
                    frame=['WSrt', 'xaf+l"Iteration"', 'yaf+l"Misfit"'])
        if self.all_band:
            for i, band in enumerate(self.bandname):
                if not avg:
                    fig.plot(x=self.iters, y=self.misfits[i], pen='0.5p')
                fig.plot(x=self.iters, y=self.misfits[i],  style='c0.25c', fill=self.colors[i], pen='0.1p', label=band)
            fig.legend()
        if avg:
            fig.plot(x=self.iters, y=self.misfit_mean, pen='0.5p')
            fig.plot(x=self.iters, y=self.misfit_mean, style='c0.25c', fill=color, pen='0.1p')
        fig.savefig('{}/misfit_M{:02d}_M{:02d}_multifreq.png'.format(outpath, self.iter_start, self.iter_end))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g., 0/10', metavar='iter_start/iter_end')
    parser.add_argument('-a', help='Plot average misfit', action='store_true',default=False)
    parser.add_argument('-l', help='Column in misfit to plot, defaults to 28', metavar='col_num', type=int, default=28)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    parser.add_argument('-n', help='Normalization when plotting mean misfits', action='store_true',default=False)
    parser.add_argument('-r', help='read rf misfits', action='store_true',default=False)
    args = parser.parse_args()
    its = [int(v) for v in args.m.split('/')]
    pm = PlotMisfit(its[0], its[1], col=args.l, all_band=True, norm=args.n, rf=args.r)
    pm.plot(args.o, avg=args.a)

