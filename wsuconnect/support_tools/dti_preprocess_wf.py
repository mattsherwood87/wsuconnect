#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 python venv environment

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 June 2023
#
# Modified on 28 August 2025 - added nipype workflows
import sys
import argparse
import os
from nipype.interfaces import fsl
from nipype.interfaces.base import TraitedSpec, File
from pathlib import Path


#append path if necessary
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-3]).resolve()
if not str(REALPATH) in sys.path:
    sys.path.append(REALPATH)


VERSION = '1.0.0'
DATE = '23 June 2023'



FSLDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]

#setup cli arguments
parser = argparse.ArgumentParser('dti_preprocess.py: preprocess all DTI rawdata according to the FSL eddy pipeline')
parser.add_argument('IN_FILE',help='Input DTI file')
parser.add_argument('DATA_DIR',help="fullpath to the Project's data directory (see 'dataDir' key in credentials JSON file)")
parser.add_argument('DTI_PARAMS',help='fullpath to the DTI JSON control JSON file')
parser.add_argument('--overwrite',action='store_true',dest='OVERWRITE',default=False,help='overwrite existing files')
parser.add_argument('--progress',action='store_true',dest='progress',default=False,help='verbose mode')


# def add_sidecar(in_file: str | list, source_file: str, roi_params: dict=None, skull: str='false', spatial_ref: str='orig'):
#     """_summary_

#     Args:
#         in_file (str | list): _description_
#         source_file (str): _description_
#         roi_params (dict, optional): _description_. Defaults to None.
#         skull (str, optional): _description_. Defaults to 'false'.
#         spatial_ref (str, optional): _description_. Defaults to 'orig'.

#     Returns:
#         _type_: _description_
#     """

#     #write JSON sidecar file
#     d = {}
#     d['Sources'] = source_file
#     if roi_params:
#         d['FslRoiParameters'] = roi_params
#     d['SpatialReference'] = spatial_ref
#     d['SkullStripped'] = skull
#     with open(in_file.split('.')[0] + '.json', 'w') as fp:
#         json.dump(d, fp, indent=4) 

#     out_file = in_file.split('.')[0] + '.json'
#     return out_file


def merge(roi_file: str, sbref_file: str, out_file: str):
    """_summary_

    Args:
        roi_file (str): _description_
        sbref_file (str): _description_
        out_file (str): _description_
    """
    from nipype.interfaces import fsl
    fslmerge = fsl.Merge(in_files=[roi_file, sbref_file], dimension='t', merged_file=out_file)
    fslmerge.run()

    return out_file


def get_basename(in_corrected: str):
    """_summary_

    Args:
        in_corrected (str): _description_

    Returns:
        _type_: _description_
    """
    # strip .nii.gz → gives "eddy_corrected"
    out_base = in_corrected.split('.nii')[0]
    out_qc = out_base + '.qc'
    return out_base, out_qc


def add_extension(in_base: str, ext: str):
    """_summary_

    Args:
        in_base (str): _description_
        ext (str): _description_

    Returns:
        _type_: _description_
    """
    # strip .nii.gz → gives "eddy_corrected"
    out_file = in_base + ext
    return out_file



#FIX nipype FSL Eddy - out_parameter is falsely catagorized as must exist but is an output
class EddyOutputSpecPatched(TraitedSpec):
    from nipype.interfaces.base import TraitedSpec, File
    out_cnr_maps = File(desc="corrected output image")
    out_corrected = File(desc="corrected output image")
    out_movement_rms = File(desc="movement RMS file")
    out_movement_over_time = File(desc="corrected output image")
    out_outlier_free = File(desc="corrected output image")
    out_outlier_map = File(desc="corrected output image")
    out_outlier_n_stdev_map = File(desc="shell MD file")
    out_outlier_n_sqr_stdev_map = File(desc="corrected output image")
    out_outlier_report = File(desc="outlier report file")
    out_parameter = File(desc="eddy parameter file")  # no exists=True
    out_residuals = File(desc="corrected output image")
    out_restricted_movement_rms = File(desc="restricted movement RMS file")
    out_rotated_bvecs = File(desc="corrected output image")
    out_shell_alignment_parameters = File(desc="shell alignment parameters file")
    out_shell_md = File(desc="shell MD file")
    out_shell_pe = File(desc="shell PE file")
    out_shell_pe_translation_parameters = File(desc="corrected output image")

