#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 venv as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 28 FEB 2024
#
# Modified on 

import os
import sys
import argparse
from pathlib import Path


#append path if necessary
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-3]).resolve()
if not str(REALPATH) in sys.path:
    sys.path.append(REALPATH)


#versioning
VERSION = '1.0.0'
DATE = '28 FEB 2024'


FSLDIR = None
if "FSLDIR" in os.environ:
    FSLDIR = os.environ["FSLDIR"]
    # print(f"FSLDIR = {FSLDIR}")
if os.path.isfile(os.path.join('opt','fsl-6.0.7',"etc","fslconf","fsl.sh")):
    os.system('. /opt/fsl-6.0.7/etc/fslconf/fsl.sh')



parser = argparse.ArgumentParser('feat_full_firstlevel.py: perform first level FEAT fMRI analysis')
    #input options for main()
parser.add_argument('--datadir',action='store',dest='DATADIR',help='input data directory')
parser.add_argument('--subname',action='store',dest='SUBNAME', help='subject ID')
parser.add_argument('--sesnum',action='store',dest='SESNUM', help='session number')
parser.add_argument('--feat-design-dir',action='store',dest='FEATDESIGNDIR', help='fullpath to FEAT design dir containing input FSF file')
parser.add_argument('--feat-output-dir',action='store',dest='FEATOUTPUTDIR', help='fullpath to output FEAT directory')
parser.add_argument('--design-basename',action='store',dest='DESIGNBASENAME', help='basename for the FEAT design file')
parser.add_argument('--reference',action='store',dest='REFERENCE',default=None)
parser.add_argument('--step2-design-basename',action='store',dest='STEP2DESIGNBASENAME',default=None)
parser.add_argument('--struc-reg-matrix',action='store',dest='struc_reg_matrix',default=None)
parser.add_argument('--progress',action='store_true',dest='progress',default=False)


