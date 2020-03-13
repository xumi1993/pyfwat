#!/usr/bin/env python
import numpy as np
import subprocess
from io import StringIO
import sys
import glob
    

class VTKFrame():
    def __init__(self, fname, y=0):
        with open(fname) as f:
            lines = f.readlines()
        nodes_num = int(lines[4].split()[1])
        points = np.array([[float(line.split()[0]), float(line.split()[1]), float(line.split()[2])] for i, line in enumerate(lines[5:5+nodes_num])])
        loc = lines.index('LOOKUP_TABLE default\n')+1
        values = np.array([float(line) for line in lines[loc:loc+nodes_num]])
        points = np.hstack((points, values.reshape(-1, 1)))
        print(points.shape)
        self.points = points[np.where(points[:, 1].reshape(-1) == 0)[0], :]
        self.points = np.delete(self.points, 1, axis=1)
        print(self.points.shape)

    def write(self, ofname):
        np.savetxt(ofname, self.points)


class AVSFrame():
    def __init__(self, fname, y=30000):
        p = subprocess.Popen("awk '$3==0&&NF==4{{print $0}}' {}".format(fname), shell=True, stdout=subprocess.PIPE)
        points = np.loadtxt(StringIO(p.stdout.read().decode()))
        values = np.loadtxt(StringIO(subprocess.Popen("awk 'NF==2{{printf \"%d %f\\n\",$1,$2}}' {}".format(fname), 
                                                      shell=True, stdout=subprocess.PIPE).stdout.read().decode()))
        self.xz_values = np.zeros([points.shape[0], 3])
        for i, point in enumerate(points[:, 0]):
            idx = np.where(values[:, 0].reshape(-1) == point)[0]
            self.xz_values[i, 0] = points[i, 1]
            self.xz_values[i, 1] = points[i, 3]
            self.xz_values[i, 2] = values[idx, 1]
    
    def write(self, ofname):
        np.savetxt(ofname, self.xz_values)

def main():
    for fname in glob.glob('OUTPUT_FILES/*it*.vtk'):
        VTKFrame(fname).write(fname+".xyz")

if __name__ == "__main__":
    main()
    # fname = 'OUTPUT_FILES/velocity_Z_it000500.vtk'
    # VTKFrame(fname).write(fname+".xyz")