#!/bin/bash

# Access passed arguments
echo "Running Docker with arguments: $@"

# Run the Docker command with passed arguments
/usr/bin/docker "$@"

# Ensure the job exits with 0
exit 0
