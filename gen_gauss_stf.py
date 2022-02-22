import numpy as np
from obspy.io.sac import SACTrace


def gauss(x, a=1, b=0, c=2):
    return a*np.exp(-(x-b)**2/2*c**2)


def create_stf(npts=1500, dt=0.04, shift=6, a=1e-5, b=20, c=0.6):
    x = np.arange(0, npts)*dt - shift
    y = gauss(x, a, b, c)
    sac = SACTrace(data=y, b=-shift, delta=dt)
    sac.write('src_rec/STF_13.sac')
    # with open('src_rec/sources_ls.dat.tele') as f:
    #     for line in f.readlines():
    #         label = line.strip().split()[0]
    #         sac.write('src_rec/STF_{}.sac'.format(label))


if __name__ == '__main__':
    create_stf()
    
