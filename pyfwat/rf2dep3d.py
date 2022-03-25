#!/usr/bin/env python
import numpy as np
from obspy.io.sac import SACTrace
from os.path import join
from obspy.taup import TauPyModel
from seispy.geo import srad2skm, km2deg, latlon_from, deg2km, rad2deg
from seispy.rfcorrect import psrf2depth, DepModel
model = TauPyModel(model="iasp91")

class SACStation():
    def __init__(self, staname, stla, stlo):
        self.staname = staname
        self.stla = stla
        self.stlo = stlo
        self.shift = 10
        self.datar = None
        self.rayp = None
        self.sampling = None
        self.baz = None
        self.RFlength = None
        self.ev_num = None
        self.rfdep = None
        self.x_s = None
        self.x_p = None


def readsta(pname):
    sta_lst = join(pname, 'DATA', 'STATIONS')
    dtype = {'names': ('sta', 'net', 'y', 'x', 'z', 'b'),
             'formats': ('U20', 'U20', 'f8', 'f8', 'f8', 'f4')}
    staname, netname, y, x, z, _ = np.loadtxt(sta_lst, dtype=dtype, unpack=True)
    return staname, netname, y, x, z


def readrf(pname):
    evts = np.loadtxt(join(pname, 'evts.lst'))
    staname, netname, stay, stax, _ = readsta(pname)
    rfpath = join(pname, 'OUTPUT_RF')
    rf_all = []
    for sta, net, x, y in zip(staname, netname, stax, stay):
        datar = []
        rayp = np.array([])
        baz = np.array([])
        stadata = SACStation(net+'.'+sta, y, x)
        for i, evt in enumerate(evts):
            sac = SACTrace.read(join(rfpath, '{:.0f}.{:.0f}'.format(evt[1], evt[2]), '{}.{}.rf.r'.format(net, sta)))
            datar.append(sac.data)
            baz = np.append(baz, evt[2])
            rayp = np.append(rayp, model.get_travel_times(evt[0], evt[1], phase_list=['P'])[0].ray_param)
        stadata.datar = np.vstack(datar)
        stadata.baz = baz
        stadata.rayp = rayp
        stadata.sampling = sac.delta
        stadata.RFlength = sac.npts
        stadata.ev_num = evts.shape[0]
        
        rf_all.append(stadata)
    return rf_all


def write_xyz(x, z, data, fname='stack.dat'):
    with open(fname, 'w') as f:
        for i, xx in enumerate(x):
            for j, zz in enumerate(z):
                f.write('{:.2f} {:.2f} {:.4f}\n'.format(xx*1000, zz*-1000, data[j, i]))

class SEMRF():
    def __init__(self, pname):
        self.rf_all = readrf(pname)
        self.model = np.load(join(pname, 'vel.npz'))

    def rf2depth(self, maxdep=100):
        self.deprange = np.arange(0, maxdep+1)
        for stadata in self.rf_all:
            stadata.rfdep, _, stadata.x_s, stadata.x_p = psrf2depth(stadata, self.deprange, stadata.sampling, stadata.shift, velmod_3d=self.model)
            stadata.x_s = rad2deg(stadata.x_s)
            stadata.x_p = rad2deg(stadata.x_p)
    
    def writerays(self):
        with open('srays.dat', 'w') as f:
            for stadata in self.rf_all:
                for i in range(stadata.ev_num):
                    f.write('> {:.4f} {:.4f}\n'.format(stadata.baz[i], stadata.rayp[i]))
                    pierce_lat, pierce_lon = latlon_from(km2deg(stadata.stla*0.001), km2deg(stadata.stlo*0.001), stadata.baz[i], stadata.x_s[i])
                    pierce_lat = deg2km(pierce_lat)*1000
                    pierce_lon = deg2km(pierce_lon)*1000
                    for lo, la, z in zip(pierce_lon, pierce_lat, self.deprange):
                        f.write('{:.2f} {:.2f} {:.2f}\n'.format(lo, la, z*-1000))
        
    def stack(self, step=5000, stack_begin=0, stack_end=200000, fname='stack.dat'):
        profile_range = np.append(np.arange(stack_begin, stack_end, step), stack_end)/1000
        depmod = DepModel(self.deprange)
        fresnel_radius = np.sqrt(0.5 * 5 * depmod.vs * self.deprange)
        self.stack_data = np.zeros([len(self.deprange), len(profile_range)])*np.nan
        count = np.zeros_like(self.stack_data)
        for i, x in enumerate(profile_range):
            for j, z in enumerate(self.deprange):
                stack_bin = 0
                for sta in self.rf_all:
                    x_s = deg2km(sta.x_s)+sta.stlo/1000
                    idx = np.where(np.abs(x_s[:, j]-x)<fresnel_radius[j])[0]
                    if len(idx) != 0:
                        stack_bin += np.sum(sta.rfdep[idx, j])
                        count[j, i] += len(idx)
                if count[j, i] != 0:
                    self.stack_data[j, i] = stack_bin / count[j, i] 
        write_xyz(profile_range, self.deprange, self.stack_data, fname=fname)

                    

if __name__ == "__main__":
    pname = '/share/home/goxu/xu_mijian/workspace/semfk/slop_evts'
    rf = SEMRF(pname)
    rf.rf2depth()
    # rf.writerays()
    rf.stack()
