import subprocess
from .system.slurm import Slurm
from ..pario import readpar
from ..utils import unix
import os
import sys
from ..pario import chpar
from .logger import logger
from ..para import FWATPara

class Mesh():
    def __init__(self, para: FWATPara):
        self.para = para
        self.cluster = para.slurm
        self.title = 'mesh_database'
        self.runner = Slurm(para, self.title)
        self.commanddir = os.path.join(para.path['specfemdir'], 'bin')
        self.par_file = os.path.join(para.path['datadir'], 'Par_file')
        self.setup_params()

    def init(self):
        """
        Initialize path for the meshing job
        """
        logger.mesh.info("Initialize path for the meshing job")
        unix.mkdir(os.path.join(self.para.abs_workdir, 'OUTPUT_FILES'))
        local_path = readpar(self.par_file, 'LOCAL_PATH')
        unix.mkdir(local_path)
        is_force_solution = readpar(self.par_file, 'USE_FORCE_POINT_SOURCE')
        if is_force_solution:
            unix.touch(
                os.path.exists(os.path.join(self.para.abs_workdir, 'DATA', 'FORCESOLUTION'))
            )
        else:
            unix.touch(
                os.path.exists(os.path.join(self.para.abs_workdir, 'DATA', 'CMTSOLUTION'))
            )

    def setup_params(self):
        """
        Setup parameters for the forward simulation
        """
        with open(self.par_file) as f:
            content = f.read()
        if self.para.tele['wavefield_discontinuity']:
            content = chpar(content, 'PML_CONDITIONS', True)
            content = chpar(content, 'STACEY_ABSORBING_CONDITIONS', False)
            content = chpar(content, 'IS_WAVEFIELD_DISCONTINUITY', True)
            content = chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', False)
        else:
            content = chpar(content, 'IS_WAVEFIELD_DISCONTINUITY', False)
        with open(self.par_file, 'w') as f:
            f.write(content)
    
    def submit(self, tasktime='00:05:00'):
        """
        Submit the meshing job to the system
        """
        unix.cd(self.para.abs_workdir)
        logger.mesh.info("Submit the meshing job to the system")
        executable = f"{self.para.exec} -n {self.cluster['ntasks']} {self.commanddir}/xmeshfem3D "
        self.runner.submit(executable, array=None, use_gpu=False, tasktime=tasktime)
        logger.mesh.info("Submit the database generation job to the system")
        executable = f"{self.para.exec} -n {self.cluster['ntasks']} {self.commanddir}/xgenerate_databases "
        self.runner.submit(executable, array=None, use_gpu=False, tasktime=tasktime)

        
