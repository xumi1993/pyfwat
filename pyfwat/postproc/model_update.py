"""Update the model with steepest descent or L-BFGS.

Command-line tool: ``fwat_model_update``.
"""

import h5py
import numpy as np
import sys
from ..utils.pario import readfwatpar
import os
import argparse


data_names = ['vp', 'vs', 'rho']
model_h5 = 'DATA/tomo_files/tomography_model.h5'

class ModUpdate():
    """Model update from the models and gradients in ``optimize/``.

    Optimization settings are read from ``MODEL_UPDATE`` in
    ``DATA/fwat_params.yml``: ``ITER_START``, ``LBFGS_M_STORE``, ``DO_LS`` and
    ``OPT_METHOD`` (1 for steepest descent, 2 for L-BFGS).
    """
    def __init__(self, model_name, step_length):
        """:param model_name: Current model, e.g. ``M03``
        :type model_name: str
        :param step_length: Step length applied to the normalized search direction
        :type step_length: float
        """
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
        """Compute the L-BFGS search direction in ``r_vector``.

        Uses the model and gradient differences of up to ``LBFGS_M_STORE`` previous
        iterations, but not before ``ITER_START``.
        """
        iter_store = self.iter_current - self.m_store
        if iter_store <= self.iter_start:
            iter_store = self.iter_start
        q_vector = self.read_gradient(self.iter_current)
        p = np.zeros(1000)
        a = np.zeros(1000)

        for i in range(self.iter_current - 1, iter_store - 1, -1):
            g0 = self.read_gradient(i)
            g1 = self.read_gradient(i + 1)
            m0 = self.read_model(i)
            m1 = self.read_model(i + 1)
            gradient_diff = g1 - g0
            model_diff = m1 - m0
            p[i] = 1 / self.inner_product(gradient_diff, model_diff)
            a[i] = p[i] * self.inner_product(model_diff, q_vector)
            q_vector -= a[i] * gradient_diff
        
        i = self.iter_current - 1
        g0 = self.read_gradient(i)
        g1 = self.read_gradient(i + 1)
        m0 = self.read_model(i)
        m1 = self.read_model(i + 1)
        gradient_diff = g1 - g0
        model_diff = m1 - m0
        p_k_up_sum = self.inner_product(gradient_diff, model_diff)
        p_k_down_sum = self.inner_product(gradient_diff, gradient_diff)
        p_k = p_k_up_sum / p_k_down_sum
        self.r_vector = p_k * q_vector

        for i in range(iter_store, self.iter_current):
            g0 = self.read_gradient(i)
            g1 = self.read_gradient(i + 1)
            m0 = self.read_model(i)
            m1 = self.read_model(i + 1)
            gradient_diff = g1 - g0
            model_diff = m1 - m0
            b = p[i] * self.inner_product(gradient_diff, self.r_vector)
            self.r_vector += (a[i] - b) * model_diff
    
    def model_update(self):
        """Update the model and write ``DATA/tomo_files/tomography_model.h5``.

        The search direction is the gradient at the first iteration or with
        ``OPT_METHOD`` 1, and the L-BFGS direction with ``OPT_METHOD`` 2. It is
        normalized to a maximum absolute value of 1 before the step length is
        applied.

        :raises ValueError: If ``OPT_METHOD`` is neither 1 nor 2
        """
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
        """Read the grid coordinates, spacings and sizes of the current model."""
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
        """Read the logarithm of Vp, Vs and density of a model.

        :param imod: Iteration number of ``optimize/model_M<imod>.h5``
        :type imod: int
        :return: Array of shape ``(3, nx, ny, nz)`` with ln(Vp), ln(Vs) and ln(rho)
        :rtype: numpy.ndarray
        """
        with h5py.File(f'optimize/model_M{imod:02d}.h5') as f:
            vp = np.log(f['vp'][:])
            vs = np.log(f['vs'][:])
            rho = np.log(f['rho'][:])
        model = np.stack((vp, vs, rho))
        return model

    def read_gradient(self, imod:int):
        """Read the smoothed Vp, Vs and density kernels of a model.

        :param imod: Iteration number of ``optimize/gradient_M<imod>.h5``
        :type imod: int
        :return: Array of shape ``(3, nx, ny, nz)`` with the alpha, beta and rhop
            kernels
        :rtype: numpy.ndarray
        """
        with h5py.File(f'optimize/gradient_M{imod:02d}.h5') as f:
            kalpha = f['alpha_kernel_smooth'][:]
            kbata = f['beta_kernel_smooth'][:]
            krho = f['rhop_kernel_smooth'][:]
        grad = np.stack((kalpha, kbata, krho))
        return grad

    def write(self, path, model):
        """Write Vp, Vs, density and the grid coordinates to an HDF5 file.

        :param path: Output path
        :type path: str
        :param model: Array of shape ``(3, nx, ny, nz)`` with Vp, Vs and density
        :type model: numpy.ndarray
        """
        with h5py.File(path, 'w') as f:
            for i in range(3):
                # model = np.asfortranarray(model)
                f.create_dataset(data_names[i], data=model[i])
            f.create_dataset('x', data=self.x)
            f.create_dataset('y', data=self.y)
            f.create_dataset('z', data=self.z)

    def inner_product(self, a, b):
        """Inner product of two model-space fields over the grid volume.

        :param a: First field
        :type a: numpy.ndarray
        :param b: Second field, same shape as ``a``
        :type b: numpy.ndarray
        :return: Sum of ``a * b`` times the grid cell volume in km^3
        :rtype: float
        """
        return np.sum(a * b * self.dx/1000 * self.dy/1000 * self.dz/1000)


def main():
    """Command-line entry point of ``fwat_model_update``."""
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
