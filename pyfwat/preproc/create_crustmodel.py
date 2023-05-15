import numpy as np
from ..pario import readpar
from pyproj import Proj
from scipy.signal.windows import hann
from scipy.interpolate import griddata
from os.path import join, dirname, abspath
import argparse


def ignore_nan_3d(data):
    index = np.where(~np.isnan(data))
    values = data[index]
    points = np.array(index).T
    zidx = np.arange(data.shape[0])
    yidx = np.arange(data.shape[1])
    xidx = np.arange(data.shape[2])
    zz, xx, yy = np.meshgrid(zidx, yidx, xidx, indexing='ij')
    interpolated = griddata(
        points, values, 
        (zz, xx, yy), 
        method='nearest'
    )
    result = interpolated.reshape(data.shape)
    return result


def get_rho(vp):
    # vp = 0.9409 + 2.0947*vs - 0.8206*vs**2 + 0.2683*vs**3 - 0.0251*vs**4
    rho = 1.6612*vp - 0.4721*vp**2 + 0.0671*vp**3 - 0.0043*vp**4 + 0.000106*vp**5
    # vs = 0.7858 - 1.2344*vp + 0.7949*vp**2 - 0.1238*vp**3 + 0.0064*vp**4
    return rho


class CrustModel():
    def __init__(self, fname=join(dirname(abspath(__file__)), 'crust1.0.npz')) -> None:
        """Read internal CRUST1.0 model

        :param fname: _description_, defaults to join(dirname(dirname(abspath(__file__))), 'data', 'crust1.0-vp.npz')
        :type fname: str, optional
        """
        self.points = np.load(fname)['model']
        self.read_par()

    def read_par(self, fname='DATA/meshfem3D_files/Mesh_Par_file'):
        latmin = readpar(fname, 'LATITUDE_MIN')
        latmax = readpar(fname, 'LATITUDE_MAX')
        lonmin = readpar(fname, 'LONGITUDE_MIN')
        lonmax = readpar(fname, 'LONGITUDE_MAX')
        self.depmax = readpar(fname, 'DEPTH_BLOCK_KM')
        sup_utm = readpar(fname, 'SUPPRESS_UTM_PROJECTION')
        self.depmin = 0.
        if not sup_utm:
            zone = int(readpar(fname, 'UTM_PROJECTION_ZONE'))
            utm2latlon = Proj(proj='utm', ellps='WGS84', zone=zone)
            self.xmin, self.ymin = utm2latlon(lonmin, latmin)
            self.xmax, self.ymax = utm2latlon(lonmax, latmax)
        else:
            self.xmin = lonmin
            self.xmax = lonmax
            self.ymin = latmin
            self.ymax = latmax

    def griddata(self, hx=5000., hz=1000.):
        """Linearly interpolate velocity into regular grids

        :param hx: interval in meter along X and Y axis, 
        :type hx: float
        :param hz: interval in meter along Z axis
        :type hz: float
        """
        self.hx = hx
        self.hz = hz
        self.x = np.arange(self.xmin, self.xmax+hx, hx)
        self.y = np.arange(self.ymin, self.ymax+hx, hx)
        self.dep = np.arange(self.depmin, self.depmax+hz/1000, hz/1000)

        # Grid data 
        new_dep, new_lat, new_lon = np.meshgrid(self.dep, self.y, self.x, indexing='ij')
        self.grid_vp = griddata(
            self.points[:, 0:3],
            self.points[:, 3], 
            (new_dep, new_lat, new_lon), 
            method='linear'
        )
        self.grid_vs = griddata(
            self.points[:, 0:3],
            self.points[:, 4], 
            (new_dep, new_lat, new_lon), 
            method='linear'
        )

        # Set NaN to nearest value
        self.grid_vp = ignore_nan_3d(self.grid_vp)
        self.grid_vs = ignore_nan_3d(self.grid_vs)
        

    def taper(self, sup_h=5000, buff_h=20000):
        mask_x = np.ones_like(self.x)
        nsup = int(sup_h/self.hx)
        ntaper = int(buff_h/self.hx)
        w = hann(ntaper*2, sym=False)[0:ntaper]
        mask_x[0:nsup] *= 0
        mask_x[nsup:ntaper+nsup] *= w
        w = hann(ntaper*2)[ntaper:]
        mask_x[-nsup:] *= 0
        mask_x[-(nsup+ntaper):-nsup] *= w

        mask_y = np.ones_like(self.y)
        w = hann(ntaper*2, sym=False)[0:ntaper]
        mask_y[0:nsup] *= 0
        mask_y[nsup:ntaper+nsup] *= w
        w = hann(ntaper*2)[ntaper:]
        mask_y[-nsup:] *= 0
        mask_y[-(nsup+ntaper):-nsup] *= w
        mask_xx, mask_yy = np.meshgrid(mask_x, mask_y)
        mask = mask_xx*mask_yy

        for i, _ in enumerate(self.dep):
            self.grid_vp[i, :, :] *= mask
            self.grid_vs[i, :, :] *= mask

    def write(self, fname='DATA/tomo_files/tomography_model.xyz', maxelev=3000.):
        rho = get_rho(self.grid_vp)
        with open(fname, 'w') as f:
            f.write('{:.3f} {:.3f} {:.3f} {:.3f} {:.3f} {:.3f}\n'.format(
                        self.xmin, self.ymin, -self.depmax*1000,
                        self.xmax, self.ymax, maxelev))
            f.write('{:.1f} {:.1f} {:.1f}\n'.format(self.hx, self.hx, self.hz))
            f.write('{:.0f} {:.0f} {:.0f}\n'.format(self.x.size, self.y.size, self.dep.size))
            f.write('{:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.format(
                    np.min(self.grid_vp)*1000, np.max(self.grid_vp)*1000,
                    np.min(self.grid_vs)*1000, np.max(self.grid_vs)*1000,
                    np.min(rho)*1000, np.max(rho)*1000))
            for i, dep in enumerate(self.dep):
                for j, yy in enumerate(self.y):
                    for k, xx in enumerate(self.x):
                        f.write('{:.3f} {:.3f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.format(
                                xx, yy, -dep*1000, 
                                self.grid_vp[i, j, k]*1000,
                                self.grid_vs[i, j, k]*1000,
                                rho[i, j, k]*1000))


def main():
    parser = argparse.ArgumentParser('Create initial model from CRUST1.0')
    parser.add_argument('-o', help='Path to output file, defaults to DATA/tomo_files/tomography_model.xyz',
                        metavar='path', default='DATA/tomo_files/tomography_model.xyz')
    parser.add_argument('-a', help='Interval in meter along horizontal and vertial axis',
                        metavar='hx/hz', default='2000/1000')
    parser.add_argument('-t', help='Boundary taper, sup_x/buff_x, defaults to None', default=None)
    args = parser.parse_args()
    val = [float(v) for v in args.a.split('/')]
    cm = CrustModel(*val)
    cm.griddata()
    if args.t is not None:
        buff = [float(v) for v in args.t.split('/')]
        cm.taper(*buff)
    cm.write(args.o)


if __name__ == '__main__':
    cm = CrustModel()
    cm.griddata()
    cm.taper()
    cm.write()