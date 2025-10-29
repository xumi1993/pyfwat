#!/bin/bash

set -e

workdir=$1
cd $workdir
abs_workdir=`pwd`

model=$2
src_set=$3
srcdir=${workdir}/solver/$model/`awk 'NR="'${SLURM_ARRAY_TASK_ID}'"{print $1}' src_rec/sources_{src_set}.dat`
cd $srcdir
mpirun -np ${SLURM_NTASKS} ./xspecfem3D

cd $abs_workdir