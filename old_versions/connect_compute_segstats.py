#!/resshare/general_processing_codes/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
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
from pycondor import Job, Dagman


#local import
REALPATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(REALPATH)
from helper_functions.mysql_commands import *
from helper_functions.read_credentials import *
from helper_functions.create_freesurfer_condor_job import *
from helper_functions.create_python_condor_job import *

from support_tools.creds import *


# GLOBAL INFO
#versioning
VERSION = '2.0.0'
DATE = '17 April 2023'

#input argument parser
parser = argparse.ArgumentParser()

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
def parse_arguments():

    #input options for main()
    requiredNamed = parser.add_argument_group('required arguments')
    requiredNamed.add_argument('-p','--project', action="store", dest="PROJECT", help="update the selected project: " + ' '.join(creds.projects), default=None)
    parser.add_argument('--cbf', action="store_true", dest="CBF", help="Compute segstats for CBF")
    parser.add_argument('--apt', action="store_true", dest="CBF", help="Compute segstats for CBF")
    parser.add_argument('--dti', action="store_true", dest="CBF", help="Compute segstats for CBF")
    parser.add_argument('--fmri', action="store_true", dest="CBF", help="Compute segstats for CBF")
    parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
    parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
    parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
    options = parser.parse_args()

    #determine the search table and search string
    if not options.PROJECT in creds.projects:
        if not options.version:
            print("ERROR: user must define a project using [-p|--project <project>]\n\n")
            parser.print_help()
        else:
            print('connect_rawdata_check.py version {0}.'.format(VERSION)+" DATED: "+DATE)
        sys.exit()

    return options


# ******************* EVALUATE COMMAND LINE ARGUMENTS ********************
def evaluate_args(options):
    
    #SEARCHTABLE=None
    groupIdFile = None    

    if os.path.isfile(os.path.join(creds.dataDir,'rawdata','participants.tsv')):
        groupIdFile = os.path.join(creds.dataDir,'rawdata','participants.tsv')


    return groupIdFile



# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    options = parse_arguments()
    read_credentials(options.PROJECT)
    groupIdFile = evaluate_args(options)

    #do some prep for parallel processing 
    if options.SUBMIT:
        #get some precursors
        now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        base = os.path.join(creds.dataDir,'derivatives','processing_logs','connect_segstats')
        if not os.path.isdir(base):
            os.makedirs(base)

        #output files
        submit = os.path.join(base,'segstats_' + now + '.submit')
        error = os.path.join(base,'segstats_' + now + '.error')
        output = os.path.join(base,'segstats_' + now + '.output')
        log = os.path.join(base,'segstats_' + now + '.log')
        dagman = Dagman(name=options.PROJECT + '-segstats', submit=submit)

        job_segstats = create_freesurfer_condor_job('mri_segstats','mri_segstats',creds.machineNames,submit,error,output,log,dagman)
        segstats_flag = False

    try:
        #read participants tsv file
        df_participants = pd.read_csv(groupIdFile, sep='\t')
   
    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    #sort participants
    df_participants.sort_values(by=['participant_id'])


    #search each raw directory
    allSegsToProcess = sql_query_files('aseg-native.mgz',searchcol='filename',progress=False,inclusion='a2009s')
    # df_fullDataMatrix = pd.read_csv(outputCsv)
    for idx, df_participant in df_participants.iterrows():
        if df_participant.discard in ['YES','Yes','yes','true','True']:
            continue

        #return just the subject files
        subName = str(df_participant.participant_id)
        subFilesToProcess = [x for x in allSegsToProcess if subName in x]

        #get unique session names for this particular subject
        tmp_ls = [i.split('ses-')[1] for i in subFilesToProcess]
        tmp_ls = ['ses-' + re.split(os.sep + '|_',i)[0] for i in tmp_ls]
        tmp_np = np.array(tmp_ls)
        tmp_np = np.unique(tmp_np)
        tmp_np = np.sort(tmp_np)

        #loop over sorted sessions
        for tmp_sesNum in tmp_np:
            sesNum = tmp_sesNum.replace('ses-','')
            filesToProcess = [x for x in subFilesToProcess if sesNum in x]

            #should only be 1 file to process
            for f in filesToProcess:
                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'flirt','dwi','*proc-flirt_res-hi_space-individual_desc-iout-tmean-brain_dwi*1000.nii.gz'))

                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','dwi')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','dwi'))

                #     if not options.SUBMIT:
                #         os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','dwi',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #     else:
                #         job_segstats.add_arg('--seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','dwi',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #         segstats_flag = True
                #         if options.progress:
                #             print('Added job for mri_segstats for ' + inTargFile)



                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'feat','func',subName + '_ses-' + sesNum + '_task-nback_bold.feat','reg_highres','stats','*zstat*.nii.gz'))

                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func'))

                #     if not options.SUBMIT:
                #         os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #     else:
                #         job_segstats.add_arg('--seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #         segstats_flag = True
                #         if options.progress:
                #             print('Added job for mri_segstats for ' + inTargFile)
                
                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'feat','func',subName + '_ses-' + sesNum + '_task-nback_bold.feat','reg_highres','stats','*percent-signal*.nii.gz'))

                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func'))

                #     if not options.SUBMIT:
                #         os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #     else:
                #         job_segstats.add_arg('--seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','func',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #         segstats_flag = True
                #         if options.progress:
                #             print('Added job for mri_segstats for ' + inTargFile)


                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'flirt','perf','*acq-cbf*proc-flirt_res-hi_space-individual_desc-vol-1-brain_asl.nii.gz'))
                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf'))
                #     if not os.path.isfile(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf',os.path.basename(inTargFile).replace('.nii.gz','.dat'))):
                #         os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf',os.path.basename(inTargFile).replace('.nii.gz','.dat')))

                inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'flirt','perf','*acq-source_task-rest_proc-flirt_res-hi_space-individual_desc-vol-1-brain_cbf.nii.gz'))
                for inTargFile in inTargFiles:
                    if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf')):
                        os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf'))

                    if not options.SUBMIT:
                        os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                    else:
                        job_segstats.add_arg('--seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','perf',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                        segstats_flag = True
                        if options.progress:
                            print('Added job for mri_segstats for ' + inTargFile)


                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives',subName,'ses-' + sesNum,'flirt','apt','*acq-mtrasym_proc-flirt_res-hi_space-individual_desc-brain_apt.nii.gz'))
                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','apt')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','apt'))

                #     if not options.SUBMIT:
                #         os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','apt',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #     else:
                #         job_segstats.add_arg('--seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives',subName, 'ses-' + sesNum,'segstats','apt',os.path.basename(inTargFile).replace('.nii.gz','.dat')))
                #         segstats_flag = True
                #         if options.progress:
                #             print('Added job for mri_segstats for ' + inTargFile)


                # inTargFiles = glob(os.path.join(creds.dataDir,'derivatives','sub-' + subName,'ses-' + sesNum,'bet','anat','*acq-axial_proc-ants_res-hi_desc-brain_T1w.nii.gz'))

                # for inTargFile in inTargFiles:
                #     if not os.path.isdir(os.path.join(creds.dataDir,'derivatives','sub-' + subName, 'ses-' + sesNum,'segstats','anat')):
                #         os.makedirs(os.path.join(creds.dataDir,'derivatives','sub-' + subName, 'ses-' + sesNum,'segstats','anat'))
                #     os.system('mri_segstats --seg ' + f + ' --nonempty --ctab-default --in ' + inTargFile + ' --sum ' + os.path.join(creds.dataDir,'derivatives','sub-' + subName, 'ses-' + sesNum,'segstats','anat',os.path.basename(inTargFile).replace('.nii.gz','.dat')))


                # mri_segstats --seg ~/Documents/AFRL_neuroinflammation/SUBJECTS/Damato2/mri/aparc+aseg-native.nii.gz --nonempty --ctab-default --in ../Damato_01052023/processed_data/Damato_01052023_3D_pCASL_7.5min_4mm_-good_601059_brain_highres.nii.gz --sum ../Damato_01052023/processed_data/CBF_brain_space-T1w.segstats.dat


            
    #         df_dataMatrix = pd.DataFrame(d_dataMatrix, index=[0])
    #         #write dataframe to csv
    #         if os.path.isfile(outputCsv):
    #             df_dataMatrix.to_csv(outputCsv, mode='a', index=False, header=False)
    #         else:
    #             df_dataMatrix.to_csv(outputCsv, mode='a', index=False)

    # print('SUCCESS: output saved to ' + outputCsv)

        

    if segstats_flag:
        dagman.build_submit()
    

if __name__ == '__main__':
    main()
