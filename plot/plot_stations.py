#!/usr/bin/env python
import sys
from os.path import dirname, abspath
sys.path.append(dirname(dirname(abspath(__file__))))
from utils import readpar
import pygmt
import numpy as np
import argparse


def read_sta(stafile):
    return np.loadtxt(stafile, usecols=[0,1,2,3,4],
                    dtype = {'names': ('station', 'net','stla', 'stlo', 'stel'),
                                'formats': ('U20', 'U20', 'f4', 'f4', 'f2')},
                    unpack=True, ndmin=1)


def plot(stafile='DATA/STATIONS', outpath='./figures', coast=False):
    par_file = 'DATA/meshfem3D_files/Mesh_Par_file'
    xmin = readpar(par_file, 'LONGITUDE_MIN')
    xmax = readpar(par_file, 'LONGITUDE_MAX')
    ymin = readpar(par_file, 'LATITUDE_MIN')
    ymax = readpar(par_file, 'LATITUDE_MAX')
    sta, net, stla, stlo, stel = read_sta(stafile)
    suppress_utm = readpar(par_file, 'SUPPRESS_UTM_PROJECTION')
    if suppress_utm:
        proj = 'X10c'
        coast = False
    else:
        proj = 'M10c'
    fig = pygmt.Figure()
    pygmt.config(FORMAT_GEO_MAP='ddd.x')
    fig.basemap(region=[xmin, xmax, ymin, ymax], projection=proj,
                frame=['a0.2f0.2', 'WSne'])
    if coast:
        fig.coast(resolution='f',land="250", water="173/217/230", pen='0.1p')
    fig.plot(x=stlo, y=stla, style='t0.3c', color='255/25/25', pen='0.2p')
    fig.savefig('{}/stations.png'.format(outpath))


def main():
    parser = argparse.ArgumentParser('Plot stations in the box region.')
    parser.add_argument('-s', help='Path to STATIONS, defaults to DATA/STATIONS', default='DATA/STATIONS', metavar='station_file')
    parser.add_argument('-o', help='Output path, defaults to ./figures', default='./figures', metavar='output_path')
    parser.add_argument('-c', help='Whether plot coast, defaults to False. If SUPPRESS_UTM_PROJECTION = .true.'
                        ' in DATA/meshfem3D_files/Mesh_Par_file, this argument will be invalid.', default=False, action='store_true')
    args = parser.parse_args()
    plot(args.s, args.o, args.c)


if __name__ == '__main__':
    main()