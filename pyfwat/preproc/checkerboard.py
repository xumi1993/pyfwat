import h5py
import numpy as np
from ..pario import readfwatpar
import argparse
import sys

class Checker:
    def __init__(self, model_file:str, par_file='DATA/fwat_params.yml'):
        """
        Initialize the Checker class.

        :param model_file: Path to the model file
        :type model_file: str
        :param par_file: Path to the parameter file, defaults to 'DATA/fwat_params.yml'
        :type par_file: str, optional
        """
        self.model_file = model_file
        self.para = readfwatpar(par_file)
        with h5py.File(model_file, 'r') as f:
            self.x = f['x'][:]
            self.y = f['y'][:]
            self.z = f['z'][:]
            self.npar = len(f.keys()) - 3
            self.keys = list(f.keys())
            for tname in ['x', 'y', 'z']:
                self.keys.remove(tname)
            for i in range(self.npar):
                self.__dict__[self.keys[i]] = f[self.keys[i]][:]
    
    def _create_tape(self, xleft, xright, type='x'):
        if type == 'x':
            x = self.x
            dx = self.x[1] - self.x[0]
        elif type == 'y':
            x = self.y
            dx = self.y[1] - self.y[0]
        elif type == 'z':
            x = self.z
            dx = self.z[1] - self.z[0]
        else:
            raise ValueError("Invalid type. Choose from 'x', 'y', or 'z'.")
        if xleft < x[0] or xright > x[-1]:
            raise ValueError("xleft and xright must be within the range of axis.")
        ntaper_left = int((xleft - x[0]) / dx)
        ntaper_right = int((x[-1] - xright) / dx)
        return ntaper_left, ntaper_right
    
    def checkerboard(self, n_pert_x:int, n_pert_y:int, n_pert_z:int,
                     pert_vel=0.1, lim_x=None, lim_y=None, lim_z=None):
        """
        Create a checkerboard model.

        :param n_pert_x: Number of perturbations in the x direction
        :type n_pert_x: int
        :param n_pert_y: Number of perturbations in the y direction
        :type n_pert_y: int
        :param n_pert_z: Number of perturbations in the z direction
        :type n_pert_z: int
        :param pert_vel: Perturbation velocity, defaults to 0.1
        :type pert_vel: float, optional
        :param lim_x: Limits for the x direction, defaults to None
        :type lim_x: tuple, optional
        :param lim_y: Limits for the y direction, defaults to None
        :type lim_y: tuple, optional
        :param lim_z: Limits for the z direction, defaults to None
        :type lim_z: tuple, optional
        """
        if lim_x is not None:
            ntaper_left, ntaper_right = self._create_tape(lim_x[0], lim_x[1], type='x')
        else:
            ntaper_left, ntaper_right = 0, 0
        x_pert = np.zeros_like(self.x)
        x_pert[ntaper_left:-ntaper_right] = \
            np.sin(n_pert_x * np.pi * np.arange(self.x.size - ntaper_left - ntaper_right) \
            / (self.x.size - ntaper_left - ntaper_right))
        
        if lim_y is not None:
            ntaper_left, ntaper_right = self._create_tape(lim_y[0], lim_y[1], type='y')
        else:
            ntaper_left, ntaper_right = 0, 0
        y_pert = np.zeros_like(self.y)
        y_pert[ntaper_left:-ntaper_right] = \
            np.sin(n_pert_y * np.pi * np.arange(self.y.size - ntaper_left - ntaper_right) \
            / (self.y.size - ntaper_left - ntaper_right))
        
        if lim_z is not None:
            ntaper_left, ntaper_right = self._create_tape(lim_z[0], lim_z[1], type='z')
        else:
            ntaper_left, ntaper_right = 0, 0
        z_pert = np.zeros_like(self.z)
        z_pert[ntaper_left:-ntaper_right] = \
            np.sin(n_pert_z * np.pi * np.arange(self.z.size - ntaper_left - ntaper_right) \
            / (self.z.size - ntaper_left - ntaper_right))
        
        xx, yy, zz = np.meshgrid(x_pert, y_pert, z_pert, indexing='ij')
        self.perturbation = pert_vel * xx * yy * zz
        for key in self.keys:
            self.__dict__[key] *= 1+self.perturbation

    def write(self, fname:str):
        """
        Write the checkerboard model to a file.

        :param fname: Filename to write the model
        :type fname: str
        """
        with h5py.File(fname, 'w') as f:
            f.create_dataset('x', data=self.x)
            f.create_dataset('y', data=self.y)
            f.create_dataset('z', data=self.z)
            for key in self.keys:
                f.create_dataset(key, data=self.__dict__[key])
            f.create_dataset('pert', data=self.perturbation)

def main():
    parser = argparse.ArgumentParser(description="Create a checkerboard model.")
    parser.add_argument('-i', required=True, type=str, help='Input model file')
    parser.add_argument('-n', help='nx, ny and nz of velocity anomalies along longitude, latitude and depth',
                         metavar='nx/ny/nz', required=True)
    parser.add_argument('-o', required=True, type=str, help='Output model file')
    parser.add_argument('-p', help='Perturbation velocity', type=float, default=0.1)
    parser.add_argument('-x', help='Upper and lower limits of x', metavar='xmin/xmax', type=str, default=None)
    parser.add_argument('-y', help='Upper and lower limits of y', metavar='ymin/ymax', type=str, default=None)
    parser.add_argument('-z', help='Upper and lower limits of z', metavar='zmin/zmax', type=str, default=None)
    args = parser.parse_args(sys.argv[2:])
    n_pert_x, n_pert_y, n_pert_z = [int(i) for i in args.n.split('/')]
    lim_x = [float(i) for i in args.x.split('/')] if args.x is not None else None
    lim_y = [float(i) for i in args.y.split('/')] if args.y is not None else None
    lim_z = [float(i) for i in args.z.split('/')] if args.z is not None else None
    ckb = Checker(args.i)
    ckb.checkerboard(n_pert_x, n_pert_y, n_pert_z, args.p, lim_x, lim_y, lim_z)
    ckb.write(args.o)
