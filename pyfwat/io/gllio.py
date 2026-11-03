"""Read and write SPECFEM binary mesh and GLL model files."""

import numpy as np
import os
import re
from glob import glob
from scipy.interpolate import griddata


def read_fortran_external_mesh(filename, ngllx=5, nglly=5, ngllz=5):
    """Read the mesh of one processor from a SPECFEM ``proc*_external_mesh.bin``.

    :param filename: Path to the binary mesh file
    :type filename: str
    :param ngllx: Number of GLL points per element along x, defaults to 5
    :type ngllx: int, optional
    :param nglly: Number of GLL points per element along y, defaults to 5
    :type nglly: int, optional
    :param ngllz: Number of GLL points per element along z, defaults to 5
    :type ngllz: int, optional
    :return: ``nspec_ab``, ``nglob_ab`` and ``nspec_irr`` counts, the global
        numbering ``ibool`` of shape ``(ngllx, nglly, ngllz, nspec_ab)`` and the
        global point coordinates ``xstore``, ``ystore``, ``zstore``
    :rtype: dict
    """
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
    """Read a GLL model of one processor from a SPECFEM ``proc*_<name>.bin``.

    :param filename: Path to the binary model file
    :type filename: str
    :param nspec_ab: Number of spectral elements of the processor
    :type nspec_ab: int
    :param ngllx: Number of GLL points per element along x, defaults to 5
    :type ngllx: int, optional
    :param nglly: Number of GLL points per element along y, defaults to 5
    :type nglly: int, optional
    :param ngllz: Number of GLL points per element along z, defaults to 5
    :type ngllz: int, optional
    :return: Model values of shape ``(ngllx, nglly, ngllz, nspec_ab)``
    :rtype: numpy.ndarray
    """
    with open(filename, "rb") as file:
        file.seek(0)
        data = np.fromfile(file, dtype="float32", offset=4)[:-1].reshape(
            ngllx,nglly,ngllz,nspec_ab, order='F')
        return data


def write_fortran_model(filename, data):
    """Write a GLL model to a Fortran unformatted binary file.

    The data are written in Fortran order as one record, framed by the record
    length in bytes.

    :param filename: Output path of the binary file
    :type filename: str
    :param data: Model values of shape ``(ngllx, nglly, ngllz, nspec_ab)``
    :type data: numpy.ndarray
    """
    # Flatten the data in Fortran order
    data_flat = data.flatten(order='F').astype('float32')
    
    # Calculate record length in bytes
    record_length = data_flat.nbytes
    
    with open(filename, "wb") as file:
        # Write header (4-byte integer for record length)
        np.array([record_length], dtype='int32').tofile(file)
        # Write data
        data_flat.tofile(file)
        # Write footer (4-byte integer for record length)
        np.array([record_length], dtype='int32').tofile(file)


