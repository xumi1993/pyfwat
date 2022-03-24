#!/usr/bin/env python

from matplotlib.pyplot import figure
import numpy as np
import pygmt
from seispy.geo import sind
import sys
import glob
from os.path import exists, dirname
from os import makedirs
sys.path.append(dirname(dirname(__file__)))
from utils import readfkpar


def get_rayp(evtid):
    par_file = 'src_rec/FKmodel_{}'.format(evtid)
    model = readfkpar(par_file, 'LAYER')
    baz = readfkpar(par_file, 'BACK_AZIMUTH')
    inc = readfkpar(par_file, 'TAKE_OFF')
    rayp = sind(inc)/(model[-1, 2]/1000)
    return baz, rayp


def main(label_angle=22.5):
    if len(sys.argv[1:]) == 0:
        outpath = './figures'
    elif len(sys.argv[1:]) == 1:
        outpath = sys.argv[1]
    else:
        print(' Usage: plot_rf_evts.py [outpath]')
        print(' narg: {}'.format(len(sys.argv[1:])))
    if not exists(outpath):
        makedirs(outpath)
    srcfiles = sorted(glob.glob('src_rec/sources_*.dat'))
    baz = np.zeros(len(srcfiles))
    rayp = np.zeros_like(baz)
    for i, fsrc in enumerate(srcfiles):
        with open(fsrc) as f:
            evtid = f.readlines()[0].split()[0]
        baz[i], rayp[i] = get_rayp(evtid)
    fig = pygmt.Figure()
    pygmt.config(FORMAT_GEO_MAP="+D")
    ymin = 0.035
    ymax = 0.085
    fig.basemap(region=[0, 360, ymin, ymax], projection="P8c+a",  frame=["xa45f", "yg0.02"])
    fig.plot(x=baz, y=rayp, style='a0.26c', pen='0.1p', color='255/25/25')
    fig.text(text='{:.3f}'.format(ymin), x=label_angle, y=ymin, font='8p', angle=-label_angle, no_clip=True, fill='255')
    fig.text(text='{:.3f}'.format(ymax), x=label_angle, y=ymax, font='8p', angle=-label_angle, no_clip=True, fill='255')
    fig.savefig('{}/rf_evts.png'.format(outpath))


if __name__ == '__main__':
    main()