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
from .src_rec import SrcRec

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
        self.sr = SrcRec.read(para, simu_type)
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
                # content = chpar(content, 'USE_FORCE_POINT_SOURCE', True)
                # content = chpar(content, 'COUPLE_WITH_INJECTION_TECHNIQUE', False)
                # content = chpar(content, 'STACEY_ABSORBING_CONDITIONS', False)
                # content = chpar(content, 'PML_CONDITIONS', True)
                # content = chpar(content, 'IS_WAVEFIELD_DISCONTINUITY', True)
                logger.forward.warn("Do NOT support wavefield discontinuity mode")
            # else:
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

    def init_path(self):
        """
        Initialize path for the forward simulation
        """
        logger.forward.info("Initialize path for the forward simulation")
        model_dir = os.path.join(self.para.abs_workdir, SOLVER_DIR, self.model)
        unix.mkdir(model_dir)
        for _, src in self.sr.sources.iterrows():
            src_dir = os.path.join(model_dir, src.evtid)
            unix.mkdir(src_dir)
            unix.mkdir(os.path.join(src_dir, self.local_path))
            unix.rm(os.path.join(src_dir, OUTPUT_DIR))
            unix.cp(OUTPUT_DIR, os.path.join(src_dir, OUTPUT_DIR))
            # copy mesh files
            databases = ['Database', 'external_mesh.bin']
            for suffix in databases:
                for mesh_file in glob.glob(os.path.join(self.local_path, f'*{suffix}')):
                    unix.rm(os.path.join(src_dir, self.local_path, os.path.basename(mesh_file)))
                    unix.ln(
                        os.path.abspath(mesh_file),
                        os.path.join(src_dir, self.local_path, os.path.basename(mesh_file))
                    )
            unix.rm(os.path.join(src_dir, 'DATA'))
            unix.mkdir(os.path.join(src_dir, 'DATA'))
            # write receiver files
            src['receivers'].to_csv(
                os.path.join(src_dir, 'DATA', 'STATIONS'),
                columns=['station', 'network', 'lon', 'lat', 'elev', 'buried'],
                header=False, sep=' ', index=False
            )
            # copy Par_file
            unix.cp(self.par_file, os.path.join(src_dir, 'DATA', 'Par_file'))
            # copy source files
            
            if self.simu_type == 'noise':
                unix.ln(
                    src.solution_path,
                    os.path.join(src_dir, 'DATA', 'FORCESOLUTION')
                )
            elif 'tele' in self.simu_type or self.simu_type == 'rf':
                unix.ln(
                    src.fkmodel_path,
                    os.path.join(src_dir, 'DATA', 'FKmodel')
                )
                unix.ln(
                    src.solution_path,
                    os.path.join(src_dir, 'DATA', 'CMTSOLUTION')
                )
                # change Par_file for teleseismic simulation
                with open(os.path.join(src_dir, 'DATA', 'Par_file')) as f:
                    content = f.read()
                content = chpar(content, 'INJECTION_TECHNIQUE_TYPE', 2)
                wb_dir = os.path.join(self.para.abs_workdir, self.local_path, f"wavefield_boundary_{src.evtid}")
                unix.ln(wb_dir, os.path.join(src_dir, self.local_path, f"wavefield_boundary_{src.evtid}"))
                content = chpar(content, 'TRACTION_PATH', 
                                os.path.join(self.local_path, f"wavefield_boundary_{src.evtid}"))
                with open(os.path.join(src_dir, 'DATA', 'Par_file'), 'w') as f:
                    f.write(content)
            unix.ln(
                os.path.join(self.para.abs_workdir, 'DATA', 'meshfem3D_files'),
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
            for _, src in self.sr.sources.iterrows():
                src_dir = os.path.join(self.para.abs_workdir, SOLVER_DIR, self.model, src.evtid)
                unix.cd(src_dir)
                executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} ./bin/xspecfem3D"
                logger.forward.info(f"Submit forward simulation for source {src.evtid}")
                self.runner.submit(executable, use_gpu=use_gpu, tasktime=self.para.slurm['walltime'])
        unix.cd(self.para.abs_workdir)
    
    def submit_fk_injection_field(self):
        """
        Submit job to compute the FK injection field
        """
        unix.cd(self.para.abs_workdir)
        fkexec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'compute_fk_injection_field')
        for _, src in self.sr.sources.iterrows():
            executable = f"{self.para.exec} -n {self.para.slurm['ntasks']} " \
                         f"{fkexec} {self.local_path} " \
                         f"{src.fkmodel_path}"
                        #  f"{os.path.join(self.para.abs_workdir, SRC_REC_DIR, f'FKmodel_{src}')}"
            self.runner.submit(executable, use_gpu=False, tasktime='00:10:00')
            wb_dir = os.path.join(self.local_path, f"wavefield_boundary_{src.evtid}")
            unix.mkdir(wb_dir)
            unix.mv(glob.glob(f"{self.local_path}/proc??????_sol_axisem"), wb_dir)

    def submit_wavefield_discontinuity(self):
        """
        Check if wavefield_discontinuity is available
        """
        fkmod = 'fk_model'
        unix.cd(self.para.abs_workdir)
        for src in self.sr.sources.evtid:
            unix.rm(fkmod)
            wb_dir = os.path.join(self.para.abs_workdir, self.local_path, f"wavefield_boundary_{src.evtid}")
            if os.path.isdir(wb_dir):
                num_wb = len(glob.glob(os.path.join(wb_dir, 'proc??????_wavefield_discontinuity.bin')))
                if num_wb == self.para.slurm['ntasks']:
                    continue
            logger.forward.info(f"Copmute wavefield_discontinuity for source {src.evtid}")
            unix.mkdir(wb_dir)
            unix.ln(
                src.fkmodel_path,
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