class GllModel:
    """GLL model of all processors of a SPECFEM mesh.

    The mesh and model files are read on creation. ``model_data[name]`` holds one
    array per processor, and ``xmin`` ... ``zmax`` give the extent of the mesh.
    """
    def __init__(self, mesh_path, volumn_path, volumns=['vp', 'vs', 'rho'], ngllx=5, nglly=5, ngllz=5) -> None:
        """:param mesh_path: Directory with the ``proc*_external_mesh.bin`` files
        :type mesh_path: str
        :param volumn_path: Directory with the ``proc*_<name>.bin`` model files
        :type volumn_path: str
        :param volumns: Names of the model parameters to read, defaults to
            ``['vp', 'vs', 'rho']``
        :type volumns: list of str or str, optional
        :param ngllx: Number of GLL points per element along x, defaults to 5
        :type ngllx: int, optional
        :param nglly: Number of GLL points per element along y, defaults to 5
        :type nglly: int, optional
        :param ngllz: Number of GLL points per element along z, defaults to 5
        :type ngllz: int, optional
        """
        self.mesh_path = mesh_path
        self.volumn_path = volumn_path
        self.model_data = {}
        if isinstance(volumns, str):
            volumns = [volumns]
        self.parameters = volumns
        for para in volumns:
            self.model_data[para] = []
        self.nglls = {'ngllx': ngllx,
                      'nglly': nglly,
                      'ngllz': ngllz}
        self.read_external_mesh()
        self._get_minmax()

    def _get_minmax(self):
        """Set ``xmin``, ``xmax``, ``ymin``, ``ymax``, ``zmin`` and ``zmax`` from the mesh of all processors."""
        self.xmin = np.min([np.min(ex['xstore']) for ex in self.external_meshs])
        self.xmax = np.max([np.max(ex['xstore']) for ex in self.external_meshs])
        self.ymin = np.min([np.min(ex['ystore']) for ex in self.external_meshs])
        self.ymax = np.max([np.max(ex['ystore']) for ex in self.external_meshs])
        self.zmin = np.min([np.min(ex['zstore']) for ex in self.external_meshs])
        self.zmax = np.max([np.max(ex['zstore']) for ex in self.external_meshs])

    def read_external_mesh(self):
        """Read the mesh and the model parameters of every processor.

        Fills ``external_meshs``, ``nproc`` and ``model_data``.
        """
        self.external_meshs = []
        extbins = glob(os.path.join(
            self.mesh_path, 'proc*_external_mesh.bin')
        )
        self.nproc = len(extbins)
        for _, extbin in enumerate(extbins):
            pname = re.search(r'proc(\d{6})', extbin).groups()[0]
            mesh_data = read_fortran_external_mesh(extbin, **self.nglls)
            self.external_meshs.append(mesh_data)
            for para in self.parameters:
                fname = os.path.join(self.volumn_path, 'proc{}_{}.bin'.format(pname, para))
                self.model_data[para].append(read_fortran_model(fname, mesh_data['nspec_ab'], **self.nglls))

    def get_points_data(self):
        """Collect the GLL points of all processors into ``points``.

        ``points`` has one row per GLL point: x, y, z, then one column per model
        parameter. Call it before :meth:`griddata`.
        """
        self.points = np.empty([0, 3+len(self.parameters)])
        for i in range(self.nproc):
            self.points = np.vstack((self.points, self._get_gll_point(i)))

    def write(self, output_path, key=None):
        """Write the model data back to Fortran binary files.

        :param output_path: Directory of the output ``proc*_<name>.bin`` files,
            created if needed
        :type output_path: str
        :param key: Name of the only parameter to write, defaults to all parameters
        :type key: str, optional
        """
        os.makedirs(output_path, exist_ok=True)
        if key is None:
            fields = self.parameters
        else:
            fields = [key]
        for i in range(self.nproc):
            pname = f"{i:06d}"
            for para in fields:
                fname = os.path.join(output_path, f'proc{pname}_{para}.bin')
                write_fortran_model(fname, self.model_data[para][i])

    def griddata(self, x, y, z, method='linear'):
        """Interpolate the GLL model onto a regular grid.

        :meth:`get_points_data` must be called first.

        :param x: Grid coordinates along x
        :type x: numpy.ndarray
        :param y: Grid coordinates along y
        :type y: numpy.ndarray
        :param z: Grid coordinates along z
        :type z: numpy.ndarray
        :param method: Interpolation method of :func:`scipy.interpolate.griddata`,
            defaults to ``'linear'``
        :type method: str, optional
        :return: Gridded values of each parameter, shaped like
            ``numpy.meshgrid(x, y, z)``
        :rtype: dict of numpy.ndarray
        """
        # points = np.empty([0, 3+len(self.parameters)])
        x_inter, y_inter, z_inter = np.meshgrid(x, y, z)
        # for i in range(self.nproc):
        #     points = np.vstack((points, self._get_gll_point(i)))
        grid_data = {}
        for i, para in enumerate(self.parameters):
            grid_data[para] = griddata(self.points[:, 0:3], self.points[:, i+3],
                (x_inter, y_inter, z_inter), method=method)
        return grid_data

    def _get_gll_point(self, idx):
        """Return the coordinates and model values of every GLL point of a processor.

        :param idx: Index of the processor
        :type idx: int
        :return: One row per GLL point: x, y, z, then one column per parameter
        :rtype: numpy.ndarray
        """
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

