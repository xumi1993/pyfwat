"""Color-table paths, density from Vp, and NaN filling in 3-D arrays."""

from posixpath import dirname
import numpy as np
from scipy.interpolate import griddata
import subprocess
from os.path import join, basename, abspath
import re
import sys

def parse_cpt_name(cpt_name):
    """Return the path of a color table bundled with the module.

    :param cpt_name: Name of the color table without the ``.cpt`` extension
    :type cpt_name: str
    :return: Path ``<directory of this module>/cpt/<cpt_name>.cpt``
    :rtype: str
    """
    cpt_path = join(dirname(abspath(__file__)), 'cpt', cpt_name+'.cpt')
    return cpt_path


def get_rho(vp):
    # vp = 0.9409 + 2.0947*vs - 0.8206*vs**2 + 0.2683*vs**3 - 0.0251*vs**4
    """Density from P-wave velocity with the Brocher (2005) Nafe-Drake relation.

    :param vp: P-wave velocity in km/s
    :type vp: float or numpy.ndarray
    :return: Density in g/cm^3
    :rtype: float or numpy.ndarray
    """
    rho = 1.6612*vp - 0.4721*vp**2 + 0.0671*vp**3 - 0.0043*vp**4 + 0.000106*vp**5
    # vs = 0.7858 - 1.2344*vp + 0.7949*vp**2 - 0.1238*vp**3 + 0.0064*vp**4
    return rho


def ignore_nan_3d(data):
    """Fill NaNs in a 3-D array with the value of the nearest valid grid point.

    :param data: 3-D array that may contain NaNs
    :type data: numpy.ndarray
    :return: Array of the same shape without NaNs
    :rtype: numpy.ndarray
    """
    index = np.where(~np.isnan(data))
    values = data[index]
    points = np.array(index).T
    zidx = np.arange(data.shape[0])
    yidx = np.arange(data.shape[1])
    xidx = np.arange(data.shape[2])
    zz, xx, yy = np.meshgrid(zidx, yidx, xidx, indexing='ij')
    interpolated = griddata(
        points, values, 
        (zz, xx, yy), 
        method='nearest'
    )
    result = interpolated.reshape(data.shape)
    return result
