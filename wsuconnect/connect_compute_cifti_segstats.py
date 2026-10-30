#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
#
# Modified on 7 November 2025 - added image as an input to select various aslprep versions
#


import os
import argparse
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
from pathlib import Path


#local import
# REALPATH = os.path.realpath(__file__)

REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-1]).resolve()
if not any(Path(p).resolve() == str(REALPATH) for p in sys.path if Path(p).exists()):
    sys.path.append(str(REALPATH))

# sys.path.append(os.path.dirname(REALPATH))
import wsuconnect.support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '7 November 2025'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser(description="Compute segmentation statistics for CIFTI images, as defined in the project's cifti_segstats_input.json.")
parser.add_argument('--type', action="store", dest="TYPE", help="type (must be in project's cifti_segstats_input.json), ex. func", required=True)
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="select a project: " + ' '.join(st.creds.projects))
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force processing by skipping directory and database checking", default=False)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
parser.add_argument('-t', '--task-id', action='store', dest='TASKID', help='select a specific task to be processed', default=None)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit jobs to HTCondor for parallel processing", default=False)
parser.add_argument('--image', action="store", dest="IMAGE", help="Docker image to use, default pennlinc/aslprep:latest", default="pennlinc/aslprep:latest")
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

    from bids.layout.writing import build_path
    from glob import glob
    from pycondor import Dagman
    import datetime
    import pandas as pd
    import json

    #get and evaluate options
    options = parser.parse_args()
    
    if options.version or options.progress:
        print('connect_zmap_cifti.py version {0}.'.format(VERSION)+" DATED: "+DATE)

    
    st.creds.read(options.PROJECT)
    segstatsInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_cifti_segstats_input.json')
    if not os.path.isfile(segstatsInputFile):
        print(f"ERROR: cannot find project's cifti_segstats_input.json file")
        sys.exit()

    with open(segstatsInputFile) as j:
        segstatsInput = json.load(j)

    if not options.TYPE in segstatsInput.keys():
        print(f"ERROR: cannot find {options.TYPE} in cifti_segstats_input.json")
        sys.exit()


    now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
    if options.SUBMIT:

        #splitDirs = source_dirsToProcess[0].split('/')
        base = Path(st.creds.dataDir) / 'code' /'processing_logs' / 'connect_segstats_cifti'
        # base = base.replace(creds.s3_prefix + '/','')
        base.mkdir(exist_ok=True)


    if not options.SUBJECTS:
        inputTsv = Path(st.creds.dataDir) / 'rawdata' / 'participants.tsv'
        with open(inputTsv) as f:
            df_participants = pd.read_csv(f,delimiter='\t')


        if 'discard' in df_participants.columns:
            df_participants = df_participants[~df_participants['discard']]
    else:
        df_participants = pd.DataFrame(options.SUBJECTS, columns=['participant_id'])
    
    # derivatives_dir = Path(st.creds.dataDir) / 'derivatives'
    
    
    for index, row in df_participants.iterrows():
        
        participant_id = row['participant_id']
        # participant_folder = derivatives_dir / participant_id


        derPath = Path(st.creds.dataDir) / 'derivatives' / participant_id / 'ses-*' / segstatsInput[options.TYPE]['type'] / segstatsInput[options.TYPE]['regex']
        cifti_files = glob(str(derPath))
        # cifti_files = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,regex="zstat.dtseries.nii",searchcol="fullpath",returncol="fullpath",progress=False,inclusion=[participant_id,'nii.gz','space-fsLR'],exclusion=['work'])
 
        # Skip the participant if their folder already exists (we should really do some other check, derivative folder may contain other types of data)
        # if os.path.exists(participant_folder):
        #     continue  # Move to the next participant


        #NEED TO MOVE THESE ARGS TO *_fmriprep_input.json
        cpus = 1
        mem = 4000


        for cifti_file in cifti_files:   
            print(cifti_file)         
            submit = base / f"segstats_cifti_{participant_id}_{now}.submit"
            error = base / f"segstats_cifti_{participant_id}_{now}.error"
            output = base / f"segstats_cifti_{participant_id}_{now}.output"
            log = base / f"segstats_cifti_{participant_id}_{now}.log"
            dagman = Dagman(name=f"{options.PROJECT}_segs-cifti_{participant_id}", submit=submit)



            # job_fmriprep.add_child(job_clean_workdir)
            job_do_cifti = st.condor.create_bin_condor_job('segstats-cifti',
                                                            'docker',
                                                            st.creds.machineNames,
                                                            str(submit),
                                                            str(error),
                                                            str(output),
                                                            str(log),
                                                            dagman,
                                                            # docker=True,
                                                            # docker_image='nipreps/fmriprep',
                                                            # docker_mount_if=st.creds.dockerMountIf,
                                                            request_cpus=cpus,
                                                            request_memory=mem)
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
            argStr += f' --user=root --entrypoint /bin/bash -m 4g --cpus=1 {options.IMAGE} {REALPATH / "support_tools" / "python_aslprep_wrapper.sh"} {REALPATH / "support_tools" / "compute_cifti_segstats.py"} '

            argStr += ' '.join(['--in-file',cifti_file,
                                '--data-dir',st.creds.dataDir,
                                '--label-file',segstatsInput[options.TYPE]['label_file'],
                                '--datatype',segstatsInput[options.TYPE]['type']])
            if 'threshold' in segstatsInput[options.TYPE].keys():
                argStr += f" --threshold {segstatsInput[options.TYPE]['threshold']}"
            if 'exclude_outliers' in segstatsInput[options.TYPE].keys():
                argStr += f" --exclude-outliers {segstatsInput[options.TYPE]['exclude_outliers']}"
                                #'--subject-id',participant_id.split('-')[-1]])
            
            job_do_cifti.add_arg(argStr)

            if options.progress:
                print('Added job for aslprep for participant ' + row['participant_id'].split('sub-')[-1]) 
            dagman.build_submit()

            print('\n\n docker pennlinc/aslprep job submitted to condor. please run condor_q -all to check status')
    

