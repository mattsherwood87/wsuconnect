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
parser.add_argument('--old-scan-id', action="store", dest="OLDSCANID", help="filename of old scan IDs", default=None)
parser.add_argument('-t', '--test', action="store_true", dest="TEST", help="print conversion information only", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)



# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json
    ls_updatedFiles = []
    ls_existingFiles = []

    #get and evaluate options
    options = parser.parse_args()
    
    if options.version:
        print('connect_dcm2nii.py version {0}.'.format(VERSION)+" DATED: "+DATE)
    
    # #determine if the project exists
    # if not options.PROJECT in st.creds.projects:
    #     if not options.version:
    #         print("ERROR: user must define a project using [-p|--project <project>]\n\n")
    #         parser.print_help()
    #     sys.exit()

    
    st.creds.read(options.PROJECT)


    inputJson = os.path.join(st.creds.dataDir,'code',st.creds.project + '_scan_id.json')
    with open(inputJson) as j:
        inputParams = json.load(j)

    if options.OLDSCANID:
        # inputJson = options.OLDSCANID
        inputJson = options.OLDSCANID
    else:
        inputJson = os.path.join(st.creds.dataDir,'code',st.creds.project + '_scan_id.json.bak')
    with open(inputJson) as j:
        old_inputParams = json.load(j)


    # find all directories to process
    for k in old_inputParams.keys():

        if not 'bids_labels' in old_inputParams[k] and not "BidsDir" in inputParams[k]:
            continue
        if 'bids_labels' in old_inputParams[k]:
            orig_filename = st.bids.get_bids_filename(**old_inputParams[k]['bids_labels'], extension='nii.gz')
        else:
            orig_filename = inputParams[k]['BidsDir']

        allFiles = st.mysql.sql_query(st.creds.searchTable, regex=orig_filename, searchcol="fullpath", inclusion="rawdata")

        for f in sorted(allFiles):
            if not 'sub' in f and not 'ses' in f:
                print(f"No subject/session {f}")
                continue
            st.subject.get_id(f)
            if 'bids_labels' in old_inputParams[k]:
                new_filename = st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**inputParams[k]['bids_labels'],extension='nii.gz')
            else:
                new_filename = os.path.basename(f)
            bidsDir = inputParams[k]['BidsDir']
      

            new_filename = os.path.join(st.creds.dataDir,'rawdata','sub-' + st.subject.id,'ses-' + st.subject.sesNum,bidsDir,new_filename)

            if f == new_filename:
                # print(f)
                # print(f"NO change: {new_filename}")
                continue

            print(f)
            print(f"\t{new_filename}")

            if not options.TEST:
                if not os.path.isdir(os.path.dirname(new_filename)):
                    os.makedirs(os.path.dirname(new_filename))

                    # if os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(f)),'beh')):
                    #     shutil.move(os.path.join(os.path.dirname(os.path.dirname(f)),'beh'), os.path.join(os.path.dirname(os.path.dirname(new_filename)),'beh'))

                if os.path.isfile(f):
                    shutil.move(f, new_filename)

            for ext in ['.txt','.json','.bvec','.bval']:
                new_f = f.replace('.nii.gz',ext)
                if os.path.isfile(new_f):
                    if options.TEST:
                        print(f"\t{new_filename.replace('.nii.gz',ext)}")
                    else:
                        shutil.move(new_f,new_filename.replace('.nii.gz',ext))

                if 'asl.nii.gz' in f:
                    new_f = f.replace('asl.nii.gz','aslcontext.tsv')
                    
                    if os.path.isfile(new_f):
                        if options.TEST:
                            print(f"\t{new_filename.replace('asl.nii.gz','aslcontext.tsv')}")
                        else:
                            shutil.move(new_f,new_filename.replace('asl.nii.gz','aslcontext.tsv'))

            if not options.TEST and os.path.dirname(f) != os.path.dirname(new_filename):
                os.system('rmdir ' + os.path.dirname(f))
                os.system('rmdir ' + os.path.dirname(os.path.dirname(f)))


    print('\nCOMPLETE')






