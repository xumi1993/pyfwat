#!/usr/bin/env python
import numpy as np
from scipy.interpolate import interpn
import sys


def cutsec(fname, key='vs'):
    data = np.load(fname)
    points = []
    for z in data['dep']:
        for x in data['lon']:
            points.append([z, 0, x])
    points = np.array(points)
    values = interpn((data['dep'], data['lat'], data['lon']), data[key], points, bounds_error=False, fill_value=None)
    with open('sec_xz_{}.dat'.format(key), 'w') as f:
        for i, value in enumerate(values):
            f.write('{:.2f} {:.2f} {:.2f}\n'.format(points[i][2], points[i][0], value))


if __name__ == "__main__":
    argv = sys.argv[1:]
    cutsec(argv[0], argv[1])