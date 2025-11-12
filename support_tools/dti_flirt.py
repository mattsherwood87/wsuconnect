#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 26 July 2023
#
# Modified on 2 September 2025 - adapt for fmriprep output 
VERSION = '2.0.0'
DATE = '2 September 2025'

import sys
import os
import argparse
from pathlib import Path

#append path if necessary
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-3]).resolve()
if not str(REALPATH) in sys.path:
    sys.path.append(REALPATH)


FSLDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]

#setup cli arguments
parser = argparse.ArgumentParser('asl_flirt.py: perform FLIRT registration between 2D ASL and structural/standard brain images')
parser.add_argument('IN_FILE', help=' fullpath to a NIfTI file')
parser.add_argument('DATA_DIR', help="fullpath to the project's data directory (project's 'dataDir' credential)")
parser.add_argument('FLIRT_PARAMS', help="fullpath to project's FLIRT parameter file")
parser.add_argument('--overwrite',action='store_true',dest='OVERWRITE',default=False, help='flag to overwrite existing files')
parser.add_argument('--progress',action='store_true',dest='progress',default=False, help='flag to display command line output providing additional details on the processing status')


#function to append png
def pngappend(in_file: str, ref_file: str, out_file: str):
    """_summary_

    Args:
        in_file (str): _description_
        ref_file (str): _description_
        out_file (str): _description_

    Returns:
        _type_: _description_
    """
    from wsuconnect import support_tools as st
    out_file = out_file.split('.')[0] + '.png'
    st.flirt_pngappend(in_file, ref_file, out_file)
    return out_file


def c3d_affine_tool(source_file: str, reference_file: str, transform_file: str, itk_transform: str, fsl2ras: bool):
    """_summary_

    Args:
        source_file (str): _description_
        reference_file (str): _description_
        transform_file (str): _description_
        itk_transform (str): _description_
        fsl2ras (bool): _description_

    Returns:
        _type_: _description_
    """
    from nipype.interfaces.c3 import C3dAffineTool  
    from nipype.interfaces.base import TraitedSpec, File
    from glob import glob as glob

    #FIX nipype ANTS ApplyTransforms - out_parameter is falsely catagorized as must exist but is an output
    class C3dAffineToolOutputSpecPatched(TraitedSpec):
        itk_transform = File(desc="ITK representation of input matrix.")

    # Subclass Eddy with new output spec
    class C3dAffineToolPatched(C3dAffineTool):
        output_spec = C3dAffineToolOutputSpecPatched

    itk_transform = itk_transform.replace('.mat','.txt')

    c3d = C3dAffineToolPatched()
    c3d.inputs.source_file = source_file
    c3d.inputs.reference_file = reference_file
    c3d.inputs.transform_file = transform_file
    c3d.inputs.itk_transform = itk_transform
    c3d.inputs.fsl2ras = fsl2ras


    return itk_transform


def applytransforms(input_image: str, reference_image: str, transform1: str, transform2: str, dimension: int, interpolation: str, print_out_composite_warp_file: bool, output_image: str):
    """_summary_

    Args:
        input_image (str): _description_
        reference_image (str): _description_
        transform1 (str): _description_
        transform2 (str): _description_
        dimension (int): _description_
        interpolation (str): _description_
        print_out_warp_file (bool): _description_
        output_image (str): _description_
    """
    transforms = [transform1, transform2]

    
    from nipype.interfaces.ants import ApplyTransforms
    at = ApplyTransforms()
    at.inputs.input_image = input_image
    at.inputs.reference_image = reference_image
    at.inputs.transforms =  transforms
    at.inputs.dimension = dimension
    at.inputs.interpolation = interpolation
    at.inputs.print_out_composite_warp_file = print_out_composite_warp_file
    at.inputs.output_image = output_image
    at.run()

    return output_image



