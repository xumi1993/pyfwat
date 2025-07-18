import numpy as np
from ..pario import readpar, readfwatpar, readfkpar
from pyproj import Proj
from scipy.signal.windows import hann, bartlett
from scipy.ndimage import gaussian_filter
from scipy.interpolate import griddata
from os.path import join, dirname, abspath, exists
from ..utils.utils import get_rho, ignore_nan_3d
import h5py
import argparse

CRUST1_PATH = join(dirname(dirname(abspath(__file__))), 'data', 'crust1.0.npz')

class CrustModel():
    def __init__(self, fname, mesh_fname='DATA/meshfem3D_files/Mesh_Par_file') -> None:
        """Read internal CRUST1.0 model

        :param fname: The model file, defaults to join(dirname(dirname(abspath(__file__))), 'data', 'crust1.0-vp.npz')
                      For custom model, use the ``npz`` file with keys 'model' for points with 5 columns lon, lat, depth, vp, vs.
        :type fname: str, optional
        """
        try:
            self.points = np.loadtxt(fname)
        except:
            self.points = np.load(CRUST1_PATH)['model']
        if not exists(mesh_fname):
            raise FileNotFoundError(f'Mesh parameter file {mesh_fname} does not exist.')
        self.read_par(mesh_fname)
        self.points[:, 0], self.points[:, 1] = self.utm2latlon(self.points[:,0], self.points[:,1])
        self.points[:, 2] *= -1000  # Convert depth to meter

    def read_par(self, fname='DATA/meshfem3D_files/Mesh_Par_file'):
        latmin = readpar(fname, 'LATITUDE_MIN')
        latmax = readpar(fname, 'LATITUDE_MAX')
        lonmin = readpar(fname, 'LONGITUDE_MIN')
        lonmax = readpar(fname, 'LONGITUDE_MAX')
        self.depmin = -readpar(fname, 'DEPTH_BLOCK_KM')*1000
        sup_utm = readpar(fname, 'SUPPRESS_UTM_PROJECTION')
        self.depmax = 0.
        if not sup_utm:
            zone = int(readpar(fname, 'UTM_PROJECTION_ZONE'))
            self.utm2latlon = Proj(proj='utm', ellps='WGS84', zone=zone)
            self.xmin, self.ymin = self.utm2latlon(lonmin, latmin)
            self.xmax, self.ymax = self.utm2latlon(lonmax, latmax)
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
        self.z = np.arange(self.depmin, self.depmax+hz, hz)

        # Grid data 
        new_xx, new_yy, new_zz  = np.meshgrid(self.x, self.y, self.z, indexing='ij')
        self.grid_vp = griddata(
            self.points[:, 0:3],
            self.points[:, 3], 
            (new_xx, new_yy, new_zz), 
            method='linear'
        )
        self.grid_vs = griddata(
            self.points[:, 0:3],
            self.points[:, 4], 
            (new_xx, new_yy, new_zz), 
            method='linear'
        )

        # Set NaN to nearest value
        self.grid_vp = ignore_nan_3d(self.grid_vp)
        self.grid_vs = ignore_nan_3d(self.grid_vs)
        self.grid_rho = get_rho(self.grid_vp)
    
    def smooth(self, sigma_h, sigma_v):
        """
        Smooth the model using Gaussian filter
        :param sigma_h: Standard deviation in m for horizontal smoothing
        :type sigma_h: float
        :param sigma_v: Standard deviation in m for vertical smoothing
        :type sigma_v: float
        """

        if sigma_h <= 0 or sigma_v <= 0:
            raise ValueError('sigma_h and sigma_v must be positive')
        # Convert to grid units
        sigma_h /= self.hx
        sigma_v /= self.hz
        self.grid_vp = gaussian_filter(self.grid_vp, [sigma_h, sigma_h, sigma_v])
        self.grid_vs = gaussian_filter(self.grid_vs, [sigma_h, sigma_h, sigma_v])
        self.grid_rho = get_rho(self.grid_vp)

    def _gen_fk_1d(self, fkmodel):
        nlayer = fkmodel.shape[0]
        ztop = fkmodel[:, -1]
        z1d = np.zeros(2*nlayer)
        vp1d = np.zeros(2*nlayer)
        vs1d = np.zeros(2*nlayer)
        rho1d = np.zeros(2*nlayer)
        z1d[0] = self.depmin
        for i in range(nlayer):
            z1d[2*i+1] = ztop[i]
            vp1d[2*i+1] = fkmodel[i, 2]
            vs1d[2*i+1] = fkmodel[i, 3]
            rho1d[2*i+1] = fkmodel[i, 1]
            vp1d[2*i] = fkmodel[i, 2]
            vs1d[2*i] = fkmodel[i, 3]
            rho1d[2*i] = fkmodel[i, 1]
            if i > 0:
                z1d[2*i] = ztop[i-1] + 1
        vs1dgrid = np.zeros_like(self.grid_vp)
        vp1dgrid = np.zeros_like(self.grid_vs)
        rho1dgrid = np.zeros_like(self.grid_rho)
        for iz, zval in enumerate(self.z):
            vp1dgrid[:, :, iz] = np.interp(zval, z1d, vp1d)
            vs1dgrid[:, :, iz] = np.interp(zval, z1d, vs1d)
            rho1dgrid[:, :, iz] = np.interp(zval, z1d, rho1d)
        return vp1dgrid, vs1dgrid, rho1dgrid

    def taper(self, fkmodel_path, sup_h=5000, buff_h=20000, win=hann):
        fkmodel = np.flipud(readfkpar(fkmodel_path, 'LAYER'))
        vp1dgrid, vs1dgrid, rho1dgrid = self._gen_fk_1d(fkmodel)
        mask_x = np.ones_like(self.x)
        nsup = int(sup_h/self.hx)
        ntaper = int(buff_h/self.hx)
        w = win(ntaper*2, sym=False)[0:ntaper]
        mask_x[0:nsup] *= 0
        mask_x[nsup:ntaper+nsup] *= w
        w = win(ntaper*2)[ntaper:]
        mask_x[-nsup:] *= 0
        mask_x[-(nsup+ntaper):-nsup] *= w

        mask_y = np.ones_like(self.y)
        w = win(ntaper*2, sym=False)[0:ntaper]
        mask_y[0:nsup] *= 0
        mask_y[nsup:ntaper+nsup] *= w
        w = win(ntaper*2)[ntaper:]
        mask_y[-nsup:] *= 0
        mask_y[-(nsup+ntaper):-nsup] *= w
        mask_xx, mask_yy = np.meshgrid(mask_x, mask_y)
        mask = mask_xx*mask_yy

        dvp = (self.grid_vp - vp1dgrid) / vp1dgrid
        dvs = (self.grid_vs - vs1dgrid) / vs1dgrid
        drho = (self.grid_rho - rho1dgrid) / rho1dgrid

        for i, _ in enumerate(self.z):
            dvp[:, :, i] *= mask
            dvs[:, :, i] *= mask
            drho[:, :, i] *= mask
        
        self.grid_vp = (dvp*vp1dgrid) + vs1dgrid
        self.grid_vs = (dvs*vs1dgrid) + vs1dgrid
        self.grid_rho = (drho*rho1dgrid) + rho1dgrid

    def write(self, fname:str, format=None):
        """Write the model to file

        :param fname: The output file name
        :type fname: str
        :param format: The output format, can be 'h5' or 'xyz'
        :type format: str
        """
        if format is None:
            format = fname.split('.')[-1].lower()
        if format not in ['h5', 'xyz']:
            raise ValueError(f'Unknown format {format}, only "h5" and "xyz" are supported.')
        if format == 'h5':
            self.write_h5(fname)
        elif format == 'xyz':
            self.write_xyz(fname)
        else:
            pass

    def write_h5(self, fname='DATA/tomo_files/tomography_model.h5'):
        rho = get_rho(self.grid_vp)
        with h5py.File(fname, 'w') as f:
            f.create_dataset('x', data=self.x)
            f.create_dataset('y', data=self.y)
            f.create_dataset('z', data=self.z)
            f.create_dataset('vp', data=self.grid_vp*1000)
            f.create_dataset('vs', data=self.grid_vs*1000)
            f.create_dataset('rho', data=rho*1000)

    def write_xyz(self, fname='DATA/tomo_files/tomography_model.xyz', maxelev=3000.):
        rho = get_rho(self.grid_vp)
        with open(fname, 'w') as f:
            f.write('{:.3f} {:.3f} {:.3f} {:.3f} {:.3f} {:.3f}\n'.format(
                        self.xmin, self.ymin, self.depmin,
                        self.xmax, self.ymax, maxelev))
            f.write('{:.1f} {:.1f} {:.1f}\n'.format(self.hx, self.hx, self.hz))
            f.write('{:.0f} {:.0f} {:.0f}\n'.format(self.x.size, self.y.size, self.dep.size))
            f.write('{:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.format(
                    np.min(self.grid_vp)*1000, np.max(self.grid_vp)*1000,
                    np.min(self.grid_vs)*1000, np.max(self.grid_vs)*1000,
                    np.min(rho)*1000, np.max(rho)*1000))
            for i, dep in enumerate(self.z):
                for j, yy in enumerate(self.y):
                    for k, xx in enumerate(self.x):
                        f.write('{:.3f} {:.3f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.format(
                                xx, yy, -dep*1000, 
                                self.grid_vp[k, j, i]*1000,
                                self.grid_vs[k, j, i]*1000,
                                rho[k, j, i]*1000))


