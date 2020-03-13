import numpy as np
from seispy.geo import *


class InterfZ():
    def __init__(self, nx, ny, xmin, ymin, spx, spy):
        self.nx = nx
        self.ny = ny
        self.xmin = xmin
        self.xmax = (nx-1)*spx
        self.ymax = (ny-1)*spy
        self.ymin = ymin
        self.spx = spx
        self.spy = spy
        self.xaxis = np.linspace(xmin, self.xmax, nx)
        self.yaxis = np.linspace(ymin, self.ymax, ny)

    def z_2d(self, angle, z_deep, z_shallow):
        x_slop_len = np.abs(z_shallow - z_deep)/tand(angle)
        x1 = (self.xmax-self.xmin)/2-(x_slop_len/2)
        x2 = x1 + (x_slop_len)
        x1 = round(x1/self.spx)*self.spx
        x2 = round(x2/self.spx)*self.spx
        self.xz = np.zeros_like(self.xaxis)
        for i, x in enumerate(self.xaxis):
            if x < x1:
                self.xz[i] = z_deep
            elif x1 <= x < x2:
                self.xz[i] = z_deep + (x-x1)*tand(angle)
            else:
                self.xz[i] = z_shallow

    def create_interf_z(self, path):
        with open(path, 'w') as f:
            for j, y in enumerate(self.yaxis):
                for i, x in enumerate(self.xaxis):
                    f.write('{:.4f}\n'.format(self.xz[i]))



if __name__ == "__main__":
    iz = InterfZ(201, 101, 0, -30000., 1000., 600.)
    iz.z_2d(20, -60000, -40000)
    print(iz.xz)
    iz.create_interf_z('/share/home/goxu/xu_mijian/workspace/semfk/slop/DATA/meshfem3D_files/interf_2.dat')