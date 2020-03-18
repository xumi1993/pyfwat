#!/usr/bin/env python
import numpy as np
from seispy.geo import *
from obspy.taup import TauPyModel
import inspect
from os.path import dirname, join, abspath
from scipy.interpolate import interp1d
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
    inc_angle = asind(rayp*inc_vp)
    rayp = get_rayp(evdp, dis)
    return rayp, inc_angle

if __name__ == "__main__":
    print(dis2inc(60, 10, 50))
    
