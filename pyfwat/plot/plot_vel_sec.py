#!/usr/bin/env python

import numpy as np
import sys
from os.path import basename, dirname, join, exists
from scipy.interpolate import interpn
import pygmt
import argparse
from ..utils import parse_cpt_name
from ..pario import readpar
from pyproj import Geod, Proj


def vs2vprho(vs):
    vp = 0.9409 + 2.0947*vs - 0.8206*vs**2+ 0.2683*vs**3 - 0.0251*vs**4
    rho = 1.6612*vp - 0.4721*vp**2 + 0.0671*vp**3 - 0.0043*vp**4 + 0.000106*vp**5
    return vp, rho



def proj_sta(stafile, lat1, lon1, lat2, lon2, xunit=None, utm=False):
    st, net, stla, stlo, stel = np.loadtxt(stafile, usecols=[0,1,2,3,4],
                                           dtype = {'names': ('station', 'net','stla', 'stlo', 'stel'),
                                                        'formats': ('U20', 'U20', 'f4', 'f4', 'f2')},
                                           unpack=True, ndmin=1)
    sta = ['{}.{}'.format(net[i], st[i]) for i in range(st.size)]
    if xunit == 'la':
        convention = 's'
    elif xunit == 'lo':
        convention = 'r'
    else:
        convention = 'p'
    if utm:
        pos = np.vstack((stlo, stla)).T
        st_pos = pygmt.project(pos, center=[lon1, lat1], endpoint=[lon2, lat2], convention=convention, unit=True)
    else:
        pos = np.vstack((stlo/1000, stla/1000)).T
        st_pos = pygmt.project(pos, center=[lon1, lat1], endpoint=[lon2, lat2], convention=convention, flat_earth=True)
    # dimension need to be checked
    return sta, st_pos.values[:,0], stel


def interp_sec(data, lat1, lon1, lat2, lon2, hval=2, vval=2, name='vs',
               xunit=None, utm=False, unit_trans=True, enf=1):
    """
    hval = horizantal interval in km
    vval = vertical interval in km
    points = lon, lat, dist-from-start
    """
    if utm:
        points = pygmt.project(center='{}/{}'.format(lon1, lat1),
                       endpoint='{}/{}'.format(lon2, lat2),
                       generate=hval, unit=True)
        xx, yy, zz = data['x'], data['y'], data['z']
    else:
        points = pygmt.project(center='{}/{}'.format(lon1, lat1),
                       endpoint='{}/{}'.format(lon2, lat2),
                       generate=hval, flat_earth=True)
        xx, yy, zz = data['x']/1000, data['y']/1000, data['z']/1000
    depth = np.arange(zz[0], 0+vval, vval)
    points2d = np.empty([0, 4])
    for i, x in enumerate(points.values):
        for j,d in enumerate(depth):
            points2d = np.vstack((points2d, np.append(x, d)))
    if unit_trans:
        datap = data[name]/1000 * enf
    else:
        datap = data[name] * enf
    points_value = interpn((xx, yy, zz), datap, points2d[:, [0, 1, 3]],
                           bounds_error=False, fill_value=None)
    if xunit == 'la':
        x = points2d[:, 1]
        r1 = points.values[0, 1]
        r2 = points.values[-1, 1]
        inval = hval/111.19
    elif xunit == 'lo':
        x = points2d[:, 0]
        r1 = points.values[0, 0]
        r2 = points.values[-1, 0]
        inval = hval/111.19
    else:
        x = points2d[:, 2]
        r1 = points.values[0, 2]
        r2 = points.values[-1, 2]
        inval = hval
    grid = pygmt.surface(x=x, y=-points2d[:, 3], z=points_value,
                         region=[r1, r2, 0, -depth[0]],
                         spacing='{}/{}'.format(inval, vval))
    return r1, r2, depth, grid

