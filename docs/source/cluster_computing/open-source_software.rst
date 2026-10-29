

Open-Source Software
====================

Picture Archiving and Communication System (PACS)
-------------------------------------------------

`Orthanc <https://www.orthanc-server.com/>`__ is the official open-source PACS in place at the WSU CoNNECT. Using this system, which runs on the 
:doc:`master node of the CoNNECT NPC </cluster_computing/index>`, DICOM images can be sent directly from the MRI scanner to the CoNNECT NPC centralized storage.
The PACS Grabber Service then automatically detects new DICOM images arriving at the PACS storage location, moves them to the appropriate project/subject/session's sourcedata
directory, converts them to NIfTI images and stores them in the project/subject/session's rawdata directory according to the BIDS specification.

.. _orthanc_server:

.. figure:: ../_images/orthanc2.png
   :align: center
   :width: 33%
      
   PACS data transfer from MRI to centralized storage via CoNNECT NPC.


Image Viewing and Analysis Software
-----------------------------------


AFNI
^^^^

AFNI is an NIH-developed suite to visualize and analyze functional MRI data.

The afni package (installed from http://neuro.debian.net/pkgs/afni.html) is located at /usr/share/afni.

AFNI is commonly utilized to overlay fMRI statistics from FSL FEAT or other output on top of T1-weighted images. Through the AFNI surface mapper (SUMA), FreeSurfer inflated surfaces 
can be used as the background image for the statistics, which can be viewed in 3D, as well as many other views. With certain datasets, this can provide powerful visuals.

.. code-block:: shell-session

    $ afni


dcm2niix
^^^^^^^^

dcm2niix is a conversion software package developed at Chris Rorden’s Neuropsychology Lab at the University of South Carolina and is distributed by the NeuroImaging Tools and Resources Collaboratory (NITRC).

A copy of dcm2niix has been compiled and placed in the scratch ‘bash’ folder, /mnt/ss_rhb1/scratch/bash. This path has been added to the system path so it can be run from any directory without the need to know the location. A copy is also in the ubuntu user download folder.

The function dcm2niix converts raw DICOM images to NIfTI (or other) formats. The function should be executed with the flags specified in Table 4.

.. code-block:: shell-session

    $ dcm2niix


FreeSurfer
^^^^^^^^^^

FreeSurfer is developed by Massachusetts General Hospital/Harvard University to analyze MRI images of the brain. The current 
version is 7.1.1; however, version 6 is installed.

The FreeSurfer package is located at /usr/share/freesurfer. This path is stored in the FREESURFER_DIR variable available 
in bash and C shell terminals. 

common functions: 

``recon-all`` is the main FreeSurfer command to begin the cortical reconstruction process. The entire process takes 12-24hrs to complete. Preferred command 
line arguments are provided in Table 3. 

.. note:: CREATE TABLE

.. code-block:: shell-session

    $ recon-all 


``freeview`` is the volume and surface viewer used to assess quality of cortical reconstruction.

.. code-block:: shell-session

    $ freeview


FMRIB Software Library (FSL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The FMRIB Software Library (FSL) is a library of fMRI, MRI and DTI analysis tools developed by Oxford University, UK. The current installed version is 6.0.4. 

The FSL package is located at /usr/share/fsl/6.0. This path is stored in the FSL_DIR variable available in bash and C shell terminals.

**Common Functions**

.. code-block:: shell-session

    $ fsl

Main GUI for FSL. This GUI can be used to create individual and higher-level designs for fMRI analyses, execute individual or higher-level designs of fMRI analyses, 
run brain extraction, process DTI, perform registration, perform ICA for resting-state fMRI, or generate simulated MRI scans. 

.. seealso:: 
    Details can be found `here <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSL>`__. 

.. code-block:: shell-session

    $ fsleyes 

MRI visualization GUI. 

.. seealso::
    The user guide can be found `here <https://users.fmrib.ox.ac.uk/~paulmc/fsleyes/userdoc/latest/>`__.

.. code-block:: shell-session

    $ feat

Command line tool to execute fMRI design files. 

.. seealso::
    More info can be found `here <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT>`__. 

.. code-block:: shell-session

    $ randomise

Randomise (and randomise_parallel) is a non-parametric permutation inference tool for neuroimaging data. Randomise utilizes 
modelling and inferences using standard designs as used in FEAT. The main pitfall of randomise is the accommodation of correlated 
datasets (repeated measures). However, some cases of repeated measures can be accommodated. 

.. code-block:: shell-session

    $ oxford_asl

oxford_asl is a command line utility that quantifies cerebral blood flow (CBF) from arterial spin labeling (ASL) data, including 
motion-correction, registration, partial volume correction, and distortion correction. 

.. seealso::
    Command line user guide for `oxford_asl <https://asl-docs.readthedocs.io/en/latest/oxford_asl_userguide.html>`__ or  `BASIL <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/BASIL>`__,
    the GUI-based version of oxford_asl.


LCModel
^^^^^^^

.. note:: To be developed
