#!/usr/bin/env python
"""Write Gaussian source time functions for the events of a set.

Command-line tool: ``fwat_gen_gauss_stf``.
"""

from curses import meta
import numpy as np
from obspy.io.sac import SACTrace
import sys
from ..utils.pario import readfwatpar
import argparse

def gauss(x, a=1, b=0, c=2):
    """Gaussian function ``a * exp(-(x - b)**2 / (2 * c**2))``.

    :param x: Abscissa
    :type x: float or numpy.ndarray
    :param a: Amplitude, defaults to 1
    :type a: float, optional
    :param b: Center, defaults to 0
    :type b: float, optional
    :param c: Standard deviation, defaults to 2
    :type c: float, optional
    :rtype: float or numpy.ndarray
    """
    return a*np.exp(-(x-b)**2/(2*c**2))


def create_stf(evtid, npts=3000, dt=0.04, a=1e-5, c=0.8):
    """Write a Gaussian source time function to ``src_rec/STF_<evtid>.sac``.

    The trace begins at ``-npts * dt / 2`` and peaks ``2.772 * c`` s after the
    origin time.

    :param evtid: Event id
    :type evtid: str
    :param npts: Number of samples, defaults to 3000
    :type npts: int, optional
    :param dt: Sampling interval in s, defaults to 0.04
    :type dt: float, optional
    :param a: Peak amplitude, defaults to 1e-5
    :type a: float, optional
    :param c: Standard deviation of the Gaussian in s, defaults to 0.8
    :type c: float, optional
    """
    shift = 2.772*c
    x = np.arange(0, npts)*dt - shift
    b = npts/2 * dt - shift 
    y = gauss(x, a, b, c)
    times = np.arange(npts)*dt - b
    new_times = np.arange(npts) * dt - (npts/2 * dt)
    data = np.interp(new_times, times, y)
    sac = SACTrace(data=data, b=-(npts/2 * dt), delta=dt)
    sac.write('src_rec/STF_{}.sac'.format(evtid))
    # with open('src_rec/sources_ls.dat.tele') as f:
    #     for line in f.readlines():
    #         label = line.strip().split()[0]
    #         sac.write('src_rec/STF_{}.sac'.format(label))


def stf(setname, amp=1e-5,c=0.8,parfile = 'DATA/FWAT.PAR'):
    """Write Gaussian source time functions for all events of a set.

    The number of samples and the sampling interval are ``TELE_NSTEP`` and
    ``TELE_DT`` of the parameter file.

    :param setname: Set name of ``src_rec/sources_<setname>.dat``
    :type setname: str
    :param amp: Peak amplitude, defaults to 1e-5
    :type amp: float, optional
    :param c: Standard deviation of the Gaussian in s, defaults to 0.8
    :type c: float, optional
    :param parfile: SpecFWAT parameter file, defaults to ``DATA/FWAT.PAR``
    :type parfile: str, optional
    """
    with open('src_rec/sources_{}.dat'.format(setname)) as f:
        for line in f.readlines():
            evtid = line.split()[0]
            npts = int(readfwatpar(parfile, 'TELE_NSTEP'))
            dt = readfwatpar(parfile, 'TELE_DT')
            create_stf(evtid, npts, dt, amp, c)


def main():
    """Command-line entry point of ``fwat_gen_gauss_stf``."""
    parser = argparse.ArgumentParser('Plot Misfit with iterations')
    parser.add_argument('-s', help='Set name', metavar='set1')
    parser.add_argument('-a', help='Max amplitude, defaults to 1e-5', metavar='amp', type=float, default=1e-5)
    parser.add_argument('-g', help='Sigma of the gaussian function', type=float, default=0.8)
    args = parser.parse_args()
    stf(args.s, args.a, args.g)

if __name__ == '__main__':
    main()
    
