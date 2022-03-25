import numpy as np
import sys
sys.path.append('../')
# semcmd is open accessed at https://git.nju.edu.cn/xumi1993/semcmd
from semcmd.expand_model import MeshModel
from semcmd.utils import readpar
from semcmd.create_interf_z import InterfZ, read_interface
from scipy.interpolate import interp1d, interpn, interp2d
from os.path import join, dirname, abspath
from seispy.signal import smooth

basepath = abspath(dirname(__file__))
model_file = 'model_dep100.npz'

def read_model(iz, buffer_x, buffer_y):
    mm = MeshModel(iz, basepath=basepath, fname=join(basepath, model_file))
    # mm.smooth()
    mm.expand_x(buffer_x, buffer_z=20)
    mm.expand_yy(buffer_y=buffer_y)
    mm.expand_z()
    mm.plotxz()
    mm.plotyz()
    return mm


def loadnpz(fname=join(basepath, model_file)):
    model = np.load(fname)
    moho = model['moho'] * -1000
    x = model['x'] * 1000
    z = model['z'] * 1000
    return x, moho


def create_moho(z_buffer=-34000, x_buffer=50000, y_buffer=30000):
    interf_para = read_interface(join(basepath, 'DATA/meshfem3D_files/interfaces.dat'), inter_num=1)
    iz = InterfZ(*interf_para)
    x, moho = loadnpz()
    iz.loadxz(x, moho)
    iz.interf_buffer(z_buffer, iz.xmin, iz.xmin+x_buffer, direct='left')
    iz.interf_buffer(z_buffer, iz.xmax-x_buffer, iz.xmax, direct='right')
    iz.y_smooth(z_buffer, iz.ymin, iz.ymin+y_buffer, iz.ymax-y_buffer, iz.ymax)
    iz.plotxz()
    iz.write_interface(join(basepath, 'DATA/meshfem3D_files/interf_2.dat'))
    return iz


