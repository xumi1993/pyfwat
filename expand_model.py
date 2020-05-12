import numpy as np
from os.path import join, abspath, dirname
import sys
sys.path.append('../')
from semcmd.utils import readpar, readfkpar
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from seispy.signal import smooth

# basepath = abspath(dirname(__file__))


class MeshModel():
    def __init__(self, basepath='./', fname='./model.npz'):
        self.basepath = basepath
        self.model = np.load(fname)
        self.vs = self.model['vel'] * 1000
        self.moho = self.model['moho']
        self.x = self.model['x'] * 1000
        self.dx = np.mean(np.diff(self.x))
        self.z = self.model['z']
        self.zmax = readpar(join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'DEPTH_BLOCK_KM')
        self.zmin = 0
        self.xmin = readpar(join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'LONGITUDE_MIN')
        self.xmax = readpar(join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'LONGITUDE_MAX')
        self.ymin = readpar(join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'LATITUDE_MIN')
        self.ymax = readpar(join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'LATITUDE_MAX')
        self.fkmodel = readfkpar(join(basepath, 'DATA/FKMODEL'), 'LAYER')
        self.fkmodel[:, -1] /= -1000
        self.set1dmod()
    
    def smooth(self):
        for i, x in enumerate(self.x):
            idx = np.where(self.z >= self.moho[i])[0][0]
            self.vs[idx:, i] = smooth(self.vs[idx:, i], window='hanning')

    def set1dmod(self):
        self.zmodel = np.arange(self.zmin, self.zmax)
        self.vs1d = np.empty_like(self.zmodel)
        self.vs1d[np.where(self.zmodel < self.fkmodel[1, -1])] = self.fkmodel[0, -2]
        self.vs1d[np.where(self.zmodel >= self.fkmodel[1, -1])] = self.fkmodel[1, -2]
        self.vp1d = np.empty_like(self.zmodel)
        self.vp1d[np.where(self.zmodel < self.fkmodel[1, -1])] = self.fkmodel[0, -3]
        self.vp1d[np.where(self.zmodel >= self.fkmodel[1, -1])] = self.fkmodel[1, -3]
        # print(self.vp1d)

    def expand_x(self, buffer_x=50000, buffer_z=30):
        self.buffer_x = buffer_x
        self.xmodel = np.arange(self.xmin, self.xmax+self.dx, self.dx)
        self.vsxz = np.zeros([self.zmodel.shape[0], self.xmodel.shape[0]])
        for i, dep in enumerate(self.z):
            self.vsxz[i][np.where(self.xmodel<self.xmin+buffer_x)] = self.vs1d[i]
            idx_buffer_left = np.where((self.xmodel>=self.xmin+buffer_x) & (self.xmodel<self.x[0]))[0]
            if dep < self.moho[0]:
                vs_buffer_left = np.linspace(self.vs1d[0], self.vs[i][0], idx_buffer_left.shape[0])
            else:
                vs_buffer_left = np.linspace(self.vs1d[-1], self.vs[i][0], idx_buffer_left.shape[0])
            # print(idx_buffer_left, vs_buffer_left, self.vsxz[i])
            self.vsxz[i][idx_buffer_left] = vs_buffer_left
            idx_model_begin = np.where(self.xmodel==self.x[0])[0][0]
            self.vsxz[i][idx_model_begin:idx_model_begin+self.x.shape[0]] = self.vs[i]
            idx_buffer_right = np.where((self.xmodel>self.x[-1]) & (self.xmodel<=self.xmax-buffer_x))[0]
            if dep < self.moho[-1]:
                vs_buffer_right = np.linspace(self.vs[i][-1], self.vs1d[0], idx_buffer_right.shape[0])
            else:
                vs_buffer_right = np.linspace(self.vs[i][-1], self.vs1d[-1], idx_buffer_right.shape[0])
            self.vsxz[i][idx_buffer_right] = vs_buffer_right
            self.vsxz[i][np.where(self.xmodel>self.xmax-buffer_x)] = self.vs1d[i]
            self.expand_z(buffer_z)
        
    def expand_z(self, buffer_z=30):
        for i, x in enumerate(self.xmodel):
            idx = np.where((self.zmodel>self.z[-1]) & (self.zmodel<=self.z[-1]+buffer_z))[0]
            self.vsxz[idx, i] = np.linspace(self.vsxz[idx[0]-1, i], self.vs1d[-1], idx.shape[0])
            idx = np.where(self.zmodel>self.z[-1]+buffer_z)[0]
            self.vsxz[idx, i] = self.vs1d[-1]
        
    def expand_y(self, buffer_y=50000, vel_y=30000):
        self.ymodel = np.arange(self.ymin, self.ymax+self.dx, self.dx)
        self.vs3d = np.zeros([self.zmodel.shape[0], self.ymodel.shape[0], self.xmodel.shape[0]])
        vsxz1d = np.tile(self.vs1d.reshape(-1, 1), (1, self.xmodel.shape[0]))
        idx = np.where((self.ymodel>=-vel_y) & (self.ymodel<=vel_y))[0]
        for i in idx:
            self.vs3d[:, i, :] = self.vsxz
        idx = np.where((self.ymodel>=self.ymin+buffer_y) & (self.ymodel<-vel_y))[0]
        buffer_3d = np.linspace(vsxz1d, self.vsxz, idx.shape[0])
        for i, index in enumerate(idx):
            self.vs3d[:, index, :] = buffer_3d[i, :, :]
        idx = np.where((self.ymodel>vel_y) & (self.ymodel<=self.ymax-buffer_y))[0]
        buffer_3d = np.linspace(self.vsxz, vsxz1d, idx.shape[0])
        for i, index in enumerate(idx):
            self.vs3d[:, index, :] = buffer_3d[i, :, :]
        idx = np.where((self.ymodel<self.ymin+buffer_y) | (self.ymodel>self.ymax-buffer_y))[0]
        for i in idx:
            self.vs3d[:, i, :] = vsxz1d
        
    def plotyz(self, x=100000):
        xidx = np.where(self.ymodel == x)[0][0]
        yz = self.vs3d[:, :, xidx]
        plt.figure()
        plt.pcolormesh(self.ymodel, self.zmodel, yz, cmap='jet_r')
        plt.gca().invert_yaxis()
        plt.xlabel('Y (m)')
        plt.ylabel('Z (km)')
        plt.colorbar()
        plt.savefig('vs_yz_{}.png'.format(x), bbox_inches='tight')

        
    def plotxz(self, y=0):
        yidx = np.where(self.ymodel == y)[0][0]
        xz = self.vs3d[:, yidx, :]
        plt.figure(figsize=(10,3))
        plt.pcolormesh(self.xmodel, self.zmodel, xz, cmap='jet_r')
        plt.gca().invert_yaxis()
        plt.xlabel('X (m)')
        plt.ylabel('Z (km)')
        plt.colorbar()
        plt.savefig('vs_xz.png', bbox_inches='tight')



if __name__ == "__main__":
    mm = MeshModel()
    mm.expand_x()
    # mm.plotxz()
    mm.expand_y()
    # mm.plotyz()
    print(mm.vs3d[0, 15, 100])
    # print(mm.fkmodel)