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

#local import
REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
print(REALPATH)
REALPATH = '/resshare/wsuconnect'
sys.path.append(REALPATH)
import support_tools as st



FSLDIR = None
FREESURFERDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]
if "FREESURFER_HOME" in os.environ:
    FREESURFERDIR = os.environ["FREESURFER_HOME"]


VERSION = '1.1.0'
DATE = '22 April 2025'


parser = argparse.ArgumentParser('generate_stl.py: perform FLIRT registration between 2D ASL and structural/standard brain images')
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

    try:
        now = datetime.datetime.now()

        if progress:
            print('\n\nfsreconall_preprocess.py version ' + VERSION + ' dated ' + DATE + '\n')
            print('running @ ' + now.strftime("%m-%d-%Y %H:%M:%S") + '\n')


        # os.system(f'export SUBJECTS_DIR={os.path.dirname(STAGE1_DIR)}')
        if progress:
            print(f'SUBJECTS_DIR redirected to output directory: {os.path.dirname(STAGE1_DIR)}')
            print('converting pial surfaces to stl files')

        
        # create file inputs and outputs
        st.subject.get_id(STAGE1_DIR)
            
        #create output STL
        convertCmd = 'mris_convert ' + os.path.join(STAGE1_DIR,'surf','rh.pial') + ' ' + os.path.join(STAGE1_DIR,'surf','rh.stl') 
        os.system(convertCmd)
        convertCmd = 'mris_convert ' + os.path.join(STAGE1_DIR,'surf','lh.pial') + ' ' + os.path.join(STAGE1_DIR,'surf','lh.stl') 
        os.system(convertCmd)

        if progress:
            print('generating brain mesh')
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(os.path.join(STAGE1_DIR,'surf','lh.stl'))
        ms.load_new_mesh(os.path.join(STAGE1_DIR,'surf','rh.stl'))
        ms.generate_by_merging_visible_meshes()
        ms.meshing_decimation_quadric_edge_collapse()
        ms.apply_coord_hc_laplacian_smoothing()
        ms.save_current_mesh(os.path.join(STAGE1_DIR,'surf','brain_mesh.stl'),save_face_color=False)


        aparc2asegCmd = 'mri_aparc2aseg --s sub-' + st.subject.id + ' --a2009s'
        os.system(aparc2asegCmd)

        #convert revised aparc+aseg to native space
        if progress:
            print('converting aparc+aseg and computing stats')
        #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg.mgz') + ' --targ ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg-native.mgz') + ' --no-save-reg'
        vol2volCmd = 'mri_label2vol --seg ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg.mgz') + ' --temp ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg.mgz') + '--o ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg-native.mgz')
        os.system(vol2volCmd)

        #convert revised aparc+aseg to native space
        #vol2volCmd = 'mri_vol2vol --mov ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg.mgz') + ' --targ ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader --o ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg-native.mgz') + ' --no-save-reg'
        vol2volCmd = 'mri_label2vol --seg ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg.mgz') + ' --temp ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --regheader ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg.mgz') + '--o ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg-native.mgz')
        os.system(vol2volCmd)

        #compute cortical thickness measurements
        segstatsCmd = 'mri_segstats --subject sub-' + st.subject.id + ' --seg ' + os.path.join(STAGE1_DIR,'mri','aparc+aseg-native.mgz') + ' --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --sum ' + os.path.join(STAGE1_DIR,'mri','T1w.segstats.dat') + ' --sd ' + os.path.dirname(STAGE1_DIR)
        os.system(segstatsCmd)

        #compute cortical thickness measurements
        segstatsCmd = 'mri_segstats --subject sub-' + st.subject.id + ' --seg ' + os.path.join(STAGE1_DIR,'mri','aparc.a2009s+aseg-native.mgz') + ' --nonempty --brain-vol-from-seg --etiv --totalgray --surf-ctx-vol --subcortgray --ctab-default --in ' + os.path.join(STAGE1_DIR,'mri','rawavg.mgz') + ' --sum ' + os.path.join(STAGE1_DIR,'mri','T1w.a2009s.segstats.dat') + ' --sd ' + os.path.dirname(STAGE1_DIR)
        os.system(segstatsCmd)
        
    
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

    


