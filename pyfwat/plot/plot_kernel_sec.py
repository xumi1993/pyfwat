"""Cross sections of sensitivity kernels.

Command-line tool: ``fwat_plot_kernel_sec``.
"""

import numpy as np
import sys
from os.path import basename, dirname, join, exists
from scipy.interpolate import interpn
import pygmt
import argparse
from .plot_vel_sec import proj_sta, interp_sec
from pyproj import Geod
from ..utils.utils import parse_cpt_name


class Pltvel():
    """Cross sections of a sensitivity kernel.

    Sections are added with :meth:`append_lines` and plotted with
    :meth:`plot_all`.
    """
    def __init__(self, kerfile, stafile='src_rec/STATIONS', enf=1):
        """:param kerfile: ``.npz`` kernel with ``x``, ``y``, ``z`` and the kernel as
            the last array
        :type kerfile: str
        :param stafile: SPECFEM station file, defaults to ``src_rec/STATIONS``
        :type stafile: str, optional
        :param enf: Scale factor shown in the color bar label, defaults to 1
        :type enf: float, optional
        """
        self.kerfile = kerfile
        self.stafile = stafile
        self.enf = enf
        self.fname = '.'.join(basename(kerfile).split('.')[0:-1])
        self.lines = []
        self.data = np.load(kerfile)
        self.dataname = self.data.__dict__['files'][-1]


    def append_lines(self, lat1, lon1, lat2, lon2, utm=False,
                     hval=1, vval=0.5, unit_trans=False, xunit=None):
        """Interpolate the kernel on a section and add it to ``lines``.

        :param lat1: Latitude (or y) of the start of the section
        :type lat1: float
        :param lon1: Longitude (or x) of the start of the section
        :type lon1: float
        :param lat2: Latitude (or y) of the end of the section
        :type lat2: float
        :param lon2: Longitude (or x) of the end of the section
        :type lon2: float
        :param utm: True if the grid coordinates are longitude and latitude; False
            for Cartesian coordinates in m, defaults to False
        :type utm: bool, optional
        :param hval: Horizontal sampling interval in km, defaults to 1
        :type hval: float, optional
        :param vval: Vertical sampling interval in km, defaults to 0.5
        :type vval: float, optional
        :param unit_trans: Divide the values by 1000, defaults to False
        :type unit_trans: bool, optional
        :param xunit: Horizontal axis: ``'la'``, ``'lo'`` or None for distance,
            defaults to None
        :type xunit: str, optional
        """
        self.utm = utm
        sta, stpos, stel = proj_sta(self.stafile, lat1, lon1, lat2, lon2, xunit=xunit, utm=utm)
        # points, depth, grid = interp_sec(self.data, lat1, lon1, lat2, lon2, hval=hval,
        #                                  vval=vval, name=self.dataname, utm=utm,
        #                                  unit_trans=False, enf=self.enf)
        r1, r2, depth, grid = interp_sec(self.data, lat1, lon1, lat2, lon2, hval=hval,
                                         vval=vval, name=self.dataname, utm=utm, 
                                         xunit=xunit, unit_trans=unit_trans)
        region = [r1, r2, 0, -depth[0]]
        self.lines.append({'pos':[lat1, lon1, lat2, lon2], 'sta':sta,
                           'stpos':stpos, 'stel':stel, 'grid':grid, 'region':region})
    
    def plot(self, line, cpt=join(dirname(dirname(__file__)), 'cpt/kernel.cpt'),
             outpath='./figures', colorbar=True, img_scale=25):
        """Plot a section with a symmetric color range and save it as a PNG.

        The figure is ``<outpath>/<kernel>_<lat1>_<lon1>_<lat2>_<lon2>.png``.

        :param line: Section from ``lines``
        :type line: dict
        :param cpt: Color table, defaults to the bundled ``kernel.cpt``
        :type cpt: str, optional
        :param outpath: Output directory, defaults to ``./figures``
        :type outpath: str, optional
        :param colorbar: Draw a color bar, defaults to True
        :type colorbar: bool, optional
        :param img_scale: Section length per cm of figure, defaults to 25
        :type img_scale: float, optional
        """
        self.fig = pygmt.Figure()
        if self.utm:
            g = Geod(ellps="WGS84")
            _,_,dist = g.inv(line['pos'][1], line['pos'][0], line['pos'][3], line['pos'][2])
            dist /= 1000
        else:
            dist = line['region'][1]
        yscale = line['region'][-1]/img_scale
        xscale = dist/img_scale
        self.fig.basemap(region=line['region'],
                    # projection="x0.05c/-0.05c",
                    projection="X{}c/-{}c".format(xscale, yscale),
                    frame=['WSrt', 'xaf+l"Distance (km)"', 'yaf+l"Depth (km)"'])
        print('Max value of data: {}'.format(np.max(np.abs(line['grid'].values))))
        line['grid'].values
        vmax = np.max(line['grid'].values)
        vmin = -vmax
        vval = (vmax-vmin)/10
        pygmt.makecpt(cmap=cpt, series=[vmin, vmax, vval], continuous=True)
        self.fig.grdimage(grid=line['grid'], cmap=True)
        # fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.15c',
        #          style='t0.3c', pen='0.5p', fill='gray40', no_clip=True)
        if colorbar:
            self.fig.colorbar(position="JMR+o0.7c/0c+w5c/0.3c+ebf", frame=['xag', 'y+l"x{:.0e}"'.format(self.enf/self.enf/self.enf)])
        self.fig.savefig('{}/{}_{:.1f}_{:.1f}_{:.1f}_{:.1f}.png'.format(
                    outpath, self.fname, *line['pos']))
    
    def plot_all(self, **kwargs):
        """Plot every section in ``lines``.

        :param kwargs: Arguments passed to :meth:`plot`
        """
        for line in self.lines:
            self.plot(line, **kwargs)


