#!/bin/bash

# Access passed arguments
# echo "Assigned GPU: $_CONDOR_AssignedGPUs"

GPU_UUID=$_CONDOR_AssignedGPUs
echo "Execute node hostname: $(hostname)"
echo "Condor slot: $_CONDOR_SLOT"
echo "Machine name: $CONDOR_HOST"
echo "Condor ProcId: $ProcId"

# Manually map UUIDs to Docker indices
# case "$GPU_UUID" in
#   GPU-43fdd86b) GPU_INDEX=0 ;;
#   GPU-578d2352) GPU_INDEX=1 ;;
#   *) echo "Unknown GPU UUID: $GPU_UUID"; exit 1 ;;
# esac
case "$_CONDOR_SLOT" in
  slot1*) GPU_INDEX=0 ;;
  slot2*) GPU_INDEX=1 ;;
  *) echo "Unknown GPU UUID: $GPU_UUID"; exit 1 ;;
esac

#GPU_INDEX=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | \
#            awk -F', ' -v uuid="$GPU_UUID" '$2 ~ uuid {print $1}')

echo "Assigned GPU UUID: $_CONDOR_SLOT"
echo "Resolved GPU index: $GPU_INDEX"

echo "Running Docker with arguments: --rm $@"

export CUDA_VISIBLE_DEVICES=$_CONDOR_AssignedGPUs

# Run the Docker command with passed arguments
/usr/bin/docker run --rm "$@"

# Ensure the job exits with 0
exit 0
