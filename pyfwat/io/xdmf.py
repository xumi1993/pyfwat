import h5py
from os.path import dirname, basename

class XDMFIO:
    def __init__(self, filename):
        self.filename = filename
        self.path = dirname(filename)
        self.fname = '_'.join(basename(filename).split('.')[:-1])+'.xmf'
        self.model = {}
        with h5py.File(filename, 'r') as f:
            self.keys = list(f.keys())
            self.keys = [key for key in self.keys if key not in ['x', 'y', 'z']]
            for key in self.keys:
                self.model[key] = f[key][:]
            self.x = f['x'][:]
            self.y = f['y'][:]
            self.z = f['z'][:]
        self.dx = self.x[1] - self.x[0]
        self.dy = self.y[1] - self.y[0]
        self.dz = self.z[1] - self.z[0]
        self.ox = self.x[0]
        self.oy = self.y[0]
        self.oz = self.z[0]

    def create_xdmf(self):
        self.xdmf_content = f"""<?xml version="1.0" ?>
<Xdmf Version="3.0">
  <Domain>
    <Grid Name="Structured Grid" GridType="Uniform">
      
      <Topology TopologyType="3DCORECTMesh" Dimensions="{self.z.size} {self.y.size} {self.x.size}"/>
      
      <Geometry GeometryType="ORIGIN_DXDYDZ">
        <DataItem Dimensions="3" NumberType="Float" Format="XML">
          {self.ox} {self.oy} {self.oz}
        </DataItem>
        <DataItem Dimensions="3" NumberType="Float" Format="XML">
          {self.dx} {self.dy} {self.dz}
        </DataItem>
      </Geometry>

"""
        for key in self.keys:
            self.xdmf_content += f"""
        <Attribute Name="{key}" AttributeType="Scalar" Center="Cell">
          <DataItem Dimensions="{self.z.size} {self.y.size} {self.x.size}" NumberType="Float" Precision="4" Format="HDF">
            {basename(self.filename)}:/{key}
          </DataItem>
        </Attribute>

"""
        self.xdmf_content += """
    </Grid>
  </Domain>
</Xdmf>
"""

    def write(self):
        with open(f'./{self.fname}', 'w') as f:
            f.write(self.xdmf_content)


def create_xmf():
    import argparse

    parser = argparse.ArgumentParser(description='Create XDMF file for HDF5')
    parser.add_argument('filename', type=str, help='Path to HDF5 file')
    args = parser.parse_args()
    xio = XDMFIO(args.filename)
    xio.create_xdmf()
    xio.write()