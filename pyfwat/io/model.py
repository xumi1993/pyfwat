import h5py
import numpy as np
from scipy.interpolate import interpn

class FWATModel:
    def __init__(self) -> None:
        """Initialize the FWATModel class.
        """
        self.model = np.array([])
        self.x = np.array([])
        self.y = np.array([])
        self.z = np.array([])
        self.xx = np.array([])
        self.yy = np.array([])
        self.zz = np.array([])
        self.dx = 0.
        self.dy = 0.
        self.dz = 0.
        self.keyname = ''

    @classmethod
    def read(cls, filename, keyname):
        """Read the FWAT model from a HDF5 file.

        :param filename: The filename of the HDF5 file.
        :type filename: str
        :param keyname: The keyname of the dataset.
        :type keyname: str
        :return: The FWATModel object.
        :rtype: FWATModel
        """
        fm = cls()
        with h5py.File(filename, 'r') as f:
            fm.model = f[keyname][:]
            fm.x = f['x'][:]
            fm.y = f['y'][:]
            fm.z = f['z'][:]
        fm.dx = np.mean(np.diff(fm.x))
        fm.dy = np.mean(np.diff(fm.y))
        fm.dz = np.mean(np.diff(fm.z))
        fm.xx, fm.yy, fm.zz = np.meshgrid(fm.x, fm.y, fm.z, indexing='ij')
        if fm.xx.size != fm.model.size:
            raise ValueError(f'The model size {fm.model.shape} does not match the grid size {fm.xx.shape}.')
        fm.keyname = keyname
        return fm
    
    def to_geo(self, zone):
        """
        Convert the x, y coordinates to geographic coordinates.

        :param zone: The UTM zone.
        :type zone: int
        """
        from pyproj import Proj
        p = Proj(proj='utm', zone=zone, ellps='WGS84')
        self.xx, self.yy = p(self.xx, self.yy, inverse=True)

    def interp_sec(self, start_point, end_point, is_geo=True, val=5):
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
        points[:, 4] = interpn(
            (self.x, 
             self.y, 
             self.z),
            self.model,
            points[:, 0:3],
            bounds_error=False
        )
        return points
        
    