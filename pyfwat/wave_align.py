#!/usr/bin/env python
import numpy as np
from plot_seis import read_tr, get_stations
from seispy.mccc import mccc
from seispy.geo import rotateSeisENtoTR
from pyfwat.pario import readfkpar, readpar
from os.path import join
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import subprocess


def xcorr(data):
    tr_base = data[0]
    data_len = tr_base.shape[0]
    ndelta = np.array([0.])
    for tr in data[1:]:
        corr = np.correlate(tr_base, tr, 'full')
        ndelta = np.append(ndelta, np.argmax(corr) - data_len)
    return ndelta


def find_arrival_time(tr, time_axis):
    nt = np.arange(0, tr.shape[0])
    npeak = np.argmax(tr)
    atime = interp1d(nt, time_axis)(npeak)
    return atime


class WaveAlign():
    def __init__(self, path='./'):
        self.path = path
        self.baz = readfkpar(join(path, 'DATA', 'FKMODEL'), 'BACK_AZIMUTH')
        self.time_axis, seisx = read_tr(path, comp='x', filter=False)
        _, seisy = read_tr(path, comp='y', filter=False)
        _, self.seisz = read_tr(path, comp='z', filter=False)
        self.seist, self.seisr = rotateSeisENtoTR(seisx, seisy, self.baz)
        self.stations, self.network, self.x, self.y, self.z = get_stations(path)
    
    def align(self, win_begin=14, win_end=60):
        self.win_begin = win_begin
        self.win_end = win_end
        self.shift = self.time_axis[0]
        self.dt = readpar(join(self.path, 'DATA', 'Par_file'), 'DT')
        npts = int((win_end - win_begin)/self.dt)
        self.seis_align_r = np.zeros([self.seisr.shape[0], npts])
        self.seis_align_t = np.zeros([self.seisr.shape[0], npts])
        self.seis_align_z = np.zeros([self.seisr.shape[0], npts])
        atime = find_arrival_time(self.seisz[0], self.time_axis)
        n1 = int((atime - 5 - self.shift)/self.dt)
        n2 = int((atime + 8 - self.shift)/self.dt)
        ndel = xcorr(self.seisz[:, n1:n2+1])
        for i, tr in enumerate(self.seisr):
            n1 = int((win_begin - self.shift)/self.dt - ndel[i])
            n2 = int((win_end - self.shift)/self.dt - ndel[i])
            self.seis_align_r[i] = self.seisr[i, n1:n2]
            self.seis_align_t[i] = self.seist[i, n1:n2]
            self.seis_align_z[i] = self.seisz[i, n1:n2]
    
    def gmt(self, comp='z'):
        xmin = readpar(join(self.path, 'DATA', 'meshfem3D_files', 'Mesh_Par_file'), 'LONGITUDE_MIN')
        xmax = readpar(join(self.path, 'DATA', 'meshfem3D_files', 'Mesh_Par_file'), 'LONGITUDE_MAX')
        gmt = 'name={}/wave_align_{}\n'.format(self.path, comp)
        gmt += 'ps=$name.ps\n'
        gmt += 'gmt psbasemap -R{}/{}/{}/{} -JX6i/-4i -Bxaf+l"X (m)" -Bya5f1+l"Time (s)" -BWSne -K -X1.7i > $ps\n'.format(xmin, xmax, -10, 40)
        gmt += 'gmt pswiggle -R -J -O -K tmp.dat -A90 -Z6 -G-255/25/25 -G+blue -W0.5p >> $ps\n'
        gmt += 'gmt psxy -R -J -O -T >> $ps\n'
        gmt += 'gmt psconvert -A -P -Tg $ps\n'
        gmt += 'rm gmt* tmp.* $ps\n'
        return gmt

    def plot(self, comp='z'):
        o_time = np.argmax(self.seisr[0])*self.dt + self.shift
        self.time_axis_plot = self.time_axis[np.where((self.time_axis>=self.win_begin) & (self.time_axis<self.win_end))] - o_time
        with open('tmp.dat', 'w') as f:
            for i, tr in enumerate(self.__dict__['seis_align_{}'.format(comp)]):
                f.write('>\n')
                for j, amp in enumerate(tr):
                    f.write('{:2f} {:4f} {:4f}\n'.format(self.x[i], self.time_axis_plot[j], amp))
        gmt = self.gmt(comp)
        s = subprocess.Popen(['bash'], stdin=subprocess.PIPE)
        s.communicate(gmt.encode())


if __name__ == "__main__":
    path = './'
    wa = WaveAlign(path)
    wa.align()
    wa.plot(comp='z')
    wa.plot(comp='t')
    wa.plot(comp='r')
