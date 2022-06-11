import pygmt
from pygmt.clib import Session
import numpy as np
import subprocess
import obspy
from os import remove
import argparse
import glob
from os.path import basename
import os


def pre_plot(evtid, comp, periodmin, periodmax):
    files = glob.glob('fwat_data/{}/*{}.sac'.format(evtid, comp))
    freqmin = 1/periodmax
    freqmax = 1/periodmin
    if periodmin is not None and periodmax is not None:
        bandname = '.T{:03.0f}_T{:03.0f}'.format(periodmin, periodmax)
        for fname in files:
            tr = obspy.read(fname)[0]
            tr.detrend()
            tr.filter(freqmin=freqmin, freqmax=freqmax, type='bandpass',
                    corners=4, zerophase=True)
            tr.write('fwat_data/{}/{}{}'.format(
                    evtid, basename(fname), bandname), 'SAC')
    else:
        bandname = ''
    s = ''
    s += 'saclst knetwk kstnm dist f fwat_data/{}/*{}.sac{} > saclst_dat\n'.format(evtid, comp, bandname)
    s += "awk '{{print $1}}' saclst_dat> saclst_dat_plot\n"
    s += 'awk \'{print $4" a "$2"."$3}\' saclst_dat > yticklabel.txt\n'
    subp = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
    subp.communicate(s.encode())
    dis = np.loadtxt('saclst_dat', usecols=[3])
    max_dis = np.max(dis)
    # with open('saclst_dat') as f:
    #     num_sta = len(f.readlines())
    return bandname, max_dis

def post_plot(evtid, bandname):
    remove('saclst_dat')
    remove('saclst_dat_plot')
    remove('yticklabel.txt')
    if bandname != '':
        for fname in glob.glob('fwat_data/{}/*{}'.format(evtid, bandname)):
            remove(fname)

# class PlotSurf():
#     def __init__(self, modelname, evtid, max_dis=350, xlim=[0, 200]) -> None:
def plot_surf_fit(evtid, periodmin=None, periodmax=None, comp='Z',
                  xlim=[0, 200], enf=2, ref_vel=[2.3, 4.5], outpath='./figures'):
    bandname, max_dis = pre_plot(evtid, comp, periodmin, periodmax)
    fig = pygmt.Figure()
    fig.basemap(region=[*xlim, 0, max_dis*1.1], projection='X10i', 
                frame=['xaf+l"Time (s)"', '+t"Event: {}, {}"'.format(evtid, bandname[1:]), 'pycyticklabel.txt'])
    with Session() as lib:
        lib.call_module("sac", "saclst_dat_plot -Ek -M{} -W1.3p".format(enf))
    dis = np.arange(max_dis)
    time_low = dis/ref_vel[0]
    time_high = dis/ref_vel[1]
    fig.plot(x=time_low, y=dis, pen='1p,deepskyblue,-')
    fig.plot(x=time_high, y=dis, pen='1p,deepskyblue,-')
    fig.savefig('{}/{}_surf_{}_{}.png'.format(outpath, evtid, comp, bandname[1:]))
    post_plot(evtid, bandname)


def main():
    parser = argparse.ArgumentParser('Plot teleseismic fitting. read '
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/wdat* for data,'
                                     'solver/M{{model}}.set{{setid}}/{{evtid}}/OUTPUT_FILES/wsyn* for syn')
    parser.add_argument('-s', help='Evt id', metavar='evtid')
    parser.add_argument('-t', help='Bandname', default='10/50', metavar='periodmin/periodmax')
    parser.add_argument('-c', help='Component name to plot R or Z avaliable, defaults to Z', default='Z', metavar='component')
    parser.add_argument('-x', help='x-axis limits, defaults to read b and e from sac files, NOTE: donnot insert space after -x', default=None, metavar='xmin/xmax')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 2', type=float, default=2, metavar='coef')
    parser.add_argument('-o', help='Figure output path', default='./figures', metavar='outpath')
    parser.add_argument('-v', help='Upper and lower reference velocities, defaults to 2/5', default='1.75/5', metavar='uper_vel/lower_vel')
    args = parser.parse_args()

    if args.x is not None:
        xlim = [float(v) for v in args.x.split('/')]
    else:
        xlim = [0, 160]
    ref_vel = [float(v) for v in args.v.split('/')]
    periodmin = float(args.t.split('/')[0])
    periodmax = float(args.t.split('/')[1])
    plot_surf_fit(args.s, periodmin=periodmin, periodmax=periodmax, 
                  comp=args.c, xlim=xlim, outpath=args.o,
                  ref_vel=ref_vel, enf=args.e)




