#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 22 July 2023
#
# Modified on

import os
import argparse
from pycondor import Dagman
import datetime
import sys
from glob import glob as glob
import json

#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.1'
DATE = '22 July 2023'
FSLDIR = os.environ["FSLDIR"]


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True,action="store", dest="PROJECT", help="Perform FreeSurfer recon-all and/or recon-all refinement for the selected project: " + ' '.join(st.creds.projects), default=None)

parser.add_argument('--stage1', action="store_true", dest="STAGE1", help="only perform recon-all without brainmask refinement", default=False)
parser.add_argument('--stage2', action="store_true", dest="STAGE2", help="perform brainmask refinement", default=False)
parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
   


# ******************* Setup Main Processing ********************
def prepare_pipeline(options: dict,submit: str=None, error: str=None, output: str=None, log: str=None, dagman: Dagman=None):
    """_summary_

    :param options: _description_
    :type options: dict
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
    """

    #load parameter JSON control file
    try:
        reconallInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_freesurfer_recon-all_input.json')
        if not os.path.isfile(os.path.join(st.creds.dataDir,'code',options.PROJECT + '_freesurfer_recon-all_input.json')):
            return

        with open(reconallInputFile) as j:
            reconallInput = json.load(j)

            #asl sql_query inputs
            incExcDict = {}
            if 'inclusion_list' in reconallInput:
                incExcDict['inclusion'] = reconallInput.pop('inclusion_list')
            if 'exclusion_list' in reconallInput:
                incExcDict['exclusion'] = reconallInput.pop('exclusion_list')

    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    regexStr = st.bids.get_bids_filename(**reconallInput['main_image_params']['input_bids_labels'])

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,**incExcDict,progress=False)



    # loop throught files
    filesToProcess.sort()
    reconallFlag = True
    threadCount = 0
    for f in filesToProcess:

        #check for processed output
        st.subject.get_id(os.path.dirname(f))
        mainReconallOutputDir = os.path.join(st.creds.dataDir,'derivatives','recon-all')
        outFile = os.path.join(mainReconallOutputDir, 'sub-' + st.subject.id + '_ses-' + st.subject.sesNum, 'mri', 'T1w.a2009s.segstats.dat')
        if os.path.isfile(outFile) and not options.OVERWRITE:
            continue


        #run job on condor
        if options.SUBMIT:
            #create condor job
            if reconallFlag:
                if options.STAGE1 or (not options.STAGE1 and not options.STAGE2):
                    job_reconall1 = st.condor.create_python_condor_job(
                         'reconall1',
                         'fsreconall_stage1.py',
                         st.creds.machineNames,
                         submit,error,
                         output,
                         log,
                         dagman,
                         docker=True,
                         docker_image='wsuconnect/neuro:docker',
                         docker_mount_if=st.creds.dockerMountIf,
                         request_cpus=1,
                         request_memory='5g')
                if options.STAGE2:
                    job_reconall2 = st.condor.create_python_condor_job(
                         'reconall2',
                         'fsreconall_stage2.py',
                         st.creds.machineNames,
                         submit,error,
                         output,
                         log,
                         dagman,
                         docker=True,
                         docker_image='wsuconnect/neuro:docker',
                         docker_mount_if=st.creds.dockerMountIf,
                         request_cpus=1,
                         request_memory='5g')
                reconallFlag = False


            #create argument string
                
            if options.STAGE1 and options.STAGE2:
                argStr = (f + ' ' + 
                        st.creds.dataDir + ' ' +
                        reconallInputFile + ' ' + 
                        mainReconallOutputDir)
                argStr += ' --directive autorecon1'
                if options.OVERWRITE:
                    argStr += ' --overwrite'
                if options.progress:
                    argStr += ' --progress'

                #add arguments to condor job
                job_reconall1.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
                print('Added Stage-1 job for freesurfer reconall for file:  ' + f)

                argStr2 = (os.path.join(mainReconallOutputDir,'sub-' + st.subject.id + '_ses-' + st.subject.sesNum) + ' ' + 
                        st.creds.dataDir + ' ' + 
                        reconallInputFile)
                if options.OVERWRITE:
                    argStr2 += ' --overwrite'
                if options.progress:
                    argStr2 += ' --progress'    


                #add arguments to condor job
                job_reconall2.add_arg(argStr2)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
                print('Added Stage-2 job for freesurfer reconall for file:  ' + f)

            elif options.STAGE1 or (not options.STAGE1 and not options.STAGE2):
                argStr = (f + ' ' + 
                        st.creds.dataDir + ' ' +
                        reconallInputFile + ' ' + 
                        mainReconallOutputDir)
                if options.OVERWRITE:
                    argStr += ' --overwrite'
                if options.progress:
                    argStr += ' --progress'

                #add arguments to condor job
                job_reconall1.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
                print('Added Stage-1 job for freesurfer reconall for file:  ' + f)

            elif options.STAGE2:

                argStr2 = (os.path.join(mainReconallOutputDir,'sub-' + st.subject.id + '_ses-' + st.subject.sesNum) + ' ' + 
                        st.creds.dataDir + ' ' + 
                        reconallInputFile)
                if options.OVERWRITE:
                    argStr2 += ' --overwrite'
                if options.progress:
                    argStr2 += ' --progress'    


                #add arguments to condor job
                job_reconall2.add_arg(argStr2)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
                print('Added Stage-2 job for freesurfer reconall for file:  ' + f)

            # if threadCount == 20 or f in filesToProcess[-1]:
            if f in filesToProcess[-1]:

                #job order
                if options.STAGE1 and options.STAGE2:
                    job_reconall1.add_child(job_reconall2)
                dagman.build_submit()

                if f in filesToProcess[-1]:
                    return
            else:
                threadCount += 1

        else:
            if options.STAGE1 and options.STAGE2:
                st.fsreconall_stage1(f,st.creds.dataDir,reconallInputFile,mainReconallOutputDir,directive='autorecon1',overwrite=options.OVERWRITE,progress=options.progress)
                st.fsreconall_stage2(os.path.join(mainReconallOutputDir,'sub-' + st.subject.id + '_ses-' + st.subject.sesNum),st.creds.dataDir,reconallInputFile,overwrite=options.OVERWRITE,progress=options.progress)
            
            elif options.STAGE1 or (not options.STAGE1 and not options.STAGE2):
                st.fsreconall_stage1(f,st.creds.dataDir,reconallInputFile,mainReconallOutputDir,overwrite=options.OVERWRITE,progress=options.progress)

            if options.STAGE2:
                st.fsreconall_stage2(os.path.join(mainReconallOutputDir,'sub-' + st.subject.id + '_ses-' + st.subject.sesNum),st.creds.dataDir,reconallInputFile,overwrite=options.OVERWRITE,progress=options.progress)
            



# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """

    #get and evaluate options
    options = parser.parse_args()
    st.creds.read(options.PROJECT)

    #do some prep for parallel processing 
    if options.SUBMIT:
        #get some precursors
        now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_recon-all')
        if not os.path.isdir(base):
            os.makedirs(base)

        if not os.path.isdir(os.path.join(st.creds.dataDir,'derivatives','recon-all')):
            os.makedirs(os.path.join(st.creds.dataDir,'derivatives','recon-all'))

        #output files
        submit = os.path.join(base,'fsreconall_' + now + '.submit')
        error = os.path.join(base,'fsreconall_' + now + '.error')
        output = os.path.join(base,'fsreconall_' + now + '.output')
        log = os.path.join(base,'fsreconall_' + now + '.log')
        dagman = Dagman(name=options.PROJECT + '-fsreconall', submit=submit)


        #perform struc 2 standard registration
        prepare_pipeline(options,submit=submit,error=error,output=output,log=log,dagman=dagman)

    else:
        prepare_pipeline(options)

    

    

if __name__ == '__main__':
    main()
