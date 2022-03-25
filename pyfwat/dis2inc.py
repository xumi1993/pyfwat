#!/usr/bin/env python
import numpy as np
from seispy.geo import *
from obspy.taup import TauPyModel
import inspect
from os.path import dirname, join, abspath
from scipy.interpolate import interp1d
import sys
model = TauPyModel(model="iasp91")


def interp_vp(inc_dep, model=join(dirname(abspath(inspect.getfile(skm2sdeg))), 'data', 'iasp91.vel')):
    depth, vp = np.loadtxt(model, usecols=[0, 1], unpack=True)
    inc_vp = interp1d(depth, vp)(inc_dep)
    return inc_vp


def get_rayp(evdp, dis):
    rayp = srad2skm(model.get_travel_times(evdp, dis, phase_list=['P'])[0].ray_param)
    return rayp


def dis2inc(dep, evdp, dis):
    rayp = get_rayp(evdp, dis)
    inc_vp = interp_vp(dep)
    inc_vp = interp_vp(dep)
    inc_angle = asind(rayp*inc_vp)
    rayp = get_rayp(evdp, dis)
    return inc_angle


if __name__ == "__main__":
    args = [float(value) for value in sys.argv[1:]]
    if len(args) != 3:
        print('Usage: dis2inc.py dep evdp dis')
        sys.exit(1)
    print('{:.6f}'.format(dis2inc(args[0], args[1], args[2])))
    