def main():
    parser = argparse.ArgumentParser('Create initial model from CRUST1.0')
    parser.add_argument('-a', help='Interval in meter along horizontal and vertial axis',
                        metavar='hx/hz', default='2000/1000')
    parser.add_argument('-i', help='Text to crust model file with 5 columns of depth, lat, lon, vp, and vs, defaults to crust1.0.npz',
                        default='', metavar='path/to/velocity_model.xyz')
    parser.add_argument('-f', help='Output format, can be h5 or xyz, defaults to h5', default=None, metavar='h5|xyz')
    parser.add_argument('-m', help='Path to Mesh_Par_file, defaults to DATA/meshfem3D_files/Mesh_Par_file',
                        default='DATA/meshfem3D_files/Mesh_Par_file', metavar='path/to/Mesh_Par_file')
    parser.add_argument('-o', help='Path to output file, defaults to DATA/tomo_files/tomography_model.h5',
                        metavar='path', default='DATA/tomo_files/tomography_model.h5')
    parser.add_argument('-s', help='Smooth the model, provide sigma_h and sigma_v in meter, defaults to None', 
                        metavar='sigma_h/sigma_v', default=None)
    parser.add_argument('-t', help='Boundary taper, sup_x/buff_x, defaults to None', default=None)
    args = parser.parse_args()
    val = [float(v) for v in args.a.split('/')]
    cm = CrustModel(args.i, args.m)
    cm.griddata(*val)
    if args.s is not None:
        sigma = [float(v) for v in args.s.split('/')]
        cm.smooth(*sigma)
    if args.t is not None:
        buff = [float(v) for v in args.t.split('/')]
        cm.taper(*buff)
    cm.write(args.o, args.f)


if __name__ == '__main__':
    cm = CrustModel()
    cm.griddata()
    cm.taper()
    cm.write()