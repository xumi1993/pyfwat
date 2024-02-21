import pygmt
from pygmt.clib import Session
import numpy as np
import subprocess
import obspy
from os import remove
import argparse
import glob
from os.path import basename
from .plot_rf_fit import post_plot
import os

def pre_plot(modelname, evtid, comp, fltstr):
    # with open('src_rec/sources_set{}.dat'.format(setid)) as f:
    #     evtid = f.readlines()[0].strip().split()[0]
    s = ''
    s += 'saclst knetwk kstnm b e dist f solver/{}.set*/{}/OUTPUT_FILES/*{}.obs.sac.{} > saclst_dat\n'.format(modelname, evtid, comp,fltstr)
    s += "awk '{{print $1}}' saclst_dat> saclst_dat_plot\n"
    s += 'awk \'{print FNR" a "$2"."$3}\' saclst_dat > yticklabel.txt\n'
    s += 'ls solver/{}.set*/{}/OUTPUT_FILES/*{}.syn.sac.{} > saclst_syn\n'.format(modelname, evtid, comp,fltstr)
    subp = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
    subp.communicate(s.encode())
    xlim_all = np.loadtxt('saclst_dat', usecols=[3,4])
    xlim = [0, np.max(xlim_all[:, 1])]
    ylim = [0.9*np.min(np.loadtxt('saclst_dat', usecols=[5])), 
            1.1*np.max(np.loadtxt('saclst_dat', usecols=[5]))]
    num_sta = xlim_all.shape[0]
    return xlim, ylim


def plot_noise_fit(modelname, evtid, fltstr, comp='Z', xlim=None, outpath='./figures',
                  enf=0.001):
    xlim_auto, ylim = pre_plot(modelname, evtid, comp, fltstr)
    # fktimes = read_time_window(evtid)
    # if not exists(par_file):
    #     raise FileNotFoundError('No such file of {}'.format(par_file))
    # time_before = readfwatpar(par_file, 'TW_BEFORE')
    # time_after = readfwatpar(par_file, 'TW_AFTER')
    if xlim is None:
        xlim = xlim_auto
    fig = pygmt.Figure()
    pygmt.config(FONT_TITLE='14p',
                 MAP_GRID_PEN='0.3p,gray')
    # fig.basemap(region=[*xlim, *ylim], projection='X10c/10c',
    #             frame=['xafg+l"Time (s)"', '+t"{}, Event: {}"'.format(modelname, evtid), 'pycyticklabel.txt'])
    fig.basemap(region=[*xlim, *ylim], projection='X10c/10c',frame=['xafg+l"Time (s)"', 'yaf+l"Distance (km)"'])
    with Session() as lib:
        lib.call_module("sac", "saclst_dat_plot -Ek -M{} -W0.6p".format(enf))
        lib.call_module("sac", "saclst_syn -Ek -M{} -W0.6p,255/25/25".format(enf))
    fig.savefig('{}/{}.set{}_noise_{}_{}_fit.png'.format(outpath, modelname, evtid, comp, fltstr))
    post_plot()


def main():
    parser = argparse.ArgumentParser('Plot noise fitting.')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Event id', metavar='evtid')
    parser.add_argument('-f', help='Band name ', metavar='bandname')
    parser.add_argument('-c', help='Component name, defaults to Z', default='Z', metavar='comp')
    parser.add_argument('-x', help='x-axis limits, defaults to -5/30, NOTE: donnot insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 0.05', type=float, default=0.4, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()

    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = None
    plot_noise_fit(args.m, args.s, args.f, comp=args.c, xlim=xlim, outpath=args.o, enf=args.e)