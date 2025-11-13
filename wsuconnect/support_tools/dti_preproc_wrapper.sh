#!/bin/bash
# wrapper.sh
export HOME=/root
source /root/.profile     # or the specific setup script your program needs
export LD_LIBRARY_PATH=/usr/local/cuda/lib64
# echo $@
exec /resshare/wsuconnect/support_tools/dti_preprocess_wf.py "$@"