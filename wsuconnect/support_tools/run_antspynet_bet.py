#!/resshare/python3_venv/bin/python
# apply_brainmask.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 1 October 2025
#
# Modified on 

import os
import sys
import argparse
import ants
import antspynet
import traceback

REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(REALPATH)


#versioning
VERSION = '1.0.0'
DATE = '1 October 2025'

# 

#input argument parser
parser = argparse.ArgumentParser('Performs antspynet.brain_extraction (runs in docker wsuconnect/neuro image).')
parser.add_argument('-i','--input', required=True,action='store', dest="INPUT", help="input directories to copy", default=None)
parser.add_argument('-o','--output', required=True,action='store', dest="OUTPUT", help="input directories to copy", default=None)
   


# *******************  MAIN  ********************    
def run_antspynet_bet(input: str, output: str): 
    """
    Applies an fMRIprep-generated brainmask to preprocessed T1w image.

    :param INDIR: fullpath to input (source) directory(ies)
    :type INDIR: str

    :raises Exception: generic error from attenpted deletion
    """    
    try:
        inImg = ants.image_read(input)
        brainSeg = antspynet.brain_extraction(inImg, modality="t1", verbose=True)
        # ants.image_write(brainSeg, output)
        brain = inImg * brainSeg
        brain.to_file(output)
        print("\tBrain Extraction completed sucessfully")
    except Exception as e:
        print('ERROR: brain extraction')
        traceback.print_exc()


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """

    options = parser.parse_args()
    run_antspynet_bet(options.INPUT, options.OUTPUT)