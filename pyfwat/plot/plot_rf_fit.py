import pygmt
import subprocess
from os import remove
from pygmt.clib import Session
from ..utils.pario import readfwatpar
from .. import SOLVER_PATH
import argparse
import obspy
import os


def plot_rf_fit(modelname, evtid, gauss, xlim=None, outpath='./figures', enf=0.05, yunit=0.2):
    fs_dat = obspy.read(f'{SOLVER_PATH}/{modelname}.rf/{evtid}/OUTPUT_FILES/obs.*.F{gauss:3.1f}')
    fs_syn = obspy.read(f'{SOLVER_PATH}/{modelname}.rf/{evtid}/OUTPUT_FILES/syn.*.F{gauss:3.1f}')
    num_sta = len(fs_dat)
    para = readfwatpar()
    if xlim is None:
        xlim = para['TELE']['TIME_WIN']
    fig = pygmt.Figure()
    pygmt.config(FONT_TITLE='14p',
                 MAP_GRID_PEN='0.3p,gray')
    ysize = (num_sta+3) * yunit
    fig.basemap(region=[*xlim, 0, num_sta+3], projection=f'X8c/{ysize}c',
                frame=['xa5f1g5+lTime after P (s)', 'ya1' , 'wSet+t{}, Event: {}'.format(modelname, evtid)])
    for i, trdat in enumerate(fs_dat):
        times = trdat.times() + trdat.stats.sac.b
        amp = trdat.data * enf + i + 1
        fig.plot(x=times, y=amp, pen='1.2p')
        trsyn = fs_syn.select(station=trdat.stats.station, network=trdat.stats.network)[0]
        times = trsyn.times() + trsyn.stats.sac.b
        amp = trsyn.data * enf + i + 1
        fig.plot(x=times, y=amp, pen='1.2p,255/25/25')
        staname = f'{trdat.stats.sac.knetwk}.{trdat.stats.station}'
        fig.text(x=xlim[0], y=i+1, text=staname, font='7p,Helvetica,black', justify='RM', offset='-0.1c/0c', no_clip=True)
    fig.savefig('{}/{}_{}_rf_fit_F{}.png'.format(outpath, modelname, evtid, gauss))

def main():
    parser = argparse.ArgumentParser('Plot rf fitting. read data/evtid/*F{{gauss}}.rf.sac for data,'
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/syn.*.F{{gauss}} for syn')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Event id', metavar='evtid')
    parser.add_argument('-g', help='Gaussian factor, should be the same as in filename', metavar='gauss', type=float)
    parser.add_argument('-x', help='x-axis limits, defaults to -5/30, NOTE: donnot insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 5', type=float, default=5, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()
    os.makedirs(args.o, exist_ok=True)
    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = None
    plot_rf_fit(args.m, args.s, args.g, xlim=xlim, outpath=args.o, enf=args.e)
    