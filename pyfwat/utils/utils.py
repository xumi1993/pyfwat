from posixpath import dirname
import numpy as np
from scipy.interpolate import griddata
import subprocess
from os.path import join, basename, abspath
import re
import sys

def parse_cpt_name(cpt_name):
    cpt_path = join(dirname(abspath(__file__)), 'cpt', cpt_name+'.cpt')
    return cpt_path


def get_rho(vp):
    # vp = 0.9409 + 2.0947*vs - 0.8206*vs**2 + 0.2683*vs**3 - 0.0251*vs**4
    rho = 1.6612*vp - 0.4721*vp**2 + 0.0671*vp**3 - 0.0043*vp**4 + 0.000106*vp**5
    # vs = 0.7858 - 1.2344*vp + 0.7949*vp**2 - 0.1238*vp**3 + 0.0064*vp**4
    return rho


def ignore_nan_3d(data):
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