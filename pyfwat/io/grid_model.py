import numpy as np

class GridModel():
    def __init__(self, fname:str) -> None:
        npdata = np.load(fname)
        self.model = npdata[npdata.__dict__['files'][-1]]
        self.x = npdata['x']
        self.y = npdata['y']
        self.z = npdata['z']
        self.dx = np.mean(np.diff(self.x))
        self.dy = np.mean(np.diff(self.y))
        self.dz = np.mean(np.diff(self.z))

    def trim(self, sup_m):
        nsup = int(sup_m/self.dx)
        self.x = self.x[nsup:self.x.size-nsup]
        nsup = int(sup_m/self.dy)
        self.y = self.y[nsup:self.y.size-nsup]
        self.model= self.model[nsup:-nsup, nsup:-nsup, :]    
