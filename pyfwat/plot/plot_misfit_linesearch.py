import pygmt
import glob
import numpy as np
import argparse
import re
from ..pario import readfwatpar
import matplotlib.pyplot as plt

colors = ['47/127/193', '150/195/125', '196/151/178', '218/56/58']

def read_flts(simu_type, parfile='fwat_params/FWAT.PAR'):
    if simu_type != 'rf':
        nflt = readfwatpar(parfile, '{}_NUM_FILTER'.format(simu_type.upper()))
        shortp = readfwatpar(parfile, '{}_SHORT_P'.format(simu_type.upper()))
        longp = readfwatpar(parfile, '{}_LONG_P'.format(simu_type.upper()))
        flt_str = []
        for i in range(nflt):
            s = 'T{:03.0f}_T{:03.0f}'.format(shortp[i], longp[i])
            flt_str.append(s)
    else:
        nflt = readfwatpar(parfile, 'RF_NGAUSS')
        gaus = readfwatpar(parfile, 'RF_F0')
        flt_str = []
        for i in range(nflt):
            s = 'F{:.1f}'.format(gaus[i])
            flt_str.append(s)
    return flt_str


class PlotMisfitLS():
    def __init__(self, modname, filtstr, setname='ls', col=28) -> None:
        self.modname = modname
        self.col = col
        self.filtstr = filtstr
        self.files = sorted(glob.glob('misfits/{}_step*.{}_{}*'.format(modname, setname, filtstr)))
        # print(self.files)
        self.read_misfit()        
    
    def read_misfit(self):
        self.chi = np.zeros(len(self.files))
        self.steplen = np.zeros_like(self.chi)
        for i, step_file in enumerate(self.files):
            chi = np.loadtxt(step_file, usecols=[self.col], unpack=True)
            chi = chi[chi!=0.0]
            self.chi[i] = np.mean(chi)
            self.steplen[i] = float(re.findall(r'step(.+?).ls', step_file)[0])

    def plot(self, outpath='./figures', color='255/50/50'):
        fig = pygmt.Figure()
        bound = np.min(self.chi)*0.1
        ylim = [np.min(self.chi)-bound, np.max(self.chi)+bound]
        xlim = [np.min(self.steplen)*0.8, np.max(self.steplen)+np.min(self.steplen)*0.2]
        fig.basemap(region=[xlim[0], xlim[1], ylim[0], ylim[1]],
                    projection="X5c/5c",
                    frame=['WSrt', 'xa+l"Step length"', 'yaf+l"Misfit"'])
        fig.plot(x=self.steplen, y=self.chi, pen='0.7p')
        fig.plot(x=self.steplen, y=self.chi, style='c0.2c', fill=color, pen='0.1p')
        fig.savefig('{}/misfit_{}_{}_linesearch.png'.format(outpath, self.modname, self.filtstr))


def plot_all(model, simu_type, setname='ls', col=28, outpath='./figures'):
    flts = read_flts(simu_type)
    chi =  []
    steplen = []
    fig = pygmt.Figure()
    for i, flt in enumerate(flts):
        pm = PlotMisfitLS(model, flt, setname=setname, col=col)
        chi.append(pm.chi)
        steplen.append(pm.steplen)
    boundx = (pm.steplen[-1]-pm.steplen[0])*0.1
    ymax = np.max(np.array(chi))
    ymin = np.min(np.array(chi))
    boundy = (ymax-ymin)*0.1
    fig.basemap(
        region=[pm.steplen[0]-boundx, pm.steplen[-1]+boundx, ymin-boundy, ymax+boundy],
        projection='X8c/6c',
        frame=['WSrt', 'xa+l"Step length"', 'yaf+l"Misfit"'],
    )
    for i, flt in enumerate(flts):
        fig.plot(x=steplen[i], y=chi[i], style='c0.2c', fill=colors[i], label=flt)
    mean_chi = np.mean(np.array(chi), axis=0)
    fig.plot(x=pm.steplen, y=mean_chi, pen='1p')
    fig.plot(x=pm.steplen, y=mean_chi, style='c0.2c', fill='255/50/50')
    if len(flts) > 1:
        fig.legend()
    fig.savefig('{}/misfit_{}_{}_linesearch.png'.format(outpath, model, simu_type))


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-m', help='start and end iteration nunbers e.g.,M01', metavar='M??', required=True)
    parser.add_argument('-t', help='simulation type in noise, tele, rf and leq', metavar='simu_type', required=True)
    parser.add_argument('-s', help='Source set name, defaults to "ls"', metavar='setname', default='ls')
    parser.add_argument('-l', help='Column in misfit to plot, defaults to 28', metavar='col_num', type=int, default=28)
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    plot_all(args.m, args.t, args.s, args.l, args.o)
    # pm = PlotMisfit(args.m, args.f, args.l)
    # pm.plot(args.o, args.c)

