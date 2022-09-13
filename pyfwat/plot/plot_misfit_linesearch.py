import pygmt
import glob
import numpy as np
import argparse
import re

class PlotMisfit():
    def __init__(self, modname, filtstr, col=26) -> None:
        self.modname = modname
        self.col = col
        self.filtstr = filtstr
        self.files = sorted(glob.glob('misfits/{}_step*{}*'.format(modname, filtstr)))
        self.read_misfit()        
    
    def read_misfit(self):
        self.chi = np.zeros(len(self.files))
        self.steplen = np.zeros_like(self.chi)
        for i, step_file in enumerate(self.files):
            chi = np.loadtxt(step_file, usecols=[self.col], unpack=True)
            self.chi[i] = np.mean(chi)
            self.steplen[i] = float(re.findall(r'step(.+?).ls', step_file)[0])

    def plot(self, outpath='./figures', color='255/50/50'):
        fig = pygmt.Figure()
        bound = np.min(self.chi)*0.1
        ylim = [np.min(self.chi)-bound, np.max(self.chi)+bound]
        xlim = [np.min(self.steplen)*0.8, np.max(self.steplen)+np.min(self.steplen)*0.2]
        fig.basemap(region=[xlim[0], xlim[1], ylim[0], ylim[1]],
                    projection="X5c/5c",
                    frame=['WSrt', 'xa0.01+l"Step length"', 'yaf+l"Misfit"'])
        fig.plot(x=self.steplen, y=self.chi, pen='0.7p')
        fig.plot(x=self.steplen, y=self.chi, style='c0.2c', color=color, pen='0.1p')
        fig.savefig('{}/misfit_{}_{}_linesearch.png'.format(outpath, self.modname, self.filtstr))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g.,M01', metavar='M??')
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050')
    parser.add_argument('-c', help='Color of markers, defaults to 255/25/25', metavar='color', default='255/50/50')
    parser.add_argument('-l', help='Column in misfit to plot, defaults to 28', metavar='col_num', type=int, default=28)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    pm = PlotMisfit(args.m, args.f, args.l)
    pm.plot(args.o, args.c)

