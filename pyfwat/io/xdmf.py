import h5py
from os.path import dirname, basename, join

class XDMFIO:
    def __init__(self, filename):
        self.filename = filename
        self.basename = basename(filename)
        self.path = dirname(filename)
        self.fname = join(self.path, '_'.join(basename(filename).split('.')[:-1])+'.xmf')
        self.model = {}
        with h5py.File(filename, 'r') as f:
            self.keys = list(f.keys())
            self.keys = [key for key in self.keys if key not in ['x', 'y', 'z']]
            for key in self.keys:
                self.model[key] = f[key][:]
            self.x = f['x'][:]
            self.y = f['y'][:]
            self.z = f['z'][:]
        self.dims = (len(self.x), len(self.y), len(self.z))
        self.dx = self.x[1] - self.x[0]
        self.dy = self.y[1] - self.y[0]
        self.dz = self.z[1] - self.z[0]
        self.ox = self.x[0]
        self.oy = self.y[0]
        self.oz = self.z[0]

    def create_xdmf(self):
        self.xmf = f'''<?xml version="1.0" ?>
<Xdmf Version="3.0" xmlns:xi="http://www.w3.org/2001/XInclude">
  <Domain>
    <Grid Name="Model" GridType="Uniform">
      <Topology TopologyType="3DRectMesh" Dimensions="{self.dims[0]} {self.dims[1]} {self.dims[2]}"/>
      <Geometry GeometryType="VxVyVz">
        <DataItem Name="X" Dimensions="{self.dims[0]}" NumberType="Float" Precision="8" Format="HDF">
          {self.basename}:/x
        </DataItem>
        <DataItem Name="Y" Dimensions="{self.dims[1]}" NumberType="Float" Precision="8" Format="HDF">
          {self.basename}:/y
        </DataItem>
        <DataItem Name="Z" Dimensions="{self.dims[2]}" NumberType="Float" Precision="8" Format="HDF">
          {self.basename}:/z
        </DataItem>
      </Geometry>
'''
        for name in self.keys:
            self.xmf += f'''      <Attribute Name="{name}" AttributeType="Scalar" Center="Node">
        <DataItem Dimensions="{self.dims[0]} {self.dims[1]} {self.dims[2]}" NumberType="Float" Precision="8" Format="HDF">
          {self.basename}:/{name}
        </DataItem>
      </Attribute>
'''
        self.xmf += '''    </Grid>
  </Domain>
</Xdmf>
'''

    def write(self):
        with open(f'{self.fname}', 'w') as f:
            f.write(self.xmf)


def create_xmf():
    import argparse

    parser = argparse.ArgumentParser(description='Create XDMF file for HDF5')
    parser.add_argument('filename', type=str, help='Path to HDF5 file')
    args = parser.parse_args()
    xio = XDMFIO(args.filename)
    xio.create_xdmf()
    xio.write()