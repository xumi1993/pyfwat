import numpy as np
import re
from ..plot.plot_misfit_linesearch import PlotMisfit
import shutil
import argparse

def optimize(modname, filterstr):
    nextmod = 'M{:02d}'.format(int(modname[1:])+1)
    pm = PlotMisfit(modname, filterstr)
    idx = np.argmin(pm.chi)
    misname = pm.files[idx]
    suffix = re.findall(r'(step.+?).ls', misname)[0]
    shutil.move('optimize/MODEL_{}_{}'.format(modname, suffix), 
                'optimize/MODEL_{}'.format(nextmod))


def main():
    parser = argparse.ArgumentParser('Select optimal step length')
    parser.add_argument('-m', help='Model name e.g.,M01', metavar='M??', required=True)
    parser.add_argument('-f', help='Filter info in the filename, e.g., T005_T050', metavar='T???_T???|F?.?', required=True)
    args = parser.parse_args()
    optimize(args.m, args.f)
