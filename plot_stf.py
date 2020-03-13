import matplotlib.pyplot as plt
import numpy as np
from os.path import join
import sys

"""
Compute sorce time function following Eq.4 in Tong et al., 2014

"""

def gen_stf(f0):
    time_axis = np.arange(-5, 5, 0.01)
    stf = (f0/np.sqrt(np.pi))*np.exp(-1*(f0*time_axis)**2)
    return time_axis, stf


def plot_stf(f0, path):
    time_axis, stf = gen_stf(f0)
    stfv = np.diff(stf)
    plt.plot(time_axis[1:], stfv)
    line = plt.plot(time_axis, stf, label='f0={:.1f}'.format(f0))
    plt.legend(line)
    plt.savefig(join(path, 'OUTPUT_FILES/stf.png'))


if __name__ == "__main__":
    path = sys.argv[1]
    f0 = float(sys.argv[2])
    plot_stf(f0, path)