

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

Docker images are executed through the :term:`HTCondor` batch submission system.
Each node in the cluster is configured with Docker, allowing containerized 
workloads to be dispatched transparently from the scheduler.

Images
------

The CoNNECT NPC hosts its own set of Docker images. The main image is 
wsuconnect/neuro. This is an Ubuntu 24.04 image loaded with the open-source software 
described below and GUI access via noVNC. A GPU variant, wsuconnect/neuro-gpu, provides support
for NVIDIA CUDA. We also host an additional MATLAB image 
wsuconnect/matlab:r2024b that allows GUI access through noVNC. Our own RStudio image 
wsuconnect/rstudio enables access to R and RStudio (via RStudio Server) and is built from the 
rocker/rstudio base image. Additional images also available include pennlinc/aslprep, 
nipreps/fmriprep, and bids/validator.

Docker containers can be manually started using the commands below.

Helpful Docker Commands
------------------------

.. code-block:: shell-session

    $ docker run -it --rm wsuconnect/neuro

    Run the wsuconnect/neuro container with a bash entrypoint.


.. code-block:: shell-session

    $ docker run -it --rm -v /path/to/local/drive:/container/path:rw wsuconnect/neuro 

    Bind mount a local path into the wsuconnect/neuro container with a bash entrypoint. Mount 
    options are read-only (ro) and read-write (rw).


.. code-block:: shell-session

    $ docker run -it --rm -p 6080:6080 wsuconnect/neuro -vnc

    Add access to container GUI through port 6080. Once running, point a browser to 
    http://localhost:6080/vnc.html and use the password matlab.


.. code-block:: shell-session

    $ docker run -it --rm -p 6080:6080 -v /resshare/wsuconnect/wsuconnect/licenses:/licenses:rw wsuconnect/matlab:r2024b -vnc

    For MATLAB, pass the GUI port (6080) and the license path. Once running, point a browser to 
    http://localhost:6080/vnc.html and use the password matlab.


.. code-block:: shell-session

    $ docker run -it --rm -p 127.0.0.1:8787:8787 wsuconnect/rstudio

    For RStudio, publish the RStudio Server HTTP port 8787. Once running,
    point a browser to http://127.0.0.1:8787 to access RStudio. This prompts for a login as the
    user rstudio.


.. code-block:: shell-session

    $ docker run -it --rm -e PASSWORD=password -p 127.0.0.1:8787:8787 wsuconnect/rstudio

    Set the password of the rstudio user for the container.


.. code-block:: shell-session

    $ docker run -it --rm -e DISABLE_AUTH=true -p 127.0.0.1:8787:8787 wsuconnect/rstudio

    Set environment variable DISABLE_AUTH to bypass the RStudio login.


.. code-block:: shell-session

    $ docker run -it --rm -e GROUPID=1000 -p 127.0.0.1:8787:8787 wsuconnect/rstudio

    Set environment variable GROUPID to change the group ID of the rstudio user. This is 
    necessary when mounting drives with specific group privileges.

.. seealso:: 
   Additional helpful RStudio Docker commands can be found at the links below:
   https://rocker-project.org/images/versioned/rstudio.html
   and 
   https://davetang.org/muse/2021/04/24/running-rstudio-server-with-docker/



Workflow Summary
----------------

1. **Job Submission**
   - Jobs are submitted to :term:`HTCondor` using ``condor_submit`` or ``condor_qsub``.
   - Jobs can also be submitted from Python via PyCondor.
   - Wrappers for Python job submission are defined in the custom *support tools*,
     such as :mod:`wsuconnect.support_tools.condor`.

2. **Container Launch (optional)**
   - Jobs can run in a Docker container (docker universe) or directly on the node, such as a Python or bash script (vanilla universe).
   - Each task launches a container from a predefined image (e.g., ``wsuconnect/neuro``).
   - Volumes are mounted to map input data directories:

    .. code-block:: shell-session

        $ docker run --rm -v /mydata:/data wsuconnect/neuro

3. **Parallel Execution**
   - The scheduler distributes multiple jobs across available compute nodes.
   - Each node pulls the image from the local Docker cache.

4. **File Access**
   - Shared network storage (e.g., NFS) ensures that containers access consistent 
     datasets regardless of node location.

5. **Cleanup and Logging**
   - Container logs and exit codes are collected per job by HTCondor.