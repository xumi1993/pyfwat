#!/usr/bin/env python
from genericpath import exists
from os import makedirs
import numpy as np
from seispy.geo import asind, latlon_from
import sys
from ..pario import readfkpar, chpar, readpar
import argparse
from scipy.interpolate import interp1d
from pyproj import Proj



def get_dist(px):
    dist = np.array([30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90])
    rayp = np.array([0.079422, 0.0773818, 0.0745565, 0.0714173, 0.0682781, 0.0649819, \
                     0.0616857, 0.0585465, 0.0552503, 0.0519541, 0.0485010, 0.0450478, 0.0415947])
    return interp1d(rayp, dist, bounds_error=False, fill_value='extrapolate')(px)

def get_evt(la, lo, baz, dis):
    for i, ba in baz:
        for j, di in dis:
            lat, lon = latlon_from(la, lo, ba, di)


class FKEvts():
    def __init__(self, baz, rayp, fkfile='DATA/FKMODEL',
                 stafile='DATA/STATIONS') -> None:
        self.baz = baz
        self.rayp = rayp
        model = readfkpar(fkfile, 'LAYER')
        vp_half = model[-1, 2]/1000
        with open(stafile) as f:
            self.stations = f.read()
        with open(fkfile) as f:
            self.fkpar = f.read()
        self.inc_angle = asind(self.rayp*vp_half)
        self.dis = get_dist(rayp)
        
    def evt_set(self, basepath='src_rec', center_la=None, center_lo=None):
        if not exists(basepath):
            makedirs(basepath)
        count = 0
        latmin = readpar('DATA/meshfem3D_files/Mesh_Par_file', 'LATITUDE_MIN')
        latmax = readpar('DATA/meshfem3D_files/Mesh_Par_file', 'LATITUDE_MAX')
        lonmin = readpar('DATA/meshfem3D_files/Mesh_Par_file', 'LONGITUDE_MIN')
        lonmax = readpar('DATA/meshfem3D_files/Mesh_Par_file', 'LONGITUDE_MAX')
        zmax = readpar('DATA/meshfem3D_files/Mesh_Par_file', 'DEPTH_BLOCK_KM')*-1000 - 20000
        utm_zone = str(int(readpar('DATA/meshfem3D_files/Mesh_Par_file', 'UTM_PROJECTION_ZONE')))
        if not readpar('DATA/meshfem3D_files/Mesh_Par_file', 'SUPPRESS_UTM_PROJECTION'):
            center_la = (latmin+latmax)/2
            center_lo = (lonmin+lonmax)/2
            utm = Proj(proj='utm', ellps='WGS84', zone=utm_zone)
            xmin, ymin = utm(lonmin, latmin)
            xmax, ymax = utm(lonmax, latmax)
        else:
            xmin = lonmin
            ymin = latmin
            xmax = lonmax
            ymax = lonmax
        with open('{}/sources_ls.dat'.format(basepath), 'w') as fls:
            for baz in self.baz:
                for i, inc in enumerate(self.inc_angle):
                    count += 1
                    if not readpar('DATA/meshfem3D_files/Mesh_Par_file', 'SUPPRESS_UTM_PROJECTION'):
                        evla, evlo = latlon_from(center_la, center_lo, baz, self.dis[i])
                    else:
                        evla, evlo = 0., 0.
                    evtid = '{}'.format(count)
                    setid = 'set{:d}'.format(count)
                    self.fkpar = chpar(self.fkpar, 'BACK_AZIMUTH', baz, type='fk')
                    self.fkpar = chpar(self.fkpar, 'TAKE_OFF', inc, type='fk')
                    if 0 <= baz < 90:
                        self.fkpar = chpar(self.fkpar, 'ORIGIN_WAVEFRONT', '{:.1f} {:.1f} {:.1f}'.format(xmax,ymax, zmax), type='fk')
                    if 90 <= baz < 180:
                        self.fkpar = chpar(self.fkpar, 'ORIGIN_WAVEFRONT', '{:.1f} {:.1f} {:.1f}'.format(xmax,ymin, zmax), type='fk')
                    if 180 <= baz < 270:
                        self.fkpar = chpar(self.fkpar, 'ORIGIN_WAVEFRONT', '{:.1f} {:.1f} {:.1f}'.format(xmin,ymin, zmax), type='fk')
                    if 270 <= baz < 360:
                        self.fkpar = chpar(self.fkpar, 'ORIGIN_WAVEFRONT', '{:.1f} {:.1f} {:.1f}'.format(xmin,ymax, zmax), type='fk')
                    with open('{}/FKmodel_{}'.format(basepath, evtid), 'w') as f:
                        f.write(self.fkpar)
                    with open('{}/sources_{}.dat'.format(basepath, setid), 'w') as f:
                        f.write('{} {:.4f} {:.4f} 0.0 0.0\n'.format(evtid, evla, evlo))
                    with open('{}/STATIONS_{}'.format(basepath, evtid), 'w') as f:
                        f.write(self.stations)
                    fls.write('{} {:.4f} {:.4f} 0.0 0.0\n'.format(evtid, evla, evlo))
            


def main():
    parser = argparse.ArgumentParser('Generate FKmodel, sources and STATIONS')
    parser.add_argument('-b', help='Range of back-azimuth, defaults to 0/360/45',
                        default='0/360/45', metavar='baz_start/baz_end/baz_val')
    parser.add_argument('-c', help='Central location of the region, defaults to read from Meshfile3D',
                        default=None, metavar='central_la/central_lo')
    parser.add_argument('-r', help='Range of ray_parameters in s/km, defaults to 0.045/0.09/0.015',
                        default='0.045/0.09/0.015', metavar='rayp_start/rayp_end/rayp_val')
    parser.add_argument('-f', help='Path to a template of FKMODEL, defaults to DATA/FKMODEL',
                        default='DATA/FKMODEL', metavar='FKMODEL')
    parser.add_argument('-s', help='Path to a template of STATIONS, defaults to DATA/STATIONS',
                        default='DATA/STATIONS', metavar='STATIONS')
    parser.add_argument('-o', help='Output path, defaults to ./src_rec', default='./src_rec', metavar='src_rec')
    args = parser.parse_args()
    if args.c is None:
        center_la = None
        center_lo = None
    else:
        try:
            central_loc = [float(v) for v in args.c.split('/')]
            center_la = central_loc[0]
            center_lo = central_loc[1]
        except:
            print('ERROR: Error format in -c argument')
            sys.exit(1)
    try:
        bazs = [float(v) for v in args.b.split('/')]
        baz = np.arange(*bazs)
        # print(baz)
    except:
        print('ERROR: Error format in -b argument')
        sys.exit(1)
    try:
        rayps = [float(v) for v in args.r.split('/')]
        rayp = np.arange(*rayps)
        # print(rayp)
    except:
        print("ERROR: Error format in -r argument")
        sys.exit(1)
    fke = FKEvts(baz, rayp, args.f, args.s)
    fke.evt_set(args.o,center_la, center_lo)


if __name__ == '__main__':
    main()