#!/bin/bash
# wrapper.sh

# Fail on errors
set -euo pipefail
#setup the shell
export MAMBA_EXE=/usr/bin/micromamba
export HOME=/home/fmriprep
export PATH=/opt/conda/envs/fmriprep/bin:/opt/conda/condabin:/opt/conda/envs/fmriprep/bin:/opt/workbench/bin_linux64:/opt/afni-latest:/opt/freesurfer/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /home/fmriprep/.profile     # or the specific setup script your program needs
source /home/fmriprep/.bashrc
# export LD_LIBRARY_PATH=/usr/local/cuda/lib64
# echo $PATH
source /etc/profile
source /opt/conda/etc/profile.d/mamba.sh
micromamba activate fmriprep



# First argument: the python script (must be executable with shebang)
script="$1"
shift   # Remove the first argument, leaving only script args

# Run the script with the remaining arguments
which python
echo "$script" "$@"
exec "$script" "$@"