from ..utils import unix
from .system.slurm import Slurm
import os
from .logger import logger
from pyfwat.workflow import SOLVER_DIR, SRC_REC_DIR, OUTPUT_DIR
import pandas as pd
import sys
from ..pario import chpar, readpar
import glob
from ..para import FWATPara

class Forward():
    def __init__(self, para:FWATPara, model:str, simu_type:str, save_forward=True, **kwargs):
        self.para = para
        self.model = model
        self.runner = Slurm(para, 'forward')
        self.simu_type = simu_type
        self.kwargs = kwargs
        self.save_forward = save_forward
        self.workdir = para.path['workdir']
        self.local_path = readpar(os.path.join(para.path['datadir'], 'Par_file'), 'LOCAL_PATH')
        self.par_file = os.path.join(os.path.abspath(self.para.path['datadir']), 'Par_file')
        self.read_sources()
        self.setup_params()

    def setup_params(self):
        """
        Setup parameters for the forward simulation
        """
        with open(self.par_file) as f:
            content = f.read()
        content = chpar(content, 'SAVE_FORWARD', self.save_forward)
        if self.simu_type == 'noise':
            content = chpar(content, 'USE_FORCE_POINT_SOURCE', True)
            content = chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', False)
            content = chpar(content, 'NSTEP', self.para.noise['nstep'])
            content = chpar(content, 'DT', self.para.noise['dt'])
        elif 'tele' in self.simu_type or self.simu_type == 'rf':
            if self.para.tele['wavefield_discontinuity']:
                content = chpar(content, 'USE_FORCE_POINT_SOURCE', True)
                content = chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', False)
                content = chpar(content, 'STACEY_ABSORBING_CONDITIONS', False)
                content = chpar(content, 'PML_CONDITIONS', True)
                content = chpar(content, 'IS_WAVEFIELD_DISCONTINUITY', True)
            else:
                content = chpar(content, 'USE_FORCE_POINT_SOURCE', False)
                content = chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', True)
                content = chpar(content, 'STACEY_ABSORBING_CONDITIONS', True)
                content = chpar(content, 'PML_CONDITIONS', False)
                content = chpar(content, 'IS_WAVEFIELD_DISCONTINUITY', False)
                content = chpar(content, 'FKMODEL_FILE', 'DATA/FKmodel')
            content = chpar(content, 'NSTEP', self.para.tele['nstep'])
            content = chpar(content, 'DT', self.para.tele['dt'])
        with open(self.par_file, 'w') as f:
            f.write(content)

    def read_sources(self):
        """
        Read sources from the source file
        """
        simu_type = 'tele' if 'tele' in self.simu_type or self.simu_type == 'rf' else self.simu_type
        self.source_file = os.path.join(self.para.abs_workdir, SRC_REC_DIR, f'sources_{getattr(self.para, simu_type)['set_name']}.dat')
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
        model_dir = os.path.join(self.para.abs_workdir, SOLVER_DIR, self.model)
        unix.mkdir(model_dir)
        for src in self.sources.evtid:
            src_dir = os.path.join(model_dir, src)
            unix.mkdir(src_dir)
            unix.mkdir(os.path.join(src_dir, self.local_path))
            unix.rm(os.path.join(src_dir, OUTPUT_DIR))
            unix.cp(OUTPUT_DIR, os.path.join(src_dir, OUTPUT_DIR))
            # copy mesh files
            databases = ['Database', 'external_mesh.bin']
            if ('tele' in self.simu_type or self.simu_type == 'rf') and self.para.tele['wavefield_discontinuity']:
                databases.append('wavefield_discontinuity_database.bin')
            for suffix in databases:
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
                if self.para.tele['wavefield_discontinuity']:
                    # for suffix in ['wavefield_discontinuity', 'wavefield_discontinuity_database']:
                    for wd_file in glob.glob(os.path.join(
                            self.para.abs_workdir, self.local_path, f'wavefield_boundary_{src}', f'proc??????_wavefield_discontinuity.bin'
                        )):
                        unix.rm(os.path.join(src_dir, self.local_path, os.path.basename(wd_file)))
                        unix.ln(
                            os.path.abspath(wd_file),
                            os.path.join(src_dir, self.local_path, os.path.basename(wd_file))
                        )
                    unix.touch(os.path.join(src_dir, 'DATA', 'FORCESOLUTION'))
                else:
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
            unix.cp(self.par_file, os.path.join(src_dir, 'DATA', 'Par_file'))
            if 'tele' in self.simu_type or self.simu_type == 'rf':
                with open(os.path.join(src_dir, 'DATA', 'Par_file')) as f:
                    content = f.read()
                content = chpar(content, 'INJECTION_TECHNIQUE_TYPE', 2)
                content = chpar(content, 'TRACTION_PATH', os.path.join(self.local_path, f"wavefield_boundary_{src}"))
                with open(os.path.join(src_dir, 'DATA', 'Par_file'), 'w') as f:
                    f.write(content)
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

        logger.forward.info("Starting forward simulation to the system")
        use_gpu = readpar(self.par_file, 'GPU_MODE')
        # prepare wavefield discontinuity for teleseismic simulation
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
                src_dir = os.path.join(self.para.abs_workdir, SOLVER_DIR, self.model, src)
                unix.cd(src_dir)
                executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} ./bin/xspecfem3D"
                logger.forward.info(f"Submit forward simulation for source {src}")
                self.runner.submit(executable, use_gpu=use_gpu, tasktime=self.para.slurm['walltime'])
        unix.cd(self.para.abs_workdir)
    
    def submit_fk_injection_field(self):
        """
        Submit job to compute the FK injection field
        """
        unix.cd(self.para.abs_workdir)
        fkexec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'compute_fk_injection_field')
        for src in self.sources.evtid:
            executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} " \
                         f"{fkexec} {self.local_path} " \
                         f"{os.path.join(self.para.abs_workdir, SRC_REC_DIR, f'FKmodel_{src}')}"
            self.runner.submit(executable, use_gpu=False, tasktime='00:10:00')
            wb_dir = os.path.join(self.local_path, f"wavefield_boundary_{src}")
            unix.mkdir(wb_dir)
            unix.mv(glob.glob(f"{self.local_path}/proc??????_sol_axisem"), wb_dir)

    def submit_wavefield_discontinuity(self):
        """
        Check if wavefield_discontinuity is available
        """
        fkmod = 'fk_model'
        unix.cd(self.para.abs_workdir)
        for src in self.sources.evtid:
            unix.rm(fkmod)
            wb_dir = os.path.join(self.para.abs_workdir, self.local_path, f"wavefield_boundary_{src}")
            if os.path.isdir(wb_dir):
                num_wb = len(glob.glob(os.path.join(wb_dir, 'proc??????_wavefield_discontinuity.bin')))
                if num_wb == self.para.slurm['ntasks']:
                    continue
            logger.forward.info(f"Copmute wavefield_discontinuity for source {src}")
            unix.mkdir(wb_dir)
            unix.ln(
                os.path.join(self.para.abs_workdir, SRC_REC_DIR, f"FKmodel_{src}"),
                os.path.join(self.para.abs_workdir, fkmod)
            )

            # change par for wavefield discontinuity
            with open(fkmod) as f:
                content = f.read()
            content = chpar(content, 'NSTEP', self.para.tele['nstep'], 'fk')
            content = chpar(content, 'DELTAT', self.para.tele['dt'], 'fk')
            with open(fkmod, 'w') as f:
                f.write(content)

            # submit job to compute wavefield discontinuity
            executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} " \
                         f"{os.path.dirname(os.path.dirname(__file__))}/compute_fk_injection_field {self.local_path}"
            self.runner.submit(executable, use_gpu=False, tasktime='00:10:00')
            unix.mv(glob.glob(f"{self.local_path}/proc??????_wavefield_discontinuity.bin"), wb_dir)
