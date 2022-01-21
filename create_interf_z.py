#!/usr/bin/env python
import numpy as np
from seispy.geo import *
import matplotlib.pyplot as plt
from .utils import read_interface
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from scipy.interpolate import interpn, interp1d
# from os.path import dirname, abspath, join

def create_buffer(z, z_buffer, xaxis, x1, x2, dir='left'):
    if dir == 'left':
        xidx = np.where((xaxis < x2) & (xaxis > x1))[0]
        if z < z_buffer:
            window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(z_buffer-z)+z
        else:
            window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(z-z_buffer)+z_buffer
    else:
        xidx = np.where((xaxis < x2) & (xaxis > x1))[0]
        if z < z_buffer:
            window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(z_buffer-z)+z
        else:
            window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(z-z_buffer)+z_buffer
    return xidx, window


def xdip(angle, z_deep, z_shallow, x_begin, x_end, spx):
    x_slop_len = np.abs(z_shallow - z_deep)/tand(angle)
    x1 = (x_end-x_begin)/2-(x_slop_len/2)
    x2 = x1 + (x_slop_len)
    x1 = round(x1/spx)*spx
    x2 = round(x2/spx)*spx
    return x1, x2


class InterfZ():
    def __init__(self, nx, ny, xmin, ymin, spx, spy):
        self.nx = int(nx)
        self.ny = int(ny)
        self.xmin = xmin
        self.xmax = (nx-1)*spx + xmin
        self.ymax = (ny-1)*spy + ymin
        self.ymin = ymin
        self.spx = spx
        self.spy = spy
        self.xaxis = np.linspace(xmin, self.xmax, self.nx)
        self.yaxis = np.linspace(ymin, self.ymax, self.ny)
        self.xz = np.array([])

    def loadxz(self, x, moho):
        self.xz = interp1d(x, moho, bounds_error=False, fill_value='extrapolate')(self.xaxis)
        self.z_deep = moho[0]
        self.z_shallow = moho[-1]

    def z_2d(self, angle, z_deep, z_shallow, x_begin=0, x_end=200000):
        self.z_deep = z_deep
        self.z_shallow = z_shallow
        x1, x2 = xdip(angle, z_deep, z_shallow, x_begin, x_end, self.spx)
        self.xz = np.zeros_like(self.xaxis)
        idx = np.where((self.xaxis>=x1) & (self.xaxis<x2))[0]
        for i, x in enumerate(self.xaxis):
            if x < x1:
                self.xz[i] = z_deep
            elif x>=x2:
                self.xz[i] = z_shallow
        self.xz[idx] = (z_shallow - z_deep) * np.cos(np.linspace(np.pi/2., np.pi, idx.shape[0]))**2 + z_deep

    def z_thick(self, z_deep, z_shallow, x1, x2, x3, x4):
        self.xz = np.zeros_like(self.xaxis)
        idx = np.where(self.xaxis<x1)[0]
        self.xz[idx] = np.ones(idx.shape[0])*z_shallow
        idx = np.where((self.xaxis>=x1) & (self.xaxis<x2))[0]
        self.xz[idx] = (z_shallow - z_deep) * np.cos(np.linspace(0, np.pi/2, idx.shape[0]))**2 + z_deep
        idx = np.where((self.xaxis>=x2) & (self.xaxis<x3))[0]
        self.xz[idx] = np.ones(idx.shape[0])*z_deep
        idx = np.where((self.xaxis>=x3) & (self.xaxis<x4))[0]
        self.xz[idx] = (z_shallow - z_deep) * np.cos(np.linspace(np.pi/2., np.pi, idx.shape[0]))**2 + z_deep
        idx = np.where(self.xaxis>=x4)[0]
        self.xz[idx] = np.ones(idx.shape[0])*z_shallow

    def y_smooth(self, z_buffer, y1, y2, y3, y4):
        self.interface = np.zeros([self.ny, self.nx])
        for i, z in enumerate(self.xz):
            idx = np.where(self.yaxis<=y1)[0]
            self.interface[idx, i] = np.ones(idx.shape[0])*z_buffer
            idx, buffer = create_buffer(z, z_buffer, self.yaxis, y1, y2, dir='left')
            self.interface[idx, i] = buffer
            idx = np.where((self.yaxis>=y2) & (self.yaxis<=y3))[0]
            self.interface[idx, i] = np.ones(idx.shape[0])*z
            idx, buffer = create_buffer(z, z_buffer, self.yaxis, y3, y4, dir='right')
            self.interface[idx, i] = buffer
            idx = np.where(self.yaxis>=y4)[0]
            self.interface[idx, i] = np.ones(idx.shape[0])*z_buffer
    
    def write_interface(self, path):
        with open(path, 'w') as f:
            for j, y in enumerate(self.yaxis):
                for i, x in enumerate(self.xaxis):
                    f.write('{:.4f}\n'.format(self.interface[j, i]))

    def cut_sec(self, x_begin, y_begin, x_end, y_end, num=500):
        x_po = np.linspace(x_begin, x_end, num)
        y_po = np.linspace(y_begin, y_end, num)
        xx, yy = np.meshgrid(self.xaxis, self.yaxis, indexing='ij')
        z = interpn((self.yaxis, self.xaxis), self.interface, (y_po, x_po))
        return np.vstack((x_po, y_po, z)).T

    def plot2d(self, path='interface.png'):
        x, y = np.meshgrid(self.xaxis, self.yaxis)
        plt.clf()
        fig = plt.figure()
        ax = Axes3D(fig)
        ax.plot_surface(x, y, self.interface, cmap = cm.coolwarm)
        ax.set_aspect('equal')
        fig.savefig(path, bbox_inches='tight')
    
    def plotyz(self, xpos=300000):
        sec_moho = self.cut_sec(xpos, self.yaxis[0], xpos, self.yaxis[-1])
        plt.figure(figsize=(5, 4))
        plt.plot(sec_moho[:, 1], sec_moho[:, 2])
        plt.grid()
        plt.xlabel('X (m)')
        plt.ylabel('Z (m)')
        plt.savefig('interface_yz_{}.png'.format(xpos), bbox_inches='tight')

    def plotxz(self, path='interface_xz.png', ylim=[-60000, 0]):
        plt.figure(figsize=(10, 4))
        plt.plot(self.xaxis, self.xz)
        plt.gca().set(ylim=(-60000, 0))
        # plt.axis('equal')
        plt.grid()
        plt.xlabel('X (m)')
        plt.ylabel('Z (m)')
        plt.savefig(path, bbox_inches='tight')

    def create_buffer(self, z_buffer, xaxis, x1, x2, dir='left'):
        if dir == 'left':
            xidx = np.where((xaxis < x2) & (xaxis > x1))[0]
            if self.z_deep < z_buffer:
                window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(z_buffer-self.z_deep)+self.z_deep
            else:
                window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(self.z_deep-z_buffer)+z_buffer
        else:
            xidx = np.where((xaxis < x2) & (xaxis > x1))[0]
            if self.z_shallow < z_buffer:
                window = np.cos(np.linspace(np.pi/2., np.pi, xidx.shape[0]))**2*(z_buffer-self.z_shallow)+self.z_shallow
            else:
                window = np.cos(np.linspace(0, np.pi/2, xidx.shape[0]))**2*(self.z_shallow-z_buffer)+z_buffer
        return xidx, window
    
    def interf_buffer(self, z_buffer, x_buffer_begin, x_buffer_end, direct='left'):
        xidx, buffer = self.create_buffer(z_buffer, self.xaxis, x_buffer_begin, x_buffer_end, dir=direct)
        self.xz[xidx] = buffer
        if direct == 'left':
            self.xz[np.where(self.xaxis <= x_buffer_begin)] = z_buffer
        else:
            self.xz[np.where(self.xaxis >= x_buffer_end)] = z_buffer

    def create_interf_z(self, path):
        with open(path, 'w') as f:
            for j, y in enumerate(self.yaxis):
                for i, x in enumerate(self.xaxis):
                    f.write('{:.4f}\n'.format(self.xz[i]))


if __name__ == "__main__":
    interf_para = read_interface(inter_num=1)
    iz = InterfZ(*interf_para)
    iz.z_2d(20, -60000, -40000)
    # iz.z_thick(-40000, -30000, 20000, 60000, 140000, 180000)
    # iz.y_smooth(-30000, -25000, -20000, 20000, 25000)
    # iz.plot2d()
    iz.interf_buffer(-50000, -300000, -200000, direct='left')
    iz.interf_buffer(-50000, 250000, 350000, direct='right')
    iz.plotxz()
    for x, z in zip(iz.xaxis, iz.xz):
        print(x, z)
    iz.create_interf_z('DATA/meshfem3D_files/interf_2.dat')