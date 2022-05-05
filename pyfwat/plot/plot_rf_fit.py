import pygmt
import subprocess
from os import remove
from pygmt.clib import Session
import argparse


def pre_plot(modelname, setid, gauss):
    with open('src_rec/sources_set{}.dat'.format(setid)) as f:
        evtid = f.readlines()[0].strip().split()[0]
    s = ''
    s += 'saclst knetwk kstnm f data/{}/*.F{}.rf.sac > saclst_dat\n'.format(evtid, gauss)
    s += "awk '{{print $1}}' saclst_dat> saclst_dat_plot\n"
    s += 'awk \'{print FNR" a "$2"."$3}\' saclst_dat > yticklabel.txt\n'
    s += 'ls solver/{}.set{}/{}/OUTPUT_FILES/syn.*.F{} > saclst_syn\n'.format(modelname, setid, evtid, gauss)
    subp = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
    subp.communicate(s.encode())
    with open('saclst_dat') as f:
        num_sta = len(f.readlines())
    return evtid, num_sta

def post_plot():
    remove('saclst_dat')
    remove('saclst_dat_plot')
    remove('yticklabel.txt')
    remove('saclst_syn')

def plot_rf_fit(modelname, setid, gauss, xlim=(-5,30), outpath='./figures', enf=0.05):
    evtid, num_sta = pre_plot(modelname, setid, gauss)
    fig = pygmt.Figure()
    pygmt.config(FONT_TITLE='14p',
                 MAP_GRID_PEN='0.3p,gray')
    fig.basemap(region=[*xlim, 0, num_sta+3], projection='x0.4c/0.6c',
                frame=['xa5f1g5+l"Time after P (s)"', '+t"{}, Event: {}"'.format(modelname, evtid), 'pycyticklabel.txt'])
    with Session() as lib:
        lib.call_module("sac", "saclst_dat_plot -En1 -M{} -W1p".format(enf))
        lib.call_module("sac", "saclst_syn -En1 -M{} -W1p,255/25/25".format(enf))
    fig.savefig('{}/{}.set{}_rf_fit_F{}.png'.format(outpath, modelname, setid, gauss))
    post_plot()


def main():
    parser = argparse.ArgumentParser('Plot rf fitting. read data/evtid/*F{{gauss}}.rf.sac for data,'
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/syn.*.F{{gauss}} for syn')
    parser.add_argument('-m', help='Model name e.g., M00, M01...', metavar='model')
    parser.add_argument('-s', help='Set id', metavar='setid')
    parser.add_argument('-g', help='Gaussian factor, should be the same as in filename', metavar='gauss')
    parser.add_argument('-x', help='x-axis limits, defaults to -5/30, NOTE: donnot insert space after -x', default='-5/30', metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 0.05', type=float, default=0.05, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    args = parser.parse_args()

    xlim = [float(v) for v in args.x.split('/')]
    plot_rf_fit(args.m, args.s, args.g, xlim=xlim, outpath=args.o, enf=args.e)
    