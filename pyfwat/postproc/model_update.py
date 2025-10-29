import h5py
import numpy as np
import sys
from ..pario import readfwatpar
import os
import argparse


data_names = ['vp', 'vs', 'rho']
model_h5 = 'DATA/tomo_files/tomography_model.h5'

class ModUpdate():
    def __init__(self, model_name, step_length):
        self.para = readfwatpar()
        self.step_length = step_length
        self.model_name = model_name
        self.iter_current = int(model_name[1:])
        self.iter_next = self.iter_current + 1
        self.iter_start = self.para['MODEL_UPDATE']['ITER_START']
        self.m_store = self.para['MODEL_UPDATE']['LBFGS_M_STORE']
        self.do_ls = self.para['MODEL_UPDATE']['DO_LS']
        self.optim_method = self.para['MODEL_UPDATE']['OPT_METHOD']
        self.read_coord()

    def lbfgs(self):
        iter_store = self.iter_current - self.m_store
        if iter_store <= self.iter_start:
            iter_store = self.iter_start
        q_vector = self.read_gradient(self.iter_current)
        p = np.zeros(1000)
        a = np.zeros(1000)

        for i in range(self.iter_current - 1, iter_store - 1, -1):
            g0 = self.read_gradient(i)
            g1 = self.read_gradient(i + 1)
            m0 = self.read_model_lbfgs(i)
            m1 = self.read_model_lbfgs(i + 1)
            gradient_diff = g1 - g0
            model_diff = m1 - m0
            p[i] = 1 / self.inner_product(gradient_diff, model_diff)
            a[i] = p[i] * self.inner_product(model_diff, q_vector)
            q_vector -= a[i] * gradient_diff
        
        i = self.iter_current - 1
        g0 = self.read_gradient(i)
        g1 = self.read_gradient(i + 1)
        m0 = self.read_model_lbfgs(i)
        m1 = self.read_model_lbfgs(i + 1)
        gradient_diff = g1 - g0
        model_diff = m1 - m0
        p_k_up_sum = self.inner_product(gradient_diff, model_diff)
        p_k_down_sum = self.inner_product(gradient_diff, gradient_diff)
        p_k = p_k_up_sum / p_k_down_sum
        self.r_vector = p_k * q_vector

        for i in range(iter_store, self.iter_current):
            g0 = self.read_gradient(i)
            g1 = self.read_gradient(i + 1)
            m0 = self.read_model_lbfgs(i)
            m1 = self.read_model_lbfgs(i + 1)
            gradient_diff = g1 - g0
            model_diff = m1 - m0
            b = p[i] * self.inner_product(gradient_diff, self.r_vector)
            self.r_vector += (a[i] - b) * model_diff
    
    def model_update(self):
        if self.iter_current == self.iter_start or self.optim_method == 1:
            self.r_vector = self.read_gradient(self.iter_current)
        elif self.optim_method == 2:
            self.lbfgs()
        else:
            raise ValueError(f'Unknown optimization method: {self.optim_method}')
        self.r_vector /= np.max(np.abs(self.r_vector))
        model = self.read_model(self.iter_current)
        model *= np.exp(-self.step_length * self.r_vector)
        self.write(model_h5, model)

    def read_coord(self):
        with h5py.File(f'optimize/model_{self.model_name}.h5') as f:
            self.x = f['x'][:]
            self.y = f['y'][:]
            self.z = f['z'][:]
        self.dx = self.x[1] - self.x[0]
        self.dy = self.y[1] - self.y[0]
        self.dz = self.z[1] - self.z[0]
        self.nx = self.x.size
        self.ny = self.y.size
        self.nz = self.z.size

    def read_model(self, imod:int):
        with h5py.File(f'optimize/model_M{imod:02d}.h5') as f:
            vp = np.log(f['vp'][:])
            vs = np.log(f['vs'][:])
            rho = np.log(f['rho'][:])
        model = np.stack((vp, vs, rho))
        return model
    
    def read_model_lbfgs(self, imod:int):
        model = self.read_model(imod)
        return np.log(model)

    def read_gradient(self, imod:int):
        with h5py.File(f'optimize/gradient_M{imod:02d}.h5') as f:
            kalpha = f['alpha_kernel_smooth'][:]
            kbata = f['beta_kernel_smooth'][:]
            krho = f['rhop_kernel_smooth'][:]
        grad = np.stack((kalpha, kbata, krho))
        return grad

    def write(self, path, model):
        with h5py.File(path, 'w') as f:
            for i in range(3):
                # model = np.asfortranarray(model)
                f.create_dataset(data_names[i], data=model[i])
            f.create_dataset('x', data=self.x)
            f.create_dataset('y', data=self.y)
            f.create_dataset('z', data=self.z)

    def inner_product(self, a, b):
        return np.sum(a * b * self.dx/1000 * self.dy/1000 * self.dz/1000)


def main():
    parser = argparse.ArgumentParser('Model update using L-BFGS method')
    parser.add_argument('-m', help='Model name e.g.,M01', metavar='M??', required=True)
    parser.add_argument('-l', help='Step length', metavar='step_length', type=float, required=True)
    args = parser.parse_args()
    mu = ModUpdate(args.m, args.l)
    mu.model_update()
    if not mu.do_ls:
        os.system(f'cp {model_h5} optimize/model_M{mu.iter_next:02d}.h5')

if __name__ == '__main__':
    mu = ModUpdate(sys.argv[1], float(sys.argv[2]))
    mu.model_update()
    # copy model file to optimize
    if not mu.do_ls:
        os.system(f'cp {model_h5} optimize/model_M{mu.iter_next:02d}.h5')
