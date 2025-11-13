#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 19 July 2023
#
# Modified on 17 May 2024 - slight tweak to change recon-all to autorecon1 when running stage2
VERSION = '1.0.1'
DATE = '17 May 2023'

import sys
import os
import argparse
from pathlib import Path

#append path if necessary
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-3]).resolve()
if not str(REALPATH) in sys.path:
    sys.path.append(REALPATH)



FSLDIR = None
FREESURFERDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]
if "FREESURFER_HOME" in os.environ:
    FREESURFERDIR = os.environ["FREESURFER_HOME"]




parser = argparse.ArgumentParser('fsreconall_stage1.py: perform recon-all - either all stages or autorecon1 if also running stage2')

parser.add_argument('IN_FILE', help=' fullpath to a NIfTI file')
parser.add_argument('DATA_DIR', help="fullpath to the project's data directory (project's 'dataDir' credential)")
parser.add_argument('RECONALL_PARAMS', help="fullpath to project's RECONALL parameter control file")
parser.add_argument('MAINRECONALLOUTPUTDIR', help='fullpath to the main reconall output directory')
parser.add_argument('--directive',action='store',dest='DIRECTIVE',default=None, help='freesurfer manual workflow directive')
parser.add_argument('--overwrite',action='store_true',dest='OVERWRITE',default=False, help='overwrite existing files')
parser.add_argument('--progress',action='store_true',dest='progress',default=False, help='verbose mode')


class InvalidJsonInput(Exception):
    "Raised when the input JSON control file does not contain the appropriate mandatory definitions"
    pass


def mask_to_nii(stage1_dir: str,in_file: str) -> str:
    """
    compute the number of volumes in a NIfTI image

    :param main_file: fullpath to a NIfTI image
    :type main_file: str

    :param FSLDIR: path to the location of the FSL installation
    :type FSLDIR: str

    :return: number of volumes in image main_file
    :rtype: int
    """    
    import os
    out_nii = os.path.join(stage1_dir,'mri','brainmask-native.nii.gz')
    convertCmd = 'mri_convert -it mgz -ot nii ' + in_file + ' ' + out_nii
    os.system(convertCmd)

    binCmd = 'fslmaths ' + out_nii + ' -bin ' + out_nii
    os.system(binCmd)
    return out_nii