# Subclass Eddy with new output spec
class EddyPatched(fsl.Eddy):
    output_spec = EddyOutputSpecPatched


#FIX nipype FSL DTIFIT - out_parameter is falsely catagorized as must exist but is an output
class DTIFitOutputSpecPatched(TraitedSpec):
    FA = File(desc="fractional anisotropy.")
    L1 = File(desc="1st eigenvalue.")
    L2 = File(desc="2nd eigenvalue.")
    L3 = File(desc="3rd eigenvalue.")
    MD = File(desc="mean diffusivity.")
    MO = File(desc="mode of anisotropy")
    S0 = File(desc="raw T2 signal with no diffusion weighting.")
    V1 = File(desc="1st eigenvector")
    V2 = File(desc="2nd eigenvector")
    V3 = File(desc="3rd eigenvector")
    sse = File(desc="summed square error")
    tensor = File(desc="4D tensor volume")

# Subclass Eddy with new output spec
class DTIFitPatched(fsl.DTIFit):
    output_spec = DTIFitOutputSpecPatched


# ******************* s3 bucket check ********************
def dti_preprocess(IN_FILE: str, DATA_DIR: str, DTI_PARAMS: str, overwrite: bool=False, progress: bool=False):
    """
    This function performs FSL-based DTI preprocessing according to the FDT DTI pipeline (https://open.win.ox.ac.uk/pages/fslcourse/practicals/fdt1/index.html) prior to FLIRT/FNIRT and TBSS. 

    :param IN_FILE: fullpath to a DTI rawdata NIfTI file
    :type IN_FILE: str

    :param DATA_DIR: fullpath to the project's data directory (project's 'dataDir' credential)
    :type DATA_DIR: str

    :param DTI_PARAMS: fullpath to project's 2D ASL FLIRT parameter file
    :type DTI_PARAMS: str

    :param overwrite: overwrite existing files, defaults to False
    :type overwrite: bool, optional

    :param progress: verbose mode, defaults to False
    :type progress: bool, optional

    :raises FileNotFoundError: FLIRT_PARAMS file not found on disk

    :raises Exception: general error encountered during execution
    """
    import os
    import json
    import nipype.pipeline.engine as pe
    from nipype.interfaces.utility import Function
    from glob import glob as glob
    import datetime
    import shutil
    import traceback
    from wsuconnect import support_tools as st
    
    WF = pe.Workflow(name='connect_dti_preprocess')

    try:
        now = datetime.datetime.now()

        if progress:
            print('\n\ndti_preprocess.py version ' + VERSION + ' dated ' + DATE + '\n')
            print('running @ ' + now.strftime("%m-%d-%Y %H:%M:%S") + '\n')
            print('Reading JSON Files')

        try:
            with open(DTI_PARAMS) as j:
                dtiFullParams = json.load(j)

                # Organize parameter inputs
                #additional processing options

                #get main image parameters
                if 'main_image_params' in dtiFullParams:
                    mainParams = dtiFullParams.pop('main_image_params')
                    
                #get main eddy parameters
                if 'eddy_params' in dtiFullParams:
                    eddyParams = dtiFullParams.pop('eddy_params')
                    
                #get main eddy parameters
                if 'dtifit_params' in dtiFullParams:
                    dtifitParams = dtiFullParams.pop('dtifit_params')

        except FileNotFoundError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = exc_tb.tb_frame.f_code.co_filename
            lineno = exc_tb.tb_lineno
            print(f"Exception occurred in file: {filename}, line: {lineno}")
            print(f"\tException type: {exc_type.__name__}")
            print(f"\tException message: {e}")
            traceback.print_exc()
            return


        #check if file exists on local disk
        mainFile = IN_FILE
        if progress:
            print('Main Image: ' + mainFile)
        if not os.path.isfile(mainFile):
            if progress:
                print('\tERROR: Main Image File Not Found. Skipping')
            return
        elif progress:
            print('\tMain Image File Found: ' + mainFile)
        
        # create file inputs and outputs
        mainFileDir = os.path.dirname(mainFile)
        st.subject.get_id(mainFileDir)
        mainBetOutputDir = os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dwi')#create base path and filename for move
        mainTopupOutputDir = os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dwi')#create base path and filename for move
        mainEddyOutputDir = os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dwi')#create base path and filename for move
        mainDtifitOutputDir = os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dwi')#create base path and filename for move

        #make output directory structure if it does not exist
        if not os.path.isdir(mainBetOutputDir):
            os.makedirs(mainBetOutputDir)

        
        shutil.copyfile(eddyParams['in_acqp'],os.path.join(mainEddyOutputDir,os.path.basename(eddyParams['in_acqp'])))
        shutil.copyfile(eddyParams['in_index'],os.path.join(mainEddyOutputDir,os.path.basename(eddyParams['in_index'])))
        shutil.copyfile(eddyParams['slice_order'],os.path.join(mainEddyOutputDir,os.path.basename(eddyParams['slice_order'])))


        mainBidsLabels = st.bids.get_bids_labels(mainFile)
        outputFileList = []

        #********************************************************
        # STEP 1: FSLROI - extract first B0 image from Main Image
        #********************************************************
        vols = 0
        roi_mainBidsLabels = mainBidsLabels.copy()
        roi_mainBidsLabels['process'] = 'fslroi'
        roi_mainBidsLabels['description'] = 'vol-' + str(vols)
        outMainVolFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**roi_mainBidsLabels))
        
        n_fslroi = pe.Node(interface=fsl.ExtractROI(), name='fslroi')
        n_fslroi.label = 'Extract AP B0 image'
        n_fslroi.inputs.in_file = mainFile
        n_fslroi.inputs.roi_file = outMainVolFile
        n_fslroi.inputs.t_min = vols
        n_fslroi.inputs.t_size = 1
        WF.add_nodes([n_fslroi])



        #********************************************************
        # STEP 2: FSLMERGE - merge first B0 Image (A->P) with sbref image (P->A)
        #********************************************************
        #find sbref
        sbrefFile = glob(os.path.join(mainFileDir,'*sbref.nii.gz'))
        if len(sbrefFile) == 1:
            sbrefFile = sbrefFile[0]
            if progress:
                print('SBREF Image File Found: ' + sbrefFile)
                print('\tContinue processing...')
        else:
            print('WARNING: sbref image ' + os.path.join(os.path.dirname(mainFileDir),'*sbref.nii.gz') + ' not found... skipping')
            return
                
        merge_mainBidsLabels = mainBidsLabels.copy()
        merge_mainBidsLabels['process'] = 'fslmerge'
        merge_mainBidsLabels['description'] = 'AP-PA'
        outMergeFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**merge_mainBidsLabels))

        #Merge Volumes
        n_merge = pe.Node(interface=Function(input_names=["roi_file","sbref_file","out_file"],
                                                    output_names=["out_file"],
                                                    function=merge),
                                name='fslmerge')
        n_merge.label = 'merge PA and AP B0 images'
        n_merge.inputs.sbref_file = sbrefFile
        n_merge.inputs.out_file = outMergeFile
        WF.connect([(n_fslroi,n_merge,[('roi_file','roi_file')])])  

        
        #********************************************************
        # STEP 3: FSL TOPUP - bias field correction
        #********************************************************
        # formulate output
        tu_corr_mainBidsLabels = mainBidsLabels.copy()
        tu_corr_mainBidsLabels['process'] = 'topup'
        tu_corr_mainBidsLabels['description'] = 'iout'
        tu_corr_mainBidsLabels['extension'] = None
        outCorrFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**tu_corr_mainBidsLabels))
        tu_base_mainBidsLabels = mainBidsLabels.copy()
        tu_base_mainBidsLabels['process'] = 'topup'
        tu_base_mainBidsLabels['description'] = 'B1'
        tu_base_mainBidsLabels['extension'] = None
        outBaseFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**tu_base_mainBidsLabels))
        tu_field_mainBidsLabels = mainBidsLabels.copy()
        tu_field_mainBidsLabels['process'] = 'topup'
        tu_field_mainBidsLabels['description'] = 'fout'
        tu_field_mainBidsLabels['extension'] = None
        outFieldFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**tu_field_mainBidsLabels))

        # create topup object
        #first copy acqp input to local eddy output directory
        # shutil.copyfile(eddyParams['acqp'],os.path.join(mainEddyOutputDir,os.path.basename(eddyParams['acqp'])))
        eddyParams['in_acqp'] = os.path.join(mainEddyOutputDir,os.path.basename(eddyParams['in_acqp']))
        # topup = fsl.TOPUP(in_file=outMergeFile,config=dtiFullParams['topup_config'],encoding_file=eddyParams['acqp'],out_base=outBaseFile,out_corrected=outCorrFile,out_field=outFieldFile,out_logfile=os.path.join(mainTopupOutputDir,'topup.log'))


        n_topup = pe.Node(interface=fsl.TOPUP(config=dtiFullParams['topup_config'],encoding_file=eddyParams['in_acqp'],out_base=outBaseFile,out_corrected=outCorrFile,out_field=outFieldFile,out_logfile=os.path.join(mainTopupOutputDir,'topup.log')), 
                          name="topup")
        n_topup.label = 'estimate susceptibility-induced field'
        WF.connect([(n_merge,n_topup,[("out_file","in_file")])])


        #********************************************************
        # STEP 4: FSL BET - extract brain/produce brain mask
        #********************************************************
        #average topup iout
        tmean_mainBidsLabels = mainBidsLabels.copy()
        tmean_mainBidsLabels['process'] = 'topup'
        tmean_mainBidsLabels['description'] = 'iout-tmean'
        tmean_mainBidsLabels['extension'] = None
        outTmeanFile = os.path.join(mainTopupOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**tmean_mainBidsLabels))

        # else: #run topup and produce JSON sidecar
        n_fslmaths = pe.Node(interface=fsl.maths.MeanImage(dimension='T', out_file=outTmeanFile), name="fslmaths")
        n_fslmaths.label = 'compute temporal mean of distortion-corrected data'

        n_addext = pe.Node(Function(input_names=['in_base','ext'], output_names=['out_file'],function=add_extension), name='add_extension')
        n_addext.inputs.ext = '.nii.gz'
        n_addext.label = 'add nifti extension'
        WF.connect([(n_topup,n_addext,[('out_corrected','in_base')])])
        WF.connect([(n_addext,n_fslmaths,[('out_file','in_file')])])

        #extract brain
        os.chdir(mainBetOutputDir)
        tmean_brain_mainBidsLabels = mainBidsLabels.copy()
        tmean_brain_mainBidsLabels['process'] = 'fslbet'
        tmean_brain_mainBidsLabels['description'] = 'iout-tmean-brain'
        tmean_brain_mainBidsLabels['extension'] = None
        outTmeanBrainFile = os.path.join(mainBetOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**tmean_brain_mainBidsLabels))    


        n_fslbet = pe.Node(interface=fsl.BET(frac=0.3,mask=True, out_file=outTmeanBrainFile), name='fslbet')
        n_fslbet.label = 'extract brain'

        n_addext2 = pe.Node(Function(input_names=['in_base','ext'], output_names=['out_file'],function=add_extension), name='add_extension2')
        n_addext2.inputs.ext = '.nii.gz'
        n_addext2.label = 'add nifti extension'
        WF.connect([(n_fslmaths,n_addext2,[('out_file','in_base')])])
        WF.connect([(n_addext2,n_fslbet,[('out_file','in_file')])])



        #********************************************************
        # STEP 5: FSL EDDY - Perform eddy current correction
        #********************************************************
        # Formulate output
        os.chdir(mainEddyOutputDir)
        eddy_mainBidsLabels = mainBidsLabels.copy()
        eddy_mainBidsLabels['process'] = 'eddy-gpu'
        eddy_mainBidsLabels['description'] = 'unwarped'
        eddy_mainBidsLabels['extension'] = None
        outEddyFile = os.path.join(mainEddyOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**eddy_mainBidsLabels)) 

        n_eddy = pe.Node(interface=EddyPatched(in_file=mainFile,
                                            in_bvec=mainFile.replace('.nii.gz','.bvec'),
                                            in_bval=mainFile.replace('.nii.gz','.bval'),
                                            out_base=outEddyFile,**eddyParams), 
                         name='eddy')
        n_eddy.label = 'perform eddy correction'
        WF.connect([(n_fslbet,n_eddy,[('mask_file','in_mask')])])
        WF.connect([(n_topup,n_eddy,[('out_fieldcoef','in_topup_fieldcoef'),('out_movpar','in_topup_movpar')])])

        n_eddyquad = pe.Node(interface=fsl.EddyQuad(idx_file=n_eddy.inputs.in_index,
                                                    bval_file=n_eddy.inputs.in_bval,
                                                    bvec_file=n_eddy.inputs.in_bvec,
                                                    param_file=n_eddy.inputs.in_acqp,
                                                    slice_spec=n_eddy.inputs.slice_order), 
                             name='eddy_quad')
        n_eddyquad.label = 'compute eddy QC'
        
        n_basename = pe.Node(Function(input_names=['in_corrected'], output_names=['out_base','out_qc'],function=get_basename), name='get_basename')
        n_basename.label = 'get basename of topup output'

        n_addext3 = pe.Node(Function(input_names=['in_base','ext'], output_names=['out_file'],function=add_extension), name='add_extension3')
        n_addext3.inputs.ext = '.nii.gz'
        n_addext3.label = 'add nifti extension'
        WF.connect([(n_topup,n_addext3,[('out_field','in_base')])])
        WF.connect([(n_fslbet,n_eddyquad,[('mask_file','mask_file')])])
        WF.connect([(n_addext3,n_eddyquad,[("out_file","field")])])
        WF.connect([(n_eddy,n_basename,[('out_corrected','in_corrected')])])
        WF.connect([(n_basename,n_eddyquad,[('out_base','base_name'),('out_qc','output_dir')])])
        


        #********************************************************
        # STEP 5: FSL DTIFIT - produce FA/MD/other DTI outputs
        #********************************************************
        #formulate output
        os.chdir(mainDtifitOutputDir)
        dtifit_mainBidsLabels = mainBidsLabels.copy()
        dtifit_mainBidsLabels['process'] = 'dtifit'
        eddy_mainBidsLabels['description'] = 'dti'
        dtifit_mainBidsLabels['extension'] = None
        outDtifitFile = os.path.join(mainDtifitOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**dtifit_mainBidsLabels)) 

        #create dtifit object
        n_dtifit = pe.Node(interface=DTIFitPatched(bvals=n_eddy.inputs.in_bval,
                                                bvecs=n_eddy.inputs.in_bvec,
                                                base_name=outDtifitFile),
                            name='dtifit')
        n_dtifit.label = 'fit diffusion tensor model'
        WF.connect([(n_fslbet,n_dtifit,[('mask_file','mask')])])
        WF.connect([(n_eddy,n_dtifit,[('out_corrected','dwi')])])

        
        # set workflow working directory
        WF.base_dir = mainBetOutputDir

        WF.write_graph(graph2use='flat')
        WF.write_graph(dotfilename=os.path.join(WF.base_dir,'dti_preprocess_workflow-graph.dot'), graph2use='colored', format='png', simple_form=True)
        WF.run()


    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        print(f"Exception occurred in file: {filename}, line: {lineno}")
        print(f"\tException type: {exc_type.__name__}")
        print(f"\tException message: {e}")
        traceback.print_exc()
        return



if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """

    options = parser.parse_args()
    argsDict = {}
    if options.OVERWRITE:
        argsDict['overwrite'] = options.OVERWRITE
    if options.progress:
        argsDict['progress'] = options.progress
    dti_preprocess(options.IN_FILE,options.DATA_DIR,options.DTI_PARAMS,**argsDict)

    


