"""Select the step length with the lowest line-search misfit.

Command-line tool: ``fwat_optimize_ls``.
"""

import numpy as np
import re
from ..plot.plot_misfit_linesearch import PlotMisfit, read_flts
import shutil
import argparse


def optimize(modname, simu_type):
    """Promote the line-search trial model with the lowest misfit.

    The misfit of each step length is averaged over the period bands of the
    simulation type, and ``optimize/MODEL_<modname>_<step>`` with the lowest
    misfit is moved to ``optimize/MODEL_<next model>``.

    :param modname: Current model, e.g. ``M03``
    :type modname: str
    :param simu_type: Simulation type: ``noise``, ``tele``, ``rf`` or ``leq``
    :type simu_type: str
    """
    flt_str = read_flts(simu_type)
    nextmod = 'M{:02d}'.format(int(modname[1:])+1)
    chi = 0
    for flt in flt_str:
        pm = PlotMisfit(modname, flt, 28)
        chi += pm.chi
    chi /= len(flt_str)
    idx = np.argmin(chi)
    misname = pm.files[idx]
    suffix = re.findall(r'(step.+?).ls', misname)[0]
    shutil.move('optimize/MODEL_{}_{}'.format(modname, suffix), 
                'optimize/MODEL_{}'.format(nextmod))


def main():
    """Command-line entry point of ``fwat_optimize_ls``."""
    parser = argparse.ArgumentParser('Select optimal step length')
    parser.add_argument('-m', help='Model name e.g.,M01', metavar='M??', required=True)
    parser.add_argument('-s', help='simulation type in noise, tele, rf and leq', metavar='simu_type', required=True)
    args = parser.parse_args()
    optimize(args.m, args.f)
