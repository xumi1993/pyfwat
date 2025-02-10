import os
from ...utils import unix
from ...utils.utils import Dict, walltime2sec
from ..logger import logger
import subprocess
import time
import sys

class Slurm():
    def __init__(self, para, title):
        self.title = title
        self.para = para
        self.ntasks = para.slurm['ntasks']
        self.walltime = para.slurm['walltime']
        self.slurm_args = para.slurm['args']
        self.ngpus = para.slurm['ngpus']
        self.log_path = os.path.join(self.para.abs_workdir, 'logs')
        self._completed_states = ["COMPLETED"]
        self._failed_states = ["TIMEOUT", "FAILED", "NODE_FAIL", 
                               "OUT_OF_MEMORY", "CANCELLED"]
        self._pending_states = ["PENDING", "RUNNING"]

    def get_optional_args(self, use_gpu=False, tasktime=None, log_fname=None):
        self.partition = self.para.slurm.partition_gpu if use_gpu else self.para.slurm.partition_cpu
        tasktime = tasktime or self.walltime
        self.time_arg = f"--time={tasktime}" if tasktime is None else ""
        self.gpu_arg = f"--gpus={self.ngpus:d}" if use_gpu else ""
        self.log_arg = f"--output={self.log_path}/{log_fname}.log" if log_fname is None else f"--output={log_fname}"
    
    def submit_header(self, use_gpu=False, tasktime=None, log_fname=None):
        """
        The submit call defines the SBATCH header which is used to submit a
        workflow task list to the system. It is usually dictated by the
        system's job scheduler. This is the header for BSCC.
        """
        self.get_optional_args(use_gpu, tasktime, log_fname)
        _call = " ".join([
            f"sbatch",
            f"--job-name={self.title}",
            f"--ntasks={self.ntasks:d}",
            f"{self.gpu_arg}",
            f"{self.log_arg}",
            f"--partition={self.partition}",
            f"{self.time_arg}",
            f"--parsable",
        ])
        return _call

    def submit_array_header(self, array=None, use_gpu=False, tasktime=None):
        """
        The submit call defines the SBATCH header which is used to submit a
        workflow task list to the system. It is usually dictated by the
        system's job scheduler. This is the header for BSCC.
        """
        self.get_optional_args(use_gpu, tasktime)
        _call = " ".join([
            f"sbatch",
            f"--job-name={self.title}",
            f"--ntasks={self.ntasks:d}",
            f"{self.gpu_arg}",
            f"--output={self.log_path}/{self.title}_%A.%a.log",
            f"--partition={self.partition}",
            f"{self.time_arg}",
            f"--array={array}",
            f"--parsable",
        ])
        return _call
    
    def submit(self, executable, array=None, use_gpu=False, tasktime=None):
        """
        Submit a job to the system
        """
        if array is not None:
            _call = self.submit_array_header(array, use_gpu, tasktime)
        else:
            _call = self.submit_header(use_gpu, tasktime)
        _call = f"{_call} {executable}"
        logger.monitor.info(f"{_call}")
        try:
            stdout = subprocess.run(_call, shell=True, check=True, text=True, stdout=subprocess.PIPE)
            jobid = stdout.stdout.strip()
            logger.monitor.info(f"job submitted with jobid: {jobid}")
        except subprocess.CalledProcessError as e:
            logger.monitor.error(f"Error submitting job: {e}")
            sys.exit(1)
        
        status = self.monitor_job_status(jobid)
        if status == -1:
            logger.monitor.error(f"job failed with jobid: {jobid}")
            sys.exit(1)
        elif status == 1:
            logger.monitor.info(f"job completed with jobid: {jobid}")
            time.sleep(3)

    def monitor_job_status(self, jobid, timeout=300, time_interval=6):
        """
        Monitor the status of the job
        """
        logger.monitor.info(f"monitoring job status for job: {jobid}")
        time_waited = 0
        bad_jobs = []
        while True:
            time.sleep(time_interval)
            job_ids, states = [], []
            _job_ids, _states = self.query_job_states(jobid)
            job_ids += _job_ids            
            states += _states
            
            # Condition to deal with `query_job_states` not returning correctly
            if not job_ids or not states:
                # Only increment wait counter if job query unsuccessful 
                time_waited += time_interval

                # After some timeout time, exit main job, likely error
                if time_waited >= timeout:
                    logger.monitor.critical(
                        f"Cannot access job information for job {self.para.jobids}. "
                        f"`System.query_job_states()` waited {timeout}s. "
                        f"Please check function, job scheduler and logs, or "
                        f"increase timeout constant in `timeout_s` in function "
                        f"`System.Cluster.monitor_job_status`",
                        header="system run timeout", border="="
                    )
                    sys.exit(-1)
                continue

            # COMPLETE: All jobs completed nominally, proceed
            if all([state in self._completed_states for state in states]):
                logger.monitor.debug(f"all array jobs returned a complete state")
                return 1  # Pass
            # FAILED: All jobs are finished, but not all 'completed'
            elif all([state not in self._pending_states for state in states]):
                # List out any failed jobs not already listed in FAILING state
                for jid, state in zip(job_ids, states):
                    if state in self._failed_states and jid not in bad_jobs:
                        logger.monitor.critical(f"{jid}: {state}")
                logger.monitor.critical("some array jobs have returned a non-complete "
                                "state")
                return -1
            # FAILING: Jobs still running but >1 non-complete. Keep monitoring
            elif any([check in states for check in self._failed_states]):
                for jid, state in zip(job_ids, states):
                    if state in self._failed_states and jid not in bad_jobs:
                        # Let User know failing jobs as they arise, only once
                        logger.critical(f"{jid}: {state}")
                        bad_jobs.append(jid)
                continue    
            # PENDING: Jobs running, mixture of pending and complete states
            else:
                continue

    def query_job_states(self, job_id, sort=False):
        """
        Overwrites `system.cluster.Cluster.query_job_states`

        Queries completion status of an array job by running the SLURM `sacct`

        .. note::
            The actual command line call wil look something like this
            $ sacct -nLX -o jobid,state -j 441630
            441630_0    PENDING
            441630_1    COMPLETED

        .. note::
            SACCT flag options are described as follows:
            -L: queries all available clusters, not just the cluster that ran 
                the `sacct` call. Used for federated clusters
            -X: supress the .batch and .extern jobnames that are normally 
                returned but don't represent that actual running job

        :type job_id: str
        :param job_id: main job id to query, returned from the subprocess.run 
            that ran the jobs
        :type sort: bool
        :param sort: sort by job ids or job array ids. Defaults to False because
            currently running jobs may return job numbers that cannot be sorted
            e.g., 1_0, 1_1, 1_[2-5]. We only use sort when recovering from job 
            failure because then we are assured that all jobs have run.
        :rtype: (list, list)
        :return: (job ids, corresponding job states). Returns (None, None) if
            `sacct` does not return a useful stdout (e.g., jobs have not
            yet initialized on system)
        """
        job_ids, job_states = [], []
        cmd = f"sacct -nLX -o jobid,state -j {job_id}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        stdout = result.stdout

        # If no return, return None so calling function knows something is wrong
        if not stdout:
            return None, None

        # Return the job numbers and respective states for the given job ID
        for job_line in str(stdout).strip().split("\n"):
            if not job_line:
                continue
            job_id, job_state = job_line.split()
            job_ids.append(job_id)
            job_states.append(job_state)
    
        if sort:
            # Sort by job ids because we assume that logically job numbers are 
            # in a numerically ascending order i.e., 1,2,3 
            job_ids, job_states = zip(*sorted(zip(job_ids, job_states)))

            # Sort array jobs because normal 'sorted' function doesn't work when
            # strings are hyphenated (e.g., 1_0, 1_1, 1_2)
            # https://stackoverflow.com/questions/20862968/\
            #            numbers-with-hyphens-or-strings-of-numbers-with-hyphens
            job_ids, job_states = zip(
                *sorted(zip(job_ids, job_states), 
                        key=lambda x: [int(y) for y in x[0].split('_')])
                        )

        return job_ids, job_states