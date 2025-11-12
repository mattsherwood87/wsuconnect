#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 21 Jan 2021
#
# Modified on 5 Aug 2024 - modified database query - input bids labels are now split and utilized as inidividual inclusion items
# Modified on 23 May 2023 - updated to WSU implementation
# Modified on 9 Nov 2021 - added logs support in struc_flirt and asl_2d_flirt
# Modified on 21 Jan 2021 

import os
import argparse
from pycondor import Job, Dagman
import datetime
import sys
import json
from typing import Tuple


#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '2.0.2'
DATE = '5 Aug 2024'

#WHAT ABOUT DOCKER?
FSLDIR = os.environ["FSLDIR"]
STD1MM = os.path.join(FSLDIR,'data','standard','MNI152_T1_1mm.nii.gz')
STD1MM_BRAIN = os.path.join(FSLDIR,'data','standard','MNI152_T1_1mm_brain.nii.gz')
STD2MM = os.path.join(FSLDIR,'data','standard','MNI152_T1_2mm.nii.gz')
STD2MM_BRAIN = os.path.join(FSLDIR,'data','standard','MNI152_T1_2mm_brain.nii.gz')


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="Perform FLIRT for the selected project: " + ' '.join(st.creds.projects), default=None)

parser.add_argument('--asl', action="store_true", dest="ASL", help="Perform registration between ASL and structural (and standard if structural to standard exists", default=False)
parser.add_argument('--T1', action="store_true", dest="STRUC", help="Perform registration between structural and standard (MNI T1 2mm)", default=False)
parser.add_argument('--apt', action="store_true", dest="APT", help="Perform registration between APT and structural (and standard if structural to standard exists", default=False)

parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('--docker', action="store_true", dest="DOCKER", help="Submit conversion to HTCondor and process in wsuconnect/neuro docker container [default=False]", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)



