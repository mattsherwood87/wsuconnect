#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 Jan 2025
#
# Modified on 

import os
import sys
import datetime
import argparse

#local import
REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
# sys.path.append(REALPATH)
REALPATH = os.path.join('/resshare','wsuconnect')
sys.path.append(REALPATH)

import support_tools as st

FSLDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]


VERSION = '3.1.0'
DATE = '15 Nov 2024'


parser = argparse.ArgumentParser('flirt.py: perform FLIRT registration between input and reference/standard brain images')

parser.add_argument('-d','--data-dir', action='store', dest='DATA_DIR', help='fullpath to the project data directory (st.creds.dataDir)')
parser.add_argument('-p','--participant-label', action='store', dest='PARTICIPANT_LABEL', help="unique subject ID (sub-XXX)")
parser.add_argument('-w','--work-dir', action='store', dest='WORK_DIR', help="fullpath to fmriprep working directory", required=True)
parser.add_argument('-c','--condor-output-dir', action='store', dest='CONDOR_OUTPUT_DIR', help="fullpath to fmriprep working directory", required=True)


def fmriprep_clean_workdir(data_dir: str, participant_label: str, work_dir: str, condor_output_dir: str):
    """_summary_

    Args:
        data_dir (str): _description_
        participant_label (str): _description_
        work_dir (str): _description_
        condor_out_dir (str): _description_
    """
    import toml
    import os
    import glob
    import re

    #return subject label
    print(f'sub-{participant_label}')

    #find all fmriprep.toml files
    for f in glob.glob(os.path.join(data_dir,'derivatives','sub-' + participant_label, 'log','**','fmriprep.toml'),recursive=True):

        #read toml and extract the run uuid -> this will specify the working directory
        t_log = toml.load(f)
        run_uuid = t_log['execution']['run_uuid']

        #determine if the fMRIPrep job was successful (and ensure we are looking at the right condor output file)
        b_success = False
        b_participantLabel = False
        b_runuuid = False
        for f2 in glob.glob(os.path.join(condor_output_dir,'*.output')):

            with open(f2, 'r') as file:
                for line in file:
                    if re.search('fMRIPrep finished successfully!', line):
                        # print(line)
                        b_success = True
                    if re.search(f'--participant-label {participant_label}', line):
                        # print(line)
                        b_participantLabel = True
                    if re.search(f'Run identifier: {run_uuid}', line):
                        b_runuuid = True

        #remove directory if fMRIPrep was successful
        if b_success and b_participantLabel and b_runuuid:
            if os.path.isdir(os.path.join(work_dir,run_uuid)):
                print(f'\tfMRIPrep was successfully, removing working directory \n\t{os.path.join(work_dir,run_uuid)}')
                os.system(f'rm -rf {os.path.join(work_dir,run_uuid)}')
            else:
                print(f'\tWorking directory not found... \n\t{os.path.join(work_dir,run_uuid)}')


            #remove other wf dirs
            #if os.path.isdir(os.path.join(work_dir,"fmriprep_24_1_wf","fsdir_run_" + run_uuid.replace("-","_"))):
            #    print(f'\t{os.path.join(work_dir,"fmriprep_24_1_wf","fsdir_run_" + run_uuid.replace("-","_"))}')
            #    os.system(f'rm -rf {os.path.join(work_dir,"fmriprep_24_1_wf","fsdir_run_" + run_uuid.replace("-","_"))}')
            #else:
            #    print(f'\tcannot find {os.path.join(work_dir,"fmriprep_24_1_wf","fsdir_run_" + run_uuid.replace("-","_"))}')
            
            # if os.path.isdir(os.path.join(work_dir,"sub-" + participant_label + "_wf")):
            #     print(f'\t{os.path.join(work_dir,"sub-" + participant_label + "_wf")}')
            #     os.system(f'rm -rf {os.path.join(work_dir,"sub-" + participant_label + "_wf")}')
            # else:
            #     print(f'\tcannot find {os.path.join(work_dir,"sub-" + participant_label + "_wf")}')
                            



    

if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """
    options = parser.parse_args()
    fmriprep_clean_workdir(data_dir=options.DATA_DIR, participant_label=options.PARTICIPANT_LABEL, work_dir=options.WORK_DIR, condor_output_dir=options.CONDOR_OUTPUT_DIR)

