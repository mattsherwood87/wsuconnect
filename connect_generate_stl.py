#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
#
#
# v1.2.0 on 6 February 2025


import os
import argparse
from pycondor import Dagman
import datetime
import sys
import json
import pandas as pd
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 


#local import
REALPATH = os.path.realpath(__file__)

sys.path.append(os.path.dirname(REALPATH))
import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '19 Feb 2025'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser("This program is the batch wrapper command to perform the preprocessing pipeline using fmriprep. The program searches the specified project's searchSourceTable for acquisition folders (acq-*) which contain DICOM images and runs wsuconnect.support_tools.convert_dicoms for each returned directory.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects))
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
# parser.add_argument('--docker', action="store_true", dest="DOCKER", help="Submit conversion to HTCondor and process in wsuconnect/neuro docker container [default=False]", default=False)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
parser.add_argument('--test', action="store_true", dest="test", help="only print command lines to execute, do not run", default=False)


# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    # #read crendentials from $SCRATCH_DIR/instance_ids.json
    # ls_updatedFiles = []
    # ls_existingFiles = []

    #get and evaluate options
    options = parser.parse_args()
    
    if options.version or options.progress:
        print('connect_generate_stl.py version {0}.'.format(VERSION)+" DATED: "+DATE)

    
    st.creds.read(options.PROJECT)

    now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
    if options.SUBMIT:

        #splitDirs = source_dirsToProcess[0].split('/')
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_generate_stl')
        # base = base.replace(creds.s3_prefix + '/','')
        if not os.path.isdir(base):
            os.makedirs(base)


    # # finds all subject directories to analyze
    # raw_dirsToProcess = st.mysql.sql_query_dirs(regex='sub-',source=False,inclusion=['rawdata'])
    # new_d =[]
    # for d in raw_dirsToProcess:
    #     a = d.removeprefix(st.creds.dataDir).split(os.path.sep)
    #     new_d.append(os.path.join(st.creds.dataDir,a[1],a[2]))

    # raw_dirsToProcess = list(set(new_d))

    if not options.SUBJECTS:
        inputTsv = os.path.join(st.creds.dataDir,'rawdata','participants.tsv')
        with open(inputTsv) as f:
            df_participants = pd.read_csv(f,delimiter='\t')


        if 'discard' in df_participants.columns:
            df_participants = df_participants[~df_participants['discard']]
    else:
        df_participants = pd.DataFrame(options.SUBJECTS, columns=['participant_id'])
    
    derivatives_dir = os.path.join(st.creds.dataDir, 'derivatives')
    
    
    for index, row in df_participants.iterrows():
        
        participant_id = row['participant_id']
        participant_folder = os.path.join(derivatives_dir, 'sourcedata','freesurfer',participant_id)
 
        # Skip the participant if their folder already exists (we should really do some other check, derivative folder may contain other types of data)
        if os.path.isfile(os.path.join(participant_folder,'surf','brain_mesh.stl')) and not options.OVERWRITE:
            continue  # Move to the next participant


        submit = os.path.join(base, f"generate_stl_sub-{participant_id}_{now}.submit")
        error = os.path.join(base, f"generate_stl_sub-{participant_id}_{now}.error")
        output = os.path.join(base, f"generate_stl_sub-{participant_id}_{now}.output")
        log = os.path.join(base, f"generate_stl_sub-{participant_id}_{now}.log")
        dagman = Dagman(name=f"{options.PROJECT}_generate_stl_{participant_id}", submit=submit)


        #NEED TO MOVE THESE ARGS TO *_fmriprep_input.json
        cpus = 1
        mem = '4g'

        #setup initial args
        
        job_generate_stl = st.condor.create_python_condor_job('generate_stl',
                                                    'generate_stl.py',
                                                    st.creds.machineNames,
                                                    submit,
                                                    error,
                                                    output,
                                                    log,
                                                    dagman,
                                                    docker=True,
                                                    docker_image='wsuconnect/neuro:docker',
                                                    docker_mount_if=st.creds.dockerMountIf,
                                                    request_cpus=cpus,
                                                    request_memory=mem,
                                                    extra_lines=[f'environment = "SUBJECTS_DIR={os.path.dirname(participant_folder)}"'])

        #parse input control JSON file for selected project into string arguments
        argStr = participant_folder
        if options.progress:
            argStr += ' --progress'

        job_generate_stl.add_arg(argStr)


        print(f'\tAdded job to generate brain mesh stl for participant: {participant_id}' )
        dagman.build_submit()
    

