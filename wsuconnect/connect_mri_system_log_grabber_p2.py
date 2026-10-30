#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 13 July 2023
#
# Last Modified on 1 Aug 2024 - added functionality to adapt to R11 software revision changes from r5.7
# 

# ******* IMPORTS ***********
import os
import argparse
import json
import pandas as pd
import shutil
import datetime
import csv
import re
# import numpy as np
# import math
import time
import sys
from pathlib import Path
from chardet import detect
import codecs
import numpy as np
from pathlib import Path
import traceback


# ******* LOCAL IMPORTS ******
#GLOBALS
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-1]).resolve()
if not any(Path(p).resolve() == str(REALPATH) for p in sys.path if Path(p).exists()):
    sys.path.append(str(REALPATH))
import wsuconnect.support_tools as st


# ******* GLOBAL INFO *******
#versioning
VERSION = '2.0.1'
DATE = '1 August 2024' 

#input argument parser
parser = argparse.ArgumentParser(description="Extract the scan events in a Philips MRI system log and write a philips-scan-log.csv for each subject/session to the project's sourcedata and rawdata directories.")


time_offset = None

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input options for main()
requiredNamed = parser.add_argument_group('required arguments')
requiredNamed.add_argument('-i','--in', action="store", dest="INLOGFILE", help="input Philips system logfile", default=None)
requiredNamed.add_argument('--offset', action="store", dest="OFFSET", help="hour offset (int) to apply to all logfile times", default=None)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
# parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)


def parse_arguments():
    options = parser.parse_args()

    return options


def string_convert(str_to_convert):
    return str(str_to_convert)

def date_convert(time_to_convert):
    return datetime.datetime.strptime(time_to_convert, '%m/%d/%Y %H:%M:%S')

def get_encoding_type(file):
    with open(file, 'rb') as f:
        rawdata = f.read()
    return detect(rawdata)['encoding']

def add_time_offset(item):
    global time_offset
    if not isinstance(item, str):
        return item
    
    t = datetime.datetime.strptime(item,'%H:%M:%S.%f')

    t = t + datetime.timedelta(hours=int(time_offset))
    return t.strftime('%H:%M:%S.%f')