class Pltvel():
    def __init__(self, velfile, stafile='DATA/STATIONS'):
        self.velfile = velfile
        self.stafile = stafile
        try:
            self.data = np.load(velfile)
        except:
            print("Error: No such file of {}".format(self.velfile))
            sys.exit(1)
        if not exists(self.stafile):
            print('Error: No such file of {}'.format(stafile))
            sys.exit(1)
        self.dataname = self.data.__dict__['files'][-1]
            # print('Error: vs, vp or rho should be included in the filename')
            # sys.exit(1)
        self.fname = basename(velfile).split('.')[0]
        self.lines = []

    def append_lines(self, data, lat1, lon1, lat2, lon2, utm=False, 
                     hval=1, vval=0.5, unit_trans=True, xunit=None, maxdep=None):
        self.xunit = xunit
        self.utm = utm
        sta, stpos, stel = proj_sta(self.stafile, lat1, lon1, lat2, lon2,
                                    xunit=xunit, utm=utm)
        r1, r2, depth, grid = interp_sec(data, lat1, lon1, lat2, lon2, hval=hval,
                                         vval=vval, name=self.dataname, utm=utm, 
                                         xunit=xunit, unit_trans=unit_trans)
        if maxdep is None:
            maxdep = -depth[0]
        region = [r1, r2, 0, maxdep]
        self.lines.append({'pos':[lat1, lon1, lat2, lon2], 'sta':sta,
                           'stpos':stpos, 'stel':stel, 'grid':grid, 'region':region})

    #  cpt=join(dirname(dirname(__file__)), 'cpt/vel.cpt')
    def plot(self, line, cpt=join(dirname(dirname(__file__)), 'cpt/vel.cpt'),
             reverse=False, outpath='./figures', colorbar=True, norm=None,
             img_scale=25, smooth=10):
        fig = pygmt.Figure()
        if self.utm:
            g = Geod(ellps="WGS84")
            _,_,dist = g.inv(line['pos'][1], line['pos'][0], line['pos'][3], line['pos'][2])
            dist /= 1000
        else:
            dist = line['region'][1]
        yscale = line['region'][-1]/img_scale
        xscale = dist/img_scale
        if self.xunit == 'la':
            xlabel = 'Latitude (\\260)'
        if self.xunit == 'lo':
            xlabel = 'longitude (\\260)'
        else:
            xlabel = 'Distance (km)'
        fig.basemap(region=line['region'],
                    # projection="x0.04c/-0.04c",
                    projection="X{}c/-{}c".format(xscale, yscale),
                    frame=['WSrt', 'xaf+l"{}"'.format(xlabel), 'yaf+l"Depth (km)"'])
        # vmin = np.min(line['grid'].values)-0.05
        # vmax = np.max(line['grid'].values)+0.05
        if self.dataname == 'vs':
            vmin = 2.7
            vmax = 4.8
            label = 'Vs (km/s)'
        elif self.dataname == 'vp':
            vmin, _ = vs2vprho(2.7)
            vmax, _ = vs2vprho(4.8)
            label = 'Vp (km/s)'
        else:
            _, vmin = vs2vprho(2.7)
            _, vmax = vs2vprho(4.8)
            # vmax+=0.2
            label = 'Density (g/cm@+3@+)'
        if norm is None:
            pygmt.makecpt(cmap=cpt, series=[vmin, vmax, 0.05], reverse=reverse, continuous=True)
            cmapp = True
        elif norm:
            pygmt.makecpt(cmap=cpt, series=[norm[0], norm[1], 0.05], reverse=reverse, continuous=True)
            cmapp = True
        else:
            cmapp = cpt
        if smooth is None:
            smgrid = line['grid']
        else:
            smgrid = pygmt.grdfilter(grid=line['grid'], filter='g{}'.format(smooth), distance='0')
        fig.grdimage(grid=smgrid, cmap=cmapp)
        fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.15c',
                 style='t0.3c', pen='0.5p', fill='gray40', no_clip=True)
        if colorbar:
            fig.colorbar(position="JMR+o0.7c/0c+w4c+ebf", frame=['xag+l"{}"'.format(label)])
        fig.savefig('{}/{}_{:.1f}_{:.1f}_{:.1f}_{:.1f}.png'.format(
                    outpath, self.fname, *line['pos']))
    
    def plot_all(self, **kwargs):
        for line in self.lines:
            self.plot(line, **kwargs)


def main(): 
    parser = argparse.ArgumentParser('Plot model parameter (Vp, vs or rho) with cross sections')
    parser.add_argument('sections', help='File to line positions or positions of single line (lat1/lon1/lat2/lon2)')
    parser.add_argument('-i', help='Path to 3D data structure in npz format, generated with \'xproject_and_combine_vol_data_on_regular_grid\'',
                        metavar='data_structure_file', required=True)
    parser.add_argument('-o', help='Output path, defaults to ./figures', default='./figures')
    parser.add_argument('-s', help='Path to STATIONS, defaults to DATA/STATIONS', default='DATA/STATIONS')
    parser.add_argument('-c', help='Whether plot color bar, defaults to False', action='store_true', default=False)
    parser.add_argument('-n', help='Normalize the colors with upper/lower bounds, defaults to None, add \'a\' for auto normalization', default=None, metavar='vmin/vmax')
    parser.add_argument('-C', help='Cmap name', default='vel_norm', metavar='cpt_name')
    parser.add_argument('-I', help='Whether invert the color map ', default=False, action='store_true')
    parser.add_argument('-u', help='Use UTM coordinates', action='store_true', default=False)
    parser.add_argument('-x', help='Unit of x-axis as la, lo or distance, defaults to distance', default=None, metavar='[la|lo]')
    parser.add_argument('-d', help='Max depth to plot', type=float, metavar='max_depth', default=None)
    parser.add_argument('-a', help='Horizental and vertical spacing in km', default='1/1', metavar='hx/hz')
    parser.add_argument('-m', help='Smoothing scale in km', default=None, metavar='smoothing_scale')
    args = parser.parse_args()
    val = [ float(v) for v in args.a.split('/')]
    plotsec =  Pltvel(args.i, stafile=args.s)
    if exists(args.sections):
        lines = np.loadtxt(args.sections)
        for line in lines:
            plotsec.append_lines(plotsec.data, *list(line), utm=args.u,
                                 xunit=args.x, hval=val[0], vval=val[1],
                                 maxdep=args.d)
    else:
        line = [float(v) for v in args.sections.split('/')]
        plotsec.append_lines(plotsec.data, *line, utm=args.u,
                             xunit=args.x, hval=val[0], vval=val[1],
                             maxdep=args.d)
    if args.n is None:
        norm = False
    elif args.n == 'a':
        norm = None
    else:
        norm = [float(v) for v in args.n.split('/')]
    cpt_path = parse_cpt_name(args.C)
    if not exists(cpt_path):
        cpt_path = args.C
    plotsec.plot_all(outpath=args.o, colorbar=args.c,
                     cpt=cpt_path, reverse=args.I, 
                     norm=norm, smooth=args.m)


if __name__ == '__main__':
    main()