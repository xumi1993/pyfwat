#!/usr/bin/env python

import numpy as np
import pygmt
from seispy.geo import sind
import sys
import glob
from os.path import exists, dirname
from os import makedirs
from ..utils import readfkpar
import argparse

def get_rayp(evtid):
    par_file = 'src_rec/FKmodel_{}'.format(evtid)
    model = readfkpar(par_file, 'LAYER')
    baz = readfkpar(par_file, 'BACK_AZIMUTH')
    inc = readfkpar(par_file, 'TAKE_OFF')
    rayp = sind(inc)/(model[-1, 2]/1000)
    return baz, rayp


def plot_evts(label_angle=22.5, outpath='./figures'):
    srcfiles = sorted(glob.glob('src_rec/sources_*.dat'))
    baz = np.zeros(len(srcfiles))
    rayp = np.zeros_like(baz)
    for i, fsrc in enumerate(srcfiles):
        with open(fsrc) as f:
            evtid = f.readlines()[0].split()[0]
        baz[i], rayp[i] = get_rayp(evtid)
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


def main():
    parser = argparse.ArgumentParser(help='Plot virtual events of RFs with back-azimuth and ray-parameters.'
                                          'This command read event id in src_rec/sources_*.dat'
                                          'and read TAKE_OFF in src_rec/FKmodel_* for computing ray-parameters.')
    parser.add_argument('-a', help='Azimuth of label position of rayp, defaults to 22.5',
                        type=float, metavar='angle', default=22.5)
    parser.add_argument('-o', help='Figure output path, defaults to ./figures', default='./figures')
    args = parser.parse_args()
    if not exists(args.o):
        makedirs(args.o)
    plot_evts(args.a, args.o)


if __name__ == '__main__':
    main()