#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

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
REALPATH = os.path.realpath(__file__)

sys.path.append(os.path.dirname(REALPATH))
import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.1.0'
DATE = '21 Nov 2024'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser("This program is the batch wrapper command to perform DICOM to NIfTI conversion using dcm2niix. The program searches the specified project's searchSourceTable for acquisition folders (acq-*) which contain DICOM images and runs wsuconnect.support_tools.convert_dicoms for each returned directory.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects))
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
    filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex='desc-confounds_timeseries.tsv',inclusion=['derivatives','func'],progress=False)


    combined_df = pd.DataFrame(columns=['subject','session','task','acquisition','run','mean_framewise_displacement'])
    for fileToProcess in sorted(filesToProcess):
        new_df = pd.read_csv(fileToProcess, sep='\t')
        mean_fd = new_df['framewise_displacement'].mean()
        st.subject.get_id(fileToProcess)

        fileBasename = os.path.basename(fileToProcess)
        if 'task' in fileBasename:
            task = os.path.basename(fileToProcess).split('task-')[1].split('_')[0]
        else:
            task = 'na'
        if 'acq' in fileBasename:
            acq = os.path.basename(fileToProcess).split('acq-')[1].split('_')[0]
        else:
            acq = 'na'
        if 'run' in fileBasename:
            run = os.path.basename(fileToProcess).split('run-')[1].split('_')[0]
        else:
            run = 'na'

        new_df = pd.DataFrame([[f"sub-{st.subject.id}",f"ses-{st.subject.sesNum}",task,acq,run,mean_fd]], columns=combined_df.columns)
        combined_df = pd.concat([combined_df, new_df], ignore_index=True)


    combined_df.to_csv(os.path.join(st.creds.dataDir,'derivatives','desc-confounds_timeseries.tsv'), sep='\t')


    print(f"\nCOMPLETE. Output saved to {os.path.join(st.creds.dataDir,'derivatives','desc-confounds_timeseries.tsv')}")






