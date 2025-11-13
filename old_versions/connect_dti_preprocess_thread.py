#!/usr/bin/env python3
# the command above ^^^ sets python 3.11.11 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 6 July 2023
#
# Modified on

import os
import argparse
from pycondor import Job, Dagman
import datetime
import sys
from glob import glob as glob
from concurrent.futures.thread import ThreadPoolExecutor

#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))
from helper_functions.bids_commands import *
from helper_functions.get_dir_identifiers import *
from helper_functions.read_credentials import *
from helper_functions.mysql_commands import *
from helper_functions.create_fsl_condor_job import *
from helper_functions.create_python_condor_job import *
from helper_functions.dti_preprocess_thread import dti_preprocess

from classes.creds import *


# GLOBAL INFO
#versioning
VERSION = '1.0.1'
DATE = '6 July 2023'
FSLDIR = os.environ["FSLDIR"]

#input argument parser
parser = argparse.ArgumentParser()

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
def parse_arguments():

    #input options for main()
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamed.add_argument('-p','--project', action="store", dest="PROJECT", help="Perform DTI preprocessing for the selected project: " + ' '.join(creds.projects), default=None)

    parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
    parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
    parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
    parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
    options = parser.parse_args()

    #determine the search table and search string
    if not options.PROJECT in creds.projects:
        if not options.version:
            print("ERROR: user must define a project using [-p|--project <project>]\n\n")
            parser.print_help()
        sys.exit()
        
    return options



