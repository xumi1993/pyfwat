import numpy as np
import h5py
from scipy.interpolate import interpn
import copy
import xarray as xr


class GridModel():
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
        """ Interpolate the model at a specific depth.

        :param depth: The depth to interpolate.
        :type depth: float
        :param is_pert: Whether to interpolate the perturbation model.
        :type is_pert: bool
        :return: The interpolated 2D model at the specified depth.
        :rtype: numpy.ndarray
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
        """ Interpolate the section between two points.

        :param start_point: The start point.
        :type start_point: tuple
        :param end_point: The end point.
        :type end_point: tuple
        :param val: The interval value.
        :type val: float
        :param is_geo: Whether the input points are in geographic coordinates.
        :type is_geo: bool
        :param is_pert: Whether to interpolate the perturbation model.
        :type is_pert: bool
        :param output_grid: Whether to output the result as a grid.
        :type output_grid: bool
        :param x_col: The column index for the x-coordinate in the output grid.
        :type x_col: int
        :return: The interpolated points or grid.
        :rtype: numpy.ndarray or xarray.DataArray
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