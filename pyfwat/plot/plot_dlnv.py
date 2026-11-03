"""Cross sections of the relative perturbation of a model with respect to an initial model."""

import numpy as np
import pygmt
from scipy.interpolate import interpn
import sys


def proj_sta(stafile, lat1, lon1, lat2, lon2):
    """Project stations onto a great-circle section.

    :param stafile: SPECFEM station file
    :type stafile: str
    :param lat1: Latitude of the start of the section
    :type lat1: float
    :param lon1: Longitude of the start of the section
    :type lon1: float
    :param lat2: Latitude of the end of the section
    :type lat2: float
    :param lon2: Longitude of the end of the section
    :type lon2: float
    :return: ``NET.STA`` names, distances along the section in km and elevations
    :rtype: tuple
    """
    st, net, stla, stlo, stel = np.loadtxt(stafile, usecols=[0,1,2,3,4],
                                           dtype = {'names': ('station', 'net','stla', 'stlo', 'stel'),
                                                        'formats': ('U20', 'U20', 'f4', 'f4', 'f2')},
                                           unpack=True, ndmin=1)
    sta = ['{}.{}'.format(net[i], st[i]) for i in range(st.size)]
    pos = np.vstack((stlo, stla)).T
    st_pos = pygmt.project(pos, center=[lon1, lat1], endpoint=[lon2, lat2], convention='p', unit=True)
    # dimension need to be checked
    return sta, st_pos.values[:,0], stel


def interp_sec(data, datainit, lat1, lon1, lat2, lon2, hval=0.5, vval=0.5, name='vs'):
    """Interpolate the perturbation of a model relative to an initial model on a section.

    The perturbation is ``100 * (m - m0) / m0`` in percent.

    :param data: Model with ``x`` (longitude), ``y`` (latitude), ``z`` (km) and
        parameter arrays
    :type data: Mapping
    :param datainit: Initial model on the same grid
    :type datainit: Mapping
    :param lat1: Latitude of the start of the section
    :type lat1: float
    :param lon1: Longitude of the start of the section
    :type lon1: float
    :param lat2: Latitude of the end of the section
    :type lat2: float
    :param lon2: Longitude of the end of the section
    :type lon2: float
    :param hval: Horizontal sampling interval in km, defaults to 0.5
    :type hval: float, optional
    :param vval: Vertical sampling interval in km, defaults to 0.5
    :type vval: float, optional
    :param name: Name of the parameter, defaults to ``'vs'``
    :type name: str, optional
    :return: Section points (longitude, latitude, distance), depth samples and
        the section grid
    :rtype: tuple
    """
    points = pygmt.project(center='{}/{}'.format(lon1, lat1),
                       endpoint='{}/{}'.format(lon2, lat2),
                       generate=hval, unit=True)
    data_enf = ((data[name] - datainit[name]) / datainit[name])*100
    depth = np.arange(data['z'][0], 0-vval, vval)
    points2d = np.empty([0, 4])
    for i, x in enumerate(points.values):
        for j,d in enumerate(depth):
            points2d = np.vstack((points2d, np.append(x, d)))
    # inter_dep, inter_y, inter_x = np.meshgrid(data['z'], data['y'], data['x'], indexing='ij')
    points_value = interpn((data['x'], data['y'], data['z']),
                            data_enf, points2d[:, [0, 1, 3]], bounds_error=False, fill_value=None)
    grid = pygmt.surface(x=points2d[:, 2], y=-points2d[:, 3], z=points_value,
                         region=[points.values[0, -1], points.values[-1, -1], 0, -depth[0]],
                         spacing='{}/{}'.format(hval, vval))
    return points, depth, grid


