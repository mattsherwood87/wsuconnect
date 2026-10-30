#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 31 Jan 2023
#
# Last Modified on 5 July 2024 - add removal of processed participants from the PACS database
# Modified on 11 June 2024 - changes to allow for the acceptance of classic DICOMs
# Modified on 28 Feb 2023 - slight changes to grab path of script automatically 

# ******* IMPORTS ***********
from cmath import inf
import os
import pydicom 
import argparse
import json
import pandas as pd
import shutil
import time as tm
import sys
from pathlib import Path
from datetime import datetime, timedelta, time
import traceback
#versioning
VERSION = '4.0.1'
DATE = '25 October 2024'


# ******* LOCAL IMPORTS ******
#GLOBALS
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-2]).resolve()
if not REALPATH in sys.path:
    sys.path.append(REALPATH)
    
import wsuconnect.support_tools as st
from wsuconnect.connect_create_raw_nii import process_single_dir

# ******* GLOBAL INFO *******

DCMPATH = "/PACS_m2"


os.environ["FSLDIR"] = '/usr/local/fsl'
os.system('FSLDIR=' + os.environ["FSLDIR"])

#input argument parser
parser = argparse.ArgumentParser(f'This program monitors a source directory ({DCMPATH}) for new files (DICOM), determines the associated project and subject information, moves the files to the target sourcedata directory, converts to NIfTI, and creates the rawdata directory according to BIDS structure.')
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
 


def string_convert(str_to_convert):
    return str(str_to_convert)


def time_convert(time_to_convert):
    return datetime.strptime(time_to_convert, '%Y%m%d %H%M%S.%f')


