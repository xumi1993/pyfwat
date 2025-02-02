from ..utils import unix
from .system.slurm import Slurm
import os
from .logger import logger
from pyfwat.workflow import SOLVER_DIR, SRC_REC_DIR, OUTPUT_DIR
import pandas as pd
import sys
from ..pario import chpar, readpar
import glob

class Forward():
    def __init__(self, para, model, simu_type, save_forward=True, **kwargs):
        self.para = para
        self.model = model
        self.runner = Slurm(para, 'forward')
        self.simu_type = simu_type
        self.kwargs = kwargs
        self.save_forward = save_forward
        self.workdir = para.path['workdir']
        self.local_path = readpar(os.path.join(para.path['datadir'], 'Par_file'), 'LOCAL_PATH')
        self.par_file = os.path.join(os.path.abspath(self.para.path['datadir']), 'Par_file')
        self.setup_params()
        self.read_sources()

    def setup_params(self):
        """
        Setup parameters for the forward simulation
        """
        with open(self.par_file) as f:
            content = f.read()
        chpar(content, 'SAVE_FORWARD', self.save_forward)
        if self.simu_type == 'noise':
            chpar(content, 'USE_FORCE_POINT_SOURCE', True)
            chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', False)
            chpar(content, 'NSTEP', self.para.noise['nstep'])
            chpar(content, 'DT', self.para.noise['dt'])
        elif 'tele' in self.simu_type or self.simu_type == 'rf':
            chpar(content, 'USE_FORCE_POINT_SOURCE', False)
            chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', True)
            chpar(content, 'FKMODEL_FILE', 'DATA/FKmodel')
            chpar(content, 'NSTEP', self.para.tele['nstep'])
            chpar(content, 'DT', self.para.tele['dt'])
        with open(self.par_file, 'w') as f:
            f.write(content)

    def read_sources(self):
        """
        Read sources from the source file
        """
        simu_type = 'tele' if 'tele' in self.simu_type or self.simu_type == 'rf' else self.simu_type
        self.source_file = os.path.join(self.workdir, SRC_REC_DIR, f'sources_{getattr(self.para, simu_type)['set_name']}.dat')
        if not os.path.isfile(self.source_file):
            logger.forward.error(f"Source file {self.source_file} does not exist")
            sys.exit(1)
        try:
            self.sources = pd.read_csv(self.source_file, header=None, sep=r'\s+')
        except pd.errors.ParserError as e:
            logger.forward.error(f"Error reading source file {self.source_file}: {e}")
            sys.exit(1)
        if self.sources.shape[1] == 5:
            self.sources.columns = ['evtid', 'lat', 'lon', 'dep', 'buried']
            self.sources['weight'] = 1.0
        elif self.sources.shape[1] == 6:
            self.sources.columns = ['evtid', 'lat', 'lon', 'dep', 'buried', 'weight']
        else:
            logger.forward.error(f"Source file {self.source_file} has wrong format")
            sys.exit(1)
        self.sources = self.sources.astype({'evtid': str, 'lat': float, 'lon': float, 'dep': float, 'buried': float, 'weight': float})

    def init_path(self):
        """
        Initialize path for the forward simulation
        """
        logger.forward.info("Initialize path for the forward simulation")
        model_dir = os.path.join(os.path.abspath(self.workdir), SOLVER_DIR, self.model)
        unix.mkdir(model_dir)
        for src in self.sources.evtid:
            src_dir = os.path.join(model_dir, src)
            unix.mkdir(src_dir)
            unix.mkdir(os.path.join(src_dir, self.local_path))
            unix.rm(os.path.join(src_dir, OUTPUT_DIR))
            unix.cp(OUTPUT_DIR, os.path.join(src_dir, OUTPUT_DIR))
            # copy mesh files
            for suffix in ['Database', 'external_mesh.bin']:
                for mesh_file in glob.glob(os.path.join(self.local_path, f'*{suffix}')):
                    unix.rm(os.path.join(src_dir, self.local_path, os.path.basename(mesh_file)))
                    unix.ln(
                        os.path.abspath(mesh_file),
                        os.path.join(src_dir, self.local_path, os.path.basename(mesh_file))
                    )
            unix.rm(os.path.join(src_dir, 'DATA'))
            unix.mkdir(os.path.join(src_dir, 'DATA'))
            # copy source files
            if self.simu_type == 'noise':
                unix.cp(
                    os.path.join(self.workdir, SRC_REC_DIR, f'FORCESOLUTION_{src}'), 
                    os.path.join(src_dir, 'DATA', 'FORCESOLUTION')
                )
            elif 'tele' in self.simu_type or self.simu_type == 'rf':
                unix.cp(
                    os.path.join(self.workdir, SRC_REC_DIR, f'FKmodel_{src}'),
                    os.path.join(src_dir, 'DATA', 'FKmodel')
                )
                unix.ln(
                    os.path.join(os.path.abspath(self.para.path['datadir']), 'CMTSOLUTION'),
                    os.path.join(src_dir, 'DATA', 'CMTSOLUTION')
                )
            # copy receiver files
            unix.cp(
                os.path.join(self.workdir, SRC_REC_DIR, f'STATIONS_{src}'),
                os.path.join(src_dir, 'DATA', 'STATIONS')
            )
            # link Par_file
            unix.ln(self.par_file, os.path.join(src_dir, 'DATA', 'Par_file'))
            unix.ln(
                os.path.join(os.path.abspath(self.para.path['datadir']), 'meshfem3D_files'),
                os.path.join(src_dir, 'DATA', 'meshfem3D_files')
            )
            # link executables
            unix.rm(os.path.join(src_dir, 'bin'))
            unix.ln(
                os.path.join(os.path.abspath(self.para.path['specfemdir']), 'bin'),
                os.path.join(src_dir, 'bin')
            )
    
    def submit(self, array=False):
        """
        Submit the forward simulation to the system
        """
        logger.forward.info("Submit the forward simulation to the system")
        use_gpu = readpar(self.par_file, 'GPU_MODE')
        abs_model_dir = os.path.abspath(self.workdir)
        if array:
            # array_arg = f"1-{self.sources.shape[0]}%{self.para.slurm['max_array_size']}"
            # mod_dir = f"{os.path.join(os.path.abspath(self.workdir), SOLVER_DIR, self.model)}"
            # cd_cmd = f"cd {mod_dir}/`awk 'NR==\"'$SLURM_ARRAY_TASK_ID'\"' {{print $1}} {self.source_file}`"
            # executable = f"{cd_cmd} && " \
            #              f"{self.para.exec} -n {self.para.slurm['ntasks']} ./bin/xspecfem3D"
            # logger.forward.info(f"Submit forward simulation as array job")
            # self.runner.submit(executable, array=array_arg, use_gpu=use_gpu, tasktime=self.para.slurm['walltime'])
            pass
        else:
            for src in self.sources.evtid:
                src_dir = os.path.join(abs_model_dir, SOLVER_DIR, self.model, src)
                unix.cd(src_dir)
                executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} ./bin/xspecfem3D"
                logger.forward.info(f"Submit forward simulation for source {src}")
                self.runner.submit(executable, use_gpu=use_gpu, tasktime=self.para.slurm['walltime'])
