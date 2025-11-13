#!/resshare/python3_venv/bin/python
# apply_brainmask.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 27 August 2025
#
# Modified on 
VERSION = '1.0.0'
DATE = '27 August 2025'

import argparse
# 

#input argument parser
parser = argparse.ArgumentParser('Applies an fMRIprep-generated brainmask to preprocessed T1w image.')
parser.add_argument('-d','--data-dir', required=True,action='store', dest="DATADIR", help="input directories to copy", default=None)
parser.add_argument('-s','--subject', required=True,action='store', dest="SUBID", help="input directories to copy", default=None)
   


# *******************  MAIN  ********************    
def apply_brainmask(dataDir: str, subid: str): 
    """
    Applies an fMRIprep-generated brainmask to preprocessed T1w image.

    :param INDIR: fullpath to input (source) directory(ies)
    :type INDIR: str

    :raises Exception: generic error from attenpted deletion
    """   
    import os
    import sys 
    from nipype.interfaces.fsl.maths import ApplyMask
    from glob import glob
    try:
        # time.sleep(300) #wait just a few minutes
        inDir = os.path.join(dataDir,'derivatives',subid,'anat')
        if not os.path.isdir(inDir):
            print(f"ERROR: input directory {inDir} does not exist, exiting...")
            sys.exit()

        print(f"INPUT DIR: {dataDir}")
        print(f"SUBJECT ID: {subid}")


        maskFile = glob(os.path.join(inDir,f"{subid}_*_desc-brain_mask.nii.gz"), recursive=True)
        anatFile = glob(os.path.join(inDir,f"{subid}_*_desc-preproc_T1w.nii.gz"), recursive=True)
        maskFile = [f for f in maskFile if 'space' not in f]
        anatFile = [f for f in anatFile if 'space' not in f]
        if not maskFile or not anatFile:
            print(f"ERROR: input directory {inDir} does not contain the mask or preproc T1w image, exiting...")
            sys.exit()

        outFile = anatFile[0].replace('preproc','brain')
        print(f"Creating brain-extracted image:\n\tbrainmask: {maskFile[0]}\n\tT1w: {anatFile[0]}\n\tbrain T1w: {outFile}")
        app = ApplyMask()
        app.inputs.mask_file = maskFile[0]
        app.inputs.in_file = anatFile[0]
        app.inputs.out_file = outFile
        app.run()
        print("SUCCESS")


    except Exception as e:
        print("Error Message: {0}".format(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        return


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """

    options = parser.parse_args()
    apply_brainmask(options.DATADIR,options.SUBID)