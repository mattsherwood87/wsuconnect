#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 21 Jan 2021
#
# Modified on 2 September 2025 - revised for docker implementation
# Modified on 23 May 2023 - updated to WSU implementation
# Modified on 9 Nov 2021 - added logs support in struc_flirt and asl_2d_flirt
# Modified on 21 Jan 2021 

import os
from numpy.core.numeric import convolve
import argparse
from pycondor import Job, Dagman
import datetime
import sys
import json
from glob import glob


#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '2.1.0'
DATE = '2 September 2025'

# ******************* PARSE COMMAND LINE ARGUMENTS ********************

#input argument parser
parser = argparse.ArgumentParser()

#input options for main()
parser.add_argument('-p','--project', required=True,action="store", dest="PROJECT", help="Perform FLIRT for the selected project: " + ' '.join(st.creds.projects), default=None)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel processing via Docker container", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)




# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    #read credentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    options = parser.parse_args()
    st.creds.read(options.PROJECT)

    #load parameter JSON control file
    try:
        flirtInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_dti_flirt_input.json')
        if not os.path.isfile(flirtInputFile):
            print(f"ERROR: cannot find project's dti_flirt input control JSON file: {flirtInputFile}")
            sys.exit()

        with open(flirtInputFile) as j:
            flirtInput = json.load(j)

            #asl sql_query inputs
            incExcDict = {}
            if 'inclusion_list' in flirtInput:
                incExcDict['inclusion'] = flirtInput.pop('inclusion_list')
            if 'exclusion_list' in flirtInput:
                incExcDict['exclusion'] = flirtInput.pop('exclusion_list')


    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    regexStr = st.bids.get_bids_filename(**flirtInput['main_image_params']['input_bids_labels'])

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,**incExcDict,progress=False)

    # loop throught files
    filesToProcess.sort()
    flirt_flag = False
    for f in filesToProcess:

        #get subject ID and session number, check for output
        
        st.subject.get_id(os.path.dirname(f))
        st.subject.check(st.creds.dataDir)

        #SKIP IF
        #subjects is specified and doesn't match this subject ID
        if options.SUBJECTS:
            if not f"sub-{st.subject.id}" in options.SUBJECTS:
                continue

        #subject is discarded
        if st.subject.discard:
            continue

        #output files exist
        if glob(os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'dwi','*.mat')) and not options.OVERWRITE:
            if options.progress:
                print('WARNING: Output files found in ' + os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'dwi'))
                print('\toverwrite not specified, skipping')
            continue

        #run job on condor
        if options.SUBMIT:

            #output files
            #get some precursors
            now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
            base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_dti_flirt')
            if not os.path.isdir(base):
                os.makedirs(base)

            submit = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.submit")
            error = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.error")
            output = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.output")
            log = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.log")
            dagman = Dagman(name=f"{options.PROJECT}_dti_flirt_sub-{st.subject.id}_ses-{st.subject.sesNum}", submit=submit)

            #create condor job
            job = st.condor.create_python_condor_job('dti_flirt',
                                                    'dti_flirt.py',
                                                    st.creds.machineNames,
                                                    submit,
                                                    error,
                                                    output,
                                                    log,
                                                    dagman,
                                                    docker=True,
                                                    docker_image='wsuconnect/neuro',
                                                    docker_mount_if=st.creds.dockerMountIf,
                                                    request_cpus=1,
                                                    request_memory='5g')

            #create argument string
            argStr = (f + ' ' + 
                    st.creds.dataDir + ' ' +
                    flirtInputFile)
            if options.OVERWRITE:
                argStr += ' --overwrite'
            if options.progress:
                argStr += ' --progress'

            #add arguments to condor job
            job.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
            print('\tAdded job for dti registration for ' + f)

            #submit job            
            dagman.build_submit()
            

        else:
            st.dti_flirt(f,st.creds.dataDir,flirtInputFile,overwrite=options.OVERWRITE,progress=options.progress)

    

    