def modality_process(modality: str,options: dict, flag: bool=False, job: Job=None, submit: str=None, error: str=None, output: str=None, log: str=None, dagman: Dagman=None) -> Tuple[bool, Job, Dagman]:
    """_summary_

    :param modality: _description_
    :type modality: str
    :param options: _description_
    :type options: dict
    :param flirt_flag: _description_, defaults to False
    :type flirt_flag: bool, optional
    :param job: _description_, defaults to None
    :type job: Job, optional
    :param submit: _description_, defaults to None
    :type submit: str, optional
    :param error: _description_, defaults to None
    :type error: str, optional
    :param output: _description_, defaults to None
    :type output: str, optional
    :param log: _description_, defaults to None
    :type log: str, optional
    :param dagman: _description_, defaults to None
    :type dagman: Dagman, optional
    :return: _description_
    :rtype: Tuple[bool, Job, Dagman]
    """    
    

    #load parameter JSON control file
    try:
        flirtInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_' + modality + '_flirt_input.json')
        if not os.path.isfile(os.path.join(st.creds.dataDir,'code',options.PROJECT + '_' + modality + '_flirt_input.json')):
            return

        with open(flirtInputFile) as j:
            flirtInput = json.load(j)

            #asl sql_query inputs
            incExcDict = {}
            if 'inclusion_list' in flirtInput:
                incExcDict['inclusion'] = flirtInput.pop('inclusion_list')
            if 'exclusion_list' in flirtInput:
                incExcDict['exclusion'] = flirtInput.pop('exclusion_list')

            #identifier for bet
            betInputFile = None
            if 'bet' in flirtInput:
                if os.path.isfile(os.path.join(st.creds.dataDir,'code',options.PROJECT + '_' + modality + '_bet_input.json')):
                    betInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_' + modality + '_bet_input.json')

    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    regexStr = st.bids.get_bids_filename(**flirtInput['main_image_params']['input_bids_labels']).split('_')
    incExcDict['inclusion'] += regexStr[2:]

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr[1],progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr[1],**incExcDict,progress=False)

    # loop throught files
    filesToProcess.sort()
    job_flag = True
    for f in filesToProcess:

        #run job on condor
        if options.SUBMIT or options.DOCKER:

            st.subject.get_id(os.path.dirname(f))
            st.subject.check(st.creds.dataDir)

            #create argument string
            if not st.subject.discard:

                #create condor job
                if not job:
                    if options.SUBMIT:
                        job = st.condor.create_python_condor_job(modality + '_flirt',
                                                                'run_docker.sh',
                                                                st.creds.machineNames,
                                                                submit,
                                                                error,
                                                                output,
                                                                log,
                                                                dagman,
                                                                request_cpus=1,
                                                                request_memory=5000)
                    else:
                        job = st.condor.create_python_condor_job(modality + '_flirt',
                                                                'flirt.py',
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
                
                
                # create argument string for flirt.pys
                # argStr = ' '.join(["run --rm",
                #                     f"-m 5000M",
                #                     "--user 0:0",
                #                     f"--cpus=1",
                #                     f"-v /resshare:/resshare:ro",
                #                     f"-v {os.path.join(st.creds.dataDir,'code')}:{os.path.join(st.creds.dataDir,'code')}:rw",
                #                     f"-v {os.path.join(st.creds.dataDir,'rawdata')}:{os.path.join(st.creds.dataDir,'rawdata')}:ro",
                #                     f"-v {os.path.join(st.creds.dataDir,'derivatives')}:{os.path.join(st.creds.dataDir,'derivatives')}:rw",
                #                     "wsuconnect/neuro",
                #                     "/resshare/wsuconnect/support_tools/flirt.py "
                #                 ])
                argStr = (f + ' ' + 
                        st.creds.dataDir + ' ' +
                        flirtInputFile)
                if options.OVERWRITE:
                    argStr += ' --overwrite'
                if options.progress:
                    argStr += ' --progress'
                if betInputFile:
                    argStr += ' --bet-params ' + betInputFile
                    

                #add arguments to condor job
                job.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
                print('Added job for ' + modality + ' registration for ' + f)
            else:
                print(f'Did not add job for {f} - subject discarded')

            flag = True
            # count += 1
            
            if f in filesToProcess[-1]:
                return flag, job, dagman

        else:
            st.flirt.flirt(f,st.creds.dataDir,flirtInputFile,overwrite=options.OVERWRITE,bet_params_file=betInputFile,progress=options.progress)



# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    #read credentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    options = parser.parse_args()
    st.creds.read(options.PROJECT)
    st.import_flirt()
    flirt_flag_struc = False
    flirt_flag_asl = False
    flirt_flag_apt = False
    job_flirt_struc = None
    job_flirt_asl = None
    job_flirt_apt = None

    #do some prep for parallel processing 
    if options.SUBMIT or options.DOCKER:
        #get some precursors
        now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_flirt')
        if not os.path.isdir(base):
            os.makedirs(base)

        #output files
        submit = os.path.join(base,'flirt_' + now + '.submit')
        error = os.path.join(base,'flirt_' + now + '.error')
        output = os.path.join(base,'flirt_' + now + '.output')
        log = os.path.join(base,'flirt_' + now + '.log')
        dagman = Dagman(name=options.PROJECT + '-flirt', submit=submit)


        #perform struc 2 standard registration
        if options.STRUC:
            flirt_flag_struc,job_flirt_struc,dagman = modality_process('struc',options,flag=flirt_flag_struc,job=job_flirt_struc,submit=submit,error=error,output=output,log=log,dagman=dagman)
        if options.ASL:
            flirt_flag_asl,job_flirt_asl,dagman = modality_process('asl',options,flag=flirt_flag_asl,job=job_flirt_asl,submit=submit,error=error,output=output,log=log,dagman=dagman)
        if options.APT:
            flirt_flag_apt,job_flirt_apt,dagman = modality_process('apt',options,flag=flirt_flag_apt,job=job_flirt_apt,submit=submit,error=error,output=output,log=log,dagman=dagman)
    else:

        if options.STRUC:
            modality_process('struc',options)
        if options.ASL:
            modality_process('asl',options)
        if options.APT:
            modality_process('apt',options)

    


    if ( options.SUBMIT or options.DOCKER ) and dagman:
        if flirt_flag_struc and flirt_flag_asl:
            job_flirt_struc.add_child(job_flirt_asl)
        if flirt_flag_struc and flirt_flag_apt:
            job_flirt_struc.add_child(job_flirt_apt)

        if flirt_flag_struc or flirt_flag_asl or flirt_flag_apt:
            dagman.build_submit()