# ******************* MAIN ********************
def connect_mri_system_log_grabber_p2(inLogFile: str, offset: int = None):
    """_summary_

    :param inLogFile: _description_
    :type inLogFile: str
    """    
    from wsuconnect.data import load as load_data
    from json import loads
    
    try:
        #read credentials.json
        projectIDs = loads(load_data.readable('credentials.json').read_text())

        #read default mac-roman format
        cols = ['c1','date','time','c4','c5','c6','c7','c8','logger','event','c11','c12','c13','c14']
        df = pd.read_csv(inLogFile,sep='\t',skiprows=1,on_bad_lines='warn',encoding='mac-roman',names=cols,header=None)
        # df = pd.read_csv('/resshare/Philips_system_logs/2023/log202306120000.log',sep='\t',skiprows=1,on_bad_lines='warn',encoding='mac-roman',names=cols,header=None)
        if offset:
            print(f"applying time offset to all time values of {offset} hours")
            global time_offset
            time_offset = offset
            df['time'] = df['time'].apply(add_time_offset)

        #Find all new exam notifications
        #df_exams=df[df['event'].str.contains(r'(?=.*ExamCardName)(?=.*ScheduledProcedureStep)',na=False,regex=True)]
        df_exams=df[df['event'].str.contains(r'(?=.*ExamOverview)(?=.*MRExamCardModel)(?=.*\(ExamOverview\))(?=.*Updating Examcard name to)',na=False,regex=True)]
        l_examIdx = df_exams.index.to_list()
        
        #get rid of exams missing examcard names
        l_examIdx = [e for e in l_examIdx if not df['event'].iloc[e].endswith("name to ")]
        df_exams = df.iloc[l_examIdx]


        #loop through all exams
        for e, examIdx in enumerate(l_examIdx):
            #create reduced dataframe template
            df_out = pd.DataFrame(columns = ['date','time','project','marker','event'])
            proj = None

            if examIdx == l_examIdx[-1]:
                df_redExam = df.iloc[examIdx:]
            else:
                df_redExam = df.iloc[examIdx:l_examIdx[e+1]-1]


            #save single exam input to output dataframe
            print('\nExam:' + df_exams['date'].iloc[e] + '\t' + df_exams['time'].iloc[e] + '\t' + df_exams['event'].iloc[e])
            df_out = df_out.T.join(df_exams[['date','time','event']].iloc[e].T).T.sort_index()

            #get project
            #examEvent = df_exams['event'].iloc[e].split(': ')[1].split(', ')[0]
            examEvent = df_exams['event'].iloc[e].split('ExamOverview(MRExamCardModel): (ExamOverview) Updating Examcard name to ')[-1]
            for k in projectIDs.keys():
                if type(projectIDs[k]) is dict:
                    if 'examCardName' in projectIDs[k].keys():
                        #if examEvent in projectIDs[k]['examCardName']:
                        if projectIDs[k]['examCardName'] in examEvent:
                            proj = k
                            break

            df_out.at[examIdx,'project'] = proj
            df_out.at[examIdx,'marker'] = 'New Exam'


            #find all manual scan starts (do these coordinate to auto scan starts? if not what does?)
            df_startButtons = df_redExam[df_redExam['event'].str.contains(r'(?=.*OnScanEngineStart\(\))(?=.*startScanButtonPressed)',na=False,regex=True)]
            l_startButtonIdx = df_startButtons.index.to_list()
            # print('\nStart Buttons')
            for sb, sbIdx in enumerate(l_startButtonIdx) :
                if sbIdx == l_startButtonIdx[-1]:
                    df_redStart = df.iloc[sbIdx:]
                else:
                    df_redStart = df.iloc[sbIdx:l_startButtonIdx[sb+1]-1]
                
                # print('\nStart Buttons')
                # print(df_startButtons['date'].iloc[sb] + '\t' + df_startButtons['time'].iloc[sb] + '\t' + df_startButtons['event'].iloc[sb])
                df_out = df_out.T.join(df_startButtons[['date','time','event']].iloc[sb].T).T.sort_index()

                df_out.at[sbIdx,'project'] = proj
                df_out.at[sbIdx,'marker'] = 'Start Button'
                
                
            #approximate scan start time for computation of time deltas
            if not df_startButtons.empty:
                dt_startT = datetime.datetime.strptime(df_startButtons['time'].iloc[0], '%H:%M:%S.%f')
            else:
                dt_startT = datetime.datetime.strptime(df_exams['time'].iloc[e], '%H:%M:%S.%f')

            dt = datetime.datetime.strptime(df_out['date'].iloc[0], '%Y-%m-%d')
            dt_startT = dt_startT.replace(year=dt.year, month=dt.month, day=dt.day)



            #find all unique scan starts that follow button press
            df_scanPreps = df_redExam[df_redExam['event'].str.contains(r'(?=.*ScanSet\(SingleScan\):)(?=.*AwaitPreScan,)(?=.*to AwaitPreScan)(?=.*ReadyToRun)(?!.*B0_PreScan)(?!.*B1_Calibration)(?!.*PreScanCompleted,)',na=False,regex=True)]
            l_scanPrepIdx = df_scanPreps.index.to_list()
            for sp, spIdx in enumerate(l_scanPrepIdx):
                if spIdx == l_scanPrepIdx[-1]:
                    df_redScan = df_redExam.loc[spIdx:]
                else:
                    df_redScan = df.loc[spIdx:l_scanPrepIdx[sp+1]-1]
                

                #output to reduced dataframe
                # print('\nScan Preps')
                # print(df_scanPreps['date'].iloc[sp] + '\t' + df_scanPreps['time'].iloc[sp] + '\t' + df_scanPreps['event'].iloc[sp])
                df_out = df_out.T.join(df_scanPreps[['date','time','event']].iloc[sp].T).T.sort_index()

                scanName = df_scanPreps['event'].iloc[sp].split(',AwaitPreScan,')[1].split(',')[0]
                df_out.at[spIdx,'marker'] = scanName
                df_out.at[spIdx,'project'] = proj


                #look for scan start
                df_startScans = df_redScan[df_redScan['event'].isin([' Scan starts'])]
                l_startIdx = df_startScans.index.to_list()
                if l_startIdx:
                    for ss, ssIdx in enumerate(l_startIdx):
                
                        # print('\ndynamics')
                        # print(df_startScans['date'].iloc[ss] + '\t' + df_startScans['time'].iloc[ss] + '\t' + df_startScans['event'].iloc[ss])
                        df_out = df_out.T.join(df_startScans[['date','time','event']].iloc[ss].T).T.sort_index()
                        df_out.at[ssIdx,'marker'] = 'CDAS Scan Starts'
                        df_out.at[ssIdx,'project'] = proj


                #look for dynamics
                df_dynamicScans = df_redScan[df_redScan['event'].str.contains(r'Performing dynamic scan 1\.',na=False,regex=True)]
                l_dynamicIdx = df_dynamicScans.index.to_list()
                if l_dynamicIdx:
                    for dy, dyIdx in enumerate(l_dynamicIdx):
                
                        # print('\ndynamics')
                        # print(df_dynamicScans['date'].iloc[dy] + '\t' + df_dynamicScans['time'].iloc[dy] + '\t' + df_dynamicScans['event'].iloc[dy])
                        df_out = df_out.T.join(df_dynamicScans[['date','time','event']].iloc[dy].T).T.sort_index()
                        df_out.at[dyIdx,'marker'] = 'Dynamic 1'
                        df_out.at[dyIdx,'project'] = proj


                df_completedScans = df_redScan[df_redScan['event'].str.contains(r'(?=.*ScanSet\(SingleScan\):)(?=.*,AcqCompleted,' + scanName + ')',na=False,regex=True)]
                l_completedIdx = df_completedScans.index.to_list()
                if l_completedIdx:
                    for c, cIdx in enumerate(l_completedIdx):
                
                        # print('\nScan Complete')
                        # print(df_completedScans['date'].iloc[c] + '\t' + df_completedScans['time'].iloc[c] + '\t' + df_completedScans['event'].iloc[c])
                        if not cIdx in df_out.index:
                            df_out = df_out.T.join(df_completedScans[['date','time','event']].iloc[c].T).T.sort_index()
                            df_out.at[cIdx,'marker'] = 'Scan Complete'
                            df_out.at[cIdx,'project'] = proj



            #get project credentials
            if proj:
                print(f"\tProject: {proj}")
                st.creds.read(proj)

                a = datetime.datetime.strptime(df_out['date'].iloc[0], '%Y-%m-%d')
                df_scanLog = st.mysql.sql_mri_tracking_query(
                    regex=a.strftime('%Y-%m-%d'), 
                    searchcol='date',
                    project=proj
                )
                if df_scanLog.empty:
                    print(f"\tWARNING: empty query 'date' = {a.strftime('%Y-%m-%d')}")
                    continue

                if len(df_scanLog) == 1: #only 1 participant from this project on this date
                    print("\tonly 1 participant returned from query on this date")
                    subDir = Path(st.creds.dataDir) / 'rawdata' / df_scanLog.iat[0, df_scanLog.columns.get_loc("subject")] / df_scanLog.iat[0, df_scanLog.columns.get_loc("session")]
                    behDir = subDir / 'beh'
                    behDir.mkdir(exist_ok=True)

                    df_out.to_csv(behDir / f"{df_scanLog.iat[0, df_scanLog.columns.get_loc("subject")]}_{df_scanLog.iat[0, df_scanLog.columns.get_loc("session")]}_philips-scan-log.csv")
                    srcDir = Path(str(subDir).replace("rawdata", "sourcedata"))
                    srcDir.mkdir(exist_ok=True)
                    df_out.to_csv(srcDir / f"{df_scanLog.iat[0, df_scanLog.columns.get_loc("subject")]}_{df_scanLog.iat[0, df_scanLog.columns.get_loc("session")]}_philips-scan-log.csv")
                    print('\tSUB: ' + df_scanLog.iat[0, df_scanLog.columns.get_loc("subject")] + ' SESSION: ' + df_scanLog.iat[0, df_scanLog.columns.get_loc("session")])

                else: #more than 1 participant from this project on this date
                    print("\tmultiple participants returned from query on this date... determining the associated participant with this scan")
                    b_found = False
                    last_diff = None
                    for idx, row in df_scanLog.iterrows():
                        dt_t = a + row['scan_start_time'].to_pytimedelta()

                        diff = dt_t - dt_startT
                        if diff.days < 0:
                            diff = dt_startT - dt_t
                        #put second check in
                        if not last_diff:
                            last_diff = diff
                            df_tmp = row
                        else:
                            if last_diff > diff:
                                last_diff = diff
                                df_tmp = row

                        if diff.seconds < 60*15: #this subject is the one
                            subDir = Path(st.creds.dataDir) / 'rawdata' / row["subject"] / row["session"]
                            behDir = subDir / 'beh'
                            behDir.mkdir(exist_ok=True)
                            df_out.to_csv(behDir / f"{row["subject"]}_{row["session"]}_philips-scan-log.csv")
                            srcDir = Path(str(subDir).replace("rawdata", "sourcedata"))
                            srcDir.mkdir(exist_ok=True)
                            df_out.to_csv(srcDir / f"{row["subject"]}_{row["session"]}_philips-scan-log.csv")
                            print('\tSUB: ' + row["subject"] + ' SESSION: ' + row["session"])
                            b_found = True
                            break

                    if not b_found:
                        print("\tWARNING: no subject found within 15 minutes of examcard time, defaulting to the closest participant scan_start_time")
                        subDir = Path(st.creds.dataDir) / 'rawdata' / df_tmp["subject"] / df_tmp["session"]
                        behDir = subDir / 'beh'
                        behDir.mkdir(exist_ok=True)
                        df_out.to_csv(behDir / f"{df_tmp["subject"]}_{df_tmp["session"]}_philips-scan-log.csv")
                        srcDir = Path(str(subDir).replace("rawdata", "sourcedata"))
                        srcDir.mkdir(exist_ok=True)
                        df_out.to_csv(srcDir / f"{df_tmp["subject"]}_{df_tmp["session"]}_philips-scan-log.csv")
                        print('\tSUB: ' + df_tmp["subject"] + ' SESSION: ' + df_tmp["session"])



    except OSError as e:
        traceback.print_exc()
    except Exception as e:
        traceback.print_exc()
                    

       


if __name__ == '__main__':
    options = parse_arguments()
    connect_mri_system_log_grabber_p2(options.INLOGFILE, offset=options.OFFSET)
