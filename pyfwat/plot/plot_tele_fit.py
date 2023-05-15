from genericpath import exists
import pygmt
import subprocess
import numpy as np
from os import remove
from pygmt.clib import Session
from .plot_rf_fit import post_plot
from ..pario import readfwatpar
import glob
import re
import argparse


def pre_plot(modelname, evtid, comp):
    # with open('src_rec/sources_set{}.dat'.format(setid)) as f:
    #     evtid = f.readlines()[0].strip().split()[0]
    s = ''
    s += 'saclst knetwk kstnm b e f solver/{}.set*/{}/OUTPUT_FILES/wdat.*.*{}.sac.* > saclst_dat\n'.format(modelname, evtid, comp)
    s += "awk '{{print $1}}' saclst_dat> saclst_dat_plot\n"
    s += 'awk \'{print FNR" a "$2"."$3}\' saclst_dat > yticklabel.txt\n'
    s += 'ls solver/{}.set*/{}/OUTPUT_FILES/wsyn.*.*{}.sac.* > saclst_syn\n'.format(modelname, evtid, comp)
    subp = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
    subp.communicate(s.encode())
    xlim_all = np.loadtxt('saclst_dat', usecols=[3,4])
    xlim = [0, np.max(xlim_all[:, 1])]
    num_sta = xlim_all.shape[0]
    return num_sta, xlim

def read_time_window(evtid):
    with open('saclst_dat') as f:
        staname = [[line.split()[1], line.split()[2]] for line in f.readlines()]
    with open('src_rec/FKtimes_{}'.format(evtid)) as f:
        fktimes_str = f.read()
    fktimes = np.zeros(len(staname))
    for i, sta in enumerate(staname):
        fktimes[i] = float(re.findall(r'{}\s+{}\s+(.+?)\s+'.format(sta[0], sta[1]), fktimes_str)[0])
    return fktimes

def plot_tele_fit(modelname, evtid, comp='R', xlim=None, outpath='./figures',
                  enf=0.05, par_file = 'fwat_params/FWAT.PAR'):
    num_sta, xlim_auto = pre_plot(modelname, evtid, comp)
    fktimes = read_time_window(evtid)
    if not exists(par_file):
        raise FileNotFoundError('No such file of {}'.format(par_file))
    time_before = readfwatpar(par_file, 'TELE_TW_BEFORE')
    time_after = readfwatpar(par_file, 'TELE_TW_AFTER')
    if xlim is None:
        xlim = xlim_auto
    fig = pygmt.Figure()
    pygmt.config(FONT_TITLE='14p',
                 MAP_GRID_PEN='0.3p,gray')
    fig.basemap(region=[*xlim, -1, num_sta+2], projection='x0.2c/0.3c',
                frame=['xa5f1g5+l"Time (s)"', '+t"{}, Event: {}"'.format(modelname, evtid), 'pycyticklabel.txt'])
    with Session() as lib:
        lib.call_module("sac", "saclst_dat_plot -En1 -M{} -W1p".format(enf))
        lib.call_module("sac", "saclst_syn -En1 -M{} -W1p,255/25/25".format(enf))
    for i, fktime in enumerate(fktimes):
        fig.plot(x=fktime-time_before, y=i+1, style='y0.5c', pen='1.2p,0/105/167')
        fig.plot(x=fktime+time_after, y=i+1, style='y0.5c', pen='1.2p,0/105/167')
        fig.plot(x=fktime, y=i+1, style='y0.5c', pen='1.2p,green3')
    fig.savefig('{}/{}.evt{}_tele_{}_fit.png'.format(outpath, modelname, evtid, comp))
    post_plot()


def main():
    parser = argparse.ArgumentParser('Plot teleseismic fitting. read '
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/wdat* for data,'
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/wsyn* for syn')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Evt id', metavar='evtid')
    parser.add_argument('-c', help='Component name to plot R or Z avaliable, defaults to Z', default='Z', metavar='component')
    parser.add_argument('-x', help='x-axis limits, defaults to read b and e from sac files, NOTE: donnot insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 0.015', type=float, default=0.015, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()

    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = None
    plot_tele_fit(args.m, args.s, comp=args.c, xlim=xlim, outpath=args.o, enf=args.e)