#!/usr/bin/env python
from obspy.io.sac import SACTrace
import numpy as np
import glob
from os.path import join, dirname, abspath, basename
import matplotlib.pyplot as plt
import sys


basepath = abspath(dirname('./'))


class RFFit():
    def __init__(self, rf_path=join(basepath, '2018.240.22.35.13')):
        self.rf_path = rf_path
        self._read_sta()
        self._read_syn()
        self._read_obs()


    def _read_sta(self, sta_path=join(basepath, 'DATA/STATIONS')):
        dtype = {'names': ('staname', 'x'), 'formats': ('U20', 'f4')}
        self.staname, self.stax = np.loadtxt(sta_path, dtype=dtype, usecols=(0, 3), unpack=True)
        self.stax /= 1000
    
    def _read_syn(self):
        self.rf = {}
        for i, sta in enumerate(self.staname):
            fname = glob.glob(join(basepath, 'OUTPUT_FILES/*.{}.rf.r'.format(sta)))[0]
            sac = SACTrace.read(fname)
            self.rf[sta] = {'syn': sac.data}
        self.time_syn = np.linspace(sac.b, sac.e, sac.npts)
    
    def _read_obs(self):
        for i, sta in enumerate(self.staname):
            fname = glob.glob(join(self.rf_path, '*{}*R.sac'.format(sta)))
            if fname:
                sac = SACTrace.read(fname[0])
                self.rf[sta]['obs'] = sac.data
            else:
                self.rf[sta]['obs'] = np.array([])
        self.time_obs = np.linspace(sac.b, sac.e, sac.npts)
        
    def plot(self, enf=5):
        plt.figure(figsize=(5, 10))
        for i, sta in enumerate(self.staname):
            if self.rf[sta]['obs'].size != 0:
                amp_obs = self.rf[sta]['obs']*enf+self.stax[i]
                plt.plot(self.time_obs, amp_obs, color='k', linewidth=1.4)
            amp_syn = self.rf[sta]['syn']*enf+self.stax[i]
            plt.plot(self.time_syn, amp_syn, color='r', linewidth=1.2)
        plt.grid()
        plt.title(basename(self.rf_path))
        plt.xlim([-1, 10])
        plt.xlabel('Time after P (s)')
        plt.ylabel('X (km)')
        plt.savefig('rffit_{}.png'.format(basename(self.rf_path)), bbox_inches='tight')


if __name__ == "__main__":
    rff = RFFit(rf_path=sys.argv[1])
    rff.plot(enf=30)