import subprocess
from .system.slurm import Slurm
from ..pario import readpar
from ..utils import unix
import os
import sys
from .logger import logger

class Mesh():
    def __init__(self, para):
        self.para = para
        self.cluster = para.slurm
        self.title = 'mesh_database'
        self.runner = Slurm(para, self.title)
        self.commanddir = os.path.join(para.path['specfemdir'], 'bin')

    def init(self):
        """
        Initialize path for the meshing job
        """
        logger.mesh.info("Initialize path for the meshing job")
        unix.mkdir(os.path.join(self.para.path['workdir'], 'OUTPUT_FILES'))
        local_path = readpar(os.path.join(self.para.path['datadir'], 'Par_file'), 'LOCAL_PATH')
        unix.mkdir(local_path)

    def submit(self, tasktime='00:05:00'):
        """
        Submit the meshing job to the system
        """
        # job_depend = f"--dependency=afterok:{self.para.jobids[-1]}" if self.para.jobids else ""
        executable = f"{self.para.exec} -n {self.cluster['ntasks']} {self.commanddir}/xmeshfem3D " \
                     f"&& {self.para.exec} -n {self.cluster['ntasks']} {self.commanddir}/xgenerate_databases "
        self.runner.submit(executable, tasktime)