def main(): 
    """Command-line entry point of ``fwat_plot_kernel_sec``."""
    parser = argparse.ArgumentParser('Plot kernel values with cross sections')
    parser.add_argument('sections', help='File to line positions or positions of single line (lat1/lon1/lat2/lon2)')
    parser.add_argument('-i', help='Path to 3D data structure in npz format, generated with \'xproject_and_combine_vol_data_on_regular_grid\'',
                        metavar='data_structure_file', required=True)
    parser.add_argument('-o', help='Output path, defaults to ./figures', default='./figures')
    parser.add_argument('-e', help='enlarge coefficient, defaults to 1', type=float, default=1, metavar='coef')
    parser.add_argument('-s', help='Path to STATIONS, defaults to DATA/STATIONS', default='DATA/STATIONS')
    parser.add_argument('-c', help='Whether plot color bar, defaults to False', action='store_true', default=False)
    parser.add_argument('-C', help='Cmap name', default='kernel_avg', metavar='cpt_name')
    parser.add_argument('-x', help='Unit of x-axis as la, lo or distance, defaults to distance', default=None, metavar='[la|lo]')
    parser.add_argument('-u', help='Use UTM coordinates', action='store_true', default=False)
    args = parser.parse_args()
    plotsec =  Pltvel(args.i, stafile=args.s, enf=args.e)
    if exists(args.sections):
        lines = np.loadtxt(args.sections)
        for line in lines:
            plotsec.append_lines(*list(line), xunit=args.x, utm=args.u)
    else:
        line = [float(v) for v in args.sections.split('/')]
        plotsec.append_lines(*line, xunit=args.x, utm=args.u)
    cpt_path = parse_cpt_name(args.C)
    if not exists(cpt_path):
        cpt_path = args.C
    plotsec.plot_all(outpath=args.o, cpt=cpt_path, colorbar=args.c)
