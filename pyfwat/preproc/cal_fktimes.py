from pyfwat.pario import readfkpar
import numpy as np
from seispy.geo import sind, cosd
import sys
from pyproj import Proj


class FKTimes():
    def __init__(self, sta_path='DATA/STATIONS', fkname='DATA/FKmodel', utm=True, zone=31) -> None:
        self.fkname = fkname
        self.sta_path = sta_path
        self.read_fk()
        self.get_stations(utm=utm, zone=zone)

    def read_fk(self):
        # fname = 'src_rec/FKmodel_{}'.format(self.evtid)
        self.mod = readfkpar(self.fkname, 'LAYER')
        self.mod[:, 1:] /= 1000
        self.phi = -readfkpar(self.fkname, 'BACK_AZIMUTH')-90.
        self.inc = readfkpar(self.fkname, 'TAKE_OFF')
        self.wavefront = readfkpar(self.fkname, 'ORIGIN_WAVEFRONT') / 1000
    
    def get_stations(self, utm=True, zone=31):
        # sta_path = 'src_rec/STATIONS_{}'.format(self.evtid)
        dtype = {'names': ('station', 'network', 'y', 'x', 'z', 'b'), 'formats': ('U10', 'U10', 'f4', 'f4', 'f4', 'f4')}
        self.stations, self.network, self.stay, self.stax, self.staz, _ = np.loadtxt(self.sta_path, dtype=dtype, unpack=True)
        if utm:
            utm2latlon = Proj(proj='utm', ellps='WGS84', zone=zone)
            self.stax, self.stay = utm2latlon(self.stax, self.stay)
        self.stay /= 1000
        self.stax /= 1000
        self.staz /= 1000

    def cal_slowness(self):
        self.rayp = sind(self.inc)/self.mod[-1, 2]
        self.eta = np.zeros(self.mod.shape[0])
        for i, layer in enumerate(self.mod):
            self.eta[i] = np.sqrt(1/layer[2]**2-self.rayp**2)

    def write_times(self, fname):
        # fname = 'src_rec/FKtimes_{}'.format(self.evtid)
        with open(fname, 'w') as f:
            for i, sta in enumerate(self.stations):
                f.write('{} {} {:.6f}\n'.format(self.network[i], sta, self.tfk[i]))

    def fktimes(self):
        self.cal_slowness()
        self.tfk = np.zeros(self.stay.size)
        h = np.diff(-self.mod[:, 4])
        for i, _ in enumerate(self.stay):
            self.tfk[i] = self.rayp*((self.stax[i]- self.wavefront[0])*cosd(self.phi)+(self.stay[i]-self.wavefront[1])*sind(self.phi)) + \
                     self.eta[-1]*(self.mod[-1, 4]-self.wavefront[2]) + np.sum(self.eta[0:-1]*h[1:])
        # self.write_times()

if __name__ == '__main__':
    fkt = FKTimes(sys.argv[1])
    fkt.fktimes()
    # print(fkt.tfk)