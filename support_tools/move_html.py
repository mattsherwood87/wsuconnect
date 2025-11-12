#!/resshare/python3_venv/bin/python
# remove_dirs.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 2 March 2025
#
# Modified on 27 August 2025: modify to run on fmriprep docker image

import os
import sys
import argparse
import shutil
import time

REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(REALPATH)


#versioning
VERSION = '1.0.1'
DATE = '27 August 2025'

# 

#input argument parser
parser = argparse.ArgumentParser('Moves or copies input (source) directories to a single output directory.')
parser.add_argument('-d','--data-dir', required=True,action='store', dest="DATADIR", help="input directories to copy", default=None)
parser.add_argument('-s','--subject', required=True,action='store', dest="SUBID", help="input directories to copy", default=None)
parser.add_argument('--suffix', required=True,action='store', dest="SUFFIX", help="suffix to append to the html filename", default=None)
   


# *******************  MAIN  ********************    
def move_html(dataDir: str, subid: str, suffix: str): 
    """
    Moves or copies input (source) directories to a single output directory.

    :param INDIR: fullpath to input (source) directory(ies)
    :type INDIR: str

    :raises Exception: generic error from attenpted deletion
    """    
    try:
        time.sleep(30) #wait just a few minutes
        inDir = os.path.join(dataDir,'derivatives')
        print(f"INPUT DIR: {dataDir}")
        print(f"SUBJECT ID: {subid}")
        print(f"Moving\n\t{os.path.join(inDir,subid + '.html')} to {os.path.join(inDir,f'{subid}_{suffix}.html')}")
        if os.path.isfile(os.path.join(inDir,f"{subid}.html")):
            shutil.move(os.path.join(inDir,f"{subid}.html"),os.path.join(inDir,f"{subid}_{suffix}.html"))
        os.system(f'chmod -R 777 {os.path.join(inDir,subid + "*")}')
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
    move_html(options.DATADIR,options.SUBID,options.SUFFIX)