import os
from ...utils import unix
from ...utils.utils import Dict

class Slurm():
    def __init__(self, para, title):
        self.title = title
        self.ntasks = para.slurm['ntasks']
        self.walltime = para.slurm['walltime']
        self.slurm_args = para.slurm['args']
        self.ngpus = para.slurm['ngpus']
        self.para = para
        self.get_path()

    def get_path(self):
        self.path = Dict({
            "output_log": f"{self.para.path['workdir']}/logs/output_{self.title}.log",
            "error_log": f"{self.para.path['workdir']}/logs/error_{self.title}.log"
        })
    
    def submit_header(self, tasktime=None):
        """
        The submit call defines the SBATCH header which is used to submit a
        workflow task list to the system. It is usually dictated by the
        system's job scheduler. This is the header for BSCC.
        """
        tasktime = tasktime or self.walltime
        _call = " ".join([
            f"sbatch",
            f"--job-name={self.title}",
            f"--output={self.path.output_log}",
            f"--error={self.path.error_log}",
            f"--ntasks=1",
            f"--partition={self.para.slurm.partition_cpu}",
            f"--time={tasktime}",
            f"--parsable",
        ])
        return _call

    def submit_array_header(self, array=None, use_gpu=False, tasktime=None):
        """
        The submit call defines the SBATCH header which is used to submit a
        workflow task list to the system. It is usually dictated by the
        system's job scheduler. This is the header for BSCC.
        """
        partition = self.para.slurm.partition_gpu if use_gpu else self.para.slurm.partition_cpu
        gpu_arg = f"--gpus=:{self.ngpus:d}" if use_gpu else ""
        tasktime = tasktime or self.walltime
        _call = " ".join([
            f"sbatch",
            f"--job-name={self.title}",
            f"--ntasks={self.ntasks:d}",
            f"{gpu_arg}",
            f"--output={self.path.output_log}_%A",
            f"--error={self.path.error_log}_%A",
            f"--partition={partition}",
            f"--time={tasktime}",
            f"--array={array}",
            f"--parsable",
        ])
        return _call