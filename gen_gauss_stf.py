import numpy as np
from obspy.io.sac import SACTrace


def gauss(x, a=1, b=0, c=2):
    return a*np.exp(-(x-b)**2/2*c**2)


def create_stf(npts=4800, dt=0.025, shift=10, a=1e-5, b=50, c=1):
    x = np.arange(0, npts)*dt - shift
    y = gauss(x, a, b, c)
    sac = SACTrace(data=y, b=-shift, delta=dt)
    with open('src_rec/sources_ls.dat.tele') as f:
        for line in f.readlines():
            label = line.strip().split()[0]
            sac.write('src_rec/STF_{}.sac'.format(label))


if __name__ == '__main__':
    create_stf()
    
