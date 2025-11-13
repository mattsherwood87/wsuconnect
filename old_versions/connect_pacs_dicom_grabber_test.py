#!/resshare/general_processing_codes/python3_venv/bin/python
# the command above ^^^ sets python 3.7.5 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 31 Jan 2023
#
# Last Modified on 11 June 2024 - changes to allow for the acceptance of classic DICOMs
# Modified on 28 Feb 2023 - slight changes to grab path of script automatically 

# ******* IMPORTS ***********
from cmath import inf
import os
import sys
import pydicom 
import argparse
import json
import pandas as pd
import shutil
import datetime
# import numpy as np
# import math
import time
import sys
# import aspose.pdf as ap
from pathlib import Path


# ******* LOCAL IMPORTS ******
#GLOBALS
REALPATH = os.path.dirname(os.path.realpath(__file__))
sys.stdout.write('Importing local functions\n')

sys.path.append(REALPATH)
from helper_functions.convert_dicoms import convert_dicoms
from helper_functions.mysql_commands import *
from helper_functions.read_credentials import *
from helper_functions import RestToolbox as RT
from support_tools.creds import *
from connect_create_raw_nii import process_single_dir
from helper_functions.evaluate_raw_file_transfer import evaluate_raw_file_transfer

sys.stdout.write('\tdone\n')

# ******* GLOBAL INFO *******
#versioning
VERSION = '3.0.1'
DATE = '17 Jun 2024'

#input argument parser
parser = argparse.ArgumentParser()

os.environ["FSLDIR"] = '/usr/local/fsl'
os.system('FSLDIR=' + os.environ["FSLDIR"])
# os.system('source /etc/profile.d/fsl.sh')

sys.stdout.write('Environment set\n')

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
def parse_arguments():

    #input options for main()
    # requiredNamed = parser.add_argument_group('required arguments')
    # requiredNamed.add_argument('-p','--path', action="store", dest="PATH", help="define search path", default=None)
    parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
    # parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
    options = parser.parse_args()

    return options


def string_convert(str_to_convert):
    return str(str_to_convert)

def time_convert(time_to_convert):
    return datetime.datetime.strptime(time_to_convert, '%Y%m%d %H%M%S.%f')