# ******************* Setup Main Processing ********************
def modality_process(options,*args,**kwargs):
    submit = kwargs.get('submit',None)
    error = kwargs.get('error',None)
    output = kwargs.get('output',None)
    log = kwargs.get('log',None)
    dagman = kwargs.get('dagman',None)

    #load parameter JSON control file
    try:
        dtiInputFile = os.path.join(creds.dataDir,'code',options.PROJECT + '_dti_preprocess_input.json')
        if not os.path.isfile(os.path.join(creds.dataDir,'code',options.PROJECT + '_dti_preprocess_input.json')):
            return

        with open(dtiInputFile) as j:
            dtiInput = json.load(j)

            #asl sql_query inputs
            incExcDict = {}
            if 'inclusion_list' in dtiInput:
                incExcDict['inclusion'] = dtiInput.pop('inclusion_list')
            if 'exclusion_list' in dtiInput:
                incExcDict['exclusion'] = dtiInput.pop('exclusion_list')

    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    regexStr = get_bids_filename(**dtiInput['main_image_params']['input_bids_labels'])

    if not incExcDict:
        filesToProcess = sql_query(database=creds.database,searchtable=creds.searchTable,searchcol='fullpath',regex=regexStr,progress=False)
    else:
        filesToProcess = sql_query(database=creds.database,searchtable=creds.searchTable,searchcol='fullpath',regex=regexStr,**incExcDict,progress=False)


    #synchronize input files for gpu-enabled processing
    if dtiInput['type'] == 'gpu':
        #create input path and synchronize input images
        #procssing codes (ensure latest)
        p=os.path.join('/connect-npc-gpu','general_processing_codes')
        if not os.path.isdir(p):
            os.makedirs(p)
        os.system('rsync -a -e "ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress ' +
                  os.path.join('/resshare','general_processing_codes') + ' msherwood@10.11.0.31:/resshare')
        
        #copy input acquisition files (index/slspec too)
        p=os.path.dirname(dtiInput['eddy_params']['acqp']).replace('resshare','connect-npc-gpu')
        if not os.path.isdir(p):
            os.makedirs(p)
        os.system('rsync -a -e "ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress ' +
                  os.path.dirname(dtiInput['eddy_params']['acqp']) + ' msherwood@10.11.0.31:' + os.path.dirname(os.path.dirname(dtiInput['eddy_params']['acqp'])))
        
        #copy input JSON control file
        p=os.path.dirname(dtiInputFile).replace('resshare','connect-npc-gpu')
        if not os.path.isdir(p):
            os.makedirs(p)
        os.system('rsync -a -e "ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress ' +
                  dtiInputFile + ' msherwood@10.11.0.31:' + os.path.dirname(dtiInputFile))
        


    # loop throught files
    filesToProcess.sort()
    dtiFlag = True
    threadCount = 0
    args = []
    for f in filesToProcess:

        #check for processed output
        subName, sesNum = get_dir_identifiers(os.path.dirname(f))
        outFile = glob(os.path.join(creds.dataDir, 'derivatives', 'sub-' + subName, 'ses-' + sesNum, 'dtifit', 'dwi', '*_FA.nii.gz'))
        if len(outFile) == 1 and not options.OVERWRITE:
            continue

        #run job on condor
        if options.SUBMIT:
            #create condor job
            if dtiFlag:
                if dtiInput['type'] == 'gpu':
                    job_dti = create_python_condor_job('dti_preprocess','dti_preprocess.py',creds.gpuMachineNames,submit,error,output,log,dagman)
                else:
                    job_dti = create_python_condor_job('dti_preprocess','dti_preprocess.py',creds.machineNames,submit,error,output,log,dagman)

                dtiFlag = False

            if dtiInput['type'] == 'gpu':
                #create input path and synchronize input images with gpu system
                p = os.path.dirname(f).replace('resshare','connect-npc-gpu')
                if not os.path.isdir(p):
                    os.makedirs(p)
                os.system('rsync -r -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress ' +
                          os.path.dirname(f) + ' msherwood@10.11.0.31:' + os.path.dirname(os.path.dirname(f)))
                
                #prep output directory on central storage for final transfer
                if not os.path.isdir(os.path.join(creds.dataDir, 'derivatives', 'sub-' + subName, 'ses-' + sesNum)):
                    os.makedirs(os.path.join(creds.dataDir, 'derivatives', 'sub-' + subName, 'ses-' + sesNum))
                


            #create argument string
            argStr = (f + ' ' + 
                    creds.dataDir + ' ' +
                    dtiInputFile)
            if options.OVERWRITE:
                argStr += ' overwrite=True'
            if options.progress:
                argStr += ' progress=True'

            args.append(argStr)

            # #add arguments to condor job
            # job_dti.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
            # print('Added job for dti preprocessing for file:  ' + f)

            # if threadCount == 20:

            #     dagman.build_submit()
            #     threadCount = 0
            #     dtiFlag = True
                
            #     #get some precursors
            #     now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
            #     base = os.path.join(creds.dataDir,'processing_logs','connect_dti_preprocess')
            #     if not os.path.isdir(base):
            #         os.makedirs(base)

            #     #output files
            #     submit = os.path.join(base,'dti_preprocess_' + now + '.submit')
            #     error = os.path.join(base,'dti_preprocess_' + now + '.error')
            #     output = os.path.join(base,'dti_preprocess_' + now + '.output')
            #     log = os.path.join(base,'dti_preprocess_' + now + '.log')
            #     dagman = Dagman(name=options.PROJECT + '-dti_preprocess', submit=submit)
            # else:
            #     threadCount += 1
            
            # if f in filesToProcess[-1]:
            #     return dagman

        else:
            dti_preprocess(f,creds.dataDir,dtiInputFile,overwrite=options.OVERWRITE,progress=options.progress)

    if options.SUBMIT:
        with ThreadPoolExecutor(max_workers=10) as executor:
            ordinal = 1
            for arg in args:
                executor.submit(lambda p: dti_preprocess(*p), arg.split(' '))
                ordinal += 1
        print('All tasks has been finished')



# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """
    #read credentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    options = parse_arguments()
    read_credentials(options.PROJECT)

    #do some prep for parallel processing 
    if options.SUBMIT:
        #get some precursors
        now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        base = os.path.join(creds.dataDir,'derivatives','processing_logs','connect_dti_preprocess')
        if not os.path.isdir(base):
            os.makedirs(base)

        #output files
        submit = os.path.join(base,'dti_preprocess_' + now + '.submit')
        error = os.path.join(base,'dti_preprocess_' + now + '.error')
        output = os.path.join(base,'dti_preprocess_' + now + '.output')
        log = os.path.join(base,'dti_preprocess_' + now + '.log')
        dagman = Dagman(name=options.PROJECT + '-dti_preprocess', submit=submit)


        #perform struc 2 standard registration
        dagman = modality_process(options,submit=submit,error=error,output=output,log=log,dagman=dagman)

    else:
        modality_process(options)

    


    # if options.SUBMIT:
    #     dagman.build_submit()
    

if __name__ == '__main__':
    main()
