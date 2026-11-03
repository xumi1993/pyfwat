"""Combine the gradients of different data types into a joint gradient.

Command-line tool: ``fwat_joint_kernel``.
"""

import h5py
import numpy as np
from ..utils.pario import readfwatpar
import sys
import glob
import argparse


simu_type = ['noise', 'tele']
kernel_name = ['alpha', 'beta', 'rhop']
basepath = './optimize'


class JointKernel():
    """Joint gradient of ambient-noise and teleseismic data.

    Each data type's gradient is normalized by its maximum absolute value at the
    starting iteration (``MODEL_UPDATE.ITER_START``) and weighted by
    ``POSTPROC.JOINT_WEIGHT`` of ``DATA/fwat_params.yml``.
    """
    def __init__(self, model):
        """:param model: Model name, e.g. ``M03``
        :type model: str
        """
        self.model = model
        self.data = self.read(model)
        self.para = readfwatpar()
        self.model_start = f'M{self.para['MODEL_UPDATE']['ITER_START']:02d}'
        self.weight = self.para['POSTPROC']['JOINT_WEIGHT']
        self.setname = {}
        # self.setname['noise'] = readfwatpar('DATA/FWAT.PAR', 'NOISE_SET_RANGE')[0]
        # self.setname['tele'] = readfwatpar('DATA/FWAT.PAR', 'TELE_SET_RANGE')[0]

    def read(self, model_name):
        """Read the smoothed alpha, beta and rhop kernels of each data type.

        :param model_name: Model name of ``optimize/gradient_<model_name>_<type>.h5``
        :type model_name: str
        :return: Kernels of each data type as an array of shape ``(3, nx, ny, nz)``
        :rtype: dict
        """
        data = {
            'noise': {},
            'tele': {},
            'leq': {}
        }
        for simu in simu_type:
            grad_all = []
            with h5py.File(f'{basepath}/gradient_{model_name}_{simu}.h5') as f:
                for kernel in kernel_name:
                    grad_all.append(f[f'{kernel}_kernel_smooth'][:])
                    data[simu] = np.stack(grad_all)
        return data

    def sum(self):
        """Normalize, weight and sum the gradients of all data types into ``grad``."""
        normval = {}
        data0 = self.read(self.model_start)
        for simu in simu_type:
            normval[simu] = np.max(np.abs(data0[simu]))
        self.grad = {}
        for kernel in kernel_name:
            self.grad[kernel] = np.zeros(self.data['noise'][0].shape)
        for i, simu in enumerate(simu_type):
            self.data[simu] /= normval[simu] / self.weight[i]
            print(f'max {simu} grad: {np.max(np.abs(self.data[simu]))}')
            for j, kernel in enumerate(kernel_name):
                self.grad[kernel] += self.data[simu][j]
    
    def write(self):
        # with h5py.File(f'{basepath}/model_{self.model}.h5', 'r') as f:
        #     x = f['x'][:]
        #     y = f['y'][:]
        #     z = f['z'][:]
        """Write the joint kernels to ``optimize/gradient_<model>.h5``."""
        with h5py.File(f'{basepath}/gradient_{self.model}.h5', 'w') as f:
            for kernel in kernel_name:
                # kdata = np.asfortranarray(self.grad[kernel])
                kdata = self.grad[kernel]
                f.create_dataset(f'{kernel}_kernel_smooth', data=kdata)
            # f.create_dataset('x', data=x)
            # f.create_dataset('y', data=y)
            # f.create_dataset('z', data=z)

def main():
    """Command-line entry point of ``fwat_joint_kernel``."""
    parser = argparse.ArgumentParser('Joint kernel of different data sets')
    parser.add_argument('-m', help='Model name e.g.,M01', metavar='M??', required=True)
    args = parser.parse_args()
    joint = JointKernel(args.m)
    joint.sum()
    joint.write()

if __name__ == '__main__':
    joint = JointKernel(sys.argv[1])
    joint.sum()
    joint.write()
