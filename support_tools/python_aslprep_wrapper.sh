#!/bin/bash
# wrapper.sh

# Fail on errors
set -euo pipefail
#setup the shell
export HOME=/home/aslprep
export PATH=/opt/conda/envs/aslprep/bin:/opt/conda/condabin:/opt/conda/envs/aslprep/bin:/opt/workbench/bin_linux64:/opt/afni-latest:/opt/freesurfer/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
source /home/aslprep/.profile     # or the specific setup script your program needs
source /home/aslprep/.bashrc
# export LD_LIBRARY_PATH=/usr/local/cuda/lib64
# echo $PATH
source /etc/profile



# First argument: the python script (must be executable with shebang)
script="$1"
shift   # Remove the first argument, leaving only script args

# Run the script with the remaining arguments
exec "$script" "$@"