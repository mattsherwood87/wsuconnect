#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 6 July 2023
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
DATE = '6 July 2023'
FSLDIR = os.environ["FSLDIR"]


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="Perform DTI preprocessing for the selected project: " + ' '.join(st.creds.projects), default=None)

parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)



# ******************* Setup Main Processing ********************
def modality_process(options: dict, submit: str=None, error: str=None, output: str=None, log: str=None, dagman: Dagman=None):
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

    


    return


# ******************* MAIN ********************
if __name__ == '__main__':
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
        base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_dti_preprocess')
        if not os.path.isdir(base):
            os.makedirs(base)

        #load parameter JSON control file
    try:
        dtiInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_dti_preprocess_input.json')
        if not os.path.isfile(os.path.join(st.creds.dataDir,'code',options.PROJECT + '_dti_preprocess_input.json')):
            print(f"ERROR: cannot find project's control file for dti preprocessing - {dtiInputFile}")
            sys.exit()

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


    #find all DTI files for processing
    regexStr = st.bids.get_bids_filename(**dtiInput['main_image_params']['input_bids_labels'])

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,**incExcDict,progress=False)      


    # loop throught files
    filesToProcess.sort()
    for f in filesToProcess:

        #get subject name and see if they should be discarded
        st.subject.get_id(os.path.dirname(f))
        st.subject.check(st.creds.dataDir)
        # print(st.subject.id)
        if options.SUBJECTS:
            if not f"sub-{st.subject.id}" in options.SUBJECTS:
                continue

        if not st.subject.discard:

            if options.SUBMIT:
                #output files
                submit = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.submit")
                error = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.error")
                output = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.output")
                log = os.path.join(base, f"sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.log")
                dagman = Dagman(name=f"{options.PROJECT}_dti_preprocess_sub-{st.subject.id}_ses-{st.subject.sesNum}", submit=submit)

            #check for processed output
            outFile = glob(os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'dwi', 'dtifit', '*_FA.nii.gz'))
            if len(outFile) == 1 and not options.OVERWRITE:
                if options.progress:
                    print('WARNING: Output files found in ' + os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'dwi','dtifit'))
                    print('\toverwrite not specified, skipping')

                continue

            else:
                if options.progress:
                    print('Preparing Job: Output files not found in ' + os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'dwi', 'dtifit'))


            #run job on condor
            if options.SUBMIT:
                #create condor job
                if dtiInput['eddy_params']['use_cuda']:
                    job_dti = st.condor.create_bin_condor_job('dti_preprocess',
                                                              'docker',
                                                              st.creds.gpuMachineNames,
                                                              submit,
                                                              error,
                                                              output,
                                                              log,
                                                              dagman,
                                                              request_cpus=2,
                                                              request_memory='5g')
                    
                else:
                    job_dti = st.condor.create_python_condor_job('dti_preprocess','dti_preprocess.py',st.creds.machineNames,submit,error,output,log,dagman)                    


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
                argStr += f' --user=root --runtime=nvidia --gpus all -m 10g --cpus=3 wsuconnect/neuro-gpu {os.path.join(os.path.dirname(REALPATH),"support_tools","dti_preproc_wrapper.sh")}'

                #add dti_preprocess.py aruments to the docker arguments
                argStr += (' ' + f + ' ' + 
                          st.creds.dataDir + ' ' +
                          dtiInputFile)
                if options.OVERWRITE:
                    argStr += ' --overwrite'
                if options.progress:
                    argStr += ' --progress'

                #add arguments to condor job
                job_dti.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))

                if options.progress:
                    print('Added job for dti preprocessing for file:  ' + f)

                #submit job
                dagman.build_submit()

            else:
                st.import_dti_preprocess()
                st.dti_preprocess(f,st.creds.dataDir,dtiInputFile,overwrite=options.OVERWRITE,progress=options.progress)

