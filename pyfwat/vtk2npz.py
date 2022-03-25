#!/usr/bin/env python
import numpy as np
import glob
from scipy.interpolate import griddata, interpn, LinearNDInterpolator
from pyfwat.pario import readpar
from os.path import join
import matplotlib.pyplot as plt
import pyvista as pv


# def unstructured(points_vtk):
#     unstrgrid = pv.UnstructuredGrid()
#     unstrgrid.SetPoints = points_vtk.GetOutput().


def read_vtk(path, nx=600, ny=60, nz=100, enf=0.001):
    blocks=[]
    for fname in sorted(glob.glob(path)):
        blocks.append(pv.read(fname))
    points_vtk = pv.MultiBlock(blocks)
    mesh = points_vtk.combine()
    mesh.points *= enf
    grid = pv.create_grid(mesh, dimensions=(nx, ny, nz))
    image = grid.sample(mesh)
    return image


class VolVTK():
    def __init__(self, tag, basepath='./', enf=0.001):
        self.tag = tag
        self.vtk_data = read_vtk(join(basepath, './DATABASES_MPI', '*{}.vtk'.format(tag)), enf=enf)
        meshpname = join(basepath, 'DATA/meshfem3D_files/Mesh_Par_file')
        self.latmin = readpar(meshpname, 'LATITUDE_MIN') * enf
        self.latmax = readpar(meshpname, 'LATITUDE_MAX') * enf
        self.lonmin = readpar(meshpname, 'LONGITUDE_MIN') * enf
        self.lonmax = readpar(meshpname, 'LONGITUDE_MAX') * enf
        self.depmax = readpar(meshpname, 'DEPTH_BLOCK_KM') * enf * 1000

    def griddata(self, key='gll_data'):
        self.x = np.linspace(self.vtk_data.bounds[0], self.vtk_data.bounds[1], self.vtk_data.dimensions[0])
        self.y = np.linspace(self.vtk_data.bounds[2], self.vtk_data.bounds[3], self.vtk_data.dimensions[1])
        self.z = np.linspace(self.vtk_data.bounds[4], self.vtk_data.bounds[5], self.vtk_data.dimensions[2])
        self.__dict__[self.tag] = self.vtk_data.point_arrays[key].reshape((self.vtk_data.dimensions[::-1]))
        self.__dict__[self.tag][np.where(self.__dict__[self.tag] == 0)] = np.nan

    def section(self, axis='x', corr=0):
        self.axis = axis
        points = []
        if axis == 'x':
            for i, dep in enumerate(self.z):
                for j, x in enumerate(self.x):
                    points.append([dep, corr, x])
            points = np.array(points)
            # points_comp = np.hstack((points[:, 0], points[:, 2]))
            # self.mesh_z , self.mesh_l = np.meshgrid(self.dep, self.lon)
        else:
            for i, dep in enumerate(self.z):
                for j, y in enumerate(self.y):
                    points.append([dep, y, corr])
            points = np.array(points)
            # points_comp = points[:, 0:-1]
            # self.mesh_z , self.mesh_l = np.meshgrid(self.dep, self.lat, indexing='ij')
        points = np.array(points)
        sec = interpn((self.z, self.y, self.x), self.__dict__[self.tag], points, bounds_error=False, fill_value=None)
        np.savetxt('sec_{}z.dat'.format(axis), np.hstack((points, sec.reshape(-1, 1))))
        # self.sec_grid = griddata(points_comp, sec, (self.mesh_z, self.mesh_l))
        # self.plot_sec()


if __name__ == "__main__":
    # path = '/share/home/goxu/xu_mijian/workspace/semfk/slop_mesh/DATABASES_MPI/*vs.vtk'
    vvs = VolVTK('vs')
    vvs.griddata()
    # vvs.section()
    vvp = VolVTK('vp')
    vvp.griddata()
    np.savez('vel.npz', dep=vvs.z, lat=vvs.y, lon=vvs.x, vs=vvs.vs*0.001, vp=vvp.vp*0.001)