def write_log(string_to_write):
    """
    insert string to top logfile /Export/data_transfer_progress/connect_pacs_dicom_grabber-YYYYMM.log

    This log file is written to the scanner Export folder mounted locally to the server.

    Parameters
    ----------
    string_to_write : str
        string to append  
    """
    try:
        if os.path.isfile(os.path.join('/Export','data_transfer_progress','connect_pacs_dicom_grabber-' + datetime.now().strftime('%Y%m') + '.log')):
            file = open(os.path.join('/Export','data_transfer_progress','connect_pacs_dicom_grabber-' + datetime.now().strftime('%Y%m') + '.log'), 'r+')
            l = file.readlines()
        else:
            file = open(os.path.join('/Export','data_transfer_progress','connect_pacs_dicom_grabber-' + datetime.now().strftime('%Y%m') + '.log'), 'x')
            l = []

        l.insert(0,string_to_write + '\n')
        file.seek(0)
        file.writelines(l)
        file.close()

    except Exception as e:
        print("Error Message: {0}".format(e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)



# ******************* MAIN ********************
def main():
    """
    The cli entry point of this program.
    """
    from wsuconnect.data import load as load_data
    from json import loads
    startDateTime = datetime.now()
    # lastUpdateTime = datetime.datetime.now()
    write_log('PACS data grabber now runing @ ' + startDateTime.strftime('%m%d%Y %H:%M:%S'))
    write_log(f'Checking {DCMPATH} for new files...')

    #get and evaluate options
    # options = parse_arguments()
    URL = 'http://10.11.0.31:8042'

    #get start time/date of code
    df_dir = pd.DataFrame(columns=['project','inDir'])
    # df_procData = pd.DataFrame()
    df_procData = pd.DataFrame(columns=['subject','ls_rawDcm','project','sourcedataDir','ls_inDir','ls_acqNum','stableFlag','continueFlag'])
    df_procData.set_index('subject', inplace=True)
    ls_rawDcm = []
    ls_pacsFiles = []
    ls_dirs = []
    ls_patientNames = []
    continueFlag = True




    # Loop over directory recursively
    writeLoopFlag = True

    while True:
        projectIDs = loads(load_data.readable('credentials.json').read_text())
        loopFlag = False
        tm.sleep(30)
        for root, dirs, files in os.walk(DCMPATH, topdown=True):
            
            for filename in files:

                # check if file is in exception list
                currentDateTime = datetime.now()

                # if not ls_dirs:
                if writeLoopFlag:
                    write_log('\tcopying new batch of files [' + str(len(dirs)) + '] @ ' + currentDateTime.strftime('%m%d%Y %H:%M:%S'))
                    writeLoopFlag = False
                loopFlag = True

                try:
                    # Create input file path and read file
                    inFilePath = os.path.join(root,filename)
                
                    #try to read dicom header 
                    dcmHdr = pydicom.dcmread(inFilePath, stop_before_pixels=True)

                    # Split patient name into IRB protocol number and subject number
                    personName = str(dcmHdr[0x0010,0x0010].value)
                    if not personName in df_procData.index: #patientname

                        # print(f"new patient {personName}")
                        df_procData.loc[personName] = {
                            'ls_rawDcm': [],
                            'project': '',
                            'sourcedataDir': '',
                            'ls_inDir': [],
                            'ls_acqNum': [],
                            'stableFlag': False,
                            'continueFlag': True
                        }

                    patientNameSplit = personName.split()
                    if not df_procData.loc[personName,'project']:
                        df_procData.loc[personName,'project'] = patientNameSplit[0]
                    
                    # update destination path
                    if patientNameSplit[0] in projectIDs:
                        if 'dataDir' in projectIDs[patientNameSplit[0]]:
                            tmp_destBasePath = projectIDs[patientNameSplit[0]]['dataDir']
                        else:
                            raise ValueError('dataDir not found in credentials.json for project ' + patientNameSplit[0])
                    else:
                        raise ValueError('Project ' + patientNameSplit[0] + ' not found in credentials.json')
                    tmp_destBasePath = os.path.join(tmp_destBasePath,'sourcedata')


                    # Format Destination File Path
                    destFilePath = os.path.join(tmp_destBasePath, 
                                                f'sub-{patientNameSplit[1]}')
                    
                    if (0x0008,0x0020) in dcmHdr: #studydate
                        studyDate = dcmHdr[0x008,0x0020].value
                    elif (0x0008,0x0021) in dcmHdr: #seriesdate
                        studyDate = dcmHdr[0x008,0x0021].value
                    else: #acquisitiondate
                        studyDate = dcmHdr[0x008,0x0022].value

                    if len(patientNameSplit) >= 3:
                        destFilePath = os.path.join(destFilePath, f'ses-{patientNameSplit[2]}')
                    else:
                        destFilePath = os.path.join(destFilePath, f'ses-{studyDate}')
                    destFilePath = os.path.join(destFilePath, 'acq-%02d_%d_%s' % (int(dcmHdr.AcquisitionNumber), int(float(dcmHdr.SeriesTime)), dcmHdr.ProtocolName))
                    destFilePath = os.path.join(destFilePath, filename)


                    #check if subject/session for this date is in database - ONLY if this hasn't been checked before (once per acquisition)
                    # print(df_procData[["ls_acqNum"]].assign(index=df_procData.index))
                    if (0x0020,0x0012) in dcmHdr: #acquisitionnumber
                        acquisitionNumber = dcmHdr[0x020,0x0012].value
                    else: #seriesnumber fallback
                        acquisitionNumber = dcmHdr[0x020,0x0011].value
                    if not acquisitionNumber in df_procData.loc[personName,'ls_acqNum']:
                        #add acquisition number to tracking dataframe
                        # print(df_procData[["sourcedataDir", "ls_acqNum"]].assign(index=df_procData.index))

                        #query database for subject/session entry
                        formatted_date = f"{studyDate[:4]}-{studyDate[4:6]}-{studyDate[6:]}"
                        if len(patientNameSplit) >= 3:
                            df_scanLog = st.mysql.sql_mri_tracking_query(regex=formatted_date, 
                                                                        searchcol='date',
                                                                        project=f"{patientNameSplit[0]}",
                                                                        subject=f"sub-{patientNameSplit[1]}", 
                                                                        session=f"ses-{patientNameSplit[2]}")
                        else:
                            df_scanLog = st.mysql.sql_mri_tracking_query(regex=formatted_date, 
                                                                        searchcol='date',
                                                                        project=f"{patientNameSplit[0]}",
                                                                        subject=f"sub-{patientNameSplit[1]}",
                                                                        session=f"ses-{studyDate}")
                        
                        #format start and end time for database and database updating
                        
                        if (0x0008,0x0032) in dcmHdr: #acquisitiontime
                            acquisitionTime = dcmHdr[0x008,0x0032].value
                        else: #seriestime fallback
                            acquisitionTime = dcmHdr[0x008,0x0031].value
                        acq_start = None
                        acq_end = None
                        formatted_time = f"{acquisitionTime[0:2]}:{acquisitionTime[2:4]}:{acquisitionTime[4:6]}"
                        try:
                            if (0x0018,0x9073) in dcmHdr: #acquisitionduration
                                acquisitionDuration = dcmHdr[0x0018,0x9073].value
                            else:
                                acquisitionDuration = 60 #default fallback, 60s
                            acq_start = datetime(1900, 1, 1, int(acquisitionTime[0:2]), int(acquisitionTime[2:4]), int(acquisitionTime[4:6]), 0)  # arbitrary date
                            acq_end = acq_start + timedelta(seconds=int(acquisitionDuration))
                            acq_end = timedelta(hours=acq_end.hour,minutes=acq_end.minute,seconds=acq_end.second)
                            formatted_end_time = (datetime.min + acq_end).time().strftime("%H:%M:%S")
                        except:
                            traceback.print_exc()
                            formatted_end_time = None


                        #subject/session/date does not exist in mri_tracking SQL table, then add
                        if df_scanLog.empty:
                            counter = st.mysql.sql_mri_tracking_query_counter(subject=f"sub-{patientNameSplit[1]}", project=f"{patientNameSplit[0]}")
                            if counter:
                                counter += 1
                            print(f"inserting {personName} into sql table with counter {counter}")
                            if len(patientNameSplit) >= 3:
                                st.mysql.sql_mri_tracking_insert(project=f"{patientNameSplit[0]}",
                                                                subject=f"sub-{patientNameSplit[1]}", 
                                                                session=f"ses-{patientNameSplit[2]}", 
                                                                date=formatted_date, 
                                                                scan_start_time=formatted_time, 
                                                                scan_end_time=formatted_end_time,
                                                                all_data=False,
                                                                number_checks=0,
                                                                counter=counter)
                            else:
                                st.mysql.sql_mri_tracking_insert(project=f"{patientNameSplit[0]}",
                                                                subject=f"sub-{patientNameSplit[1]}", 
                                                                session=f"ses-{studyDate}", 
                                                                date=formatted_date, 
                                                                scan_start_time=formatted_time, 
                                                                scan_end_time=formatted_end_time,
                                                                all_data=False,
                                                                number_checks=0,
                                                                counter=counter)

                        #subject/session/date does exist in mri_tracking SQL table, update start or end time as necessary
                        else:
                            print(f'sequence start: {formatted_time}, sequence end {formatted_end_time}')
                            t = timedelta(hours=int(acquisitionTime[0:2]), minutes=int(acquisitionTime[2:4]), seconds=int(acquisitionTime[4:6]))
                            start_t = df_scanLog.loc[0, 'scan_start_time']
                            start_t = start_t.to_pytimedelta() if isinstance(start_t, pd.Timedelta) else start_t
                            end_t = df_scanLog.loc[0, 'scan_end_time']
                            end_t = end_t.to_pytimedelta() if isinstance(end_t, pd.Timedelta) else end_t
                            if formatted_time:
                                if start_t:
                                    if t < start_t:
                                        print(f'scan start updated: {formatted_time}')
                                        df_scanLog.loc[0, 'scan_start_time'] = formatted_time
                                        st.mysql.sql_mri_tracking_set(df_scanLog)
                                else:
                                    print(f'scan start updated: {formatted_time}')
                                    df_scanLog.loc[0, 'scan_start_time'] = formatted_time
                                    st.mysql.sql_mri_tracking_set(df_scanLog)
                            if acq_end:
                                if end_t:
                                    if acq_end > end_t:
                                        print(f'scan end updated: {formatted_end_time}')
                                        df_scanLog.loc[0, 'scan_end_time'] = formatted_end_time
                                        st.mysql.sql_mri_tracking_set(df_scanLog)
                                else:
                                    print(f'scan end updated: {formatted_end_time}')
                                    df_scanLog.loc[0, 'scan_start_time'] = formatted_time
                                    st.mysql.sql_mri_tracking_set(df_scanLog)

                        #add acquisition number if we made it this far!!
                        tmp_ls = df_procData.loc[personName,'ls_acqNum']
                        tmp_ls.append(acquisitionNumber)
                        df_procData.at[personName,'ls_acqNum'] = tmp_ls
                    
                    

                    #move file to the destination path
                    destFilePath = destFilePath.replace(' ','_')
                    if not os.path.exists(os.path.dirname(destFilePath)):
                        os.makedirs(os.path.dirname(destFilePath))
                    shutil.copyfile(inFilePath,destFilePath)
                    ls_pacsFiles.append(inFilePath)
                    

                    #output dict
                    d = {}
                    d['fullpath'] = destFilePath
                    d['filename'] = os.path.basename(destFilePath)
                    


                    #add conversion directory to DCM list
                    dcmDir = os.path.dirname(destFilePath)
                    if not dcmDir in df_procData.loc[personName,'ls_rawDcm']:
                        # ls_rawDcm.append(dcmDir)
                        tmp_ls = df_procData.loc[personName,'ls_rawDcm']
                        tmp_ls.append(dcmDir)
                        df_procData.at[personName,'ls_rawDcm'] = tmp_ls
                        # print(f"setting ls_rawDcm {tmp_ls}")

                    #subject/session sourcedata directory 
                    if not df_procData.loc[personName,'sourcedataDir']:
                        df_procData.loc[personName,'sourcedataDir'] = os.path.dirname(dcmDir)
                        # print(f"setting ls_rawDcm {os.path.dirname(dcmDir)}")
                        
                    if not df_procData.loc[personName,'ls_inDir']:
                        df_procData.loc[personName,'ls_inDir'] = [os.path.dirname(inFilePath)]
                        # print(f"setting ls_rawDcm {os.path.dirname(inFilePath)}")
                    elif not bool([s for s in df_procData.loc[personName,'ls_inDir'] if (os.path.dirname(dcmDir) in s)]):
                        tmp_ls = df_procData.loc[personName,'ls_inDir']
                        tmp_ls.append(os.path.dirname(inFilePath))
                        df_procData.at[personName,'ls_inDir'] = tmp_ls 

                except TypeError as e:
                    ls_pacsFiles.append(inFilePath)
                    traceback.print_exc()

                except pydicom.errors.InvalidDicomError as e:
                    ls_pacsFiles.append(inFilePath)
                    traceback.print_exc()

                except AttributeError as e:
                    ls_pacsFiles.append(inFilePath)
                    print('Attribute Error ')

                except Exception as e:
                    ls_pacsFiles.append(inFilePath)
                    traceback.print_exc()



        # Remove DICOMS - prevent from detection in future loops
        tm.sleep(1)
        if ls_pacsFiles:
            print(f"removing some files from {DCMPATH}")
            for pacsFile in ls_pacsFiles:
                try:
                    if os.path.isfile(pacsFile):
                        os.remove(pacsFile)
                        d = os.path.dirname(pacsFile)
                    while not d.endswith('PACS_m2'):
                        os.rmdir(d)
                        d = os.path.dirname(d)
                except OSError as e:
                    a=e #do nothing
                except Exception as e:
                    traceback.print_exc()
                    # print("Error Message: stop {0}".format(e))
        
            ls_pacsFiles = []


        try:
            patientUIDs = st.RestToolbox.DoGet(URL + '/patients') 
            for patientUID in patientUIDs:
                d_patientInfo = st.RestToolbox.DoGet(URL + '/patients/' + patientUID)
                if not 'MainDicomTags' in d_patientInfo.keys():
                    continue
                # d_patientInfo = st.RestToolbox.DoGet(f'{URL}/studies/{d_patientInfo['Studies'][0]}')
                if d_patientInfo['MainDicomTags']['PatientName'] in df_procData.index and d_patientInfo['IsStable']:
                    df_procData.loc[d_patientInfo['MainDicomTags']['PatientName'],'stableFlag'] = True
        except Exception as e:
            # print("Error Message: {0}".format(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            traceback.print_exc()
        # ls_patientNames = []  


        #Do some additional stuff for datasets that have been fully transferred
        subsToDrop = []    
        # print(len(df_procData))
        for idx, row in df_procData.iterrows():

            #check if "patient" is stable - fully transferred
            if not row['stableFlag']:
                print(f"subject {idx} is not stable")
                continue
            elif row['stableFlag'] and row['continueFlag']: #do 1 more pass for good measure

                print(f"subject {idx} is stable, 1 more loop for good measure")
                write_log(f"\tPatient {idx} is stable but performing one more loop @ {datetime.now().strftime('%m%d%Y %H:%M:%S')}")
                tm.sleep(180)
                df_procData.loc[idx,'continueFlag'] = False
                continue

            write_log(f"\tPatient {idx} is stable, processing data @ {datetime.now().strftime('%m%d%Y %H:%M:%S')}")
            write_log(f"\tclearing patient from PACS database @ {datetime.now().strftime('%m%d%Y %H:%M:%S')}")
            patientUIDs = st.RestToolbox.DoGet(URL + '/patients') 
            for patientUID in patientUIDs:
                d_patientInfo = st.RestToolbox.DoGet(URL + '/patients/' + patientUID)
                if not 'MainDicomTags' in d_patientInfo.keys():
                    st.RestToolbox.DoDelete(URL + '/patients/' + patientUID)
                    continue
                if d_patientInfo['MainDicomTags']['PatientName'] == idx:
                    subsToDrop.append(idx)
                    st.RestToolbox.DoDelete(URL + '/patients/' + patientUID)
            


            # list files and add to table/resshare/projects/2023_UES/EPIC/sourcedata/sub-1106/ses-20240610-1A/acq-06_123445_B0_map
            for destFilePath in row['ls_rawDcm']:
                try:

                    write_log('\t' + destFilePath)
                    write_log('\t\tconverting DICOMS and other fun stuff in @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
                    #Convert DICOM to NIfTI images
                    st.convert_dicoms(destFilePath,progress=False)
                    
                    #insert new NIfTI images into SQL table
                    d = {}
                    fullpath = []
                    filename = []
                    # for path in Path(os.path.dirname(destFilePath)).glob('*'):
                    #     if not os.path.isdir(str(path)):
                    #         fullpath.append(str(path))
                    #         filename.append(os.path.basename(str(path)))
                    # d['fullpath'] = fullpath
                    # d['filename'] = filename

                    tmp_project = row['project']
                    st.creds.read(tmp_project)
                    #print(tmp_project + ' ' + destFilePath)
                    #sql_table_insert(creds.searchSourceTable,d)



                    #now I can copy nifti files!!!
                    write_log('\t\tcreating rawdata files from sourcedata @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
                    ls_updatedFiles = process_single_dir(os.path.dirname(destFilePath),True,False)[0]
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
                        
                        st.mysql.sql_table_insert(st.creds.searchTable,d)

                except Exception as e:
                    # print("Error Message: {0}".format(e))
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    traceback.print_exc()

                    write_log("\t\tError Message: {0}".format(e))
                    write_log('\t\t' + str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))


            write_log("\tEvaluating files in subject rawdata directory")
            try:
                # print(df_procData.loc[idx])
                st.evaluate_source_file_transfer(row['project'], row['sourcedataDir'])
            except Exception as e:
                # print("Error Message: {0}".format(e))
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                traceback.print_exc()

                write_log("\t\tError Message: {0}".format(e))
                write_log('\t\t' + str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))


            write_log('\tFinished processing DICOM group @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
            write_log('Checking /PACS_m2 for new files...')
            writeLoopFlag = True
            continueFlag = True

        if subsToDrop:
            for item in subsToDrop:
                print(f"finalized subject {item}")
                df_procData = df_procData.drop(item)

                       
                


if __name__ == '__main__':
    main()
