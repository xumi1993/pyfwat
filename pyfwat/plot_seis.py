#!/usr/bin/env python
from time import time
import numpy as np
from os.path import join
import sys
from utils import *
from seispy.geo import rotateSeisENtoTR
import matplotlib.pyplot as plt
from obspy.signal.filter import bandpass, highpass, lowpass
from obspy.io.sac import SACTrace


def get_stations(basepath):
    sta_path = join(basepath, 'DATA', 'STATIONS')
    dtype = {'names': ('station', 'network', 'y', 'x', 'z', 'b'), 'formats': ('U10', 'U10', 'f4', 'f4', 'f4', 'f4')}
    stations, network, y, x, z, _ = np.loadtxt(sta_path, dtype=dtype, unpack=True)
    return stations, network, x, y, z


def read_tr(basepath, comp='z', filter=True, unit='d'):
    stations, network, x, y, z = get_stations(basepath)
    npts = int(readpar(join(basepath, 'DATA', 'Par_file'), 'NSTEP'))
    # print(npts)
    st = np.zeros([x.shape[0], npts])
    time_axis = np.loadtxt(join(basepath, 'OUTPUT_FILES', network[0]+'.'+stations[0]+'.BX'+comp.upper()+'.sem'+unit), usecols=[0,])
    dt = np.mean(np.diff(time_axis))
    for i, staname in enumerate(stations):
        fname = join(basepath, 'OUTPUT_FILES', network[i]+'.'+staname+'.BX'+comp.upper()+'.sem'+unit)
        st[i] = np.loadtxt(fname, usecols=[1,])
        if filter:
            st[i] = lowpass(st[i], 1, 1/dt)
    return time_axis, st


def rotate(basepath, unit='d'):
    baz = readfkpar(join(basepath, 'DATA', 'FKMODEL'), 'BACK_AZIMUTH')
    _, stx = read_tr(basepath, comp='E', unit=unit)
    _, sty = read_tr(basepath, comp='N', unit=unit)
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
    plt.figure(figsize=(16, 8), dpi=300)
    axr = plt.subplot(1, 3, 1)
    axr.set_title('R comp')
    axt = plt.subplot(1, 3, 2)
    axt.set_title('T comp')
    axz = plt.subplot(1, 3, 3)
    axz.set_title('Z comp')
    _, _, x, _, _ = get_stations(basepath)
    for ax in [axr, axt, axz]:
        ax.grid(True, axis='x')
        ax.set_ylim([x[0]/1000-5,x[-1]/1000+5])
    time_axis, zst = read_tr(basepath, comp='z')
    tst, rst = rotate(basepath)
    single_draw(axr, time_axis, x, rst)
    single_draw(axt, time_axis, x, tst)
    single_draw(axz, time_axis, x, zst)
    plt.savefig(join(basepath, 'OUTPUT_FILES', 'waves_rtz.png'), bbox_inches='tight')


def save(time_axis, data, comp, sta, net, path='./'):
    sac = SACTrace(data=data)
    sac.b = time_axis[0]
    sac.delta = np.mean(np.diff(time_axis))
    sac.kcmpnm = 'BX{}'.format(comp)
    sac.kstnm = sta
    sac.knetwk = net
    sac.write('{}/{}.{}.BX{}.syn'.format(path, net, sta, comp))


def savesemd(basepath='./', outpath='OUTPUT_FILES'):
    sta, net, x, _, _ = get_stations(basepath)
    time_axis, zst = read_tr(basepath, comp='z')
    tst, rst = rotate(basepath)
    for i, staname in enumerate(sta):
        save(time_axis, rst[i], 'R', staname, net[i], outpath)
        save(time_axis, zst[i], 'Z', staname, net[i], outpath)


if __name__ == "__main__":
    basepath = sys.argv[1]
    # basepath = 'benchmark_line_baz0_inc33.3489'
    draw(basepath)
    savesemd(basepath)