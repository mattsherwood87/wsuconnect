#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 27 July 2023
#
# Modified on 7 Feb 2024 - added condor job support

import os
# import pymysql
import argparse
import sys
import pandas as pd
import numpy as np
from glob import glob as glob
import datetime
from pycondor import Dagman
import json
import re


#local import
REALPATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(REALPATH)

import support_tools as st



# GLOBAL INFO
#versioning
VERSION = '3.0.0'
DATE = '15 July 2024'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()

parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects), default=None)
parser.add_argument('--cbf', action="store_true", dest="cbf", help="Compute segstats for CBF")
parser.add_argument('--apt', action="store_true", dest="apt", help="Compute segstats for APT")
parser.add_argument('--dti', action="store_true", dest="dti", help="Compute segstats for DTI")
parser.add_argument('--t1w', action="store_true", dest="T1w", help="Compute segstats for T1W")
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force segstats computation", default=False)
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)


# ******************* EVALUATE COMMAND LINE ARGUMENTS ********************
def evaluate_args(options):
    
    #SEARCHTABLE=None
    groupIdFile = None    

    if os.path.isfile(os.path.join(st.creds.dataDir,'rawdata','participants.tsv')):
        groupIdFile = os.path.join(st.creds.dataDir,'rawdata','participants.tsv')

    segstatsInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_compute_segstats_input.json')
    if not os.path.isfile(segstatsInputFile):
        return

    with open(segstatsInputFile) as j:
        segstatsInput = json.load(j)


    return groupIdFile, segstatsInput



# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    options = parser.parse_args()
    st.creds.read(options.PROJECT)
    groupIdFile, segstatsInput = evaluate_args(options)

    ls_inputType = []
    for k, v in vars(options).items():
        if k in ['cbf','apt','dti','T1w'] and k in segstatsInput.keys() and v:
            ls_inputType.append(k)
    if not ls_inputType:
        parser.print_help()
        sys.exit()


    #do some prep for parallel processing 
    if options.SUBMIT:
        #get some precursors
        now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_segstats')
        if not os.path.isdir(base):
            os.makedirs(base)

        #output files
        submit = os.path.join(base,'segstats_' + now + '.submit')
        error = os.path.join(base,'segstats_' + now + '.error')
        output = os.path.join(base,'segstats_' + now + '.output')
        log = os.path.join(base,'segstats_' + now + '.log')
        dagman = Dagman(name=options.PROJECT + '-segstats', submit=submit)

        job_segstats = st.condor.create_python_condor_job('compute_segstats',
                                                              'compute_segstats.py',
                                                              st.creds.machineNames,
                                                              submit,
                                                              error,
                                                              output,
                                                              log,
                                                              dagman,
                                                              docker=True,
                                                              docker_image='wsuconnect/neuro:docker',
                                                              docker_mount_if=st.creds.dockerMountIf,
                                                              request_cpus=1,
                                                              request_memory='2g')
        segstats_flag = False

    try:
        #read participants tsv file
        df_participants = pd.read_csv(groupIdFile, sep='\t')
   
    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    #sort participants
    df_participants.sort_values(by=['participant_id'])

    #skip those with 'discard' set to true
    if 'discard' in df_participants.columns:
        df_participants = df_participants[~df_participants['discard']]

    #search each raw directory
    allSegsToProcess = st.mysql.sql_query(searchtable=st.creds.searchTable,regex='aseg.mgz',searchcol='filename',progress=False,inclusion=["aparc+"],exclusion=['DKTatlas','a2009s','a2005'])
    # df_fullDataMatrix = pd.read_csv(outputCsv)
    segstats_flag = False
    for asegToProcess in allSegsToProcess:
        print(asegToProcess)

        if 'fsaverage' in asegToProcess:
            continue
        st.subject.get_id(asegToProcess)
        st.subject.check(st.creds.dataDir)

        if st.subject.discard:
            continue

        # print('\tproceeding')

        #loop over all provided imaging types
        for inputType in ls_inputType:

            #loop over any files found using specified search criteria
            if segstatsInput['fmriprep']:
                # print(os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-*',*segstatsInput[inputType]['regex']))
                inTargFiles = glob(os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-*',*segstatsInput[inputType]['regex']))
            else:
                inTargFiles = glob(os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,*segstatsInput[inputType]['regex']))

            # print(len(inTargFiles))
            for inTargFile in inTargFiles:
                st.subject.get_id(inTargFile)
                outDir = os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id, 'ses-' + st.subject.sesNum,segstatsInput[inputType]['type'])


                if options.SUBMIT:
                    argStr = f'--in-file {inTargFile} --seg {asegToProcess} --out-dir {outDir}'
                    if options.OVERWRITE:
                        argStr += ' --overwrite'
                    job_segstats.add_arg(argStr)
                    segstats_flag = True
                    if options.progress:
                        print('Added job for mri_segstats for ' + inTargFile)
                else:
                    st.compute_segstats(inTargFile,asegToProcess,outDir)

                # if not os.path.isdir(outDir):
                #     os.makedirs(outDir)

                # outFile = inTargFile.replace('space-','space-FS')
                # if not os.path.isfile(outFile):
                #     vol2volCmd = 'mri_vol2vol --mov ' + inTargFile + ' --targ ' + os.path.join(os.path.dirname(asegToProcess),'T1.mgz') + ' --regheader --o ' + outFile + ' --no-save-reg'
                #     os.system(vol2volCmd)
                #     print('SUCCESS: moved input file to ' + os.path.join(os.path.dirname(asegToProcess),'T1.mgz'))



                # if not os.path.isfile(os.path.join(outDir,os.path.basename(inTargFile).replace('.nii.gz','.dat'))) or options.OVERWRITE:
                #     if not options.SUBMIT:
                #         os.system('mri_segstats --seg ' + asegToProcess + ' --nonempty --ctab-default --in ' + outFile + ' --sum ' + os.path.join(outDir,os.path.basename(outFile).replace('.nii.gz','.dat')))
                #     else:
                #         job_segstats.add_arg('--seg ' + asegToProcess + ' --nonempty --ctab-default --in ' + outFile + ' --sum ' + os.path.join(outDir,os.path.basename(outFile).replace('.nii.gz','.dat')))
                #         segstats_flag = True
                #         if options.progress:
                #             print('Added job for mri_segstats for ' + inTargFile)

        

    if segstats_flag:
        dagman.build_submit()
    
