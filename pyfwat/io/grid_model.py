import numpy as np
import h5py
from scipy.interpolate import interpn

class GridModel():
    def __init__(self, fname:str, key=None) -> None:
        try:
            npdata = np.load(fname)
            if key is not None:
                self.key_name = key
            else:
                self.key_name = npdata.__dict__['files'][-1]
            self.model = npdata[self.key_name]
            self.x = npdata['x']
            self.y = npdata['y']
            self.z = npdata['z']
        except:
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

    def _meshgrid(self):
        self.xx, self.yy, self.zz = np.meshgrid(self.x, self.y, self.z, indexing='ij')

    def trim(self, sup_m):
        nsup = int(sup_m/self.dx)
        self.x = self.x[nsup:self.x.size-nsup]
        nsup = int(sup_m/self.dy)
        self.y = self.y[nsup:self.y.size-nsup]
        self._meshgrid()
        self.model= self.model[nsup:-nsup, nsup:-nsup, :]
        if self.dv is not None:
            self.dv = self.dv[nsup:-nsup, nsup:-nsup, :]

    def to_geo(self, zone:int):
        from pyproj import Proj
        p = Proj(proj='utm', zone=zone, ellps='WGS84')
        return p(self.xx, self.yy, inverse=True)
    
    def calc_dv(self, ref_model_fname:str):
        with h5py.File(ref_model_fname, 'r') as f:
            ref_model = f[self.key_name][:]
        # self.dv = 100 * (self.model - ref_model) / ref_model
        self.dv = 100 * np.log(self.model / ref_model)
    
    def calc_dv_avg(self):
        self.dv = np.zeros_like(self.model)
        for i in range(self.z.size):
            self.dv[:, :, i] = 100 * (self.model[:, :, i] - np.mean(self.model[:, :, i])) / np.mean(self.model[:, :, i])

    def interp_sec(self, start_point, end_point, is_geo=True, val=5, is_pert=False):
        """ Interpolate the section between two points.

        :param start_point: The start point.
        :type start_point: tuple
        :param end_point: The end point.
        :type end_point: tuple
        :param val: The interval value.
        :type val: float
        """
        from pyproj import Geod

        # Initialize a profile
        if is_geo:
            g = Geod(ellps='WGS84')
            az, _, dist = g.inv(start_point[0],start_point[1],end_point[0],end_point[1])
            sec_range = np.arange(0, dist/1000, val)
            r = g.fwd_intermediate(start_point[0],start_point[1], az, npts=sec_range.size, del_s=val*1000)
            lat = r.lats
            lon = r.lons
        else:
            az = np.arctan2(end_point[1]-start_point[1], end_point[0]-start_point[0])
            dist = np.sqrt((end_point[0]-start_point[0])**2+(end_point[1]-start_point[1])**2)
            sec_range = np.arange(0, dist, val)
            lat = np.zeros(sec_range.size)
            lon = np.zeros(sec_range.size)
            for i, r in enumerate(sec_range):
                lon[i] = start_point[0]+r*np.cos(az)
                lat[i] = start_point[1]+r*np.sin(az)

        # create points array
        points = np.zeros([sec_range.size*self.z.size, 5])
        offset = 0
        for i, lola in enumerate(zip(lon, lat)):
            for _, dep in enumerate(self.z):
                points[offset] = [lola[0], lola[1], dep, sec_range[i], 0.]
                offset += 1

        # Interpolation
        if is_pert:
            model = self.dv
        else:
            model = self.model
        points[:, 4] = interpn(
            (self.x, 
             self.y, 
             self.z),
            model,
            points[:, 0:3],
            bounds_error=False
        )
        return points