def write_log(string_to_write):
    try:
        file = open(os.path.join(REALPATH,'logs','connect_pacs_dicom_grabber-' + datetime.datetime.now().strftime('%Y%m') + '.log'), 'a+')
        file.write(string_to_write + '\n')
        file.close()
    except Exception as e:
        print("Error Message: {0}".format(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """

    #get and evaluate options
    # options = parse_arguments()
    dcmPath = "/PACS_m2"
    URL = 'http://10.11.0.31:8042'

    #get start time/date of code
    startDateTime = datetime.datetime.now()
    lastUpdateTime = datetime.datetime.now()
    df_dir = pd.DataFrame(columns=['project','inDir'])
    ls_rawDcm = []
    ls_pacsFiles = []


    with open(os.path.join(REALPATH,'credentials.json')) as f:
        projectIDs = json.load(f)


    # Loop over directory recursively

    ls_dirs = []
    while True:

        #look for any new patients
        patientUIDs = RT.DoGet(URL + '/patients')

        #loop over any found patients
        for patientUID in patientUIDs:
            ls_outLog = []

            try:
                #get patient information
                d_patientInfo = RT.DoGet(URL + '/patients/' + patientUID)
                sys.stdout.write('Found patient ' + d_patientInfo['MainDicomTags']['PatientName'] + ' @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S') + '\n')
                write_log('Found patient ' + d_patientInfo['MainDicomTags']['PatientName'] + ' @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))

                #separate out patient name (project, subject ID, session [optional])
                if not 'MainDicomTags' in d_patientInfo.keys():
                    continue
                patientNameSplit = d_patientInfo['MainDicomTags']['PatientName'].split()
                
                # update destination path
                if patientNameSplit[0] in projectIDs:
                    if 'dataDir' in projectIDs[patientNameSplit[0]]:
                        tmp_destBasePath = projectIDs[patientNameSplit[0]]['dataDir']
                    else:
                        write_log('\tERROR: dataDir not found in credentials.json for project ' + patientNameSplit[0])
                        RT.DoDelete(URL + '/patients/' + patientUID)
                        raise ValueError('dataDir not found in credentials.json for project ' + patientNameSplit[0])
                else:
                    write_log('\tERROR: Project NOT FOUND in credentials.json')
                    RT.DoDelete(URL + '/patients/' + patientUID)
                    raise ValueError('Project ' + patientNameSplit[0] + ' not found in project_identifiers.json')
                tmp_destBasePath = os.path.join(tmp_destBasePath,'sourcedata')
                

                # Determine if data transfer is complete
                isStable = d_patientInfo['IsStable']

                #if not complete, wait until complete
                while not isStable:
                    # time.sleep(30)
                    # d_patientInfo = RT.DoGet(URL + '/patients/' + patientUID)
                    # isStable = d_patientInfo['IsStable']
                
                    print('\tPatient is stable @', datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                    write_log('\tPatient is stable @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))

                    # Get info from all images
                    d_seriesS = RT.DoGet(URL + '/patients/' + patientUID + '/studies')[0]
                    d_seriesS = d_seriesS['Series']

                    #loop over all images
                    for series in d_seriesS:

                        #get series info, wait for series to be stable
                        d_series = RT.DoGet(URL + '/series/' + series)
                        seriesStable = d_series['IsStable']
                        while not seriesStable:
                            time.sleep(30)
                            d_series = RT.DoGet(URL + '/series/' + series)
                            seriesStable = d_series['IsStable']

                        if not 'MainDicomTags' in d_series.keys():
                            continue
                        else:
                            if not 'ProtocolName' in d_series['MainDicomTags'].keys():
                                continue
                        
                        

                        seriesStartTime = datetime.datetime.now()
                        write_log('\t\tworking new series ' + d_series['MainDicomTags']['ProtocolName'] + ' @ ' + seriesStartTime.strftime('%m%d%Y %H:%M:%S'))
                        if d_series['MainDicomTags']['SeriesInstanceUID'] == '1.3.46.670589.54.2.15933249081091640911.31586148384085399051':
                            continue

                        try:
                            d_studyInfo = RT.DoGet(URL + '/studies/' + d_series['ParentStudy'])
                        except Exception as e:
                            # print("Error Message: {0}".format(e))
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            print(exc_type, fname, exc_tb.tb_lineno)

                            tmp_str = str(exc_type) + ' ' + fname + ' ' + str(exc_tb.tb_lineno)
                            for k in d_series.keys():
                                if isinstance(d_series[k],str):
                                    tmp_str += '\n\t\t' + d_series[k]
                            write_log(tmp_str)
                            continue

                        # Loop over all instances [Images]
                        instanceUIDs = d_series['Instances']
                        for instanceUID in instanceUIDs:
                            currentTime = datetime.datetime.now()
                            if currentTime - seriesStartTime > datetime.timedelta(minutes=60):
                                raise ValueError('processing time exceeds what was expected, restart and see if that helps')
                            
                            d_instance = RT.DoGet(URL + '/instances/' + instanceUID)

                            #get path of instance [image]
                            srcFile = os.path.join(dcmPath,
                                                d_instance['FileUuid'][0:2],
                                                d_instance['FileUuid'][2:4],
                                                d_instance['FileUuid'])
                        
                            # Format Destination File Path
                            destFilePath = os.path.join(tmp_destBasePath, 
                                                        'sub-' + patientNameSplit[1], 
                                                        'ses-' + d_studyInfo['MainDicomTags']['StudyDate'])
                            
                            #add options session identifier
                            if len(patientNameSplit) >= 3:
                                destFilePath = destFilePath + '-' + patientNameSplit[2]

                            #add acquisition info (directory) to destination
                            if 'AcquisitionNumber' in d_instance['MainDicomTags'].keys():
                                if 'SeriesTime' in d_series['MainDicomTags'].keys():
                                    destFilePath = os.path.join(destFilePath, 'acq-%02d_%d_%s' % (int(d_instance['MainDicomTags']['AcquisitionNumber']), int(float(d_series['MainDicomTags']['SeriesTime'])), d_series['MainDicomTags']['ProtocolName'].replace(' ','-')))
                                else:
                                    destFilePath = os.path.join(destFilePath, 'acq-%02d_XXXXXX_%s' % (int(d_instance['MainDicomTags']['AcquisitionNumber']), d_series['MainDicomTags']['ProtocolName'].replace(' ','-')))
                            else:
                                if 'SeriesTime' in d_series['MainDicomTags'].keys():
                                    destFilePath = os.path.join(destFilePath, 'acq-99_%d_%s' % (int(float(d_series['MainDicomTags']['SeriesTime'])), d_series['MainDicomTags']['ProtocolName'].replace(' ','-')))
                                else:
                                    if 'ProtocolName' in d_series['MainDicomTags'].keys():
                                        destFilePath = os.path.join(destFilePath, 'acq-99_XXXXXX_%s' % (d_series['MainDicomTags']['ProtocolName'].replace(' ','-')))
                                    else:
                                        destFilePath = os.path.join(destFilePath, 'acq-99_XXXXXX_YYYY')


                            #format destination filename
                            if 'InstanceNumber' in d_instance['MainDicomTags'].keys(): #dicom contains multiple frames, only expect 1 file
                                destFilePath = os.path.join(destFilePath,
                                                            'IM_%05d' % int(d_instance['MainDicomTags']['InstanceNumber']))
                            else:
                                destFilePath = os.path.join('IM')
                                                    
                            if 'TemporalPositionIdentifier' in d_instance['MainDicomTags'].keys(): #dicom has multiple temporal positions (part of a dynamic or functional set of images)
                                destFilePath = destFilePath + '_%03d' % int(d_instance['MainDicomTags']['TemporalPositionIdentifier'])
                        

                            # Move file to the destination path
                            destFilePath = destFilePath.replace(' ','_')
                            if not os.path.exists(os.path.dirname(destFilePath)):
                                os.makedirs(os.path.dirname(destFilePath))

                            if os.path.isfile(srcFile):
                                shutil.move(srcFile,destFilePath)

                            ls_pacsFiles.append(srcFile)

                            #update sourcedata table with dcm files
                            d = {}
                            d['fullpath'] = destFilePath
                            d['filename'] = os.path.basename(destFilePath)
                            # sql_table_insert(creds.searchSourceTable,d))
                            sql_table_insert(projectIDs[patientNameSplit[0]]['project'].replace('-','_') + '_sourcedata',d)


                            #add conversion directory to DCM list
                            dcmDir = os.path.dirname(destFilePath)
                            if not dcmDir in ls_rawDcm:
                                ls_rawDcm.append(dcmDir)
                                
                            if not df_dir['inDir'].str.contains(os.path.dirname(dcmDir)).any():
                                df_dir = pd.concat([df_dir,pd.DataFrame.from_dict({'project':[projectIDs[patientNameSplit[0]]['project']], 'inDir':[os.path.dirname(dcmDir)]})],ignore_index=True)

                            RT.DoDelete(URL + '/instances/' + instanceUID)

                        #cleanup series
                        RT.DoDelete(URL + '/series/' + d_series['ID'])
                            
                    
                    time.sleep(30)
                    d_patientInfo = RT.DoGet(URL + '/patients/' + patientUID)

                    if not d_seriesS and d_patientInfo['IsStable']:
                        isStable = False

                # Finished with Patient, clear out patient and changes
                write_log('\tfinished copying raw DICOMS @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                RT.DoDelete(URL + '/patients/' + patientUID)
                RT.DoDelete(URL + '/changes')
                write_log('\tfinished removing patient from PACS database @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))

            except Exception as e:
                # print("Error Message: {0}".format(e))
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

                write_log(str(exc_type) + ' ' + fname + ' ' + str(exc_tb.tb_lineno) + ' @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                write_log("Error Message: {0}".format(e))
                continue
            
            # do some cool stuff with the destination 
            if ls_rawDcm: #not df_dir.empty:
                write_log('\tremoving empty directories from PACS temporary directory @ '+ datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                for d in ls_pacsFiles:
                
                    try:
                        # shutil.rmtree(d, ignore_errors=True)
                        # if len(os.listdir(os.path.dirname(d))) == 0:
                        #     os.rmdir(os.path.dirname(d))
                        d = os.path.dirname(d)
                        while not d.endswith('PACS'):
                            # if os.path.isdir(d):
                            #     if len(os.listdir(d)) == 0:
                            os.rmdir(d)
                            d = os.path.dirname(d)

                    except Exception as e:
                        print("Error Message: {0}".format(e))
                        # exc_type, exc_obj, exc_tb = sys.exc_info()
                        # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        # print(exc_type, fname, exc_tb.tb_lineno)
                ls_pacsFiles = []

                # list files and add to table/resshare/projects/2023_UES/EPIC/sourcedata/sub-1106/ses-20240610-1A/acq-06_123445_B0_map
                # print()
                write_log('\tcreating dicoms and other activities @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                for destFilePath in ls_rawDcm:
                    try:
                        #Convert DICOM to NIfTI images
                        convert_dicoms(destFilePath,False)
                        
                        #insert new NIfTI images into SQL table
                        d = {}
                        fullpath = []
                        filename = []
                        for path in Path(os.path.dirname(destFilePath)).glob('*'):
                            if not os.path.isdir(str(path)):
                                fullpath.append(str(path))
                                filename.append(os.path.basename(str(path)))
                        d['fullpath'] = fullpath
                        d['filename'] = filename

                        tmp_project = ''
                        for k in projectIDs.keys():
                            if isinstance(projectIDs[k],dict):
                                if 'dataDir' in projectIDs[k].keys():
                                    if projectIDs[k]['dataDir'] in destFilePath:
                                        tmp_project = projectIDs[k]['project']
                                        break
                        read_credentials(tmp_project)
                        print(tmp_project + ' ' + destFilePath)
                        sql_table_insert(creds.searchSourceTable,d)



                        #now I can copy nifti files!!!
                        ls_updatedFiles = process_single_dir(os.path.dirname(destFilePath),False,False)[0]
                        if ls_updatedFiles:
                            d = {}
                            fullpath = []
                            filename = []
                            baseFilename = []
                            extension = []
                            for f in ls_updatedFiles:
                                fullpath.append(f)
                                filename.append(os.path.basename(f))
                                idx = os.path.basename(f).find('.')
                                if idx != -1:
                                    if idx == 0:
                                        baseFilename.append('NULL')
                                        extension.append(os.path.basename(f))
                                    else:
                                        baseFilename.append(os.path.basename(f)[:idx])
                                        extension.append(os.path.basename(f)[idx+1:])
                                else:
                                    baseFilename.append(os.path.basename(f))
                                    extension.append('NULL')
                            d['fullpath'] = fullpath
                            d['filename'] = filename
                            d['basename'] = baseFilename
                            d['extension'] = extension
                            
                            sql_table_insert(creds.searchTable,d)

                    except Exception as e:
                        print("Error Message: {0}".format(e))
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)

                # Check if all NIfTIs were found in rawdata directory
                for index, row in df_dir.iterrows():
                    allFiles = False
                    try:
                        allFiles = evaluate_raw_file_transfer(row['project'],row['inDir'])
                    except Exception as e:
                        print("Error Message: {0}".format(e))
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno)
                    
                    if allFiles:
                        write_log('\tfound all files in rawdata')
                    else:
                        write_log('\tdid NOT find all files in rawdata')

                    
                df_dir = pd.DataFrame(columns=['project','inDir'])
                ls_rawDcm = []

                write_log('\tfinished patient @ ' + datetime.datetime.now().strftime('%m%d%Y %H:%M:%S'))
                # try:
                #     file = open(os.path.join(REALPATH,'logs','connect_pacs_dicom_grabber-' + datetime.datetime.now().strftime('%Y%m') + '.log'), 'a+')
                #     for l in ls_outLog:
                #         file.write(l + '\n')
                #     file.close()
                # except Exception as e:
                #     print("Error Message: {0}".format(e))
                #     exc_type, exc_obj, exc_tb = sys.exc_info()
                #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                #     print(exc_type, fname, exc_tb.tb_lineno)


        # Remove DICOMS - prevent from detection in future loops
        time.sleep(60)

        

                


if __name__ == '__main__':
    main()
