#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 21 Nov 2024
#
# v

import os
import argparse
import sys
import json
import shutil 
import pandas as pd


#local import
# REALPATH = os.path.realpath(__file__)

# sys.path.append(os.path.dirname(REALPATH))
import wsuconnect.support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.1.0'
DATE = '21 Nov 2024'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser(description="Combine each participant's ASLPrep CBF quality control file (desc-qualitycontrol_cbf.tsv) into one project-level file in derivatives.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="select a project: " + ' '.join(st.creds.projects))
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)



# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """

    #get and evaluate options
    options = parser.parse_args()
    
    if options.version:
        print('connect_dcm2nii.py version {0}.'.format(VERSION)+" DATED: "+DATE)

    
    st.creds.read(options.PROJECT)

    #search for aslprep qualitycontrol_cbf tsv files
    filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex='desc-qualitycontrol_cbf.tsv',inclusion=['derivatives','perf'],progress=False)


    combined_df = pd.DataFrame()
    for fileToProcess in sorted(filesToProcess):
        new_df = pd.read_csv(fileToProcess, sep='\t')
        combined_df = pd.concat([combined_df,new_df],ignore_index=True)


    combined_df.to_csv(os.path.join(st.creds.dataDir,'derivatives','desc-qualitycontrol_cbf.tsv'), sep='\t')


    print('\nCOMPLETE')