# ******************* s3 bucket check ********************
def dti_flirt(IN_FILE: str, DATA_DIR: str, FLIRT_PARAMS: str, overwrite: bool=False, progress: bool=False):
    """
    This function performs FLIRT registration between IN_FILE and structural/standard brain images similar to flirt.py. Registration will be applied to all secondary images in the same directory as IN_FILE.

    :param IN_FILE: fullpath to a NIfTI file
    :type IN_FILE: str

    :param DATA_DIR: fullpath to the project's data directory (project's 'dataDir' credential)
    :type DATA_DIR: str

    :param FLIRT_PARAMS: fullpath to project's 2D ASL FLIRT parameter file
    :type FLIRT_PARAMS: str

    :param overwrite: OPTIONAL flag to overwrite existing files, defaults to False
    :type overwrite: bool

    :param progress: OPTIONAL flag to display command line output providing additional details on the processing status, defaults to False
    :type progress: bool

    :raises FileNotFoundError: FLIRT_PARAMS file not found on disk

    :raises Exception: general error encountered during execution
    """
    from wsuconnect import support_tools as st
    from nipype.interfaces import fsl
    import nipype.pipeline.engine as pe
    from nipype.interfaces.utility import Function
    import datetime
    import traceback
    import json
    from glob import glob as glob
    
    outputFileList = []
    stdImageFile = None
    refImageFile = None
    refImage = False

    WF = pe.Workflow(name='connect_dti_registration')

    try:
        now = datetime.datetime.now()

        struc_regexStr = None
        if progress:
            print('\n\nflirt.py version ' + VERSION + ' dated ' + DATE + '\n')
            print('running @ ' + now.strftime("%m-%d-%Y %H:%M:%S") + '\n')
            print('Reading JSON Files')

        try:
            with open(FLIRT_PARAMS) as j:
                flirtFullParams = json.load(j)

            #get main image parameters
            if 'main_image_params' in flirtFullParams:
                mainParams = flirtFullParams.pop('main_image_params')
                
            #get main FLIRT parameters
            if 'flirt_params' in flirtFullParams:
                flirtParams = flirtFullParams.pop('flirt_params')

            #(optional) get structural image parameters
            if 'reference_image_params' in flirtFullParams:
                refImageParams = flirtFullParams.pop('reference_image_params')
                refImage = True

            #(optional) get standard image parameters for additional matrix concatenation
            if 'standard_reference_params' in flirtFullParams:
                stdImageParams = flirtFullParams.pop('standard_reference_params')
                stdImage = True
                if 'type' in stdImageParams:
                    if stdImageParams['type'] == 'FSL':
                        stdImageFile = os.path.join(FSLDIR,'data','standard',stdImageParams['file'])
                    elif 'tpl' in stdImageParams['type']:
                        stdImageFile = os.path.join(REALPATH,'templateflow',stdImageParams['type'],stdImageParams['file'])
                    elif stdImageParams['type'] == 'file':
                        stdImageFile = stdImageParams['file']
                        if not os.path.isfile(stdImageFile) and progress:
                            print('WARNING: reference file specified in parameter file but the file cannot be located - ' + stdImageFile)
                            print('/tSkipping standard transformation and/or concatenation')
                            stdImage = False
                    else:
                        print('WARNING: standard reference type not supported')
                        print('/tSkipping standard transformation and/or concatenation')
                else:
                    print('WARNING: must specify type in standard_reference_params field')
                    print('/tSkipping standard transformation and/or concatenation')

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
        if not os.path.isfile(mainFile):
            if progress:
                print('ERROR: Main Image File Not Found')
            return
        elif progress:
            print('Main Image File Found: ' + mainFile)
        
        # create file inputs and outputs
        mainFileDir = os.path.dirname(mainFile)
        st.subject.get_id(mainFileDir)
        mainFlirtOutputDir = os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,mainParams['output_bids_location'])#create base path and filename for move
        if not os.path.isdir(mainFlirtOutputDir):
            os.makedirs(mainFlirtOutputDir)

        #look for accompanying structural data on disk in derivatives
        if refImage and not refImageParams['type'] == 'std':
            ref_regexStr = st.bids.get_bids_filename(**refImageParams['input_bids_labels'])
            # if refImageParams['input_bids_location'] == 'raw':
            #     refImageFile = glob(os.path.join(DATA_DIR,'rawdata','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'anat','*' + ref_regexStr + '*'))
            if refImageParams['input_bids_location'] == 'derivatives':
                refImageFile = glob(os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'anat','*' + ref_regexStr + '*'))
            else:
                print('ERROR: structural file "bids_location" not supported')
                print('/tCannot perform FLIRT... exiting')
                return

            if refImage:
                if len(refImageFile) > 0:
                    refImageFile = refImageFile[0]
                # elif refImageParams['input_bids_location'] == 'rawdata':
                #     print('ERROR: structural file ' + os.path.join(DATA_DIR,'rawdata','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'anat','*' + ref_regexStr + '*') + ' not found')
                #     print('/tCannot perform FLIRT... exiting')
                #     return
                elif refImageParams['input_bids_location'] == 'derivatives':
                    print('ERROR: structural file ' + os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'anat','*' + ref_regexStr) + ' not found')
                    print('/tCannot perform FLIRT... exiting')
                    return

            if progress and refImageFile:
                print('Reference Structural File Found: ' + refImageFile)

        elif stdImageFile:
            refImageFile = stdImageFile

        else:
            print('ERROR: standard reference file not found')
            print('/tCannot perform FLIRT... exiting')
            return
        

        mainBidsLabels = st.bids.get_bids_labels(mainFile)
        secBidsLabels = mainBidsLabels.copy()
        secFiles = glob(os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dtifit',mainParams['output_bids_location'],'*.nii.gz'))
        if not secFiles:
            print('WARNING: secondary image files not found in  ' + os.path.join(DATA_DIR,'derivatives','sub-' + st.subject.id,'ses-' + st.subject.sesNum,'dtifit',mainParams['output_bids_location'],'*.nii.gz'))
            print('\tSKIPPING application of transforms to secondary images')
            
        if progress and secFiles:
            print('Secondary Files Found')


        


        # **********************************
        # run FLIRT on Main Image Input
        # **********************************

        ###neeed to check if output exists?????
        if refImageFile:
            
            n_flt = pe.Node(interface=fsl.FLIRT(**flirtParams), name='FLIRT')

            # n_flt = fsl.FLIRT(**flirtParams)
            n_flt.inputs.in_file = mainFile
            n_flt.inputs.reference = refImageFile
            fltBidsLabels = mainBidsLabels.copy()
            
            if refImageParams['type'] == 'std':
                for k in stdImageParams['output_bids_labels'].keys():
                    fltBidsLabels[k] = stdImageParams['output_bids_labels'][k]
                if 'brain' in mainFile:
                    fltBidsLabels['description'] = 'brain'

            else:
                for k in refImageParams['output_bids_labels'].keys():
                    fltBidsLabels[k] = refImageParams['output_bids_labels'][k]
                if 'brain' in mainFile:
                    fltBidsLabels['description'] = 'brain'
            n_flt.inputs.out_file = os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**fltBidsLabels))
            if refImageParams['type'] == 'std':
                n_flt.inputs.out_matrix_file = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.mat')
            else:
                n_flt.inputs.out_matrix_file = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + refImageParams['out_matrix_base'] + '.mat')


            # if os.path.isfile(n_flt.inputs.out_matrix_file) and not overwrite:
            #     if progress:
            #         print('Skipping FLIRT: registration matrix file found: ' + flt.inputs.out_matrix_file)
                    
            # else:
            # flt.run()
            WF.add_nodes([n_flt])


            # invert registration matrix
            # ----------------------------------
            n_invt = pe.Node(interface=fsl.ConvertXFM(), name='ConvertXFM')
            invt = fsl.ConvertXFM()
            # invt.inputs.in_file = flt.inputs.out_matrix_file
            n_invt.inputs.invert_xfm = True
            if refImageParams['type'] == 'std':
                n_invt.inputs.out_file = os.path.join(mainFlirtOutputDir,stdImageParams['out_matrix_suffix'] + '2' + mainParams['out_matrix_base'] + '.mat')
            else:
                n_invt.inputs.out_file = os.path.join(mainFlirtOutputDir,refImageParams['out_matrix_base'] + '2' + mainParams['out_matrix_base'] + '.mat')


            # if not os.path.isfile(invt.inputs.out_file) or overwrite:
                # invt.run() 
            WF.connect([(n_flt,n_invt,[('out_matrix_file','in_file')])]) 

            
            if refImageParams['type'] == 'std':
                pngFile = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'])
            else:
                pngFile = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + refImageParams['out_matrix_base'])


            n_png1 = pe.Node(interface=Function(input_names=["in_file","ref_file","out_file"],
                                                output_names=["out_file"],
                                                function=pngappend),
                            name='create_png_dwi2anat')
            n_png1.inputs.out_file = pngFile
            n_png1.inputs.ref_file = n_flt.inputs.reference
            WF.connect([(n_flt,n_png1,[('out_file','in_file')])])
                
                # if not os.path.isfile(pngFile):
                #     st.flirt_pngappend(flt.inputs.out_file,flt.inputs.reference,pngFile)
                    # outputFileList.append(os.path.join(mainFlirtOutputDir,pngFile))

            
            # # apply registration to secondary image
            # # ----------------------------------
            # for secFile in secFiles:
            #     applyxfm = fsl.ApplyXFM()
            #     applyxfm.inputs.in_file = secFile
            #     applyxfm.inputs.reference = refImageFile
            #     applyxfm.inputs.apply_xfm = True
            #     applyBidsLabels = st.bids.get_bids_labels(secFile)
            #     applyBidsLabels = refImageParams['output_bids_labels'].copy()
            #     applyBidsLabels['suffix'] = 'dwi_' + st.bids.get_bids_labels(secFile)['suffix']
            #     applyxfm.inputs.out_file = os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
            #     applyxfm.inputs.in_matrix_file = flt.inputs.out_matrix_file


            #     if os.path.isfile(applyxfm.inputs.out_file) and not overwrite:
            #         if progress:
            #             print('Skipping APPLYXFM: output transformed file already exists: ' + applyxfm.inputs.out_file)
                        
            #     else:
            #         if progress:
            #             print('Applying transformation to secondary image to produce ' + applyxfm.inputs.out_file)
            #         applyxfm.run()
            #         # outputFileList.append(applyxfm.inputs.out_file)

            #         # # write JSON sidecar
            #         # d['Sources'] = [d['Sources'],
            #         #                 'bids:derivatives:' + applyxfm.inputs.in_matrix_file.split(DATA_DIR + os.sep)[1]]
            #         # with open(applyxfm.inputs.out_file.split('.')[0] + '.json', 'w') as fp:
            #         #     json.dump(d, fp, indent=4)  

            
            #         # if refImageParams['type'] == 'std':
            #         #     pngFile = os.path.join(mainFlirtOutputDir,secImageParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.png')
            #         # else:
            #         #     pngFile = os.path.join(mainFlirtOutputDir,secImageParams['out_matrix_base'] + '2' + refImageParams['out_matrix_base'] + '.png')

            #         # if not os.path.isfile(pngFile):
            #         #     flirt_pngappend(flt.inputs.out_file,flt.inputs.reference,pngFile)
            #         #     outputFileList.append(os.path.join(mainFlirtOutputDir,pngFile))                                                                                             



            # concatenate reference-to-standard to input-to-reference
            # ----------------------------------
            if not refImageParams['type'] == "std" and stdImageFile:
                # strucRegPath = os.path.join(os.path.dirname(mainFlirtOutputDir),'anat')
                # strucRegMatrix = os.path.join(strucRegPath,refImageParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.mat')
                # if not os.path.isfile(strucRegMatrix):
                #     print('Warning: cannot find structural registration file ' + strucRegMatrix)
                #     print('Skipping matrix concatenation')
                #     return

                # if progress:
                #     print('Structural to standard registration found: ' + strucRegMatrix)

                # #find concat input-to-reference with reference-to-standard
                # invt = fsl.ConvertXFM()
                # invt.inputs.in_file = flt.inputs.out_matrix_file
                # invt.inputs.in_file2 = strucRegMatrix
                # invt.inputs.concat_xfm = True
                # invt.inputs.out_file = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.mat')
                # if progress:
                #     print('Concatenating FLIRT transform with standard transform:')
                #     print('\tInput File: ' + invt.inputs.in_file)
                #     print('\tInput FIle 2: ' + invt.inputs.in_file2)
                #     print('\tOut File: ' + invt.inputs.out_file)


                # if not os.path.isfile(invt.inputs.out_file) or overwrite:
                #     invt.run()
                #     outputFileList.append(invt.inputs.out_file)
                #     if progress:
                #         print('\tSuccess!')

                # #find inverse
                # invt = fsl.ConvertXFM()
                # invt.inputs.in_file = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.mat')
                # invt.inputs.invert_xfm = True
                # invt.inputs.out_file = os.path.join(mainFlirtOutputDir,stdImageParams['out_matrix_suffix'] + '2' + mainParams['out_matrix_base'] + '.mat')


                # if not os.path.isfile(invt.inputs.out_file) or overwrite:
                #     invt.run()
                #     outputFileList.append(invt.inputs.out_file)


                #apply input-to-standard to input
                # d2a_txt = fslmat_to_itk_txt(flt.inputs.out_matrix_file, flt.inputs.in_file, flt.inputs.reference, flt.inputs.out_matrix_file.replace('.mat','.txt'))
                # concat = ConcatenateTransforms()
                # concat.inputs.dimension = 3
                # concat.inputs.transforms = [
                #     os.path.join(DATA_DIR,'derivatives',f'sub-{st.subject.id}','anat',f'sub-{st.subject.id}_{stdImageParams['xfm.h5']}'),
                #     d2a_txt
                # ]
                # concat.inputs.output_transform = os.path.join(mainFlirtOutputDir,f'sub-{st.subject.id}_{stdImageParams["out_h5_suffix"]}')
                # concat.run()

                # applyBidsLabels = mainBidsLabels.copy()
                # for k in stdImageParams['output_bids_labels'].keys():
                #     applyBidsLabels[k] = stdImageParams['output_bids_labels'][k]
                # cmd = CommandLine(f"antsApplyTransforms -d 3 -i {flt.inputs.in_file} -r {stdImageFile} "
                #                   f"-o [" + os.path.join(mainFlirtOutputDir,f'sub-{st.subject.id}_{stdImageParams["out_h5_suffix"]}') + ",1]," +  os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
                #                   f" -t fmriprep_T1_to_MNI.h5 -t dti2t1_ants.txt -n Linear")
                # res = cmd.run()


                #convert FSL dwi2T1w transform .mat to ANTS itk format
                n_c3d = pe.Node(interface=Function(input_names=["source_file","reference_file","transform_file","itk_transform","fsl2ras"],
                                                    output_names=["itk_transform"],
                                                    function=c3d_affine_tool),
                                name='c3d_affine_tool')
                n_c3d.inputs.source_file = n_flt.inputs.in_file
                n_c3d.inputs.reference_file = n_flt.inputs.reference
                n_c3d.inputs.fsl2ras = True
                WF.connect([(n_flt,n_c3d,[('out_matrix_file','transform_file'),('out_matrix_file','itk_transform')])])


                #apply xfms to gen dwi to standard transform
                n_at = pe.Node(interface=Function(input_names=["input_image","reference_image","transform1","transform2","dimension","interpolation","print_out_composite_warp_file","output_image"],
                                                  output_names=["output_image"],
                                                  function=applytransforms),
                               name='antsApplyTransforms_genwarp')

                n_at.inputs.input_image = n_flt.inputs.in_file
                n_at.inputs.reference_image = stdImageFile
                n_at.inputs.transform1 =  os.path.join(DATA_DIR,'derivatives',f'sub-{st.subject.id}','anat',f"sub-{st.subject.id}_{stdImageParams['xfm.h5']}")
                n_at.inputs.dimension = 3
                n_at.inputs.interpolation = 'Linear'
                n_at.inputs.print_out_composite_warp_file = True 

                #get output xfm h5 filename
                applyBidsLabels = mainBidsLabels.copy()
                for k in stdImageParams['output_bids_labels'].keys():
                    applyBidsLabels[k] = stdImageParams['output_bids_labels'][k]
                suffix = applyBidsLabels['suffix']
                applyBidsLabels['suffix'] = 'xfm'
                n_at.inputs.output_image = os.path.join(mainFlirtOutputDir,f'sub-{st.subject.id}_{stdImageParams["out_h5_suffix"]}')#os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
                
                WF.connect([(n_c3d,n_at,[('itk_transform','transform2')])])
                

                #apply xfms to gen dwi to standard image
                applyBidsLabels['suffix'] = suffix
                n_at2 = pe.Node(interface=Function(input_names=["input_image","reference_image","transform1","transform2","dimension","interpolation","print_out_composite_warp_file","output_image"],
                                                  output_names=["output_image"],
                                                  function=applytransforms),
                               name='antsApplyTransforms_genimage')
                n_at2.inputs.input_image = n_at.inputs.input_image
                n_at2.inputs.reference_image = n_at.inputs.reference_image
                n_at2.inputs.transform1 = n_at.inputs.transform1
                n_at2.inputs.dimension = n_at.inputs.dimension
                n_at2.inputs.interpolation = n_at.inputs.interpolation
                n_at2.inputs.input_image = n_at.inputs.input_image
                n_at2.inputs.print_out_composite_warp_file = False
                n_at2.inputs.output_image = os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
                
                WF.connect([(n_c3d,n_at2,[('itk_transform','transform2')])])


                # applyxfm = fsl.ApplyXFM()
                # applyxfm.inputs.in_file = mainFile
                # applyxfm.inputs.reference = stdImageFile
                # applyxfm.inputs.apply_xfm = True
                # applyBidsLabels = mainBidsLabels.copy()
                # for k in refImageParams['output_bids_labels'].keys():
                #     applyBidsLabels[k] = stdImageParams['output_bids_labels'][k]
                # applyxfm.inputs.out_file = os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
                # applyxfm.inputs.in_matrix_file = os.path.join(mainFlirtOutputDir,mainParams['out_matrix_base'] + '2' + stdImageParams['out_matrix_suffix'] + '.mat')


                # if os.path.isfile(applyxfm.inputs.out_file) and not overwrite:
                #     if progress:
                #         print('Skipping APPLYXFM: output transformed file already exists: ' + applyxfm.inputs.out_file)

                # else:
                #     if progress:
                #         print('Applying ' + applyxfm.inputs.in_matrix_file + ' to ' + applyxfm.inputs.in_file)
                #         print('\tOut File: ' + applyxfm.inputs.out_file)
                #     applyxfm.run()

                #     #write JSON sidecar
                #     d = {}
                #     d['Sources'] = ['bids:derivatives:' + applyxfm.inputs.in_file.split(DATA_DIR + os.sep)[1],
                #                     'bids:derivatives:' + applyxfm.inputs.in_matrix_file.split(DATA_DIR + os.sep)[1]]
                #     d['SpatialReference'] = 'file:' + applyxfm.inputs.reference
                #     if 'brain' in flt.inputs.in_file:
                #         d['SkullStripped'] = True
                #         d['Type'] = 'Brain'
                #     else:
                #         d['SkullStripped'] = False
                #     d['RegistrationFiles'] = ['bids:derivatives:' + flt.inputs.out_matrix_file.split(DATA_DIR + os.sep)[1],
                #                             'bids:derivatives:' + applyxfm.inputs.in_matrix_file.split(DATA_DIR + os.sep)[1]]
                #     for k in stdImageParams['output_json_values'].keys():
                #         d[k] = stdImageParams['output_json_values'][k]
                #     with open(applyxfm.inputs.out_file.split('.')[0] + '.json', 'w') as fp:
                #         json.dump(d, fp, indent=4)  

                    #create registration png
                n_png2 = pe.Node(interface=Function(input_names=["in_file","ref_file","out_file"],
                                                    output_names=["out_file"],
                                                    function=pngappend),
                                name='create_png_dwi2std')
                # n_png2.inputs.out_file = pngFile
                n_png2.inputs.ref_file = n_at2.inputs.reference_image
                WF.connect([(n_at2,n_png2,[('output_image','in_file')])])
                WF.connect([(n_at,n_png2,[('output_image','out_file')])])
                # st.flirt_pngappend(at.inputs.output_image,at.inputs.reference_image,os.path.join(mainFlirtOutputDir,f'sub-{st.subject.id}_{stdImageParams["out_h5_suffix"]}').split('.')[0] + '.png') #at.inputs.print_out_composite_warp_file.split('.')[0] + '.png')
                    # outputFileList.append(os.path.join(mainFlirtOutputDir,os.path.join(mainFlirtOutputDir,os.path.basename(applyxfm.inputs.in_matrix_file).split('.')[0] + '.png')))


                # # (OPTIONAL) Apply to secondary image
                # for secFile in secFiles:
                #     applyxfm = fsl.ApplyXFM()
                #     applyxfm.inputs.in_file = secFile
                #     applyxfm.inputs.reference = refImageFile
                #     applyxfm.inputs.apply_xfm = True
                #     applyBidsLabels = st.bids.get_bids_labels(secFile)
                #     applyBidsLabels = stdImageParams['output_bids_labels'].copy()
                #     applyBidsLabels['suffix'] = 'dwi_' + st.bids.get_bids_labels(secFile)['suffix']
                #     applyxfm.inputs.out_file = os.path.join(mainFlirtOutputDir,st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**applyBidsLabels))
                #     applyxfm.inputs.in_matrix_file = flt.inputs.out_matrix_file


                #     if os.path.isfile(applyxfm.inputs.out_file) and not overwrite:
                #         if progress:
                #             print('Skipping APPLYXFM: output transformed file already exists: ' + applyxfm.inputs.out_file)
                            
                #     else:
                #         if progress:
                #             print('Applying transformation to secondary image to produce ' + applyxfm.inputs.out_file)
                #         applyxfm.run()
                #         outputFileList.append(applyxfm.inputs.out_file)

                #         # write JSON sidecar
                #         d['Sources'] = [d['Sources'],
                #                         'bids:derivatives:' + applyxfm.inputs.in_matrix_file.split(DATA_DIR + os.sep)[1]]
                #         with open(applyxfm.inputs.out_file.split('.')[0] + '.json', 'w') as fp:
                #             json.dump(d, fp, indent=4) 

            # set workflow working directory
            WF.base_dir = mainFlirtOutputDir

            WF.write_graph(graph2use='flat')
            WF.write_graph(dotfilename=os.path.join(WF.base_dir,'dti_flirt_workflow-graph.dot'), graph2use='colored', format='png', simple_form=True)
            WF.run()
            print('\n\nFLIRT (flirt.py, version ' + VERSION + ' ' + DATE + ') has successfully completed for input file: ' + mainFile + '\nThe files that have been produced:')
            # print(*outputFileList, sep = "\n\t")

            #remove lingering matrix files left in the current working directory
            for f in glob(os.path.join(os.getcwd(),'sub-' + st.subject.id + '*.mat')):
                os.remove(f)


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
    dti_flirt(options.IN_FILE,options.DATA_DIR,options.FLIRT_PARAMS,**argsDict)

    


