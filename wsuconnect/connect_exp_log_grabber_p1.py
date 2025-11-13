#!/usr/bin/env python3
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 19 June 2023
#
# Last Modified on 

# ******* IMPORTS ***********
from cmath import inf
import os
import argparse
import shutil
import datetime
# import numpy as np
# import math
import time
# from pathlib import Path


# ******* LOCAL IMPORTS ******
#sys.path.append(os.path.abspath(os.path.join(os.environ['SCRATCH_DIR'],'python')))
#from helper_functions.convert_dicoms import convert_dicoms


# ******* GLOBAL INFO *******
#versioning
VERSION = '1.0.0'
DATE = '19 June 2023'

#input argument parser
parser = argparse.ArgumentParser()

#GLOBALS
REALPATH = os.path.dirname(os.path.realpath(__file__))

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
def parse_arguments():

    #input options for main()
    # requiredNamed = parser.add_argument_group('required arguments')
    # requiredNamed.add_argument('-p','--path', action="store", dest="PATH", help="define search path", default=None)
    parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
    # parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
    options = parser.parse_args()

    return options


# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """

    #input and output locations
    inLogPath = os.path.join('C:\\','Users','connect_usr','Desktop')
    outLogPath = os.path.join('W:\\','tmp_beh_logs')
    print(inLogPath)
    print(outLogPath)

    outputLog = os.path.join(inLogPath,'connect_exp_log_grabber_p1.txt')
    if os.path.isfile(outputLog):
        f = open(outputLog,'r+')
        l = f.readlines()
        # l.insert(0,d + '\n')
        # f.seek(0) #get to the first position
        # f.writelines(l)
        f.close()
        
    else:
        l = []
	



    for root, dirs, files in os.walk(inLogPath, topdown=True):
    # for path in Path(dcmPath).rglob('*'):
        for filename in files:
            if not filename + '\n' in l:
                try:
                    if '.log' in filename or '.csv' in filename or '.xdf' in filename and not 'inputs' in root:
                        print(filename)
                        shutil.copyfile(os.path.join(root,filename),os.path.join(outLogPath,filename))
                        
                        if os.path.isfile(outputLog):
                            f = open(outputLog,'r+')
                            l2 = f.readlines()
                            l2.insert(0,filename + '\n')
                        else:
                            f = open(outputLog,'x')
                            l2 = [filename + '\n']
                            
                        f.seek(0) #get to the first position
                        f.writelines(l2)
                        f.close()
                            
                except OSError as e:
                    print(e)

            else:
                print('file ' + filename + ' skipped')                


if __name__ == '__main__':
    main()