class Mesh():
    def __init__(self, buffer_x=50000, buffer_y=30000, layer_m=42, layer_c=18):
        iz = create_moho()
        self.layer_m = layer_m
        self.layer_c = layer_c
        self.buffer_x = buffer_x
        self.buffer_y = buffer_y
        self.meshmodel = read_model(iz, self.buffer_x, self.buffer_y)
        self.materials = np.empty([0, 4])
        for layer in self.meshmodel.fkmodel:
            self.materials = np.vstack((self.materials, np.array([layer[0], layer[1], layer[2], layer[3]])))
        self.z = self.meshmodel.zmodel[::-1]*-1000
        self.x_moho = iz.xaxis
        self.y_moho = iz.yaxis
        self.moho = iz.interface
        self.mesh_str = []
        self.interp_axis()
    
    def interp_axis(self):
        self.x_num = int(readpar(join(self.meshmodel.basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'NEX_XI'))
        self.x_mesh = np.linspace(self.meshmodel.xmin, self.meshmodel.xmax, self.x_num+1)[:-1]
        self.y_num = int(readpar(join(self.meshmodel.basepath, 'DATA/meshfem3D_files/Mesh_Par_file'), 'NEX_ETA'))
        self.y_mesh = np.linspace(self.meshmodel.ymin, self.meshmodel.ymax, self.y_num+1)[:-1]
    
    def gen_mesh(self, kappa=1.732, stable_mantle=False):
        for i, x in enumerate(self.x_mesh):
            for j, y in enumerate(self.y_mesh):
                moho = interp2d(self.x_moho, self.y_moho, self.moho, bounds_error=False, fill_value='extrapolate')(x, y)[0]
                dep = self.mesh_dep(moho)
                points = np.array([[d/-1000, y, x] for d in dep])
                vs1d = interpn((self.meshmodel.zmodel, self.meshmodel.ymodel, self.meshmodel.xmodel), self.meshmodel.vs3d, points, bounds_error=False)
                # if x == 331250. and y == 0:
                #     print(dep, vs1d)
                if stable_mantle:
                    self.mesh_str.append('{0} {0} {1} {1} 1 {2} 2\n'.format(i+1, j+1, self.layer_m))
                    for k, z in enumerate(dep[self.layer_m:]):
                        k += self.layer_m
                        vs = np.round(vs1d[k])
                        # material = self.mesh1d(z, moho, vs, kappa=kappa)
                        material = self.mesh1d_sm(z, vs, kappa=kappa)
                        self.mesh_str.append('{0} {0} {1} {1} {2} {2} {3}\n'.format(i+1, j+1, k+1, int(material)))
                else:
                    for k, z in enumerate(dep):
                        vs = np.round(vs1d[k])
                        material = self.mesh1d(z, moho, vs, kappa=kappa)
                        self.mesh_str.append('{0} {0} {1} {1} {2} {2} {3}\n'.format(i+1, j+1, k+1, int(material)))

    def loop_mesh(self, kappa=1.732, stable_mantle=False):
        for i, x in enumerate(self.x_mesh):
            for j, y in enumerate(self.y_mesh):
                if x < self.meshmodel.xmin+self.buffer_x or x > self.meshmodel.xmax-self.buffer_x:
                    self.mesh_str.append('{0} {0} {1} {1} 1 {2} 2\n'.format(i+1, j+1, self.layer_m))
                    self.mesh_str.append('{0} {0} {1} {1} {2} {3} 1\n'.format(i+1, j+1, self.layer_m+1, self.layer_c+self.layer_m))
                elif y < self.meshmodel.ymin+self.buffer_y and (self.meshmodel.xmin+self.buffer_x <= x <= self.meshmodel.xmax-self.buffer_x):
                    self.mesh_str.append('{0} {0} {1} {1} 1 {2} 2\n'.format(i+1, j+1, self.layer_m))
                    self.mesh_str.append('{0} {0} {1} {1} {2} {3} 1\n'.format(i+1, j+1, self.layer_m+1, self.layer_c+self.layer_m))
                elif y > self.meshmodel.ymax-self.buffer_y and (self.meshmodel.xmin+self.buffer_x <= x <= self.meshmodel.xmax-self.buffer_x):
                    self.mesh_str.append('{0} {0} {1} {1} 1 {2} 2\n'.format(i+1, j+1, self.layer_m))
                    self.mesh_str.append('{0} {0} {1} {1} {2} {3} 1\n'.format(i+1, j+1, self.layer_m+1, self.layer_c+self.layer_m))
                else:
                    moho = interp2d(self.x_moho, self.y_moho, self.moho, bounds_error=False, fill_value='extrapolate')(x, y)[0]
                    dep = self.mesh_dep(moho)
                    points = np.array([[d/-1000, y, x] for d in dep])
                    vs1d = interpn((self.meshmodel.zmodel, self.meshmodel.ymodel, self.meshmodel.xmodel), self.meshmodel.vs3d, points, bounds_error=False)
                    if stable_mantle:
                        self.mesh_str.append('{0} {0} {1} {1} 1 {2} 2\n'.format(i+1, j+1, self.layer_m))
                        for k, z in enumerate(dep[self.layer_m:]):
                            k += self.layer_m
                            vs = np.round(vs1d[k])
                            # material = self.mesh1d(z, moho, vs, kappa=kappa)
                            material = self.mesh1d_sm(z, vs, kappa=kappa)
                            self.mesh_str.append('{0} {0} {1} {1} {2} {2} {3}\n'.format(i+1, j+1, k+1, int(material)))
                    else:
                        # if x == 327500. and y == 0:
                        #     print(dep, vs1d)
                        # vs1d[0:self.layer_m] = smooth(vs1d[0:self.layer_m], half_len=5, window='hanning')
                        for k, z in enumerate(dep):
                            vs = np.round(vs1d[k])
                            material = self.mesh1d(z, moho, vs, kappa=kappa)
                            self.mesh_str.append('{0} {0} {1} {1} {2} {2} {3}\n'.format(i+1, j+1, k+1, int(material)))

    def mesh1d_sm(self, z, vs, kappa=1.732):
        idx = np.where(self.materials[:, 3] == vs)[0]
        if idx.size == 0:
            material = self.materials[-1, 0]+1
            rho = 2600.
            self.materials = np.vstack((self.materials, np.array([material, rho, np.round(vs*kappa), vs])))
        else:
            material = self.materials[idx[0], 0]
        return material

    def mesh1d(self, z, moho, vs, kappa=1.732):
        idx = np.where(self.materials[:, 3] == vs)[0]
        if idx.size == 0:
            material = self.materials[-1, 0]+1
            if z >= moho:
                rho = 2600.
            else:
                rho = 3380.
            self.materials = np.vstack((self.materials, np.array([material, rho, np.round(vs*kappa), vs])))
        else:
            material = self.materials[idx[0], 0]
        return material

    def mesh_dep(self, moho_dep):
        dep_m = np.linspace(self.z[0], moho_dep, self.layer_m)
        dep_c = np.linspace(moho_dep, self.z[-1], self.layer_c+1)[1:]
        return np.hstack((dep_m, dep_c))

    def write(self, header='Mesh_Par_file_header'):
        meshfile = join(self.meshmodel.basepath, 'DATA/meshfem3D_files/Mesh_Par_file')
        with open(header) as f:
            head = f.read()
        with open(meshfile, 'w') as f:
            f.write(head)
            f.write('NMATERIALS = {}\n'.format(self.materials.shape[0]))
            for i, mat in enumerate(self.materials):
                f.write('{} {} {} {} 9999. 600.  0  2\n'.format(int(mat[0]), mat[1], mat[2], mat[3]))
            f.write('\nNREGIONS = {}\n'.format(len(self.mesh_str)))
            for m in self.mesh_str:
                f.write(m) 
    
    def write_sta(self):
        stafile = join(self.meshmodel.basepath, 'DATA/STATIONS')
        sta = np.load(join(basepath, model_file))['sta'].all()
        x = sta['x'] * 1000
        y = sta['y'] * 1000
        with open(stafile, 'w') as f:
            for i, staname in enumerate(sta['station']):
                f.write('{} SYN {} {} 0 0\n'.format(staname, y[i], x[i]))


if __name__ == "__main__":
    mh = Mesh()
    # mh.loop_mesh()
    mh.gen_mesh(stable_mantle=False)
    mh.write()
    mh.write_sta()
