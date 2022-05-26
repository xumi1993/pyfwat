import numpy as np
import sys
from os.path import basename, dirname, join, exists
from scipy.interpolate import interpn
import pygmt
import argparse
from pyfwat.plot.plot_vel_sec import proj_sta, interp_sec


# def interp_sec(data, lat1, lon1, lat2, lon2, hval=0.5, vval=0.5, name='beta_kernel_smooth'):
#     """
#     hval = horizantal interval in km
#     vval = vertical interval in km
#     points = lon, lat, dist-from-start
#     """
#     points = pygmt.project(center='{}/{}'.format(lon1, lat1),
#                        endpoint='{}/{}'.format(lon2, lat2),
#                        generate=hval, unit=True)
#     depth = np.arange(data['z'][0], 0-vval, vval)
#     points2d = np.empty([0, 4])
#     for i, x in enumerate(points.values):
#         for j,d in enumerate(depth):
#             points2d = np.vstack((points2d, np.append(x, d)))
#     # inter_dep, inter_y, inter_x = np.meshgrid(data['z'], data['y'], data['x'], indexing='ij')
#     points_value = interpn((data['x'], data['y'], data['z']),
#                             data[name], points2d[:, [0, 1, 3]], bounds_error=False, fill_value=None)
#     grid = pygmt.surface(x=points2d[:, 2], y=-points2d[:, 3], z=points_value,
#                          region=[points.values[0, -1], points.values[-1, -1], 0, -depth[0]],
#                          spacing='{}/{}'.format(hval, vval))
#     return points, depth, grid


class Pltvel():
    def __init__(self, kerfile, stafile='src_rec/STATIONS', key='beta_kernel_smooth'):
        self.kerfile = kerfile
        self.stafile = stafile
        self.dataname = key
        self.fname = basename(kerfile).split('.')[0]
        self.lines = []
        self.data = np.load(kerfile)

    def append_lines(self, lat1, lon1, lat2, lon2, utm=False):
        sta, stpos, stel = proj_sta(self.stafile, lat1, lon1, lat2, lon2,utm=utm)
        hval = np.mean(np.diff(self.data['x']))
        vval = abs(np.mean(np.diff(self.data['z']/1000)))
        points, depth, grid = interp_sec(self.data, lat1, lon1, lat2, lon2, hval=hval,
                                         vval=vval, name=self.dataname, utm=utm)
        region = [points.values[0, 2], points.values[-1, 2], 0, -depth[0]]
        self.lines.append({'pos':[lat1, lon1, lat2, lon2], 'sta':sta,
                           'stpos':stpos, 'stel':stel, 'grid':grid, 'region':region})
    
    def plot(self, line, cpt=join(dirname(dirname(__file__)), 'cpt/kernel_avg.cpt'), outpath='./figures', colorbar=True, enf=1):
        fig = pygmt.Figure()
        fig.basemap(region=line['region'],
                    projection="x0.05c/-0.05c",
                    frame=['WSrt', 'xaf+l"Distance (km)"', 'yaf+l"Depth (km)"'])
        print('Max value of data: {}'.format(np.max(np.abs(line['grid'].values))))
        line['grid'].values *= enf
        vmax = np.max(np.abs(line['grid'].values))
        vmin = -vmax
        vval = (vmax-vmin)/50
        pygmt.makecpt(cmap=cpt, series=[vmin, vmax, vval], continuous=True)
        fig.grdimage(grid=line['grid'], cmap=True)
        fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.15c',
                 style='t0.3c', pen='0.5p', color='gray40', no_clip=True)
        if colorbar:
            fig.colorbar(position="JMR+o0.7c/0c+w5c/0.3c+ebf", frame=['xag', 'y+l"x{:0e}"'.format(enf/enf/enf)])
        fig.savefig('{}/{}_{:.1f}_{:.1f}_{:.1f}_{:.1f}.png'.format(
                    outpath, self.fname, *line['pos']))
    
    def plot_all(self, **kwargs):
        for line in self.lines:
            self.plot(line, **kwargs)


def main(): 
    parser = argparse.ArgumentParser('Plot kernel values with cross sections')
    parser.add_argument('sections', help='File to line positions or positions of single line (lat1/lon1/lat2/lon2)')
    parser.add_argument('-i', help='Path to 3D data structure in npz format, generated with \'xproject_and_combine_vol_data_on_regular_grid\'',
                        metavar='data_structure_file', required=True)
    parser.add_argument('-o', help='Output path, defaults to ./figures', default='./figures')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 1', type=float, default=1, metavar='coef')
    parser.add_argument('-s', help='Path to STATIONS, defaults to DATA/STATIONS', default='DATA/STATIONS')
    parser.add_argument('-c', help='Whether plot color bar, defaults to False', action='store_true', default=False)
    parser.add_argument('-k', help='Key name of the volume data',metavar='kernel_name', default='beta_kernel_smooth')
    parser.add_argument('-u', help='Use UTM coordinates', action='store_true', default=False)
    args = parser.parse_args()
    plotsec =  Pltvel(args.i, stafile=args.s, key=args.k)
    if exists(args.sections):
        lines = np.loadtxt(args.sections)
        for line in lines:
            plotsec.append_lines(*list(line), utm=args.u)
    else:
        line = [float(v) for v in args.sections.split('/')]
        plotsec.append_lines(*line)
    plotsec.plot_all(outpath=args.o, colorbar=args.c, enf=args.e)