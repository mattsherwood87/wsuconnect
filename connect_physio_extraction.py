#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.11.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 September 2024
#
# Modified on

import os
import argparse
from pycondor import Dagman
import sys
from glob import glob as glob
import json
from pathlib import Path

#local import

REALPATH = os.path.realpath(__file__)
sys.path.append(os.path.dirname(REALPATH))

import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.1'
DATE = '23 September 2024'
FSLDIR = os.environ["FSLDIR"]


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser()
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="Perform DTI preprocessing for the selected project: " + ' '.join(st.creds.projects), default=None)

parser.add_argument('--overwrite', action="store_true", dest="OVERWRITE", help="Force conversion by skipping directory and database checking", default=False)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='optional subject identifier(s), skips check of participants.tsv. Multiple inputs accepted through space delimiter')
parser.add_argument('--dynamic-exclusion', action='store', dest='DYNAMIC_EXCLUSION', default=None, help='sequence to skip when looking for first dynamic. default search is "fmri"')
#parser.add_argument('-s', '--submit', action="store_true", dest="SUBMIT", help="Submit conversion to condor for parallel conversion", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)




# ******************* Setup Main Processing ********************
def physio_extraction(options: dict):
    """_summary_

    :param options: _description_
    :type options: dict
    :param submit: _description_, defaults to None
    :type submit: str, optional
    :param error: _description_, defaults to None
    :type error: str, optional
    :param output: _description_, defaults to None
    :type output: str, optional
    :param log: _description_, defaults to None
    :type log: str, optional
    :param dagman: _description_, defaults to None
    :type dagman: Dagman, optional
    """    

    #load parameter JSON control file
    try:
        physInputFile = os.path.join(st.creds.dataDir,'code',options.PROJECT + '_physio_extraction_input.json')
        if not os.path.isfile(physInputFile):
            print("ERROR: project physio_extraction_input.json control file not found in project's code directory")
            sys.exit()

        with open(physInputFile) as j:
            physInput = json.load(j)

            #asl sql_query inputs
            incExcDict = {}
            if 'inclusion_list' in physInput:
                incExcDict['inclusion'] = physInput.pop('inclusion_list')
            if 'exclusion_list' in physInput:
                incExcDict['exclusion'] = physInput.pop('exclusion_list')

    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    # regexStr = get_bids_filename(**dtiInput['main_image_params']['input_bids_labels'])

    if not incExcDict:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=physInput['regexstr'],progress=False)
    else:
        filesToProcess = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=physInput['regexstr'],**incExcDict,progress=False)




    # loop throught files
    filesToProcess.sort()
    for f in filesToProcess:

        #get subject name and see if they should be discarded
        st.subject.get_id(os.path.dirname(f))
        st.subject.check(st.creds.dataDir)

        if options.SUBJECTS:
            if not st.subject.id in options.SUBJECTS:
                st.subject.discard = True

        if not st.subject.discard:
            print(f)

            #check for processed output
            outFilepath = os.path.join(st.creds.dataDir, 'derivatives', 'sub-' + st.subject.id, 'ses-' + st.subject.sesNum, 'beh')
            outFile = glob(os.path.join(outFilepath, '*physio-data.csv'))
            # if len(outFile) > 0 and not options.OVERWRITE:
            #     print('WARNING: Output files found in ' + outFilepath)
            #     print('\toverwrite not specified, skipping')
            #     continue

            philips_file = glob(os.path.join(os.path.dirname(f), "*philips-scan-log.csv"))
            if len(philips_file) == 1:
                philips_file = philips_file[0]
            else:
                print('ERROR: did not find the accompanying philips-scan-log.csv')
                continue


            if not os.path.isdir(os.path.dirname(outFilepath)):
                os.makedirs(os.path.dirname(outFilepath))

            l = st.xdf_extract_physio(f,philips_file,Path(outFilepath), options.OVERWRITE, options.DYNAMIC_EXCLUSION)

        


    return


    

    

if __name__ == '__main__':
    """
    The entry point of this program.
    """

    #get and evaluate options
    options = parser.parse_args()
    st.creds.read(options.PROJECT)

   
    physio_extraction(options)
