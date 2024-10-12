import numpy as np
import h5py

class GridModel():
    def __init__(self, fname:str) -> None:
        # npdata = np.load(fname)
        # self.model = npdata[npdata.__dict__['files'][-1]]
        # self.x = npdata['x']
        # self.y = npdata['y']
        # self.z = npdata['z']
        with h5py.File(fname, 'r') as f:
            key_list = list(f.keys())
            for tname in ['x', 'y', 'z']:
                key_list.remove(tname)
            self.key_name = key_list[0]
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
        self.dv = 100 * (self.model - ref_model) / ref_model
