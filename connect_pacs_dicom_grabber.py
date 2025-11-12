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
#versioning
VERSION = '4.0.1'
DATE = '25 October 2024'


# ******* LOCAL IMPORTS ******
#GLOBALS
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-2]).resolve()
if not REALPATH in sys.path:
    sys.path.append(REALPATH)
    
import support_tools as st
from connect_create_raw_nii import process_single_dir

# ******* GLOBAL INFO *******


os.environ["FSLDIR"] = '/usr/local/fsl'
os.system('FSLDIR=' + os.environ["FSLDIR"])

#input argument parser
parser = argparse.ArgumentParser('This program monitors a source directory (/PACS_ms) for new files (DICOM), determines the associated project and subject information, moves the files to the target sourcedata directory, converts to NIfTI, and creates the rawdata directory according to BIDS structure.')
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
    write_log('Checking /PACS_m2 for new files...')

    #get and evaluate options
    # options = parse_arguments()
    dcmPath = "/PACS_m2"
    URL = 'http://10.11.0.31:8042'

    #get start time/date of code
    df_dir = pd.DataFrame(columns=['project','inDir'])
    df_procData = pd.DataFrame()
    ls_rawDcm = []
    ls_pacsFiles = []
    ls_dirs = []
    ls_patientNames = []
    continueFlag = True


    projectIDs = loads(load_data.readable('credentials.json').read_text())


    # Loop over directory recursively
    writeLoopFlag = True

    while True:
        loopFlag = False
        tm.sleep(30)
        for root, dirs, files in os.walk(dcmPath, topdown=True):
            
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
                    dcmHdr = pydicom.dcmread(inFilePath)

                    # Split patient name into IRB protocol number and subject number
                    if not dcmHdr.PatientName.family_name in df_procData.keys():
                        df_procData[dcmHdr.PatientName.family_name] = {
                            'ls_rawDcm': [],
                            'project': '',
                            'sourcedataDir': '',
                            'ls_inDir': [],
                            'stableFlag': False,
                            'continueFlag': False
                        }
                    patientNameSplit = dcmHdr.PatientName.family_name.split()
                    if not df_procData[dcmHdr.PatientName.family_name]['project']:
                        df_procData[dcmHdr.PatientName.family_name]['project'] = patientNameSplit[0]
                    
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
                                                'sub-' + patientNameSplit[1])
                    
                    if len(patientNameSplit) >= 3:
                        destFilePath = os.path.join(destFilePath, 'ses-' + patientNameSplit[2])
                    else:
                        destFilePath = os.path.join(destFilePath, 'ses-' + dcmHdr.StudyDate)

                    destFilePath = os.path.join(destFilePath, 'acq-%02d_%d_%s' % (int(dcmHdr.AcquisitionNumber), int(float(dcmHdr.SeriesTime)), dcmHdr.ProtocolName))
                    destFilePath = os.path.join(destFilePath, filename)

                    # d_scanLog = {}
                    # try:
                    #     d_scanLog = loads(load_data.readable(dcmHdr.StudyDate[0:4],dcmHdr.StudyDate[0:6] + '_scan_dates.json').read_text())
                    # except FileNotFoundError:
                    #     print('did not find scan_dates.json file')

                    #check if subject/session for this date is in database
                    formatted_date = f"{dcmHdr.StudyDate[:4]}-{dcmHdr.StudyDate[4:6]}-{dcmHdr.StudyDate[6:]}"
                    if len(patientNameSplit) >= 3:
                        df_scanLog = st.mysql.sql_mri_tracking_query(regex=formatted_date, 
                                                                     searchcol='date',
                                                                     project=f"sub-{patientNameSplit[0]}",
                                                                     subject=f"sub-{patientNameSplit[1]}", 
                                                                     session=f"ses-{patientNameSplit[2]}")
                    else:
                        df_scanLog = st.mysql.sql_mri_tracking_query(regex=formatted_date, 
                                                                     searchcol='date',
                                                                     project=f"sub-{patientNameSplit[0]}",
                                                                     subject=f"sub-{patientNameSplit[1]}")
                    b_fileUpdated = not df_scanLog.empty


                    try:
                        formatted_time = f"{dcmHdr['AcquisitionTime'][0:2]}:{dcmHdr['AcquisitionTime'][2:4]}:{dcmHdr['AcquisitionTime'][4:6]}"
                        acq_start = datetime(1900, 1, 1, dcmHdr['AcquisitionTime'][0:2], dcmHdr['AcquisitionTime'][2:4], dcmHdr['AcquisitionTime'][4:6], 0)  # arbitrary date
                        acq_end = acq_start + timedelta(seconds=dcmHdr['AcquisitionDuration'])
                        # end_time = acq_end.time()
                        acq_end = timedelta(hours=acq_end.hour,minutes=acq_end.minute,seconds=acq_end.second)
                        formatted_end_time = acq_end.strftime("%H:%M:%S")
                    except:
                        formatted_time = None
                        formatted_end_time = None


                    #subject/session/date does not exist in mri_tracking SQL table, then add
                    if b_fileUpdated:
                        if len(patientNameSplit) >= 3:
                            st.mysql.sql_mri_tracking_insert(project=f"sub-{patientNameSplit[0]}",
                                                             subject=f"sub-{patientNameSplit[1]}", 
                                                             session=f"ses-{patientNameSplit[2]}", 
                                                             date=formatted_date, 
                                                             scan_start_time=formatted_time, 
                                                             scan_end_time=formatted_end_time)
                        else:
                            st.mysql.sql_mri_tracking_insert(project=f"sub-{patientNameSplit[0]}",
                                                             subject=f"sub-{patientNameSplit[1]}", 
                                                             session=f"ses-{dcmHdr.StudyDate}", 
                                                             date=formatted_date, 
                                                             scan_start_time=formatted_time, 
                                                             scan_end_time=formatted_end_time)
                        # formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                        # p = load_data(dcmHdr.StudyDate[0:4])
                        # p.mkdir(exist_ok=True)
                        # p = load_data(f"{dcmHdr.StudyDate[0:4]}/{dcmHdr.StudyDate[0:6]}_scan_dates.json")
                        # with open(str(p),'w') as j:
                        #     json.dump(d_scanLog,j,indent='\t', sort_keys=True)

                    #subject/session/date does exist in mri_tracking SQL table, update start or end time as necessary
                    else:
                        t = timedelta(hours=dcmHdr['AcquisitionTime'][0:2], minutes=dcmHdr['AcquisitionTime'][2:4], seconds=dcmHdr['AcquisitionTime'][4:6])
                        start_t = df_scanLog.loc[0, 'scan_start_time']
                        start_t = start_t.to_pytimedelta() if isinstance(start_t, pd.Timedelta) else start_t
                        end_t = df_scanLog.loc[0, 'scan_end_time']
                        end_t = start_t.to_pytimedelta() if isinstance(start_t, pd.Timedelta) else start_t
                        if acq_start and start_t:
                            if t < start_t:
                                df_scanLog.loc[0, 'scan_start_time'] = formatted_time
                                st.mysql.sql_mri_tracking_set(df_scanLog)
                        if acq_end and end_t:
                            if acq_end > end_t:
                                df_scanLog.loc[0, 'scan_end_time'] = formatted_end_time
                                st.mysql.sql_mri_tracking_set(df_scanLog)
                    
                    

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
                    if not dcmDir in df_procData[dcmHdr.PatientName.family_name]['ls_rawDcm']:
                        # ls_rawDcm.append(dcmDir)
                        tmp_ls = df_procData[dcmHdr.PatientName.family_name]['ls_rawDcm']
                        tmp_ls.append(dcmDir)
                        df_procData[dcmHdr.PatientName.family_name]['ls_rawDcm'] = tmp_ls

                    #subject/session sourcedata directory 
                    if not df_procData[dcmHdr.PatientName.family_name]['sourcedataDir']:
                        df_procData[dcmHdr.PatientName.family_name]['sourcedataDir'] = os.path.dirname(dcmDir)
                        
                    if not df_procData[dcmHdr.PatientName.family_name]['ls_inDir']:
                        df_procData[dcmHdr.PatientName.family_name]['ls_inDir'] = [os.path.dirname(inFilePath)]
                    elif not bool([s for s in df_procData[dcmHdr.PatientName.family_name]['ls_inDir'] if (os.path.dirname(dcmDir) in s)]):
                        tmp_ls = df_procData[dcmHdr.PatientName.family_name]['ls_inDir']
                        tmp_ls.append(os.path.dirname(inFilePath))
                        df_procData[dcmHdr.PatientName.family_name]['ls_inDir'] = tmp_ls 

                except TypeError as e:
                    ls_pacsFiles.append(inFilePath)

                except pydicom.errors.InvalidDicomError as e:
                    ls_pacsFiles.append(inFilePath)

                except Exception as e:
                    ls_pacsFiles.append(inFilePath)



        # Remove DICOMS - prevent from detection in future loops
        tm.sleep(1)
        for pacsFile in ls_pacsFiles:
            try:
                if os.path.isfile(pacsFile):
                    os.remove(pacsFile)
                    d = os.path.dirname(pacsFile)
                while not d.endswith('PACS_m2'):
                    os.rmdir(d)
                    d = os.path.dirname(d)
            except Exception as e:
                a=e
                # print("Error Message: stop {0}".format(e))
        
        if ls_pacsFiles:
            ls_pacsFiles = []


        try:
            patientUIDs = st.RestToolbox.DoGet(URL + '/patients') 
            for patientUID in patientUIDs:
                d_patientInfo = st.RestToolbox.DoGet(URL + '/patients/' + patientUID)
                if not 'MainDicomTags' in d_patientInfo.keys():
                    continue
                if d_patientInfo['MainDicomTags']['PatientName'] in df_procData.keys() and d_patientInfo['IsStable']:
                    df_procData[d_patientInfo['MainDicomTags']['PatientName']]['stableFlag'] = True
        except Exception as e:
            print("Error Message: {0}".format(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
        # ls_patientNames = []  
                
        for k in df_procData.keys():
            if not df_procData[k]['stableFlag']:
                continue
            elif df_procData[k]['stableFlag'] and df_procData[k]['continueFlag']: #do 1 more pass for good measure

                write_log('\tPatient ' + k + ' is stable but performing one more loop @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
                tm.sleep(240)
                df_procData[k]['continueFlag'] = False
                continue


            write_log('\tPatient ' + k + ' is stable, processing data @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
            write_log('\tclearing patient from PACS database @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
            patientUIDs = st.RestToolbox.DoGet(URL + '/patients') 
            for patientUID in patientUIDs:
                d_patientInfo = st.RestToolbox.DoGet(URL + '/patients/' + patientUID)
                if not 'MainDicomTags' in d_patientInfo.keys():
                    st.RestToolbox.DoDelete(URL + '/patients/' + patientUID)
                    continue
                if d_patientInfo['MainDicomTags']['PatientName'] == k:
                    st.RestToolbox.DoDelete(URL + '/patients/' + patientUID)
            


            # list files and add to table/resshare/projects/2023_UES/EPIC/sourcedata/sub-1106/ses-20240610-1A/acq-06_123445_B0_map
            for destFilePath in df_procData[k]['ls_rawDcm']:
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

                    tmp_project = df_procData[k]['project']
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
                    print("Error Message: {0}".format(e))
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

                    write_log("\t\tError Message: {0}".format(e))
                    write_log('\t\t' + str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))


            write_log("\tEvaluating files in subject rawdata directory")
            try:
                st.evaluate_source_file_transfer(df_procData[k]['project'],df_procData[k]['sourcedataDir'])
            except Exception as e:
                print("Error Message: {0}".format(e))
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)

                write_log("\t\tError Message: {0}".format(e))
                write_log('\t\t' + str(exc_type) + ' ' + str(fname) + ' ' + str(exc_tb.tb_lineno))

                
            df_procData = df_procData.drop(k,axis='columns')


            write_log('\tFinished processing DICOM group @ ' + datetime.now().strftime('%m%d%Y %H:%M:%S'))
            write_log('Checking /PACS_m2 for new files...')
            writeLoopFlag = True
            continueFlag = True

                       
                


if __name__ == '__main__':
    main()
