import numpy as np
from os.path import join, abspath, dirname
from pyfwat.utils import readpar, readfkpar
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from seispy.signal import smooth
from .create_interf_z import read_interface, InterfZ

# basepath = abspath(dirname(__file__))


def cos_buffer(v1, v2, nv):
    if v1 > v2:
        return np.cos(np.linspace(0, np.pi/2, nv))**2*(v1-v2)+v2
    elif v1 < v2:
        return np.cos(np.linspace(np.pi/2., np.pi, nv))**2*(v2-v1)+v1
    else:
        return np.ones(nv) * v1


class MeshModel():
    def __init__(self, iz, basepath='./', fname='./model.npz'):
        self.iz = iz
        self.basepath = basepath
        self.model = np.load(fname)
        self.vs = self.model['vel'] * 1000
        self.moho = self.model['moho']
        self.x = self.model['x'] * 1000
        self.dx = np.mean(np.diff(self.x))
        self.z = self.model['z']
        self.zmax = readpar(join(basepath, 'Mesh_Par_file_header'), 'DEPTH_BLOCK_KM')
        self.zmin = 0
        self.xmin = readpar(join(basepath, 'Mesh_Par_file_header'), 'LONGITUDE_MIN')
        self.xmax = readpar(join(basepath, 'Mesh_Par_file_header'), 'LONGITUDE_MAX')
        self.ymin = readpar(join(basepath, 'Mesh_Par_file_header'), 'LATITUDE_MIN')
        self.ymax = readpar(join(basepath, 'Mesh_Par_file_header'), 'LATITUDE_MAX')
        self.fkmodel = readfkpar(join(basepath, 'DATA/FKMODEL'), 'LAYER')
        self.fkmodel[:, -1] /= -1000
        self.set1dmod()
        self.xmodel = np.arange(self.xmin, self.xmax+self.dx, self.dx)
        self.ymodel = np.arange(self.ymin, self.ymax+self.dx, self.dx)
    
    def read_moho(self, i, j):
        return np.round(self.iz.interface[i, j]/-1000)

    def smooth(self):
        for i, x in enumerate(self.x):
            idx = np.where(self.z >= self.moho[i])[0][0]
            self.vs[idx:, i] = smooth(self.vs[idx:, i], window='hanning')

    def make_vs1d(self, moho, num):
        dep_1d = np.array([0, moho, moho+0.01, 100])
        vs = np.array([self.fkmodel[0, -2], self.fkmodel[0, -2], self.fkmodel[1, -2], self.fkmodel[1, -2]])
        return interp1d(dep_1d, vs)(self.zmodel[:num])

    def set1dmod(self):
        self.zmodel = np.arange(self.zmin, self.zmax)
        self.vs1d = np.empty_like(self.zmodel)
        self.vs1d[np.where(self.zmodel < self.fkmodel[1, -1])] = self.fkmodel[0, -2]
        self.vs1d[np.where(self.zmodel >= self.fkmodel[1, -1])] = self.fkmodel[1, -2]
        self.vp1d = np.empty_like(self.zmodel)
        self.vp1d[np.where(self.zmodel < self.fkmodel[1, -1])] = self.fkmodel[0, -3]
        self.vp1d[np.where(self.zmodel >= self.fkmodel[1, -1])] = self.fkmodel[1, -3]
        # print(self.vp1d)

    def expand_x(self, buffer_x=50000, buffer_z=20):
        num = self.z.shape[0]
        self.buffer_x = buffer_x
        self.vsxz = np.zeros([self.zmodel.shape[0], self.xmodel.shape[0]])
        idx_buffer_left = np.where((self.xmodel>=self.xmin+buffer_x) & (self.xmodel<self.x[0]))[0]
        idx_begin = np.where(self.xmodel==self.xmin+buffer_x)[0][0]
        moho = self.read_moho(int(self.ymodel.size/2), idx_begin)
        vs1d = self.make_vs1d(moho, num)
        vs_buffer_left = np.linspace(vs1d, self.vs[:, 0], idx_buffer_left.size).T

        idx_buffer_right = np.where((self.xmodel>self.x[-1]) & (self.xmodel<=self.x[-1]+buffer_x))[0]
        idx_end = np.where(self.xmodel==self.x[-1]+buffer_x)[0][0]
        moho = self.read_moho(int(self.ymodel.size/2), idx_end)
        vs1d = self.make_vs1d(moho, num)
        # print(moho, vs1d[34])
        vs_buffer_right = np.linspace(self.vs[:, -1], vs1d, idx_buffer_right.size).T
        for i, x in enumerate(self.xmodel):
            if x < self.xmin+buffer_x or x > self.x[-1]+buffer_x:
                moho = self.read_moho(int(self.ymodel.size/2), i)
                vs1d = self.make_vs1d(moho, num)
                # print(x, moho, vs1d[34])
                self.vsxz[:num, i] = vs1d
            elif self.xmin+buffer_x <= x < self.x[0]:
                idx = np.where(idx_buffer_left == i)[0]
                self.vsxz[:num, i] = vs_buffer_left[:, idx].reshape(-1)
            elif self.x[-1] < x <= self.x[-1]+buffer_x:
                idx = np.where(idx_buffer_right == i)[0]
                self.vsxz[:num, i] = vs_buffer_right[:, idx].reshape(-1)
            else:
                pass
        self.idx_model_begin = np.where(self.xmodel==self.x[0])[0][0]
        self.vsxz[:num, self.idx_model_begin:self.idx_model_begin+self.x.shape[0]] = self.vs
        # self.expand_z(buffer_z)

    '''
    def expand_x(self, buffer_x=50000, buffer_z=20):
        self.buffer_x = buffer_x
        self.xmodel = np.arange(self.xmin, self.xmax+self.dx, self.dx)
        self.vsxz = np.zeros([self.zmodel.shape[0], self.xmodel.shape[0]])
        for i, dep in enumerate(self.z):
            idx_buffer_left = np.where((self.xmodel>=self.xmin+buffer_x) & (self.xmodel<self.x[0]))[0]
            if dep < self.moho[0]:
                vs_buffer_left = np.linspace(self.vs1d[0], self.vs[i][0], idx_buffer_left.shape[0])
                self.vsxz[i][np.where(self.xmodel<self.xmin+buffer_x)] = self.vs1d[0]
            else:
                vs_buffer_left = np.linspace(self.vs1d[-1], self.vs[i][0], idx_buffer_left.shape[0])
                self.vsxz[i][np.where(self.xmodel<self.xmin+buffer_x)] = self.vs1d[-1]
            # print(idx_buffer_left, vs_buffer_left, self.vsxz[i])
            self.vsxz[i][idx_buffer_left] = vs_buffer_left
            idx_model_begin = np.where(self.xmodel==self.x[0])[0][0]
            self.vsxz[i][idx_model_begin:idx_model_begin+self.x.shape[0]] = self.vs[i]
            idx_buffer_right = np.where((self.xmodel>self.x[-1]) & (self.xmodel<=self.xmax-buffer_x))[0]
            if dep < self.moho[-1]:
                # vs_buffer_right = np.linspace(self.vs[i][-1], self.vs1d[0], idx_buffer_right.shape[0])
                vs_buffer_right = cos_buffer(self.vs[i][-1], self.vs1d[0], idx_buffer_right.shape[0])
                self.vsxz[i][np.where(self.xmodel>self.xmax-buffer_x)] = self.vs1d[0]
            else:
                # vs_buffer_right = np.linspace(self.vs[i][-1], self.vs1d[-1], idx_buffer_right.shape[0])
                vs_buffer_right = cos_buffer(self.vs[i][-1], self.vs1d[-1], idx_buffer_right.shape[0])
                self.vsxz[i][np.where(self.xmodel>self.xmax-buffer_x)] = self.vs1d[-1]
            self.vsxz[i][idx_buffer_right] = vs_buffer_right
            
            self.expand_z(buffer_z)
        # print(self.xmodel[428:430])
    '''

    def expand_z(self, buffer_z=20):
        for i, x in enumerate(self.xmodel):
            for j, y in enumerate(self.ymodel):
                idx = np.where((self.zmodel>self.z[-1]) & (self.zmodel<=self.z[-1]+buffer_z))[0]
                self.vs3d[idx, j, i] = np.linspace(self.vs3d[idx[0]-1, j, i], self.vs1d[-1], idx.shape[0])
                idx = np.where(self.zmodel>self.z[-1]+buffer_z)[0]
                self.vs3d[idx, j, i] = self.vs1d[-1]

    def expand_yy(self, vel_y=50000, buffer_y=30000):
        self.vel_y = vel_y
        self.buffer_y = buffer_y
        num = self.z.shape[0]
        self.vs3d = np.zeros([self.zmodel.shape[0], self.ymodel.shape[0], self.xmodel.shape[0]])
        idx = np.where((self.ymodel>=-vel_y) & (self.ymodel<=vel_y))[0]
        for i in idx:
            self.vs3d[:, i, :] = self.vsxz
        idx = np.where((self.ymodel>=self.ymin+buffer_y) & (self.ymodel<-vel_y))[0]
        for i, x in enumerate(self.xmodel):
            moho = self.read_moho(idx[-1], i)
            vs1d = self.make_vs1d(moho, num)
            vsz = self.vsxz[:num, i]
            self.vs3d[:num, idx, i] = np.linspace(vs1d, vsz, idx.size).T
        idx = np.where((self.ymodel>vel_y) & (self.ymodel<=self.ymax-buffer_y))[0]
        for i, x in enumerate(self.xmodel):
            moho = self.read_moho(idx[0], i) 
            vs1d = self.make_vs1d(moho, num)
            vsz = self.vsxz[:num, i]
            self.vs3d[:num, idx, i] = np.linspace(vsz, vs1d, idx.size).T
        idx = np.where((self.ymodel<self.ymin+buffer_y) | (self.ymodel>self.ymax-buffer_y))[0]
        for i, x in enumerate(self.xmodel):
            for j in idx:
                moho = self.read_moho(j, i) 
                vs1d = self.make_vs1d(moho, num)
                self.vs3d[:num, j, i] = vs1d
    
    def expand_buffer(self, iz):
        num = self.z.shape[0]
        for i, x in enumerate(self.xmodel):
            for j, y in enumerate(self.ymodel):
                if (x < self.xmin + self.buffer_x or x > self.x[-1] + self.buffer_x or
                   y < self.ymin + self.buffer_y or y > self.ymax-self.buffer_y):
                    moho = self.read_moho(j, i)
                    vs1d = self.make_vs1d(moho, num)
                    self.vs3d[:num, j, i] = vs1d

        
    def expand_y(self, buffer_y=50000, vel_y=30000):
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
        
    def plotyz(self, x=360000):
        # xidx = np.where(self.ymodel == x)[0][0]
        xidx = np.argmin(np.abs(self.xmodel - x))
        x = self.xmodel[xidx]
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
        # xz = self.vsxz
        plt.figure(figsize=(10,3))
        plt.pcolormesh(self.xmodel, self.zmodel, xz, cmap='jet_r')
        plt.gca().invert_yaxis()
        plt.xlabel('X (m)')
        plt.ylabel('Z (km)')
        plt.colorbar()
        plt.savefig('vs_xz.png', bbox_inches='tight')



