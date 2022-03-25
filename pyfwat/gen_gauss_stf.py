#!/usr/bin/env python
import numpy as np
from obspy.io.sac import SACTrace
import sys
from utils import readpar

def gauss(x, a=1, b=0, c=2):
    return a*np.exp(-(x-b)**2/2*c**2)


def create_stf(evtid, npts=3000, dt=0.04, shift=6, a=1e-5, c=0.8):
    x = np.arange(0, npts)*dt - shift
    b = npts/2 * dt - shift 
    y = gauss(x, a, b, c)
    sac = SACTrace(data=y, b=-shift, delta=dt)
    sac.write('src_rec/STF_{}.sac'.format(evtid))
    # with open('src_rec/sources_ls.dat.tele') as f:
    #     for line in f.readlines():
    #         label = line.strip().split()[0]
    #         sac.write('src_rec/STF_{}.sac'.format(label))


def stf(setname, shift=6, amp=1e-5,c=0.8):
    with open('src_rec/sources_{}.dat'.format(setname)) as f:
        evtid = f.readline().strip().split()[0]
    parfile = 'DATA/Par_file'
    npts = readpar(parfile, 'NSTEP')
    dt = readpar(parfile, 'DT')
    create_stf(evtid, npts, dt, shift, amp, c)


if __name__ == '__main__':
    if len(sys.argv[1:]) == 1:
        setname = sys.argv[1]
        stf(setname)
    elif len(sys.argv[1:]) == 4:
        setname = sys.argv[1]
        shift = float(sys.argv[2])
        amp = float(sys.argv[3])
        c = float(sys.argv[4])
        stf(setname, shift, amp, c)
    else:
        print('Usage: gen_gauss_stf set_name [time_shift amp gauss_factor]')
        sys.exit(1)
    
