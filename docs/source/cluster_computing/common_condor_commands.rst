
.. _common_condor_commands:

Common HTCondor Commands
========================

The following :term:`HTCondor` commands can be run from any CoNNECT NPC node. Full documentation for each command is in the
`HTCondor manual <https://htcondor.readthedocs.io/en/latest/>`__.

.. list-table:: Common HTCondor commands.
   :widths: 25 75
   :header-rows: 1

   * - **Command**
     - **Description**
   * - `condor_status <https://htcondor.readthedocs.io/en/latest/man-pages/condor_status.html>`__
     - Shows the status of the cluster: each node's slots (CPUs, memory and GPUs) and whether they are unclaimed or claimed by a job.
   * - `condor_submit <https://htcondor.readthedocs.io/en/latest/man-pages/condor_submit.html>`__
     - Submits jobs described in a submit description file to the job queue.
   * - `condor_q <https://htcondor.readthedocs.io/en/latest/man-pages/condor_q.html>`__
     - Shows the jobs in the queue and their state (idle, running or held). Use ``condor_q -better-analyze <job_id>`` to see
       why a job is not running.
   * - `condor_history <https://htcondor.readthedocs.io/en/latest/man-pages/condor_history.html>`__
     - Shows completed and removed jobs.
   * - `condor_rm <https://htcondor.readthedocs.io/en/latest/man-pages/condor_rm.html>`__
     - Removes one or more jobs from the queue, by job ID or by user name.
