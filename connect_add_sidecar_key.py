#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 Dec 2020
#
# Modified on 25 October 2024 - update to new session formats and use of helper_functions
# Modified on 17 April 2023 - update to WSU format
# Modified on 24 Nov 2021 - improve efficiency based on processed_data_check output
# Modified on 5 Nov 2021 - implement BIDS formatting
# Modified on 11 Jan 2021 - add utilization of instance_ids.json

import os
# import time
import sys
import argparse
import json
import shutil


#local import
REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '29 October 2024'

#input argument parser
parser = argparse.ArgumentParser('connect_add_sidecar_key.py: adds JSON sidecar keys from scan_id.json (Units or TaskName) to each appropriate NIfTI sidecar (json)')


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="select a project: " + ' '.join(st.creds.projects), default=None)
parser.add_argument('--progress', help="Show progress (default FALSE)", action="store_true", dest="progress", default=False)
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
  


# ******************* EVALUATE INPUT ARGUMENTS ********************
def evaluate_args(options):

    dataCheckFile = None
    
    #print version if selected
    if options.version:
        print('connect_add_sidecar_key.py version {0}.'.format(VERSION)+" DATED: "+DATE)

    

    return 



# ******************* EVALUATE INPUT ARGUMENTS ********************
def add_json_sidecar_key(inFile):
    #get time info for verbose option


    try:
        # splitFilename = os.path.splitext(os.path.join(inDir,filename))

        #only progress if nifti

        sourceDir = os.path.dirname(inFile)
        filename = os.path.basename(inFile)
        filename_split = os.path.splitext(filename)

        #file has an extension
        if filename_split[1] == '.json':

            #get scan identifier
            print(inFile)
            st.subject.get_id(sourceDir)
            scanName, bidsDir, scanKeys = st.get_scan_id(sourceDir,filename_split[0])
            

            baseOutput = os.path.join(sourceDir,filename)
            

            #check if additional keys are needed
            b_mod = False
            with open(baseOutput, 'r') as j:
                imgHeader = json.load(j)


            #fMRI modifiers
            for k in ['SliceTiming',
                        'TaskName',
                        'Units']:
                if k in scanKeys.keys():
                    imgHeader[k] = scanKeys[k]
                    b_mod = True

            #general modifiers
            if 'PhaseEncodingAxis' in imgHeader.keys():
                imgHeader['PhaseEncodingDirection'] = imgHeader.pop('PhaseEncodingAxis')
                b_mod = True

            if 'EstimatedEffectiveEchoSpacing' in imgHeader.keys():
                imgHeader['EffectiveEchoSpacing'] = imgHeader.pop('EstimatedEffectiveEchoSpacing')
                b_mod = True

            if 'EstimatedTotalReadoutTime' in imgHeader.keys():
                imgHeader['TotalReadoutTime'] = imgHeader.pop('EstimatedTotalReadoutTime')
                b_mod = True
                

            #B0 map modifiers
            if 'B0FieldSource' in scanKeys.keys():
                imgHeader['B0FieldSource'] = f"{scanKeys['B0FieldSource']}_{st.subject.sesNum}"
                b_mod = True

            if 'B0FieldIdentifier' in scanKeys.keys():
                imgHeader['B0FieldIdentifier'] = f"{scanKeys['B0FieldIdentifier']}_{st.subject.sesNum}"
                b_mod = True

            #ASL modifiers
            for k in ["ArterialSpinLabelingType",
                      "M0Type",
                      "TotalAcquisitionPairs",
                      "LabelingDuration",
                      "PostLabelingDelay",
                      "RepetitionTimePreparation",
                      "BackgroundSuppression",
                      "BackgroundSuppressionNumberPulses",
                      "BackgroundSuppressionPulseTime",
                      "VascularCrushing",
                      "LabelingEfficiency",
                      "LabelingPulseAverageGradient",
                      "LabelingPulseMaximumGradient",
                      "LabelingPulseAverageB1",
                      "LabelingPulseDuration",
                      "LabelingPulseInterval"
                      ]:
                if k in scanKeys.keys():
                    imgHeader[k] = scanKeys[k]
                    b_mod = True

                if os.path.isfile(os.path.join(st.creds.dataDir,'code','aslcontext.tsv')) and 'asl.json' in baseOutput and b_mod:
                    shutil.copyfile(os.path.join(st.creds.dataDir,'code','aslcontext.tsv'),baseOutput.replace('asl.json','aslcontext.tsv'))
        

            #write modified JSON sidecar
            if b_mod:
                with open(baseOutput, 'w') as j:
                    json.dump(imgHeader, j, indent='\t', sort_keys=True)

    #catch any errors
    except Exception as e:
        print('ERROR: ' + filename_split[0] + ' ', end='')
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

    return 




if __name__ == '__main__':
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    evaluate_args(options)
    st.creds.read(options.PROJECT)
    
    
    jsonFileList = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex='json',exclusion=['bak'],inclusion=['rawdata','sub-','ses-'])#orinclusion=['.nii','.7','.log','.txt','.rda','.json'])

    #loop over all tables
    for fileName in jsonFileList:
        add_json_sidecar_key(fileName)


    if options.progress:
        print('\n\tCompleted processing project ' + st.creds.project)