def loadnpz(fname='./model_dep100.npz'):
    model = np.load(fname)
    moho = model['moho'] * -1000
    x = model['x'] * 1000
    z = model['z'] * 1000
    return x, moho


def create_moho(z_buffer=-34000, x_buffer=50000, y_buffer=30000):
    interf_para = read_interface('DATA/meshfem3D_files/interfaces.dat', inter_num=1)
    iz = InterfZ(*interf_para)
    x, moho = loadnpz()
    iz.loadxz(x, moho)
    iz.interf_buffer(z_buffer, iz.xmin, iz.xmin+x_buffer, direct='left')
    iz.interf_buffer(z_buffer, iz.xmax-x_buffer, iz.xmax, direct='right')
    iz.y_smooth(z_buffer, iz.ymin, iz.ymin+y_buffer, iz.ymax-y_buffer, iz.ymax)
    return iz


if __name__ == "__main__":
    iz = create_moho()
    mm = MeshModel(iz, basepath='/scratch/goxu/xu_mijian/semfk/yn',
                   fname='/scratch/goxu/xu_mijian/semfk/yn/model_dep100.npz')
    mm.expand_x()
    mm.expand_yy()
    # mm.expand_buffer(iz)
    mm.expand_z()
    mm.plotxz()
    mm.plotyz()
    # print(mm.vs3d[0, 15, 100])
    # print(mm.fkmodel)