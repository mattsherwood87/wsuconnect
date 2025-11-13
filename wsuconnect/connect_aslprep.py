#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
#
# Modified on 10 October 2025 - added image as an input to select various aslprep versions
#
# v1.1.0 on 6 February 2025


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
VERSION = '1.1.0'
DATE = '10 October 2025'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser("This program is the batch wrapper command to perform the preprocessing pipeline using fmriprep. The program searches the specified project's searchSourceTable for acquisition folders (acq-*) which contain DICOM images and runs wsuconnect.support_tools.convert_dicoms for each returned directory.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects))
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
# parser.add_argument('--docker', action="store_true", dest="DOCKER", help="Submit conversion to HTCondor and process in wsuconnect/neuro docker container [default=False]", default=False)
parser.add_argument('-t', '--task-id', action='store', dest='TASKID', help='select a specific task to be processed', default=None)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('--image', action="store", dest="IMAGE", help="docker selected image for aslprep - default pennlinc/aslprep:latest", default="pennlinc/aslprep:latest")
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
        print('connect_aslprep.py version {0}.'.format(VERSION)+" DATED: "+DATE)

    
    st.creds.read(options.PROJECT)

    inputJson = os.path.join(st.creds.dataDir,'code',st.creds.project + '_aslprep_input.json')
    with open(inputJson) as j:
        inputParams = json.load(j)

    now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
    if options.SUBMIT:

        #splitDirs = source_dirsToProcess[0].split('/')
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_aslprep')
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
        participant_folder = os.path.join(derivatives_dir, participant_id)
 
        # Skip the participant if their folder already exists (we should really do some other check, derivative folder may contain other types of data)
        # if os.path.exists(participant_folder):
        #     continue  # Move to the next participant

        filter_file = os.path.join(st.creds.dataDir,'rawdata','bids_filter.json')


        #NEED TO MOVE THESE ARGS TO *_fmriprep_input.json
        if 'nprocs' in inputParams['nums'].keys():
            cpus = inputParams['nums']['nprocs']
        else:
            cpus = 4
        if 'mem-mb' in inputParams['nums'].keys():
            mem = inputParams['nums']['mem-mb']
        else:
            mem = 16384

        #setup initial args
        str_args = ' '.join(["run --rm",
                              "-e TEMPLATEFLOW_HOME=/home/aslprep/.cache/templateflow",
                              "-v /resshare/wsuconnect/data/templateflow:/home/aslprep/.cache/templateflow:ro",
                              f"-m {mem}M",
                              f"--cpus={cpus}",
                              f"-v {inputParams['strings']['fs-license-file']}:{inputParams['strings']['fs-license-file']}:ro",
                              f"-v {os.path.join(st.creds.dataDir,'rawdata')}:{os.path.join(st.creds.dataDir,'rawdata')}:ro",
                              f"-v {os.path.join(st.creds.dataDir,'derivatives')}:{os.path.join(st.creds.dataDir,'derivatives')}:rw",
                              f"-v {inputParams['strings']['w']}:{inputParams['strings']['w']}:rw",
                              options.IMAGE,
                              os.path.join(st.creds.dataDir,'rawdata'),
                              os.path.join(st.creds.dataDir,'derivatives'),
                              "participant",
                              f"-w {inputParams['strings']['w']}",
                              f"--participant-label {row['participant_id'].split('sub-')[-1]}",
                              f"--fs-license-file {inputParams['strings']['fs-license-file']}"
        ])

        #parse input control JSON file for selected project into string arguments
        for k in inputParams.keys():
            if k == 'flags':
                for k2 in inputParams[k]:
                    if inputParams[k][k2]:
                        str_args += f" --{k2}"
            elif k == 'nums':
                for k2 in inputParams[k]:
                    if inputParams[k][k2]:
                        str_args += f" --{k2} {str(inputParams[k][k2])}"
            elif k == 'strings':
                for k2 in inputParams[k]:
                    if inputParams[k][k2]:
                        if len(k2) == 1:
                            str_args += f" -{k2} {inputParams[k][k2]}"
                        elif isinstance(inputParams[k][k2], list):
                            str_args += f" --{k2} {' '.join(inputParams[k][k2])}"
                        else:
                            str_args += f" --{k2} {inputParams[k][k2]}"



        #     '--participant-label', row['participant_id'].split('sub-')[-1],
        #     '--bids-filter-file', filter_file,
        #     '--longitudinal',
        #     '--skull-strip-t1w', 'force',
        #     '--output-spaces', 'MNI152NLin2009cAsym:res-2', 'T1w',
        #     '--nthreads','4',
        #     '--mem-mb','16000',
        #     '--fs-license-file', '/resshare/wsuconnect/.license',
        #     '--no-tty','--skip_bids_validation',
        #     '-w', os.path.join(st.creds.dataDir,'fmriprep_work')
        # ])

        

        if not os.path.isdir(os.path.join(st.creds.dataDir,'aslprep_work')):
            os.makedirs(os.path.join(st.creds.dataDir,'aslprep_work'))


        if not options.SUBMIT or options.test:
            #do it locally
            if options.test:
                print(f"docker {str_args}")
            else:
                os.system(f"docker {str_args}")
        else:
            #output files
            submit = os.path.join(base, f"aslprep_{participant_id}_{now}.submit")
            error = os.path.join(base, f"aslprep_{participant_id}_{now}.error")
            output = os.path.join(base, f"aslprep_{participant_id}_{now}.output")
            log = os.path.join(base, f"aslprep_{participant_id}_{now}.log")
            dagman = Dagman(name=f"{options.PROJECT}_aslprep_{participant_id}", submit=submit)
    
            #THESE ARE ONLY RUNNING WITH 1 CORE ALLOCATE FROM CONDOR, DOCKER IS USING 4 (SAME WITH MB)
            if 'nprocs' in inputParams['nums'].keys():
                cpus = inputParams['nums']['nprocs']
            else:
                cpus = 4
            if 'mem-mb' in inputParams['nums'].keys():
                mem = inputParams['nums']['mem-mb']
            else:
                mem = 16384

            
            #*FIXED - MAYBE MAKE THIS PART OF FMRIPREP_INPUT.JSON
            job_aslprep = st.condor.create_python_condor_job('aslprep_docker',
                                                        'run_docker.sh',
                                                        st.creds.machineNames,
                                                        submit,
                                                        error,
                                                        output,
                                                        log,
                                                        dagman,
                                                        request_cpus=cpus,
                                                        request_memory=mem)
            job_aslprep.add_arg(str_args)
            if options.progress:
                print('Added job for aslprep for participant ' + row['participant_id'].split('sub-')[-1]) 

            # job_clean_workdir = st.condor.create_python_condor_job('clean_fmriprep_work_dir',
            #                                                        'fmriprep_clean_workdir.py',
            #                                                        st.creds.machineNames,
            #                                                        submit,
            #                                                        error,
            #                                                        output,
            #                                                        log,
            #                                                        dagman) 
            
            # job_clean_workdir.add_arg(' '.join(['--data-dir',
            #                                     st.creds.dataDir,
            #                                     '--participant-label',
            #                                     row['participant_id'].split('sub-')[-1],
            #                                     '--work-dir',
            #                                     os.path.join(st.creds.dataDir,'fmriprep_work'),
            #                                     '--condor-output-dir',
            #                                     output]))

            # job_fmriprep.add_child(job_clean_workdir)
            job_mvhtml = st.condor.create_bin_condor_job('move-html',
                                                            'docker',
                                                            st.creds.machineNames,
                                                            submit,
                                                            error,
                                                            output,
                                                            log,
                                                            dagman,
                                                            # docker=True,
                                                            # docker_image='nipreps/fmriprep',
                                                            # docker_mount_if=st.creds.dockerMountIf,
                                                            request_cpus=1,
                                                            request_memory=1000)
                                                            # extra_lines=['docker_extra = "--entrypoint bash"'])
            
            #create docker argument string with initial mount commands
            argStr = f"run --rm -v /resshare:/resshare:ro"
            if st.creds.dockerMountIf == 'resshare19':
                argStr += " -v /resshare19:/resshare19:rw"
            elif st.creds.dockerMountIf == 'resshare20':
                argStr += " -v /resshare20:/resshare20:rw"
            elif st.creds.dockerMountIf == 'resshare21':
                argStr += " -v /resshare21:/resshare21:rw"
            elif st.creds.dockerMountIf == 'resshare22':
                argStr += " -v /resshare22:/resshare22:rw"

            #add remaining docker commands to the argument string
            argStr += f' --user=root --entrypoint bash -m 1g --cpus=1 nipreps/fmriprep {os.path.join(os.path.dirname(REALPATH),"support_tools","python_wrapper.sh")} {os.path.join(os.path.dirname(REALPATH),"support_tools","move_html.py")} '

            argStr += ' '.join(['--data-dir',
                                        st.creds.dataDir,
                                        '--subject',
                                        participant_id,
                                        '--suffix',
                                        'aslprep'])
            
            job_mvhtml.add_arg(argStr)

            job_aslprep.add_child(job_mvhtml)
            dagman.build_submit()

            print('\n\n docker pennlinc/aslprep job submitted to condor. please run condor_q -all to check status')
    