# *******************  MAIN  ********************    
def feat_full_firstlevel(DATADIR: str, SUBNAME: str, SESNUM: str, FEATDESIGNDIR: str, FEATOUTPUTDIR: str, DESIGNBASENAME: str, reference: str=None, step2_design: str=None, struc_reg_matrix: str=None, progress: bool=False): 
    """
    This function moves or copies input (source) directories to a single output directory.

    :param DATADIR: fullpath to the project's data directory (<dataDir> key in credentials.json)
    :type DATADIR: str

    :param SUBNAME: subject identifier
    :type SUBNAME: str

    :param SESNUM: session identifier
    :type SESNUM: str

    :param FEATDESIGNDIR: directory containing the template feat designs
    :type FEATDESIGNDIR: str

    :param FEATOUTPUTDIR: FEAT output directory  
    :type FEATOUTPUTDIR: str

    :param DESIGNBASENAME: basename (no extension) for the design file for step 1
    :type DESIGNBASENAME: str

    :param reference: fullpath to T1 reference image, defaults to None ##DEPRECATED
    :type reference: str, optional

    :param step2_design_basename: basename (no extension) for the design file for step 2, defaults to None
    :type step2_design_basename: str, optional

    :param struc_reg_matrix: fullpath to the registration matrix between structural (T1) and standard atlas, defaults to None
    :type struc_reg_matrix: str, optional

    :param progress: flag to display command line output providing additional details on the processing status, defaults to False
    :type progress: bool, optional

    :raises Exception: general error encountered during execution
    """ 
    from glob import glob as glob
    from nipype.interfaces import fsl
    import traceback
    
    if progress:
        print('SUBJECT: ' + SUBNAME + ' SESSION: ' + SESNUM)
        print('\trunning FEAT, output directory: ' + FEATOUTPUTDIR + ' with design ' + os.path.join(FEATDESIGNDIR,DESIGNBASENAME + '.fsf'))
        #run initial FEAT design
        # os.system(f"touch {os.path.join(os.path.dirname(FEATOUTPUTDIR),'test.txt')}")
        print('feat ' + os.path.join(FEATDESIGNDIR,DESIGNBASENAME + '.fsf'))

    try:

        print(FEATDESIGNDIR)
        print(DESIGNBASENAME)
        os.system(f"feat {os.path.join(FEATDESIGNDIR,DESIGNBASENAME + '.fsf')}")
        

        #do I need to insert custom registration?
        if not reference or not os.path.isfile(struc_reg_matrix):
            if progress:
                print('\tdone')
        else:
            if progress:
                print('\tfeat step 1 complete\n\n\tcopying structural registration to standard matrix: ' + struc_reg_matrix)
            
            # replace highres2standard transform
            os.system('cp ' + struc_reg_matrix + ' ' + os.path.join(FEATOUTPUTDIR,'reg','highres2standard.mat'))


            if progress:
                print('\tupdating feat with the new registration matrix')

            # update feat output with new transform
            os.system('updatefeatreg ' + FEATOUTPUTDIR + ' -gifs')


            if progress:
                print('\n\trunning feat step 2 (stats and post-stats) on: ' + FEATOUTPUTDIR + ' with design ' + os.path.join(FEATDESIGNDIR,step2_design + '.fsf'))

            # run feat stats/poststats again
            os.system('feat ' + os.path.join(FEATDESIGNDIR,step2_design + '.fsf'))
            if progress:
                print('\tdone\n')


        # compute percent signal change
        for statsFile in glob(os.path.join(FEATOUTPUTDIR,'stats','cope*')):
            if progress:
                print('\tcreating percent signal change image for ' + os.path.basename(statsFile).split('.')[0])
            argStr = ('fslmaths ' + 
                      statsFile + 
                      ' -mul 100 -div ' +
                      os.path.join(FEATOUTPUTDIR,'mean_func.nii.gz') + 
                      ' ' + os.path.join(FEATOUTPUTDIR,'stats','desc-percent-signal-change_' + os.path.basename(statsFile).split('.')[0] + '.nii.gz')
                      )
            os.system(argStr)

        # # #add some transform shit
        statsFiles = glob(os.path.join(FEATOUTPUTDIR,'stats','*'))
        ref = 'highres'
        applyxfm = fsl.ApplyXFM()
        applyxfm.inputs.reference = os.path.join(FEATOUTPUTDIR,'reg',ref + '.nii.gz')
        applyxfm.inputs.apply_xfm = True
        applyxfm.inputs.in_matrix_file = os.path.join(FEATOUTPUTDIR,'reg','example_func2' + ref + '.mat')
        if os.path.isfile(applyxfm.inputs.in_matrix_file):

            for statsFile in statsFiles:
                if not 'pe' in os.path.basename(statsFile) and not 'zstat' in os.path.basename(statsFile) and not 'tstat' in os.path.basename(statsFile):
                    continue

                applyxfm.inputs.in_file = statsFile
                applyxfm.inputs.out_file = os.path.join(FEATOUTPUTDIR,'reg_highres','stats','space-' + ref + '_' + os.path.basename(statsFile).split('.')[0] + '.nii.gz')

                if not os.path.isdir(os.path.join(FEATOUTPUTDIR,'reg_highres','stats')):
                    os.makedirs(os.path.join(FEATOUTPUTDIR,'reg_highres','stats'))

                if progress:
                    print('\tapplying transform ' + os.path.basename(applyxfm.inputs.in_matrix_file) + ' to ' + os.path.basename(applyxfm.inputs.in_file))
                applyxfm.run()


        ref = 'standard'
        applyxfm = fsl.ApplyXFM()
        applyxfm.inputs.reference = os.path.join(FEATOUTPUTDIR,'reg',ref + '.nii.gz')
        applyxfm.inputs.apply_xfm = True
        applyxfm.inputs.in_matrix_file = os.path.join(FEATOUTPUTDIR,'reg','example_func2' + ref + '.mat')
        if os.path.isfile(applyxfm.inputs.in_matrix_file):

            for statsFile in statsFiles:
                if not 'pe' in os.path.basename(statsFile) and not 'zstat' in os.path.basename(statsFile) and not 'tstat' in os.path.basename(statsFile):
                    continue

                applyxfm.inputs.in_file = statsFile
                applyxfm.inputs.out_file = os.path.join(FEATOUTPUTDIR,'reg_standard','stats',os.path.basename(statsFile))

                if not os.path.isdir(os.path.join(FEATOUTPUTDIR,'reg_standard','stats')):
                    os.makedirs(os.path.join(FEATOUTPUTDIR,'reg_standard','stats'))

                if not os.path.isfile(applyxfm.inputs.out_file):
                    if progress:
                        print('\tapplying transform ' + os.path.basename(applyxfm.inputs.in_matrix_file) + ' to ' + os.path.basename(applyxfm.inputs.in_file))
                    applyxfm.run()



            if not os.path.isdir(os.path.join(FEATOUTPUTDIR,'reg_standard','stats')):
                os.makedirs(os.path.join(FEATOUTPUTDIR,'reg_standard','stats'))
            applyxfm.inputs.in_file = os.path.join(FEATOUTPUTDIR,'filtered_func_data.nii.gz')
            applyxfm.inputs.out_file = os.path.join(FEATOUTPUTDIR,'reg_standard','space-MNI152NLin2009cAsym_filtered_func_data.nii.gz')
            if progress:
                print('\tapplying transform ' + os.path.basename(applyxfm.inputs.in_matrix_file) + ' to ' + os.path.basename(applyxfm.inputs.in_file))
            applyxfm.run()


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
    print('starting')
    options = parser.parse_args()
    argsDict = {}
    if options.REFERENCE:
        argsDict['reference'] = options.REFERENCE
    if options.STEP2DESIGNBASENAME:
        argsDict['step2_design'] = options.STEP2DESIGNBASENAME
    if options.struc_reg_matrix:
        argsDict['struc_reg_matrix'] = options.struc_reg_matrix
    if options.progress:
        argsDict['progress'] = options.progress
    feat_full_firstlevel(options.DATADIR,options.SUBNAME,options.SESNUM,options.FEATDESIGNDIR,options.FEATOUTPUTDIR,options.DESIGNBASENAME,**argsDict)