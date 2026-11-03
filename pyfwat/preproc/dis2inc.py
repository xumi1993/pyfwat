#!/usr/bin/env python
"""P-wave ray parameter and incidence angle from source depth and epicentral distance.

Run as ``python -m pyfwat.preproc.dis2inc dep evdp dis``.
"""

import numpy as np
from ..utils.geo import *
from obspy.taup import TauPyModel
from scipy.interpolate import interp1d
import sys
model = TauPyModel(model="ak135")


def interp_vp(dep=100):
    """P-wave velocity of ak135 at a depth.

    :param dep: Depth in km, defaults to 100
    :type dep: float, optional
    :return: P-wave velocity in km/s
    :rtype: float
    """
    v_mod = model.model.s_mod.v_mod.layers
    v = np.array([[lay[0], lay[2]] for lay in v_mod])
    vbot = interp1d(v[:, 0], v[:, 1])(dep)
    return vbot


def get_rayp(evdp, dis):
    """Ray parameter of the direct P wave in ak135.

    :param evdp: Source depth in km
    :type evdp: float
    :param dis: Epicentral distance in degrees
    :type dis: float
    :return: Ray parameter in s/km
    :rtype: float
    """
    rayp = srad2skm(model.get_travel_times(evdp, dis, phase_list=['P'])[0].ray_param)
    return rayp


def dis2inc(dep, evdp, dis):
    """Incidence angle of the direct P wave at a depth.

    :param dep: Depth in km where the angle is computed
    :type dep: float
    :param evdp: Source depth in km
    :type evdp: float
    :param dis: Epicentral distance in degrees
    :type dis: float
    :return: Incidence angle in degrees
    :rtype: float
    """
    rayp = get_rayp(evdp, dis)
    inc_vp = interp_vp(dep)
    inc_angle = asind(rayp*inc_vp)
    return inc_angle


if __name__ == "__main__":
    args = [float(value) for value in sys.argv[1:]]
    if len(args) != 3:
        print('Usage: dis2inc.py dep evdp dis')
        sys.exit(1)
    print('{:.6f}'.format(dis2inc(args[0], args[1], args[2])))
    
