#!/usr/bin/env python
import numpy as np
from os.path import join
import sys
from utils import *
from seispy.geo import rotateSeisENtoTR
import matplotlib.pyplot as plt
from obspy.signal.filter import bandpass, highpass, lowpass


def get_stations(basepath):
    sta_path = join(basepath, 'DATA', 'STATIONS')
    dtype = {'names': ('station', 'network', 'y', 'x', 'z', 'b'), 'formats': ('U10', 'U10', 'f4', 'f4', 'f4', 'f4')}
    stations, network, y, x, z, _ = np.loadtxt(sta_path, dtype=dtype, unpack=True)
    return stations, network, x, y, z


def read_tr(basepath, comp='z', filter=True):
    stations, network, x, y, z = get_stations(basepath)
    npts = int(readpar(join(basepath, 'DATA', 'Par_file'), 'NSTEP'))
    st = np.zeros([x.shape[0], npts])
    time_axis = np.loadtxt(join(basepath, 'OUTPUT_FILES', network[0]+'.'+stations[0]+'.CX'+comp.upper()+'.semv'), usecols=[0,])
    dt = np.mean(np.diff(time_axis))
    for i, staname in enumerate(stations):
        fname = join(basepath, 'OUTPUT_FILES', network[i]+'.'+staname+'.CX'+comp.upper()+'.semv')
        st[i] = np.loadtxt(fname, usecols=[1,])
        # st[i] = lowpass(st[i], 1, 1/dt)
    return time_axis, st


def rotate(basepath):
    baz = readfkpar(join(basepath, 'DATA', 'FKMODEL'), 'BACK_AZIMUTH')
    _, stx = read_tr(basepath, comp='x')
    _, sty = read_tr(basepath, comp='y')
    return rotateSeisENtoTR(stx, sty, baz)


def single_draw(ax, time_axis, stx, data, enf=0.5):
    stx = stx/1000
    for i, tr in enumerate(data):
        # tr /= np.max(tr)
        tr = tr*enf + stx[i]
        ax.plot(time_axis, tr, color='k', linewidth=0.5)
        # ax.set_xlim([-10, 50])
        ax.set_xlabel('Time (s)')
        ax.set_xticks(np.arange(-10, 65, 5))
        ax.set_ylabel('XAxis (km)')


def draw(basepath):
    plt.figure(figsize=(16, 8))
    axr = plt.subplot(1, 3, 1)
    axr.set_title('R comp')
    axt = plt.subplot(1, 3, 2)
    axt.set_title('T comp')
    axz = plt.subplot(1, 3, 3)
    axz.set_title('Z comp')
    _, _, x, _, _ = get_stations(basepath)
    for ax in [axr, axt, axz]:
        ax.grid(b=True, axis='x')
        ax.set_ylim([x[0]/1000-5,x[-1]/1000+5])
    time_axis, zst = read_tr(basepath, comp='z')
    tst, rst = rotate(basepath)
    single_draw(axr, time_axis, x, rst)
    single_draw(axt, time_axis, x, tst)
    single_draw(axz, time_axis, x, zst)
    plt.savefig(join(basepath, 'OUTPUT_FILES', 'waves_rtz.png'), bbox_inches='tight')


if __name__ == "__main__":
    basepath = sys.argv[1]
    # basepath = 'benchmark_line_baz0_inc33.3489'
    draw(basepath)