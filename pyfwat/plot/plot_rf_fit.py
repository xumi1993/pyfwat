import pygmt
import subprocess
from os import remove
from pygmt.clib import Session
from ..pario import readfwatpar
import argparse


def pre_plot(modelname, evtid, gauss):
    s = ''
    s += 'saclst knetwk kstnm f fwat_data/{}/*.F{}.rf.sac > saclst_dat\n'.format(evtid, gauss)
    s += "awk '{{print $1}}' saclst_dat> saclst_dat_plot\n"
    s += 'awk \'{print FNR" a "$2"."$3}\' saclst_dat > yticklabel.txt\n'
    s += 'ls solver/{}.*/{}/OUTPUT_FILES/syn.*.F{} > saclst_syn\n'.format(modelname, evtid, gauss)
    subp = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
    subp.communicate(s.encode())
    with open('saclst_dat') as f:
        num_sta = len(f.readlines())
    return num_sta

def post_plot():
    remove('saclst_dat')
    remove('saclst_dat_plot')
    remove('yticklabel.txt')
    remove('saclst_syn')

def plot_rf_fit(modelname, evtid, gauss, xlim=None, outpath='./figures', enf=0.05):
    num_sta = pre_plot(modelname, evtid, gauss)
    if xlim is None:
        xmin = -1 * readfwatpar('fwat_params/FWAT.PAR', 'TW_BEFORE')
        xmax = readfwatpar('fwat_params/FWAT.PAR', 'TW_AFTER')
        xlim = [xmin, xmax]
    fig = pygmt.Figure()
    pygmt.config(FONT_TITLE='14p',
                 MAP_GRID_PEN='0.3p,gray')
    fig.basemap(region=[*xlim, 0, num_sta+3], projection='X8c/10c',
                frame=['xa5f1g5+l"Time after P (s)"', '+t"{}, Event: {}"'.format(modelname, evtid), 'pycyticklabel.txt'])
    with Session() as lib:
        lib.call_module("sac", "saclst_dat_plot -En1 -M{} -W1p".format(enf))
        lib.call_module("sac", "saclst_syn -En1 -M{} -W1p,255/25/25".format(enf))
    fig.savefig('{}/{}_{}_rf_fit_F{}.png'.format(outpath, modelname, evtid, gauss))
    post_plot()


def main():
    parser = argparse.ArgumentParser('Plot rf fitting. read data/evtid/*F{{gauss}}.rf.sac for data,'
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/syn.*.F{{gauss}} for syn')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Event id', metavar='evtid')
    parser.add_argument('-g', help='Gaussian factor, should be the same as in filename', metavar='gauss')
    parser.add_argument('-x', help='x-axis limits, defaults to -5/30, NOTE: donnot insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 0.05', type=float, default=0.4, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()

    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = None
    plot_rf_fit(args.m, args.s, args.g, xlim=xlim, outpath=args.o, enf=args.e)
    