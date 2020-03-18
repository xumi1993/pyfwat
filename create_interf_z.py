#!/usr/bin/env python
import numpy as np
from seispy.geo import *
import matplotlib.pyplot as plt
from utils import read_interface
# from os.path import dirname, abspath, join

def create_buffer(z, z_buffer, xaxis, x, dir='left'):
    if dir == 'left':
        xidx = np.where(xaxis < x)[0]
        if z < z_buffer:
            window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(z_buffer-z)+z
        else:
            window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(z-z_buffer)+z_buffer
    else:
        xidx = np.where(xaxis > x)[0]
        if z < z_buffer:
            window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(z_buffer-z)+z
        else:
            window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(z-z_buffer)+z_buffer
    return xidx, window


class InterfZ():
    def __init__(self, nx, ny, xmin, ymin, spx, spy):
        self.nx = nx
        self.ny = ny
        self.xmin = xmin
        self.xmax = (nx-1)*spx + xmin
        self.ymax = (ny-1)*spy + ymin
        self.ymin = ymin
        self.spx = spx
        self.spy = spy
        self.xaxis = np.linspace(xmin, self.xmax, nx)
        self.yaxis = np.linspace(ymin, self.ymax, ny)

    def z_2d(self, angle, z_deep, z_shallow, x_begin=0, x_end=200000):
        self.z_deep = z_deep
        self.z_shallow = z_shallow
        x_slop_len = np.abs(z_shallow - z_deep)/tand(angle)
        x1 = (x_end-x_begin)/2-(x_slop_len/2)
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
        # plt.plot(self.xaxis, self.xz)
        # plt.savefig('interface.png')
    
    def interf_buffer(self, z_buffer, x_buffer_begin, x_buffer_end):
        xleft, buffer_left = create_buffer(self.z_deep, z_buffer, self.xaxis, x_buffer_begin, dir='left')
        self.xz[xleft] = buffer_left
        xright, buffer_right = create_buffer(self.z_shallow, z_buffer, self.xaxis, x_buffer_end, dir='right')
        self.xz[xright] = buffer_right

    def create_interf_z(self, path):
        with open(path, 'w') as f:
            for j, y in enumerate(self.yaxis):
                for i, x in enumerate(self.xaxis):
                    f.write('{:.4f}\n'.format(self.xz[i]))


if __name__ == "__main__":
    interf_para = read_interface(inter_num=1)
    iz = InterfZ(*interf_para)
    iz.z_2d(20, -60000, -40000)
    # iz.interf_buffer(-50000, -100000, 300000)
    for x, z in zip(iz.xaxis, iz.xz):
        print(x, z)
    iz.create_interf_z('DATA/meshfem3D_files/interf_2.dat')