class Pltdlnv():
    """Cross sections of the perturbation of a model relative to the initial model.

    Reads ``output_vtk/<modid>_<dataname>_projected.npz`` and
    ``output_vtk/<dataname>_initial_projected.npz``.
    """
    def __init__(self, modid, dataname, stafile='src_rec/STATIONS_1'):
        """:param modid: Model name, e.g. ``M03``
        :type modid: str
        :param dataname: Parameter name, e.g. ``vs``
        :type dataname: str
        :param stafile: SPECFEM station file, defaults to ``src_rec/STATIONS_1``
        :type stafile: str, optional
        """
        self.modid = modid
        self.dataname = dataname
        self.stafile = stafile
        self.data = np.load('output_vtk/{}_{}_projected.npz'.format(modid, dataname))
        self.init_data = np.load('output_vtk/{}_initial_projected.npz'.format(dataname))
        self.lines = []
    
    def append_lines(self, lat1, lon1, lat2, lon2):
        """Interpolate the perturbation on a section and add it to ``lines``.

        :param lat1: Latitude of the start of the section
        :type lat1: float
        :param lon1: Longitude of the start of the section
        :type lon1: float
        :param lat2: Latitude of the end of the section
        :type lat2: float
        :param lon2: Longitude of the end of the section
        :type lon2: float
        """
        sta, stpos, stel = proj_sta(self.stafile, lat1, lon1, lat2, lon2)
        points, depth, grid = interp_sec(self.data, self.init_data,
                                lat1, lon1, lat2, lon2, hval=0.5,
                                vval=0.5, name=self.dataname)
        region = [points.values[0, 2], points.values[-1, 2], 0, -depth[0]]
        self.lines.append({'pos':[lat1, lon1, lat2, lon2], 'sta':sta,
                           'stpos':stpos, 'stel':stel, 'grid':grid, 'region':region})
    
    def plot(self, line, cpt='../semcmd/cpt/dvp.cpt', outpath='./figures', vmax=12, cpt_span=50):
        """Plot a section and save it as a PNG.

        The figure is ``<outpath>/<modid>_<dataname>_<lat1>_<lon1>_<lat2>_<lon2>.png``.

        :param line: Section from ``lines``
        :type line: dict
        :param cpt: Color table, defaults to ``../semcmd/cpt/dvp.cpt``
        :type cpt: str, optional
        :param outpath: Output directory, defaults to ``./figures``
        :type outpath: str, optional
        :param vmax: Color range ``[-vmax, vmax]`` in percent, defaults to 12
        :type vmax: float, optional
        :param cpt_span: Number of color intervals, defaults to 50
        :type cpt_span: int, optional
        """
        fig = pygmt.Figure()
        fig.basemap(region=line['region'],
                    projection="x0.1c/-0.1c",
                    frame=['WSrt+t"{}"'.format(self.dataname), 'xaf+l"Distance (km)"', 'yaf+l"Depth (km)"'])
        pygmt.makecpt(cmap=cpt, series=[-vmax, vmax, 2*vmax/cpt_span], continuous=True)
        fig.grdimage(grid=line['grid'], cmap=True)
        fig.plot(x=line['stpos'], y=line['stel'], offset='0/0.15c',
                 style='t0.3c', pen='0.5p', fill='gray40', no_clip=True)
        fig.colorbar(position="JMR+o0.7c/0c+w5c/0.3c+ebf", frame=['xag+l"dln{}"'.format(self.dataname), 'y+l"%"'])
        fig.savefig('{}/{}_{}_{:.1f}_{:.1f}_{:.1f}_{:.1f}.png'.format(
                    outpath, self.modid, self.dataname, *line['pos']))
    
    def plot_all(self, **kwargs):
        """Plot every section in ``lines``.

        :param kwargs: Arguments passed to :meth:`plot`
        """
        for line in self.lines:
            self.plot(line, **kwargs)


if __name__ == '__main__':
    if len(sys.argv[1:]) != 2:
        print('Usage: plot_sec.py data_filename')
        sys.exit(1)
    modid = sys.argv[1]
    dataname = sys.argv[2]
    pltv = Pltdlnv(modid, dataname)
    pltv.append_lines(0, 0, 0, 1)
    pltv.append_lines(-0.2, 0.5, 0.2, 0.5)
    pltv.plot_all()
