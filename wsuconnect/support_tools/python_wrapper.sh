#!/bin/bash
# wrapper.sh

#setup the shell
export HOME=/root
source /root/.profile     # or the specific setup script your program needs
export LD_LIBRARY_PATH=/usr/local/cuda/lib64

# Fail on errors
set -euo pipefail

# First argument: the python script (must be executable with shebang)
script="$1"
shift   # Remove the first argument, leaving only script args

# Run the script with the remaining arguments
exec "$script" "$@"