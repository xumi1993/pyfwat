"""Cross sections of velocity perturbations relative to the depth-averaged or an initial model.

Command-line tool: ``fwat_plot_dv_sec``.
"""

import numpy as np
import sys
from os.path import basename, dirname, join, exists
from scipy.interpolate import interpn
import pygmt
import argparse
from ..utils.utils import parse_cpt_name
from .plot_vel_sec import Pltvel
from pyproj import Geod

class PltDv(Pltvel):
    """Cross sections of velocity perturbations in percent.

    Call :meth:`get_dv` before adding sections with ``data_dv``.
    """
    def __init__(self, velfile, stafile='DATA/STATIONS', initial=None) -> None:
        """:param velfile: ``.npz`` model with ``x``, ``y``, ``z`` and the parameter
            as the last array
        :type velfile: str
        :param stafile: SPECFEM station file, defaults to ``DATA/STATIONS``
        :type stafile: str, optional
        :param initial: ``.npz`` reference model, defaults to None (the horizontal
            average of the model at each depth)
        :type initial: str, optional
        """
        Pltvel.__init__(self, velfile, stafile=stafile)
        self.initial = initial

    def get_dv(self):
        """Compute the perturbation relative to the reference model in ``data_dv``."""
        if self.initial is None:
            mean_vel = np.mean(self.data[self.dataname], axis=(0,1))
            self.ref_vel = np.tile(mean_vel, (self.data['x'].size, self.data['y'].size, 1))
        else:
            self.ref_vel = np.load(self.initial)[self.dataname]
        self.data_dv = {'x': self.data['x'], 'y':self.data['y'], 'z':self.data['z']}
        self.data_dv[self.dataname] = ((self.data[self.dataname]-self.ref_vel)/self.ref_vel)*100
    
    def plot(self, line, cpt=join(dirname(dirname(__file__)), 'cpt/dvp.cpt',), img_scale=35,
             reverse=False, outpath='./figures', colorbar=True, norm=[-10, 10]):
        """Plot a section and save it as ``<outpath>/d<model>_<lat1>_<lon1>_<lat2>_<lon2>.png``.

        :param line: Section from ``lines``
        :type line: dict
        :param cpt: Color table, defaults to the bundled ``dvp.cpt``
        :type cpt: str, optional
        :param img_scale: Section length per cm of figure, defaults to 35
        :type img_scale: float, optional
        :param reverse: Reverse the color table, defaults to False
        :type reverse: bool, optional
        :param outpath: Output directory, defaults to ``./figures``
        :type outpath: str, optional
        :param colorbar: Draw a color bar, defaults to True
        :type colorbar: bool, optional
        :param norm: Color range ``[vmin, vmax]`` in percent; None uses ``cpt`` as
            is, defaults to ``[-10, 10]``
        :type norm: list of float, optional
        """
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
            xlabel = 'Longitude (\\260)'
        else:
            xlabel = 'Distance (km)'
        fig.basemap(region=line['region'],
                    # projection="x0.04c/-0.04c",
                    projection="X{}c/-{}c".format(xscale, yscale),
                    frame=['WSrt', 'xaf+l"{}"'.format(xlabel), 'yaf+l"Depth (km)"'])
        if self.dataname == 'vs':
            label = 'dlnVs'
        elif self.dataname == 'vp':
            label = 'dlnVp'
        else:
            label = 'dln@~\162@~'
        if norm is None:
            cmapp = cpt
        else:
            pygmt.makecpt(cmap=cpt, series=[norm[0], norm[1], 0.1], reverse=reverse, continuous=True)
            cmapp = True
        fig.grdimage(grid=line['grid'], cmap=cmapp)
        fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.1c',
                 style='t{}c'.format(xscale/45), pen='0.5p', fill='gray40', no_clip=True)
        if colorbar:
            fig.colorbar(position="JMR+o0.7c/0c+w4c+ebf", frame=['xag+l"{}"'.format(label), 'y+l"%"'])
        fig.savefig('{}/d{}_{:.1f}_{:.1f}_{:.1f}_{:.1f}.png'.format(
                    outpath, self.fname, *line['pos']))

def main(): 
    """Command-line entry point of ``fwat_plot_dv_sec``."""
    parser = argparse.ArgumentParser('Plot model parameter (Vp, vs or rho) with cross sections')
    parser.add_argument('sections', help='File to line positions or positions of single line (lat1/lon1/lat2/lon2)')
    parser.add_argument('-i', help='Path to 3D data structure in npz format, generated with \'xproject_and_combine_vol_data_on_regular_grid\'',
                        metavar='data_structure_file', required=True)
    parser.add_argument('-r', help='Reference values of averaged data or path to initial model, defaults to averaged data', default=None, metavar='init_model')
    parser.add_argument('-o', help='Output path, defaults to ./figures', default='./figures')
    parser.add_argument('-s', help='Path to STATIONS, defaults to DATA/STATIONS', default='DATA/STATIONS')
    parser.add_argument('-c', help='Whether plot color bar, defaults to False', action='store_true', default=False)
    parser.add_argument('-n', help='Normalize the colors with upper/lower bounds, defaults to None, add \'a\' for auto normalization', default=None, metavar='vmin/vmax')
    parser.add_argument('-C', help='Cmap name', default='dvp', metavar='cpt_name')
    parser.add_argument('-I', help='Whether invert the color map ', default=False, action='store_true')
    parser.add_argument('-d', help='Max depth to plot', type=float, metavar='max_depth', default=None)
    parser.add_argument('-x', help='Unit of x-axis as la, lo or distance, defaults to distance', default=None, metavar='[la|lo]')
    parser.add_argument('-u', help='Use UTM coordinates', action='store_true', default=False)
    parser.add_argument('-a', help='Horizental and vertical spacing in km', default='1/1', metavar='hx/hz')
    parser.add_argument('-l', help='Image scale, defaults to 25', default=25, type=float, metavar='img_scale')
    args = parser.parse_args()
    val = [ float(v) for v in args.a.split('/')]
    
    plotsec =  PltDv(args.i, stafile=args.s, initial=args.r)
    plotsec.get_dv()
    if exists(args.sections):
        lines = np.loadtxt(args.sections)
        for line in lines:
            plotsec.append_lines(plotsec.data_dv, *list(line), utm=args.u,
                                 hval=val[0], vval=val[1], unit_trans=False,
                                 maxdep=args.d, xunit=args.x,)
    else:
        line = [float(v) for v in args.sections.split('/')]
        plotsec.append_lines(plotsec.data_dv, *line, utm=args.u, 
                             hval=val[0], vval=val[1], unit_trans=False,
                             maxdep=args.d, xunit=args.x,)    
    if args.n is None:
        norm = None
    else:
        norm = [float(v) for v in args.n.split('/')]
    if exists(args.C):
        cpt_path = args.C
    else:
        cpt_path = parse_cpt_name(args.C)
    plotsec.plot_all(outpath=args.o, colorbar=args.c,
                     cpt=cpt_path, reverse=args.I,
                     norm=norm, img_scale=args.l)
