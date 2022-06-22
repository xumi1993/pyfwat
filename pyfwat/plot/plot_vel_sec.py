#!/usr/bin/env python

from audioop import reverse
import numpy as np
import sys
from os.path import basename, dirname, join, exists
from scipy.interpolate import interpn
import pygmt
import argparse


def vs2vprho(vs):
    vp = 0.9409 + 2.0947*vs - 0.8206*vs**2+ 0.2683*vs**3 - 0.0251*vs**4
    rho = 1.6612*vp - 0.4721*vp**2 + 0.0671*vp**3 - 0.0043*vp**4 + 0.000106*vp**5
    return vp, rho



def proj_sta(stafile, lat1, lon1, lat2, lon2, utm=False):
    st, net, stla, stlo, stel = np.loadtxt(stafile, usecols=[0,1,2,3,4],
                                           dtype = {'names': ('station', 'net','stla', 'stlo', 'stel'),
                                                        'formats': ('U20', 'U20', 'f4', 'f4', 'f2')},
                                           unpack=True, ndmin=1)
    sta = ['{}.{}'.format(net[i], st[i]) for i in range(st.size)]
    if utm:
        pos = np.vstack((stlo, stla)).T
        st_pos = pygmt.project(pos, center=[lon1, lat1], endpoint=[lon2, lat2], convention='p', unit=True)
    else:
        pos = np.vstack((stlo/1000, stla/1000)).T
        st_pos = pygmt.project(pos, center=[lon1, lat1], endpoint=[lon2, lat2], convention='p', flat_earth=True)
    # dimension need to be checked
    return sta, st_pos.values[:,0], stel


def interp_sec(data, lat1, lon1, lat2, lon2, hval=1, vval=0.5, name='vs', utm=False, unit_trans=True, enf=1):
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
        xx, yy, zz = data['x']/1000, data['y']/1000, data['z']
    depth = np.arange(zz[0], 0+vval, vval)
    points2d = np.empty([0, 4])
    for i, x in enumerate(points.values):
        for j,d in enumerate(depth):
            points2d = np.vstack((points2d, np.append(x, d)))
    # inter_dep, inter_y, inter_x = np.meshgrid(data['z'], data['y'], data['x'], indexing='ij')
    if unit_trans:
        datap = data[name]/1000 * enf
    else:
        datap = data[name] * enf
    points_value = interpn((xx, yy, zz), datap, points2d[:, [0, 1, 3]],
                           bounds_error=False, fill_value=None)
    grid = pygmt.surface(x=points2d[:, 2], y=-points2d[:, 3], z=points_value,
                         region=[points.values[0, -1], points.values[-1, -1], 0, -depth[0]],
                         spacing='{}/{}'.format(hval, vval))
    return points, depth, grid

class Pltvel():
    def __init__(self, velfile, stafile='src_rec/STATIONS_1', key='vs'):
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
        if 'vs' in velfile:
            self.dataname = 'vs'
        elif 'vp' in velfile:
            self.dataname = 'vp'
        elif 'rho' in velfile:
            self.dataname = 'rho'
        else:
            self.dataname = key
            # print('Error: vs, vp or rho should be included in the filename')
            # sys.exit(1)
        self.fname = basename(velfile).split('.')[0]
        self.lines = []

    
    def append_lines(self, lat1, lon1, lat2, lon2, utm=False):
        sta, stpos, stel = proj_sta(self.stafile, lat1, lon1, lat2, lon2, utm=utm)
        hval = 1
        vval = 0.5
        points, depth, grid = interp_sec(self.data, lat1, lon1, lat2, lon2, hval=hval,
                                         vval=vval, name=self.dataname, utm=utm)
        region = [points.values[0, 2], points.values[-1, 2], 0, -depth[0]]
        self.lines.append({'pos':[lat1, lon1, lat2, lon2], 'sta':sta,
                           'stpos':stpos, 'stel':stel, 'grid':grid, 'region':region})
    #  cpt=join(dirname(dirname(__file__)), 'cpt/vel.cpt')
    def plot(self, line, cpt=join(dirname(dirname(__file__)), 'cpt/vel.cpt'),
             reverse=False, outpath='./figures', colorbar=True):
        fig = pygmt.Figure()
        enf_x = (5/line['region'][-1])*(line['region'][1]-line['region'][0])
        fig.basemap(region=line['region'],
                    projection="X{}c/-5c".format(enf_x),
                    frame=['WSrt', 'xaf+l"Distance (km)"', 'yaf+l"Depth (km)"'])
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
        pygmt.makecpt(cmap=cpt, series=[vmin, vmax, 0.05], reverse=reverse, continuous=True)
        fig.grdimage(grid=line['grid'], cmap=True)
        fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.15c',
                 style='t0.3c', pen='0.5p', color='gray40', no_clip=True)
        if colorbar:
            fig.colorbar(position="JMR+o0.7c/0c+w5c/0.3c+ebf", frame=['xag+l"{}"'.format(label)])
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
    parser.add_argument('-s', help='Path to STATIONS, defaults to src_rec/STATIONS_1', default='src_rec/STATIONS_1')
    parser.add_argument('-c', help='Whether plot color bar, defaults to False', action='store_true', default=False)
    parser.add_argument('-C', help='Cmap name', default=join(dirname(dirname(__file__)), 'cpt/vel_norm.cpt'), metavar='cpt_name')
    parser.add_argument('-I', help='Whether invert the color map ', default=False, action='store_true')
    parser.add_argument('-k', help='Key name of the volume data, default to assosiate with in file name', default='vs')
    parser.add_argument('-u', help='Use UTM coordinates', action='store_true', default=False)
    args = parser.parse_args()
    plotsec =  Pltvel(args.i, stafile=args.s, key=args.k)
    if exists(args.sections):
        lines = np.loadtxt(args.sections)
        for line in lines:
            plotsec.append_lines(*list(line), utm=args.u)
    else:
        line = [float(v) for v in args.sections.split('/')]
        plotsec.append_lines(*line, utm=args.u)
    plotsec.plot_all(outpath=args.o, colorbar=args.c, cpt=args.C, reverse=args.I)


if __name__ == '__main__':
    main()