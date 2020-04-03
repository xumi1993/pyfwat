#!/usr/bin/env python
from seispy.decov import decovit
import numpy as np
from plot_seis import read_tr, rotate, get_stations
from obspy.io.sac import SACTrace
from utils import readpar
from os.path import join
import matplotlib.pyplot as plt
import sys


def saverf(rf, time_axis, dt, path, sta, net):
    for i, r in enumerate(rf):
        sac = SACTrace(data=r)
        sac.delta = dt
        sac.b = time_axis[0]
        sac.kcmpnm = 'R'
        sac.write(join(path, '{}.{}.rf.r'.format(net[i], sta[i])))


def cal_rf(basepath, sta, net):
    _, zst = read_tr(basepath)
    _, rst = rotate(basepath)
    rrf = np.zeros_like(zst)
    dt = readpar(join(basepath, 'DATA', 'Par_file'), 'DT')
    for i, ztr in enumerate(zst):
        rrf[i], _, _ = decovit(rst[i], ztr, dt, itmax=20)
    time_axis = np.linspace(0, rrf[0].shape[0]*dt, rrf[0].shape[0]) - 10
    saverf(rrf, time_axis, dt, join(basepath, 'OUTPUT_FILES'), sta, net)
    return time_axis, rrf


def draw(basepath, enf=20):
    sta, net, xs, _, _ = get_stations(basepath)
    xs /= 1000
    time_axis, rrf = cal_rf(basepath, sta, net)
    bound = np.zeros_like(rrf[0])
    plt.figure(figsize=(5.6, 8.3))
    plt.grid(axis='x')
    for i, x in enumerate(xs):
        amp = rrf[i]*enf + x
        plt.plot(time_axis, amp, color='gray', linewidth=0.3)
        plt.fill_between(time_axis, amp, bound + x, where=amp > x, facecolor='red', alpha=0.7)
        plt.fill_between(time_axis, amp, bound + x, where=amp < x, facecolor='#1193F4', alpha=0.7)
    plt.xlim([-2, 30])
    plt.xlabel('Time after P (s)')
    plt.ylim([xs[0]-10, xs[-1]+10])
    plt.ylabel('X (km)')
    plt.savefig(join(basepath, 'OUTPUT_FILES', 'rrf.png'), bbox_inches='tight')
    # plt.show()


if __name__ == "__main__":
    # basepath = 'benchmark_line_baz90'
    basepath = sys.argv[1]
    draw(basepath)
