import h5py
import numpy as np
from ..pario import readfwatpar
import sys
import glob
import argparse


simu_type = ['noise', 'tele']
kernel_name = ['alpha', 'beta', 'rhop']
basepath = './optimize'

def read_misfit(it, setname, col=28):
    fs = glob.glob('misfits/{}.{}_*_window_chi'.format(it, setname))
    misfit = 0
    for f in fs:
        chi = np.loadtxt(f, usecols=[col], unpack=True)
        misfit += np.sum(chi)
    return misfit

class JointKernel():
    def __init__(self, model):
        self.model = model
        self.data = self.read(model)
        it_start = int(readfwatpar('DATA/FWAT.PAR', 'ITER_START'))
        self.model_start = f'M{it_start:02d}'
        self.weight = readfwatpar('DATA/FWAT.PAR', 'JOINT_WEIGHT')
        self.setname = {}
        self.setname['noise'] = readfwatpar('DATA/FWAT.PAR', 'NOISE_SET_RANGE')[0]
        self.setname['tele'] = readfwatpar('DATA/FWAT.PAR', 'TELE_SET_RANGE')[0]

    def read(self, model_name):
        data = {
            'noise': {},
            'tele': {}
        }
        for simu in simu_type:
            grad_all = []
            for kernel in kernel_name:
                with h5py.File(f'{basepath}/{kernel}_kernel_smooth_{model_name}_{simu}.h5') as f:
                    grad_all.append(f[f'{kernel}_kernel_smooth'][:])
            data[simu] = np.stack(grad_all)
        return data

    def read_misfit(self):
        self.misfit = {}
        self.misfit['noise'] = read_misfit(self.model_start, self.setname['noise'])
        self.misfit['tele'] = read_misfit(self.model_start, self.setname['tele'])

    def sum(self, misfit_norm=False):
        normval = {}
        if misfit_norm:
            for simu in simu_type:
                normval[simu] = read_misfit(self.model_start, self.setname[simu])
        else:
            data0 = self.read(self.model_start)
            for simu in simu_type:
                normval[simu] = np.max(np.abs(data0[simu]))
        self.read_misfit()
        self.grad = {}
        for kernel in kernel_name:
            self.grad[kernel] = np.zeros(self.data['noise'][0].shape)
        for i, simu in enumerate(simu_type):
            self.data[simu] /= normval[simu] * self.weight[i]
            print(f'max {simu} grad: {np.max(np.abs(self.data[simu]))}')
            for j, kernel in enumerate(kernel_name):
                self.grad[kernel] += self.data[simu][j]
    
    def write(self):
        with h5py.File(f'{basepath}/model_{self.model}.h5', 'r') as f:
            x = f['x'][:]
            y = f['y'][:]
            z = f['z'][:]
        with h5py.File(f'{basepath}/gradient_{self.model}.h5', 'w') as f:
            for kernel in kernel_name:
                # kdata = np.asfortranarray(self.grad[kernel])
                kdata = self.grad[kernel]
                f.create_dataset(f'{kernel}_kernel_smooth', data=kdata)
            f.create_dataset('x', data=x)
            f.create_dataset('y', data=y)
            f.create_dataset('z', data=z)

def main():
    parser = argparse.ArgumentParser('Joint kernel of different data sets')
    parser.add_argument('-m', help='Model name e.g.,M01', metavar='M??', required=True)
    parser.add_argument('-n', help='Normalize the gradient by misfit', action='store_true', default=False)
    args = parser.parse_args()
    joint = JointKernel(args.m)
    joint.sum(misfit_norm=args.n)
    joint.write()

if __name__ == '__main__':
    joint = JointKernel(sys.argv[1])
    joint.sum()
    joint.write()