#!/usr/bin/env python
import numpy as np
from seispy.geo import asind
import sys
from os.path import dirname, abspath
sys.path.append(dirname(dirname(abspath(__file__))))
from setfk import chpar
from utils import readfkpar
import argparse


class FKEvts():
    def __init__(self, baz, rayp, fkfile='DATA/FKMODEL',
                 stafile='DATA/STATIONS') -> None:
        self.baz = baz
        self.rayp = rayp
        model = readfkpar(fkfile, 'LAYER')
        vp_half = model[-1, 2]
        with open(stafile) as f:
            self.stations = f.read()
        with open(fkfile) as f:
            self.fkpar = f.read()
        self.inc_angle = asind(self.rayp*vp_half)
        

    def evt_set(self, basepath='src_rec'):
        count = 0
        for baz in self.baz:
            for inc in self.inc_angle:
                count += 1
                evtid = '{}'.format(count)
                setid = 'set{:d}'.format(count)
                chpar(self.fkpar, 'BACK_AZIMUTH', baz)
                chpar(self.fkpar, 'TAKE_OFF', inc)
                with open('{}/FKmodel_{}'.format(basepath, evtid), 'w') as f:
                    f.write(self.fkpar)
                with open('{}/sources_{}.dat'.format(basepath, setid), 'w') as f:
                    f.write('{} 0.0 0.0 0.0 0.0\n'.format(evtid))
                with open('{}/STATIONS_{}'.format(basepath, evtid), 'w') as f:
                    f.write(self.stations)

def main():
    parser = argparse.ArgumentParser('Generate FKmodel, sources and STATIONS')
    parser.add_argument('-b', help='Range of back-azimuth, defaults to 0/360/45',
                        default='0/360/45', metavar='baz_start/baz_end/baz_val')
    parser.add_argument('-r', help='Range of ray_parameters in s/km, defaults to 0.03/0.09/0.01',
                        default='0.03/0.09/0.01', metavar='rayp_start/rayp_end/rayp_val')
    parser.add_argument('-f', help='Path to a template of FKMODEL, defaults to DATA/FKMODEL',
                        default='DATA/FKMODEL', metavar='FKMODEL')
    parser.add_argument('-s', help='Path to a template of STATIONS, defaults to DATA/STATIONS',
                        default='DATA/STATIONS', metavar='STATIONS')
    parser.add_argument('-o', help='Output path, defaults to src_rec', default='src_rec', metavar='src_rec')
    args = parser.parse_args()
    try:
        bazs = [float(v) for v in args.b.split('/')]
        baz = np.arange(*bazs)
    except:
        print('ERROR: Error format in -b argument')
        sys.exit(1)
    try:
        rayps = [float(v) for v in args.r.split('/')]
        rayp = np.arange(*rayps)
    except:
        print("ERROR: Error format in -r argument")
        sys.exit(1)

    fke = FKEvts(baz, rayp, args.f, args.s)
    fke.evt_set(args.o)


if __name__ == '__main__':
    main()