# ******************* s3 bucket check ********************
def fsreconall_stage1(IN_FILE: str,DATA_DIR: str,RECONALL_PARAMS: str, MAINRECONALLOUTPUTDIR: str, overwrite: bool=False, progress: bool=False):
    """
    This function performs stage 1 of FreeSurfer reconall freesurfer_recon-all_input.json control file. 

    :param IN_FILE: fullpath to a NIfTI file
    :type IN_FILE: str
    
    :param DATA_DIR: fullpath to the project's data directory (project's 'dataDir' credential)
    :type DATA_DIR: str

    :param RECONALL_PARAMS: fullpath to project's FreeSurfer RECON-ALL parameter control file
    :type RECONALL_PARAMS: str

    :param MAINRECONALLOUTPUTDIR:fullpath to the desired FreeSurfer SUBJECTS_DIR
    :type MAINRECONALLOUTPUTDIR: str

    :param overwrite: flag to overwrite existing files, defaults to False
    :type overwrite: bool, optional

    :param progress: flag to display command line output providing additional details on the processing status, defaults to False
    :type progress: bool, optional

    :raises InvalidJsonInput: error encountered when the input JSON control file does not contain the appropriate mandatory definitions

    :raises OSError: OS error encountered during execution

    :raises Exception: general error encountered during execution
    """ 
    import json
    import pymeshlab
    from nipype.interfaces import freesurfer
    import nipype.pipeline.engine as pe
    from nipype.interfaces.utility import Function
    from glob import glob as glob
    import datetime
    from wsuconnect import support_tools as st

    outputFileList = []
    workFlow = pe.Workflow(name='connect_fsreconall_stage1')

    try:
        now = datetime.datetime.now()

        if progress:
            print('\n\nfsreconall_preprocess.py version ' + VERSION + ' dated ' + DATE + '\n')
            print('running @ ' + now.strftime("%m-%d-%Y %H:%M:%S") + '\n')
            print('Reading JSON Control File')

        #read parameter file
        with open(RECONALL_PARAMS) as j:
            reconallFullParams = json.load(j)

            # Organize parameter inputs
                
            #get main FLIRT parameters
            if 'reconall_params' in reconallFullParams:
                reconallParams = reconallFullParams.pop('reconall_params')
            else:
                raise InvalidJsonInput

            if 'main_image_params' in reconallFullParams:
                mainParams = reconallFullParams.pop('main_image_params')
            else:
                raise InvalidJsonInput


        #check if file exists on local disk
        mainFile = IN_FILE
        if not os.path.isfile(mainFile):
            if progress:
                print('ERROR: Main Image File Not Found')
            raise OSError
        elif progress:
            print('Main Image File Found: ' + mainFile)
        
        # create file inputs and outputs
        mainFileDir = os.path.dirname(mainFile)
        st.subject.get_id(mainFileDir)
        # mainReconallOutputDir = os.path.join(DATA_DIR,'derivatives','recon-all-new')#create base path and filename for move

        if not os.path.isdir(MAINRECONALLOUTPUTDIR):
            os.makedirs(MAINRECONALLOUTPUTDIR)



        # move subjects dir to reconall output directory
        # os.system('export SUBJECTS_DIR=' + mainReconallOutputDir)
        # if progress:
        #     print('SUBJECTS_DIR redirected to output directory: ' + mainReconallOutputDir)
            
        newRegexStr = reconallFullParams['brainmask_regex'].split('.')
        in_brainmaskFile = glob(os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'bet','anat','*' + newRegexStr[0] + '_manual.' + '.'.join(newRegexStr[1:]) + '*'))
        if len(in_brainmaskFile) == 1:
            MAINRECONALLOUTPUTDIR = MAINRECONALLOUTPUTDIR + '_manual'

        #setup and freesurfer
        # fsrecon = freesurfer.ReconAll(**reconallParams)
        n_fsrecon1 = pe.Node(interface=freesurfer.ReconAll(**reconallParams), name='stage1 reconall')
        n_fsrecon1.inputs.subject_id = 'sub-' + st.subject.id + '_ses-' + st.subject.sesNum
        n_fsrecon1.inputs.subjects_dir = MAINRECONALLOUTPUTDIR
        n_fsrecon1.inputs.T1_files = mainFile
        stage1_dir = os.path.join(MAINRECONALLOUTPUTDIR, 'sub-' + st.subject.id + '_ses-' + st.subject.sesNum)
        b_run = False
        # if directive:
        #     n_fsrecon.inputs.directive = directive
        skip = False
        if os.path.isdir(stage1_dir):
            if overwrite:
                if progress:
                    print('Output directory exists, removing and running freesurfer recon-all')
                os.system('rm -rf ' + stage1_dir)
                # n_fsrecon.run()
                b_run = True
            else:
                if progress:
                    print('WARNING: Output folder exists, overwrite was not specified skipping freesurfer recon-all')
        else:
            if progress:
                print('Output folder does not exist, running freesurfer recon-all')
            # n_fsrecon.run()
            b_run = True

        if 'directive' in reconallParams:
            if reconallParams['directive'] == 'all':
                workFlow.add_nodes([n_fsrecon1])
        
        else:            

            # ****************************************************** STAGE 2 ***********************************************************
            #find associated brainmask image 
            if 'brainmask_regex' in reconallFullParams.keys():
                newRegexStr = reconallFullParams['brainmask_regex'].split('.')
                in_brainmaskFile = glob(os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'anat','*' + newRegexStr[0] + '_manual.' + '.'.join(newRegexStr[1:]) + '*'))
                if len(in_brainmaskFile) == 1:
                    if progress:
                        print('Found input brainmask, continuing with analysis')

                else:
                    in_brainmaskFile = glob(os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'anat','*' + reconallFullParams['brainmask_regex'] + '*'))
                    if len(in_brainmaskFile) == 1:
                        if progress:
                            print('Found input brainmask, continuing with analysis')

                    else:
                        print('ERROR: did not find associated brainmask in ' + os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'anat','*' + reconallFullParams['brainmask_regex'] + '*'))
                        return

            #move output FS brainmask to orig space and convert to nifti
            if not os.path.isfile(os.path.join(stage1_dir,'mri','T1w.a2009s.segstats.dat')) or overwrite:
                if progress:
                    print('Converting freesurfer brainmask to orig space and NIfTI format')

                vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(stage1_dir,'mri','brainmask.mgz') + ' --targ ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(stage1_dir,'mri','brainmask-native.mgz') + ' --no-save-reg'
                os.system(vol2volCmd)
                n_v2v = pe.Node(interface=freesurfer.ApplyVolTransform(), name='stage1 brainmask2native')
                n_v2v.inputs.transformed_file = os.path.join(stage1_dir,'mri','brainmask-native.mgz')
                n_v2v.inputs.args = '--no-save-reg'
                n_v2v.inputs.reg_header = True
                workFlow.connect([(n_fsrecon1,n_v2v),[('brainmask','source_file'),('rawavg','target_file')]])


                
                n_toNii = pe.Node(interface=Function(input_names=["stage1_dir","in_file"],
                                                     output_names=["out_nii"],
                                                     function=mask_to_nii),
                                    name='brainmask native to nii')
                n_toNii.inputs.stage1_dir = stage1_dir
                n_toNii.inputs.out_file = os.path.join(stage1_dir,'mri','brainmask-native.nii.gz')
                workFlow.connect([n_v2v,n_toNii],[('transformed_file','in_file')])


            #copy brainmask
            if 'brainmask_regex' in reconallFullParams.keys():
                maskCmd = 'cp ' + in_brainmaskFile[0] + ' ' + os.path.join(stage1_dir,'mri','brainmask-new-native_mask.nii.gz')
                os.system(maskCmd)


                #convert back to FS space
                vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(stage1_dir,'mri','brainmask-new-native_mask.nii.gz') + ' --targ ' + os.path.join(stage1_dir,'mri','T1.mgz') + ' --regheader --o ' + os.path.join(stage1_dir,'mri','brainmask.mgz') + ' --no-save-reg'
                os.system(vol2volCmd)

                #update binary value to align with original
                binCmd = 'mri_binarize --i ' + os.path.join(stage1_dir,'mri','brainmask.mgz') + ' --o ' + os.path.join(stage1_dir,'mri','brainmask.mgz') + ' --binval 999 --min 1'
                os.system(binCmd)




            n_fsrecon2 = pe.Node(interface=freesurfer.ReconAll(**reconallParams), name='stage2_reconall')
            n_fsrecon2.inputs.subject_id = 'sub-' + st.subject.id + '_ses-' + st.subject.sesNum
            # n_fsrecon2.inputs.subjects_dir = stage1_dir
            n_fsrecon2.inputs.directive=['autorecon2','autorecon3']
            workFlow.connect([n_fsrecon1,n_fsrecon2],[('subjects_dir','subjects_dir')])



            #create output STL
            convertCmd = 'mris_convert ' + os.path.join(stage1_dir,'surf','rh.pial') + ' ' + os.path.join(stage1_dir,'surf','rh.stl') 
            os.system(convertCmd)
            convertCmd = 'mris_convert ' + os.path.join(stage1_dir,'surf','lh.pial') + ' ' + os.path.join(stage1_dir,'surf','lh.stl') 
            os.system(convertCmd)

            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(os.path.join(stage1_dir,'surf','lh.stl'))
            ms.load_new_mesh(os.path.join(stage1_dir,'surf','rh.stl'))
            ms.generate_by_merging_visible_meshes()
            ms.meshing_decimation_quadric_edge_collapse()
            ms.apply_coord_hc_laplacian_smoothing()
            ms.save_current_mesh(os.path.join(stage1_dir,'surf','brain_mesh.stl'),save_face_color=False)


            #compute segstats
            aparc2asegCmd = 'mri_aparc2aseg --s sub-' + st.subject.id + ' --a2009s'
            os.system(aparc2asegCmd)

            #convert revised aparc+aseg to native space
            #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(stage1_dir,'mri','aparc+aseg.mgz') + ' --targ ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(stage1_dir,'mri','aparc+aseg-native.mgz') + ' --no-save-reg'
            vol2volCmd = 'mri_label2vol --seg ' + os.path.join(stage1_dir,'mri','aparc+aseg.mgz') + ' --temp ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --regheader ' + os.path.join(stage1_dir,'mri','aparc+aseg.mgz') + '--o ' + os.path.join(stage1_dir,'mri','aparc+aseg-native.mgz')
            os.system(vol2volCmd)

            #convert revised aparc+aseg to native space
            #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(stage1_dir,'mri','aparc.a2009s+aseg.mgz') + ' --targ ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(stage1_dir,'mri','aparc.a2009s+aseg-native.mgz') + ' --no-save-reg'
            vol2volCmd = 'mri_label2vol --seg ' + os.path.join(stage1_dir,'mri','aparc.a2009s+aseg.mgz') + ' --temp ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --regheader ' + os.path.join(stage1_dir,'mri','aparc.a2009s+aseg.mgz') + '--o ' + os.path.join(stage1_dir,'mri','aparc+aseg-native.mgz')
            os.system(vol2volCmd)

            #compute cortical thickness measurements
            segstatsCmd = 'mri_segstats --subject sub-' + st.subject.id + '_ses-' + st.subject.sesNum + ' --seg ' + os.path.join(stage1_dir,'mri','aparc+aseg-native.mgz') + ' --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --sum ' + os.path.join(stage1_dir,'mri','T1w.segstats.dat') + ' --sd ' + os.path.dirname(stage1_dir)
            os.system(segstatsCmd)

            #compute cortical thickness measurements
            segstatsCmd = 'mri_segstats --subject sub-' + st.subject.id + '_ses-' + st.subject.sesNum + ' --seg ' + os.path.join(stage1_dir,'mri','aparc.a2009s+aseg-native.mgz') + ' --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in ' + os.path.join(stage1_dir,'mri','rawavg.mgz') + ' --sum ' + os.path.join(stage1_dir,'mri','T1w.a2009s.segstats.dat') + ' --sd ' + os.path.dirname(stage1_dir)
            os.system(segstatsCmd)



        if b_run:
            # set workflow working directory
            workFlow.base_dir = stage1_dir
            workFlow.run()

            workFlow.write_graph(graph2use='flat')
            workFlow.write_graph(dotfilename='fsreconall_stage1_graph.dot', graph2use='hierarchical', format='png', simple_form=True)

        # #run stage 2 if all inputs exist
        # if not os.path.isfile(os.path.join(stage1_dir,'mri','T1w.segstats.dat')) or overwrite and not skip:  
        #     brainMask = glob(os.path.join(DATA_DIR,'derivatives','sub-' + subName,'ses-' + st.subject.sesNum,'bet','anat','*' + reconallFullParams['brainmask_regex'] + '*')) 
        #     if len(brainMask) == 1:
        #         if progress:
        #             print('Initiating Stage 2')
                
        #         fsreconall_stage2(stage1_dir, DATA_DIR, RECONALL_PARAMS, progress=progress, overwrite=overwrite)
        #     else:
        #         fsrecon.inputs.directive = 'autorecon1'
        #         fsrecon.run()
        #         if progress:
        #             print('WARNING: skipping stage 2, either none or more than 1 brainmask file found in ' + os.path.join(DATA_DIR,'derivatives','sub-' + subName,'ses-' + sesNum,'bet','anat','*' + reconallFullParams['brainmask_regex'] + '*'))
        # else:
        #     fsrecon.run()
        #     if progress:
        #         print('WARNING: skipping stage 2 - output exists and overwrite was not specified')

    except OSError as e:
        print("Error Message: {0}".format(e))
        return
    except InvalidJsonInput:
        print("Invalid JSON Input: {0}".format(e))
        return
    except Exception as e:
        print("Error Message: {0}".format(e))
        return
        

if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """
    
    options = parser.parse_args()
    argsDict = {}
    if options.DIRECTIVE:
        argsDict['directive'] = options.DIRECTIVE
    if options.OVERWRITE:
        argsDict['overwrite'] = options.OVERWRITE
    if options.progress:
        argsDict['progress'] = options.progress
    fsreconall_stage1(options.IN_FILE,options.DATA_DIR,options.RECONALL_PARAMS,options.MAINRECONALLOUTPUTDIR,**argsDict)

    


