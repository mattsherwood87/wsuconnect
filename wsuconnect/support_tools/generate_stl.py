#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 22 April 2025
#
# MOdified on 

import sys
import os
import argparse
import pymeshlab
from glob import glob as glob
import datetime
import traceback
from pathlib import Path

#local import
# REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
# print(REALPATH)
# REALPATH = '/resshare/wsuconnect'
# sys.path.append(REALPATH)
import wsuconnect.support_tools as st



FSLDIR = None
FREESURFERDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]
if "FREESURFER_HOME" in os.environ:
    FREESURFERDIR = os.environ["FREESURFER_HOME"]


VERSION = '1.1.0'
DATE = '22 April 2025'


parser = argparse.ArgumentParser('generate_stl.py: generates brain stl file from freesurfer output')
parser.add_argument('STAGE1_DIR',help='fullpath to the output directory for freesurfer reconall')
parser.add_argument('--overwrite',action='store_true',dest='OVERWRITE',default=False, help='overwrite existing files')
parser.add_argument('--progress',action='store_true',dest='progress',default=False, help='verbose mode')




# ******************* s3 bucket check ********************
def generate_stl(STAGE1_DIR: str, progress: bool=False):
    """
    This function performs stage 2 and 3 of FreeSurfer reconall freesurfer_recon-all_input.json control file. 

    :param STAGE1_DIR: fullpath to a single subject/session reconall Stage 1 directory
    :type STAGE1_DIR: str
    
    :param DATA_DIR: fullpath to the project's data directory (project's 'dataDir' credential)
    :type DATA_DIR: str

    :param RECONALL_PARAMS: fullpath to project's FreeSurfer RECON-ALL parameter control file
    :type RECONALL_PARAMS: str

    :param overwrite: flag to overwrite existing files, defaults to False
    :type overwrite: bool, optional

    :param progress: flag to display command line output providing additional details on the processing status, defaults to False
    :type progress: bool, optional

    :raises InvalidJsonInput: error encountered when the input JSON control file does not contain the appropriate mandatory definitions

    :raises Exception: general error encountered during execution
    """ 

    base = Path(os.path.dirname(STAGE1_DIR))
    dirs = [
        p for p in base.iterdir()
        if p.is_dir() and os.path.basename(STAGE1_DIR) in p.name
    ]

    for d in dirs:
        try:
            os.environ["SUBJECTS_DIR"] = str(d.parent)
            now = datetime.datetime.now()

            if progress:
                print('\n\nfsreconall_preprocess.py version ' + VERSION + ' dated ' + DATE + '\n')
                print('running @ ' + now.strftime("%m-%d-%Y %H:%M:%S") + '\n')


            # os.system(f'export SUBJECTS_DIR={os.path.dirname(STAGE1_DIR)}')
            if progress:
                print(f'SUBJECTS_DIR redirected to output directory: {d.parent}')
                print('converting pial surfaces to stl files')

            
            # create file inputs and outputs
            st.subject.get_id(str(d))
                
            #create output STL
            print('converting rh.pial and lh.pial')
            convertCmd = f"mris_convert {d / 'surf' / 'rh.pial'} {d / 'surf' / 'rh.stl'}"
            os.system(convertCmd)
            convertCmd = f"mris_convert {d / 'surf' / 'lh.pial'} {d /'surf' / 'lh.stl'}"
            os.system(convertCmd)
            print('binarize aseg.mgz')
            convertCmd = f"mri_binarize --i {d / 'mri' / 'aseg.mgz'} --match 7 8 16 46 47 --o {d / 'mri' / 'cerebellum.mgz'}"
            print(convertCmd)
            os.system(convertCmd)
            print('close cerebellum')
            convertCmd = f"mri_morphology {d / 'mri' / 'cerebellum.mgz'} close 1 {d / 'mri' / 'cerebellum_closed.mgz'}"
            print(convertCmd)
            os.system(convertCmd)
            # print('fill cerebellum')
            # convertCmd = f"mri_fill {os.path.join(STAGE1_DIR,'mri','cerebellum.mgz')} {os.path.join(STAGE1_DIR,'mri','cerebellum_filled.mgz')}"
            # print(convertCmd)
            # os.system(convertCmd)
            print('tessellate cerebellum')
            convertCmd = f"mri_tessellate {d / 'mri' / 'cerebellum_closed.mgz'} 1 {d / 'mri' / 'cerebellum'}"
            print(convertCmd)
            os.system(convertCmd)
            print('extract main cerebellum')
            convertCmd = f"mris_extract_main_component {d / 'mri' / 'cerebellum'} {d / 'mri' / 'cerebellum.main'}"
            print(convertCmd)
            os.system(convertCmd)
            print('remove intersection cerebellum')
            convertCmd = f"mris_remove_intersection -fill-holes {d / 'mri' / 'cerebellum.main'} {d / 'mri' / 'cerebellum.clean'}"
            print(convertCmd)
            os.system(convertCmd)
            print('convert cerebellum to stl')
            convertCmd = f"mris_convert {d / 'mri' / 'cerebellum.clean'} {d / 'mri' / 'cerebellum.stl'}"
            print(convertCmd)
            os.system(convertCmd)

            #do some processing of the stl for better printing
            if progress:
                print('generating brain mesh')
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(str(d / 'mri' / 'cerebellum.stl'))
            ms.apply_coord_taubin_smoothing(stepsmoothnum = 7)
            ms.load_new_mesh(str(d / 'surf' / 'lh.stl'))
            ms.load_new_mesh(str(d / 'surf' / 'rh.stl'))
            ms.generate_by_merging_visible_meshes()
            ms.meshing_decimation_quadric_edge_collapse()
            ms.apply_coord_hc_laplacian_smoothing()
            ms.save_current_mesh(str(d / 'surf' / 'brain_mesh_w_cerebellum.stl'),save_face_color=False)

            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(str(d / 'surf' / 'lh.stl'))
            ms.load_new_mesh(str(d / 'surf' / 'rh.stl'))
            ms.generate_by_merging_visible_meshes()
            ms.meshing_decimation_quadric_edge_collapse()
            ms.apply_coord_hc_laplacian_smoothing()
            ms.save_current_mesh(str(d / 'surf' / 'brain_mesh.stl'),save_face_color=False)

            #repeat for each hemisphere sor separate printing
            for hemi in ['lh','rh','cerebellum']:
                ms = pymeshlab.MeshSet()
                if 'cerebellum' in hemi:
                    ms.load_new_mesh(str(d / 'mri' / f'{hemi}.stl'))
                    ms.apply_coord_taubin_smoothing(stepsmoothnum = 7)
                else:
                    ms.load_new_mesh(str(d / 'surf' / f'{hemi}.stl'))
                ms.meshing_decimation_quadric_edge_collapse()
                ms.apply_coord_hc_laplacian_smoothing()
                ms.save_current_mesh(str(d / 'surf' / f'brain_mesh_{hemi}.stl'),save_face_color=False)


            if 'ses' in d.name:
                aparc2asegCmd = f"mri_aparc2aseg --s sub-{st.subject.id}_ses-{st.subject.sesNum} --a2009s"
            else:
                aparc2asegCmd = f"mri_aparc2aseg --s sub-{st.subject.id} --a2009s'" 
            os.system(aparc2asegCmd)

            #convert revised aparc+aseg to native space
            if progress:
                print('converting aparc+aseg and computing stats')
            #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg.mgz') + ' --targ ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg-native.mgz') + ' --no-save-reg'
            vol2volCmd = f"mri_label2vol --seg {d / 'mri' / 'aparc+aseg.mgz'} --temp {d / 'mri' / 'rawavg.mgz'} --regheader {d / 'mri' / 'aparc+aseg.mgz'} --o {d / 'mri' / 'aparc+aseg-native.mgz'}"
            if progress:
                print(vol2volCmd)
            os.system(vol2volCmd)

            #convert revised aparc+aseg to native space
            #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg.mgz') + ' --targ ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg-native.mgz') + ' --no-save-reg'
            vol2volCmd = f"mri_label2vol --seg {d / 'mri' / 'aparc.a2009s+aseg.mgz'} --temp {d / 'mri' / 'rawavg.mgz'} --regheader {d / 'mri' / 'aparc.a2009s+aseg.mgz'} --o {d / 'mri' / 'aparc.a2009s+aseg-native.mgz'}"
            if progress:
                print(vol2volCmd)
            os.system(vol2volCmd)

            #compute cortical thickness measurements
            if 'ses' in d.name:
                segstatsCmd = f"mri_segstats --subject sub-{st.subject.id}_ses-{st.subject.sesNum} --seg {d / 'mri' / 'aparc+aseg-native.mgz'} --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in {d / 'mri' / 'rawavg.mgz'} --sum {d / 'mri' / 'T1w.segstats.dat'} --sd {d.parent}"
            else:
                segstatsCmd = f"mri_segstats --subject sub-{st.subject.id} --seg {d / 'mri' / 'aparc+aseg-native.mgz'} --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in {d / 'mri' / 'rawavg.mgz'} --sum {d / 'mri' / 'T1w.segstats.dat'} --sd {d.parent}"
            if progress:
                print(segstatsCmd)
            os.system(segstatsCmd)

            # #compute cortical thickness measurements
            # segstatsCmd = f"mri_segstats --seg {d / 'mri' / 'aparc.a2009s+aseg-native.mgz'} --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in {d / 'mri' / 'rawavg.mgz'} --sum {d / 'mri' / 'T1w.a2009s.segstats.dat'} --sd {d.parent}"
            # if progress:
            #     print(segstatsCmd)
            # os.system(segstatsCmd)
            
        
        except OSError as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            filename = exc_tb.tb_frame.f_code.co_filename
            lineno = exc_tb.tb_lineno
            print(f"Exception occurred in file: {filename}, line: {lineno}")
            print(f"\tException type: {exc_type.__name__}")
            print(f"\tException message: {e}")
            traceback.print_exc()
            return
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
    if options.progress:
        argsDict['progress'] = options.progress
    generate_stl(options.STAGE1_DIR,**argsDict)

    


