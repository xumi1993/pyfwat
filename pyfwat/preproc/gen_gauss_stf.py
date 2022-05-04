#!/usr/bin/env python
from curses import meta
import numpy as np
from obspy.io.sac import SACTrace
import sys
from ..pario import readpar
import argparse

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
    with open('src_rec/sources_set{}.dat'.format(setname)) as f:
        evtid = f.readline().strip().split()[0]
    parfile = 'DATA/Par_file'
    npts = int(readpar(parfile, 'NSTEP'))
    dt = readpar(parfile, 'DT')
    create_stf(evtid, npts, dt, shift, amp, c)


def main():
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-s', help='Start and end set ID', metavar='start_id/end_id')
    parser.add_argument('-t', help='Time shift in sec', metavar='shift', type=float)
    parser.add_argument('-a', help='Max amplitude, defaults to 1e-5', metavar='amp', type=float, default=1e-5)
    parser.add_argument('-g', help='Sigma of the gaussian function', type=float, default=0.8)
    args = parser.parse_args()
    ids = [int(v) for v in args.s.split('/')]
    for id in np.arange(ids[0], ids[1]+1):
        stf(str(id), args.t, args.a, args.g)

if __name__ == '__main__':
    main()
    
