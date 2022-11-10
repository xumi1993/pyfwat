import numpy as np
import os
import re
from glob import glob
from scipy.interpolate import griddata


def read_fortran_external_mesh(filename, ngllx=5, nglly=5, ngllz=5):
    with open(filename, "rb") as file:
        data = {}
        data['nspec_ab'] = np.fromfile(file, dtype="int32", offset=4, count=1)[0]
        data['nglob_ab'] = np.fromfile(file, dtype="int32",offset=8, count=1)[0]
        data['nspec_irr'] = np.fromfile(file, dtype="int32",offset=8, count=1)[0]
        nbool = ngllx*nglly*ngllz*data['nspec_ab']
        data['ibool'] = np.fromfile(file, dtype="int32", offset=8, count=nbool).reshape(
            ngllx,nglly,ngllz,data['nspec_ab'], order='F')
        data['xstore'] = np.fromfile(file, dtype="float32", offset=8, count=data['nglob_ab'])
        data['ystore'] = np.fromfile(file, dtype="float32", offset=8, count=data['nglob_ab'])
        data['zstore'] = np.fromfile(file, dtype="float32", offset=8, count=data['nglob_ab'])
    return data


def read_fortran_model(filename, nspec_ab, ngllx=5, nglly=5, ngllz=5):
    with open(filename, "rb") as file:
        file.seek(0)
        data = np.fromfile(file, dtype="float32", offset=4)[:-1].reshape(
            ngllx,nglly,ngllz,nspec_ab, order='F')
        return data


class GllModel:
    def __init__(self, inpath, parameters=['vp', 'vs', 'rho'], ngllx=5, nglly=5, ngllz=5) -> None:
        self.inpath = inpath
        self.parameters = parameters
        self.model_data = {}
        for para in parameters:
            self.model_data[para] = []
        self.nglls = {'ngllx': ngllx,
                      'nglly': nglly,
                      'ngllz': ngllz}
        self.read_external_mesh()
        self.get_minmax()

    def get_minmax(self):
        self.xmin = np.min([np.min(ex['xstore']) for ex in self.external_meshs])
        self.xmax = np.max([np.max(ex['xstore']) for ex in self.external_meshs])
        self.ymin = np.min([np.min(ex['ystore']) for ex in self.external_meshs])
        self.ymax = np.max([np.max(ex['ystore']) for ex in self.external_meshs])
        self.zmin = np.min([np.min(ex['zstore']) for ex in self.external_meshs])
        self.zmax = np.max([np.max(ex['zstore']) for ex in self.external_meshs])

    def read_external_mesh(self):
        self.external_meshs = []
        extbins = glob(os.path.join(
            self.inpath, 'proc*_external_mesh.bin')
        )
        self.nproc = len(extbins)
        for _, extbin in enumerate(extbins):
            pname = re.search(r'proc(\d{6})', extbin).groups()[0]
            mesh_data = read_fortran_external_mesh(extbin, **self.nglls)
            self.external_meshs.append(mesh_data)
            for para in self.parameters:
                fname = os.path.join(self.inpath, 'proc{}_{}.bin'.format(pname, para))
                self.model_data[para].append(read_fortran_model(fname, mesh_data['nspec_ab'], **self.nglls))

    def griddata(self, x, y, z, method='linear'):
        """ grid data with given series of x, y, z.

        Parameters
        ----------
        x : 1D numpy.ndarray
            Series of x
        y : 1D numpy.ndarray
            Series of y
        z : 1D numpy.ndarray
            Series of z
        method : str, optional
            method for interpolation, by default 'linear'
        """
        points = np.empty([0, 3+len(self.parameters)])
        x_inter, y_inter, z_inter = np.meshgrid(x, y, z)
        for i in range(self.nproc):
            points = np.vstack((points, self._get_gll_point(i)))
        grid_data = {}
        for i, para in enumerate(self.parameters):
            grid_data[para] = griddata(points[:, 0:3], points[:, i+3],
                (x_inter, y_inter, z_inter), method=method)
        return grid_data

    def _get_gll_point(self, idx):
        external_mesh = self.external_meshs[idx]
        data = [self.model_data[para][idx] for para in self.parameters]
        points = np.zeros([external_mesh['nspec_ab']* \
            self.nglls['ngllx']*self.nglls['nglly']*self.nglls['ngllz'],
            3+len(self.parameters)]
        )
        n = 0
        for ispec in range(external_mesh['nspec_ab']):
            for k in range(self.nglls['ngllz']):
                for j in range(self.nglls['nglly']):
                    for i in range(self.nglls['ngllx']):
                        iglob = external_mesh['ibool'][i,j,k,ispec]
                        points[n, 0] = external_mesh['xstore'][iglob-1]
                        points[n, 1] = external_mesh['ystore'][iglob-1]
                        points[n, 2] = external_mesh['zstore'][iglob-1]
                        for m, _ in enumerate(self.parameters):
                            points[n, m+3] = data[m][i, j, k, ispec]
                        n += 1
        return points

