"""Gridded HDF5 models with trimming, coordinate conversion and perturbations relative to a reference."""

import numpy as np
import h5py
from scipy.interpolate import interpn
import copy
import xarray as xr


class GridModel():
    """Model on a regular grid stored in HDF5 with ``x``, ``y`` and ``z`` datasets.

    ``model`` holds the values with shape ``(nx, ny, nz)``; ``dv`` holds the
    perturbation in percent after :meth:`calc_dv` or :meth:`calc_dv_avg`.
    """
    def __init__(self, fname:str, key=None) -> None:
        """ Grid model class to handle 3D grid data.

        Parameters
        ----------
        fname : str
            File name of the grid model (hdf5 .h5).
        key : str, optional
            Key name to access the model data.
        """

        with h5py.File(fname, 'r') as f:
            if key is None:
                key_list = list(f.keys())
                for tname in ['x', 'y', 'z']:
                    key_list.remove(tname)
                self.key_name = key_list[0]
            else:
                self.key_name = key
            self.model = f[self.key_name][:]
            self.x = f['x'][:]
            self.y = f['y'][:]
            self.z = f['z'][:]
        self.dx = np.mean(np.diff(self.x))
        self.dy = np.mean(np.diff(self.y))
        self.dz = np.mean(np.diff(self.z))
        self.dv = None
        self._meshgrid()

    def copy(self):
        """ Create a deep copy of the GridModel instance.

        :return: A deep copy of the GridModel instance.
        :rtype: GridModel
        """
        return copy.deepcopy(self)

    def _meshgrid(self):
        """Build the 3-D coordinate arrays ``xx``, ``yy`` and ``zz`` from ``x``, ``y`` and ``z``."""
        self.xx, self.yy, self.zz = np.meshgrid(self.x, self.y, self.z, indexing='ij')

    def trim(self, sup_m):
        """ Trim the model by a specified margin.

        Parameters
        ----------
        sup_m : float
            Margin in meters to trim from each side of the model.
        """
        nsup = int(sup_m/self.dx)
        self.x = self.x[nsup:self.x.size-nsup]
        nsup = int(sup_m/self.dy)
        self.y = self.y[nsup:self.y.size-nsup]
        self._meshgrid()
        self.model= self.model[nsup:-nsup, nsup:-nsup, :]
        if self.dv is not None:
            self.dv = self.dv[nsup:-nsup, nsup:-nsup, :]

    def to_geo(self, zone:int):
        """ Convert UTM coordinates to geographic coordinates (longitude, latitude).

        Parameters
        ----------
        zone : int
            UTM zone number.

        Returns
        -------
        lon : numpy.ndarray
            Longitude values.
        lat : numpy.ndarray
            Latitude values.
        """
        from pyproj import Proj
        p = Proj(proj='utm', zone=zone, ellps='WGS84')
        return p(self.xx, self.yy, inverse=True)
    
    def calc_dv(self, ref_model_fname:str):
        """ Calculate the percentage velocity perturbation (dV/V) compared to a reference model.

        Parameters
        ----------
        ref_model_fname : str
            File name of the reference model (hdf5 .h5).
        """
        with h5py.File(ref_model_fname, 'r') as f:
            ref_model = f[self.key_name][:]
        # self.dv = 100 * (self.model - ref_model) / ref_model
        self.dv = 100 * np.log(self.model / ref_model)
    
    def calc_dv_avg(self):
        """ Calculate the percentage velocity perturbation (dV/V) compared to the average model.
        """
        self.dv = np.zeros_like(self.model)
        for i in range(self.z.size):
            self.dv[:, :, i] = 100 * (self.model[:, :, i] - np.mean(self.model[:, :, i])) / np.mean(self.model[:, :, i])

    def interp_dep(self, depth:float, is_pert:bool=False, output_grid:bool=False,
                   to_geo=None, bounds_error:bool=False, fill_value=None):
        """Interpolate the model on a horizontal slice.

        :param depth: z coordinate of the slice, in the units of ``z``
        :type depth: float
        :param is_pert: Interpolate the perturbation ``dv`` instead of the model,
            defaults to False
        :type is_pert: bool, optional
        :param output_grid: Return a grid instead of a point list, defaults to False
        :type output_grid: bool, optional
        :param to_geo: UTM zone used to convert x and y of the point list to
            longitude and latitude, defaults to None (no conversion)
        :type to_geo: int, optional
        :param bounds_error: Raise an error outside the model, passed to
            :func:`scipy.interpolate.interpn`, defaults to False
        :type bounds_error: bool, optional
        :param fill_value: Value outside the model, passed to
            :func:`scipy.interpolate.interpn`; None extrapolates
        :type fill_value: float, optional
        :return: Grid with ``y`` and ``x`` dimensions if ``output_grid``, otherwise
            an ``(n, 3)`` array of x (or longitude), y (or latitude) and value
        :rtype: xarray.DataArray or numpy.ndarray
        """
        if is_pert:
            model = self.dv
        else:
            model = self.model
        points = np.hstack([[self.xx[:, :, 0].flatten(), self.yy[:, :, 0].flatten(), np.zeros_like(self.xx[:, :, 0].flatten()) + depth]]).T
        value = interpn((self.x, self.y, self.z), model, points, bounds_error=bounds_error, fill_value=fill_value)
        if output_grid:
            grid = xr.DataArray(
                data=value.reshape(self.x.size, self.y.size).T,
                coords=[self.y, self.x],
                dims=['y', 'x']
            )
            return grid
        else:
            if to_geo is not None:
                lo, la = self.to_geo(to_geo)
                out_points = np.array([lo[:, :, 0].flatten(), la[:, :, 0].flatten(), value]).T
            else:
                out_points = np.array([points[:, 0], points[:, 1], value]).T
            return out_points

    def interp_sec(self, start_point, end_point, to_geo=None, val=5, is_pert=False, output_grid=False, x_col=2, convert_km=True):
        """Interpolate the model on a vertical section between two points.

        :param start_point: x and y of the start of the section
        :type start_point: tuple
        :param end_point: x and y of the end of the section
        :type end_point: tuple
        :param to_geo: UTM zone used to report longitude and latitude, defaults to
            None (report x and y)
        :type to_geo: int, optional
        :param val: Sampling interval along the section, in the units of x and y,
            defaults to 5
        :type val: float, optional
        :param is_pert: Interpolate the perturbation ``dv`` instead of the model,
            defaults to False
        :type is_pert: bool, optional
        :param output_grid: Return a grid instead of a point list, defaults to False
        :type output_grid: bool, optional
        :param x_col: Horizontal coordinate of the grid: 0 for x (or longitude),
            1 for y (or latitude), 2 for the distance along the section, defaults to 2
        :type x_col: int, optional
        :param convert_km: Convert the distance to km and z to depth in km
            (``-z / 1000``), defaults to True
        :type convert_km: bool, optional
        :return: Grid of depth by horizontal coordinate if ``output_grid``, otherwise
            an ``(n, 5)`` array of x, y, distance, depth and value
        :rtype: xarray.DataArray or numpy.ndarray
        """
        from pyproj import Proj


        distance = np.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
        num_points = int(distance // val) + 1
        xpoints = np.linspace(start_point[0], end_point[0], num_points)
        ypoints = np.linspace(start_point[1], end_point[1], num_points)
        sec_range = np.sqrt((xpoints - start_point[0])**2 + (ypoints - start_point[1])**2)

        if to_geo is not None:
            if not isinstance(to_geo, int):
                raise ValueError("to_geo must be an integer UTM zone number.")
            p = Proj(proj='utm', zone=to_geo, ellps='WGS84')
            lon, lat = p(self.xx, self.yy, inverse=True)
        else:
            lon = xpoints
            lat = ypoints

        # create points array
        # points = np.zeros([sec_range.size*self.z.size, 5])
        # Interpolation
        if is_pert:
            model = self.dv
        else:
            model = self.model
        value = np.zeros([sec_range.size, self.z.size])
        for iz in range(self.z.size):
            value[:, iz] = interpn((self.x, self.y), model[:, :, iz], np.vstack((xpoints, ypoints)).T, bounds_error=False, fill_value=None)
        
        if convert_km:
            depth = -self.z / 1000
            sec_range = sec_range / 1000
        else:
            depth = self.z
            sec_range = sec_range
        if not output_grid:
            points = np.zeros([sec_range.size*self.z.size, 5])
            for iz in range(self.z.size):
                for ix in range(sec_range.size):
                    points[iz*sec_range.size + ix, 0] = lon[ix]
                    points[iz*sec_range.size + ix, 1] = lat[ix]
                    points[iz*sec_range.size + ix, 2] = sec_range[ix]
                    points[iz*sec_range.size + ix, 3] = depth[iz]
                    points[iz*sec_range.size + ix, 4] = value[ix, iz]
            return points
        else:
            if x_col == 0:
                x = lon
            elif x_col == 1:
                x = lat
            else:
                x = sec_range
            grid = xr.DataArray(
                data=value.T,
                coords=[depth, x],
                dims=['y', 'x']
            )
            return grid
