

Containerized Processing
========================

Overview
--------

`Docker <https://www.docker.com/>`__ is the official container support for the CoNNECT NPC.
Docker containers are used throughout the CoNNECT pipeline to ensure reproducibility,
environmental consistency, and portability across computing environments. Each job runs
inside a containerized environment that mirrors the expected dependencies and file
structure of the CoNNECT workflow.

Cluster Integration
-------------------

Docker images are executed through a batch submission system **HTCondor**.
Each node in the cluster is configured with Docker, allowing containerized 
workloads to be dispatched transparently from the scheduler.

Images
------

The CoNNECT NPC hosts its own image wsuconnect/neuro. This is a Ubuntu 24.04 image 
loaded with the software described below. We also host an additiona MATLAB image 
wsuconnect/matlab that allows GUI access through noVNC. Additional images include 
pennlinc/aslprep, nipreps/fmriprep, and bids/validator.

Workflow Summary
----------------

1. **Job Submission**
   - Jobs are submitted using `condor_submit` or `qsub`, depending on the site scheduler.
   - Jobs can also be submitted from python via pycondor.
   - Wrappers for various python submission commands defined in custom *support tools*,
     such as :mod:`wsuconnect.support_tools.condor`.

2. **Container Launch**
   - Each task launches a container from a predefined image (e.g., ``wsuconnect/neuro``).
   - Volumes are mounted to map input data directories:
     ::
         docker run --rm -v /mydata:/data wsuconnect/neuro

3. **Parallel Execution**
   - The scheduler distributes multiple Dockerized jobs across available compute nodes.
   - Each node pulls the image from the local Docker cache.

4. **File Access**
   - Shared network storage (e.g., NFS) ensures that containers access consistent 
   datasets regardless of node location.

5. **Cleanup and Logging**
   - Container logs and exit codes are collected per job by Condor.