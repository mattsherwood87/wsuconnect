#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 28 Dec 2020
#
# Modified on 25 February 2025 - update to move main function under st.check_rawdata()
# Modified on 17 April 2023 - update to WSU implementatttion
# Modified on 11 Jan 2021 - add utilization of instance_ids.json

import os
# import pymysql
import argparse
import sys
import csv
import pandas as pd
import numpy as np
import json
# import ast


#local import
REALPATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(REALPATH)

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '3.0.0'
DATE = '25 Feb 2025'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects), default=None)
#parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
#parser.add_argument('-l', '--load', action="store_true", dest="DOWNLOAD", help="Download files to local disk if they do not exist", default=False)
#parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)

        




    

if __name__ == '__main__':
    options = parser.parse_args()
    st.check_rawdata(project=options.PROJECT, progress=options.progress)
