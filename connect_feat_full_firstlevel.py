#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.11.11 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 22 FEB 2024
#
# Modified on

import os
import argparse
from pycondor import Dagman
import datetime
import sys
from glob import glob as glob
import json
import uuid
import traceback
import nibabel as nib
from nilearn.image import smooth_img
from nilearn.masking import apply_mask, unmask
# from nilearn.maskers import NiftiMasker
# from nilearn import image

#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.1'
DATE = '22 Feb 2024'
FSLDIR = os.environ["FSLDIR"]


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="Perform full firstlevel FEAT for the selected project: " + ' '.join(st.creds.projects), default=None)

parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('--docker', action="store_true", dest="DOCKER", help="Submit conversion to HTCondor and process in wsuconnect/neuro docker container [default=False]", default=False)
parser.add_argument('--skip-id-check', action="store_true", dest="SKIPIDCHECK", help="Skip subject id checking in participants.tsv file", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
  


# ******************* Setup Main Processing ********************
def modality_process(options: dict):
    
    refImage = False
    strucRegMatrix = None

    #load parameter JSON control file
    try:
        paramsInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_feat_full_firstlevel_input.json')
        if not os.path.isfile(os.path.join(st.creds.dataDir,'code',options.PROJECT + '_feat_full_firstlevel_input.json')):
            return

        with open(paramsInputFile) as j:
            featInput = json.load(j)

        #asl sql_query inputs
        incExcDict = {}
        if 'inclusion_list' in featInput:
            incExcDict['inclusion'] = featInput.pop('inclusion_list')
        if 'exclusion_list' in featInput:
            incExcDict['exclusion'] = featInput.pop('exclusion_list')

        #(optional) get structural image parameters
        if 'reference_image_params' in featInput:
            refImageParams = featInput.pop('reference_image_params')
            refImage = True

    except FileNotFoundError as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        print(f"Exception occurred in file: {filename}, line: {lineno}")
        print(f"\tException type: {exc_type.__name__}")
        print(f"\tException message: {e}")
        traceback.print_exc()
        sys.exit()

    regexStr = featInput['bold_regexstr']

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regexStr,**incExcDict,progress=False)



    # loop throught files
    filesToProcess.sort()
    featFlag = False
    job_flag = True
    featFlag = False
    job2_flag = True
    threadCount = 0

    now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
    for f in filesToProcess:
        if options.progress:
            print('Evaluating input BOLD file: ' + f)

        #get subject name and see if they should be discarded
        st.subject.get_id(f)
        if options.progress:
            print('\tSUBJECT: ' + st.subject.id + ' SESSION: ' + st.subject.sesNum)
        if st.subject.check(st.creds.dataDir) and not options.SKIPIDCHECK:
            print('WAARNING: subject excluded from analysis. To perform the analysis run with the skip ID check option.')
            continue

        boldInputLabels = st.bids.get_bids_labels(f)
        if not 'task' in boldInputLabels.keys():
            continue
        elif boldInputLabels['task'] in featInput.keys():
            boldTask = boldInputLabels['task']
        else:
            continue


        # make output directory in derivatives
        featOutputDir = os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'fmriprep-feat','func',os.path.basename(f).split('.')[0] + '.feat')
        featDesignDir = os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'fmriprep-feat','func',os.path.basename(f).split('.')[0] + '.design')
        # if not os.path.isdir(featOutputDir):
        #     os.makedirs(featOutputDir)
        if os.path.isdir(featOutputDir):
            #check for processed output
            outFile = glob(os.path.join(featOutputDir, '*zstat*.nii.gz'))
            if len(outFile) >= 1 and not options.OVERWRITE:
                continue
            elif len(outFile) >= 1: #output exists, overwrite specified
                os.system('rm -rf ' + featOutputDir)

        #copy design files
        if not os.path.isdir(featDesignDir):
            os.makedirs(featDesignDir)
        os.system('cp -RL ' + os.path.join(st.creds.dataDir, 'code' ,'bold_designs', 'task-' + boldTask, featInput[boldTask]['design_basename'] + '*') + ' ' + featDesignDir)

        if 'step2_design_basename' in featInput[boldTask].keys():
            os.system('cp -RL ' + os.path.join(st.creds.dataDir, 'code' ,'bold_designs', 'task-' + boldTask, featInput[boldTask]['step2_design_basename'] + '*') + ' ' + featDesignDir)


        #look for accompanying structural data on disk in derivatives
        mainFileDir = os.path.dirname(f)
        if refImage and 'highres_files' in featInput[boldTask]['line_pairs'].keys():
            ref_regexStr = st.bids.get_bids_filename(**refImageParams['input_bids_labels'])
            # mainFileDir = os.path.dirname(f)
            mainBetOutputDir = os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,refImageParams['input_bids_type'])#create base path and filename for move

            if refImageParams['input_bids_location'] == 'rawdata':
                refImageFile = glob(os.path.join(os.path.dirname(mainFileDir),refImageParams['input_bids_type'],'*' + ref_regexStr.split('_')[1] + '*'))
            elif refImageParams['input_bids_location'] == 'derivatives':
                refImageFile = glob(os.path.join(mainBetOutputDir,'*' + ref_regexStr.split('_')[1] + '*'))
            else:
                print('ERROR: structural file "bids_location" not supported. This should be "rawdata" or "derivatives"')
                print('\tCannot perform FEAT as specified... continuing to next file')
                continue

            for item in ref_regexStr.split('_')[2:]:
                refImageFile = [x for x in refImageFile if item in x]

            if 'exclusion_list' in refImageParams.keys():
                for item in refImageParams['exclusion_list']:
                    refImageFile = [x for x in refImageFile if not item in x]
            
            if len(refImageFile) > 0:
                refImageFile = refImageFile[0]
                if options.progress:
                    print('\tFound associated reference image: ' + refImageFile)
            elif refImageParams['input_bids_location'] == 'rawdata':
                print('ERROR: structural file ' + os.path.join(os.path.dirname(mainFileDir),'anat','*' + ref_regexStr + '*') + ' not found')
                print('\tCannot perform FEAT... skipping')
                continue
            elif refImageParams['input_bids_location'] == 'derivatives':
                print('ERROR: structural file ' + os.path.join(os.path.dirname(mainBetOutputDir),'*' + ref_regexStr + '*') + ' not found')
                print('\tCannot perform FEAT... skipping"')
                continue

       
        
        #modify design file
        try:
            with open(os.path.join(featDesignDir,featInput[boldTask]['design_basename'] + '.fsf'),'r',encoding='utf-8') as file:
                designData = file.readlines()

        except FileNotFoundError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = exc_tb.tb_frame.f_code.co_filename
            lineno = exc_tb.tb_lineno
            print(f"Exception occurred in file: {filename}, line: {lineno}")
            print(f"\tException type: {exc_type.__name__}")
            print(f"\tException message: {e}")
            traceback.print_exc()
            continue

        # Refine FEAT Design file
        for k in featInput[boldTask]['line_pairs'].keys():
            if 'outputdir' in k:
                designData[featInput[boldTask]['line_pairs'][k]-1] = 'set fmri(outputdir) "' + featOutputDir + '"\n'
            elif 'feat_files' in k:
                if featInput['smooth']:
                    print('smoothing data')
                    img = nib.load(f)
                    img = smooth_img(img, 6.25)



                    # Load ROI mask
                    roi_mask_path = os.path.join(st.creds.dataDir,'derivatives',f"sub-{st.subject.id}", "anat", f"sub-{st.subject.id}_acq-axial_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz")
                    roi_mask = nib.load(roi_mask_path)
                    # masker = NiftiMasker(mask_img=roi_mask_path)
                    # fdata = masker.fit_transform(img)
                    # image.new_img_like(f, fdata).to_filename(f.replace('preproc','smoothpreproc'))
                    img = apply_mask(img,roi_mask)
                    img = unmask(img,roi_mask)
                    nib.save(img,f.replace('preproc','smoothpreproc'))
                    #smooth data
                    #mask data
                designData[featInput[boldTask]['line_pairs'][k]-1] = 'set feat_files(1) "' + f.replace('preproc','smoothpreproc') + '"\n'
            elif 'highres_files' in k:
                designData[featInput[boldTask]['line_pairs'][k]-1] = 'set highres_files(1) "' + refImageFile + '"\n'

            elif 'custom' in k:
                ls_customFiles = []
                if featInput[boldTask][k]['input_bids_location'] == 'rawdata':
                    ls_customFiles = glob(os.path.join(os.path.dirname(mainFileDir),featInput[boldTask][k]['input_bids_type'],'*' + featInput[boldTask][k]['regex'] + '*'))
                elif featInput[boldTask][k]['input_bids_location'] == 'derivatives':
                    ls_customFiles = glob(os.path.join(os.path.dirname(f),'*' + featInput[boldTask][k]['regex'] + '*'))
                else:
                    print('ERROR: ' + k + ' "bids_location" not supported. This should be "rawdata" or "derivatives"')
                    print('\tCannot perform FEAT as specified... continuing to next file')
                    skipFlag = True
                    continue
                
                if not ls_customFiles:
                    print('ERROR: could not find any files specified by ' + k + ' regex')
                    print('\tCannot perform FEAT as specified... continuing to next file')
                    skipFlag = True
                    continue

                if 'run' in f:
                    s_run = [x for x in f.split('_') if 'run' in x][0]
                    ls_customFiles =[x for x in ls_customFiles if s_run in x]
                if 'inclusion_list' in featInput[boldTask][k].keys():
                    for item in featInput[boldTask][k]['inclusion_list']:
                        ls_customFiles =[x for x in ls_customFiles if item in x]

                if len(ls_customFiles) != 1:
                    print('ERROR: found none or more than one file specified by ' + k )
                    print('\tCannot perform FEAT as specified... continuing to next file')
                    skipFlag = True
                    continue
                designData[featInput[boldTask]['line_pairs'][k]-1] = 'set fmri(' + k + ') "' + ls_customFiles[0]  + '"\n'
            # elif 'init_standard' in k and 'out_matrix_base' in refImageParams.keys():
            #     strucRegDir = os.path.join(creds.dataDir,'derivatives','sub-' + subName,'ses-' + sesNum,'flirt',refImageParams['input_bids_type'])
            #     strucRegMatrix = os.path.join(strucRegDir,refImageParams['out_matrix_base']  + '.mat')
            #     if not os.path.isfile(strucRegMatrix):
            #         print('Warning: cannot find structural registration file ' + strucRegMatrix)
            #         print('\tSkipping matrix concatenation')
            #     else:
            #         if options.progress:
            #             print('\tStructural to standard registration found: ' + strucRegMatrix)
            #         designData[featInput[boldTask]['line_pairs'][k]-1] = 'set fmri(init_standard) "' + strucRegMatrix + '"\n'
            else:
                print('WARNING: support for line_pair option ' + k + ' is not available')
                print('\tskipping this request and proceeding. Contact Matthew Sherwood')

        with open(os.path.join(featDesignDir,featInput[boldTask]['design_basename'] + '.fsf'), 'w', encoding='utf-8') as file:
            file.writelines(designData)


        #Refine FEAT step 2 design file 
        if 'step2_line_pairs' in featInput[boldTask].keys():
            #modify design file
            try:
                with open(os.path.join(featDesignDir,featInput[boldTask]['step2_design_basename'] + '.fsf'),'r',encoding='utf-8') as file:
                    designData = file.readlines()

            except FileNotFoundError as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                filename = exc_tb.tb_frame.f_code.co_filename
                lineno = exc_tb.tb_lineno
                print(f"Exception occurred in file: {filename}, line: {lineno}")
                print(f"\tException type: {exc_type.__name__}")
                print(f"\tException message: {e}")
                traceback.print_exc()
                continue     

            skipFlag = False
            for k in featInput[boldTask]['step2_line_pairs'].keys():
                if 'analysis' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(analysis)) 2\n'
                elif 'inputtype' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(inputtype) 1\n'
                elif 'prestats' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(filtering_yn) 0\n'
                elif 'poststats' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(poststats_yn) 0\n'
                elif 'outputdir' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(outputdir) "' + featOutputDir + '"\n'
                elif 'feat_files' in k:
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set feat_files(1) "' + f + '"\n'
                elif 'custom' in k:
                    ls_customFiles = []
                    if featInput[boldTask][k]['input_bids_location'] == 'rawdata':
                        ls_customFiles = glob(os.path.join(os.path.dirname(mainFileDir),featInput[boldTask][k]['input_bids_type'],'*' + featInput[boldTask][k]['regex'] + '*'))
                    elif refImageParams['input_bids_location'] == 'derivatives':
                        ls_customFiles = glob(os.path.join(mainFileDir.replace('rawdata','derivatives'),featInput[boldTask][k]['input_bids_type'],'*' + featInput[boldTask][k]['regex'] + '*'))
                    else:
                        print('ERROR: ' + k + ' "bids_location" not supported. This should be "rawdata" or "derivatives"')
                        print('\tCannot perform FEAT as specified... continuing to next file')
                        skipFlag = True
                        continue
                    
                    if not ls_customFiles:
                        print('ERROR: could not find any files specified by ' + k + ' regex')
                        print('\tCannot perform FEAT as specified... continuing to next file')
                        skipFlag = True
                        continue

                    if 'run' in f:
                        s_run = [x for x in f.split('_') if 'run' in x][0]
                        ls_customFiles =[x for x in ls_customFiles if s_run in x]
                    if 'inclusion_list' in featInput[boldTask][k].keys():
                        for item in featInput[boldTask][k]['inclusion_list']:
                            ls_customFiles =[x for x in ls_customFiles if item in x]

                    if len(ls_customFiles) != 1:
                        print('ERROR: found none or more than one file specified by ' + k )
                        print('\tCannot perform FEAT as specified... continuing to next file')
                        skipFlag = True
                        continue
                    designData[featInput[boldTask]['step2_line_pairs'][k]-1] = 'set fmri(' + k + ') "' + ls_customFiles[0]  + '"\n'
                else:
                    print('WARNING: support for line_pair option ' + k + ' is not available')
                    print('\tskipping this request and proceeding. Contact Matthew Sherwood')

            if skipFlag:
                continue

            with open(os.path.join(featDesignDir,featInput[boldTask]['step2_design_basename'] + '.fsf'), 'w', encoding='utf-8') as file:
                file.writelines(designData)

        #do I need to insert custom registration?
        if refImage and 'out_matrix_base' in refImageParams.keys():
            strucRegDir = os.path.join(st.creds.dataDir,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,refImageParams['input_bids_type'])
            strucRegMatrix = glob(os.path.join(strucRegDir,'*' + refImageParams['out_matrix_base']  + '.mat'))
            if len(strucRegMatrix) != 1:
                print('ERROR: found none or more than one structrual registration file')
                print('\tCannot perform FEAT as specified... continuing to next file')
                continue
            strucRegMatrix = strucRegMatrix[0]
            if not os.path.isfile(strucRegMatrix):
                os.system('echo "Warning: cannot find structural registration file ' + strucRegMatrix + '"')
                os.system('echo "Skipping matrix concatenation"')


        #run job on condor?
        if not options.SUBMIT and not options.DOCKER:
            if refImage and 'out_matrix_base' in refImageParams.keys() and strucRegMatrix:
                st.feat_full_firstlevel(st.creds.dataDir, st.subject.id, st.subject.sesNum, featDesignDir, featOutputDir, featInput[boldTask]['design_basename'], progress=options.progress, reference=refImageFile, step2_design=featInput[boldTask]['step2_design_basename'], struc_reg_matrix=strucRegMatrix)
            else:
                st.feat_full_firstlevel(st.creds.dataDir, st.subject.id, st.subject.sesNum, featDesignDir, featOutputDir, featInput[boldTask]['design_basename'], progress=options.progress)
        else:
            base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_feat_full_firstlevel')
            if not os.path.isdir(base):
                os.makedirs(base)
            submit = os.path.join(base, f"feat_sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.submit")
            error = os.path.join(base, f"feat_sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.error")
            output = os.path.join(base, f"feat_sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.output")
            log = os.path.join(base, f"feat_sub-{st.subject.id}_ses-{st.subject.sesNum}_{now}.log")
            dagman = Dagman(name=f"{options.PROJECT}_feat_sub-{st.subject.id}_ses-{st.subject.sesNum}", submit=submit)

            if options.SUBMIT:
                job_feat = st.condor.create_python_condor_job('feat_full_firstlevel',
                                                                'run_docker.sh',#'feat_full_firstlevel.py',
                                                                st.creds.machineNames,
                                                                submit,
                                                                error,
                                                                output,
                                                                log,
                                                                dagman,
                                                                request_cpus=2,
                                                                request_memory=10000)
            else:
                job_feat = st.condor.create_python_condor_job('feat_full_firstlevel',
                                                            'feat_full_firstlevel.py',
                                                            st.creds.machineNames,
                                                            submit,
                                                            error,
                                                            output,
                                                            log,
                                                            dagman,
                                                            docker=True,
                                                            docker_image='wsuconnect/neuro:docker',
                                                            docker_mount_if=st.creds.dockerMountIf,
                                                            request_cpus=2,
                                                            request_memory='10g')
                # job_feat = st.condor.create_python_condor_job('feat_full_firstlevel',
                #                                         'run_docker.sh',
                #                                         st.creds.machineNames,
                #                                         submit,
                #                                         error,
                #                                         output,
                #                                         log,
                #                                         dagman,
                #                                         request_cpus=8,
                #                                         request_memory=20000)
                # job_rm = st.condor.create_bin_condor_job('remove_run_file',
                #                                              'rm',#'feat_full_firstlevel.py',
                #                                              st.creds.machineNames,
                #                                              submit,
                #                                              error,
                #                                              output,
                #                                              log,
                #                                              dagman)
                
                
            # create argument string for flirt.pys
            # runFile = f"/resshare/tmp/{str(uuid.uuid4())}.sh"
            # argStr = ' '.join(["run --rm",
            #                     f"-m 10000M",
            #                     f"--cpus=2",
            #                     f"-v /resshare:/resshare:ro",
            #                     f"-v {os.path.join(st.creds.dataDir,'code')}:{os.path.join(st.creds.dataDir,'code')}:rw",
            #                     f"-v {os.path.join(st.creds.dataDir,'rawdata')}:{os.path.join(st.creds.dataDir,'rawdata')}:ro",
            #                     f"-v {os.path.join(st.creds.dataDir,'derivatives')}:{os.path.join(st.creds.dataDir,'derivatives')}:rw",
            #                     "wsuconnect/neuro:docker"
            #                     # runFile#,
            #                     # "/resshare/wsuconnect/support_tools/feat_full_firstlevel.py "
            #                 ])

            #create argument string
            # argStr = ' '.join(['/bin/bash -c ". /opt/fsl-6.0.7/etc/fslconf/fsl.sh &&',
            argStr = ' '.join(['--datadir',st.creds.dataDir,
                               '--subname',st.subject.id,
                               '--sesnum',st.subject.sesNum,
                               '--feat-design-dir',featDesignDir,
                               '--feat-output-dir',featOutputDir,
                               '--design-basename',featInput[boldTask]['design_basename'] 
            ])
            if refImage:
                argStr += ' --reference ' + refImageFile
            if options.progress:
                argStr += ' --progress'
            if 'step2_design_basename' in featInput[boldTask].keys():
                argStr += ' --step2-design-basename ' + featInput[boldTask]['step2_design_basename']
            if strucRegMatrix:
                argStr += ' --struc-reg-matrix ' + strucRegMatrix
            # argStr += '"'
            # with open(runFile,'w') as f2:
            #     f2.writelines(argStr)
            # os.chmod(runFile,777)
            

            #add arguments to condor job
            job_feat.add_arg(argStr)# + ' > ' + os.path.join(creds.s3_dir,s3_outLog))
            # job_rm.add_arg(runFile)
            print('\tAdded job for feat full firstlevel analysis for file:  ' + f)
            print('\tOutput Directory:  ' + featOutputDir)
            featFlag = True


            dagman.build_submit()


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
    if options.SUBMIT or options.DOCKER:
        #get some precursors
        # now = datetime.datetime.today().strftime('%Y%m%d_%H%M')
        # base = os.path.join(st.creds.dataDir,'code','processing_logs','connect_feat_full_firstlevel')
        # if not os.path.isdir(base):
        #     os.makedirs(base)

        # #output files
        # submit = os.path.join(base,'feat_full_firstlevel_' + now + '.submit')
        # error = os.path.join(base,'feat_full_firstlevel_' + now + '.error')
        # output = os.path.join(base,'feat_full_firstlevel_' + now + '.output')
        # log = os.path.join(base,'feat_full_firstlevel_' + now + '.log')
        # dagman = Dagman(name=options.PROJECT + '-feat_full_firstlevel', submit=submit)


        #perform struc 2 standard registration
        modality_process(options)#,submit=submit,error=error,output=output,log=log,dagman=dagman)

    else:
        modality_process(options)

    

