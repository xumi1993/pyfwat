#!/bin/bash
#SBATCH --nodes=5  
#SBATCH --ntasks=168
#SBATCH --time=00:16:00
#SBATCH --job-name S.beta
#SBATCH --output=SM_M24_%j.txt





# script runs mesher,database generation and solver
# using this example setup
#
###################################################
#module load intel/15.0.2 openmpi/intel/1.6.4
module load intel openmpi
#=====
#cd $PBS_O_WORKDIR
cd $SLURM_SUBMIT_DIR
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/intel/lib/intel64:/usr/local/openmpi/lib
#=====


# number of processes
NPROC=168

prog=~/progs/SEM_tools/model_addpert/sem_model_addpert

mod=M27
newmod=`echo $mod |awk -FM '{printf"M%d\n",$2+1}'`
#model_dir=../../output/model_${mod}
model_dir=optimize/SD_$mod/OUTPUT_MODEL_slen0.03

topo_dir=specfem3d/OUTPUT_FILES/DATABASES_MPI

mpirun -np $NPROC $prog gaus01.dat $topo_dir $model_dir vs 0.05 15000 
