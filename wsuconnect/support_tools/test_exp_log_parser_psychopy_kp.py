#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 27 July 2023
#
# Modified on 7 Feb 2024 - added condor job support

import os
# import pymysql
import argparse
import sys
import pandas as pd
import numpy as np
from glob import glob as glob
import datetime
import pyxdf


#local import
REALPATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(REALPATH)



# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '15 July 2024'


# FSLDIR = os.environ["FSLDIR"]


#input argument parser
parser = argparse.ArgumentParser()

# ******************* PARSE COMMAND LINE ARGUMENTS ********************
# def parse_arguments():

#     #input options for main()
#     requiredNamed = parser.add_argument_group('required arguments')
#     requiredNamed.add_argument('-i','--in', required=True, action="store", dest="INFILE", help="input file to overlay and slice", default=None)
#     parser.add_argument('--start', action="store", dest="START", type=int, help="Start slice number, default 0", default=None)
#     parser.add_argument('--end', action="store", dest="END", type=int, help="End slice number, default all slices", default=None)
#     parser.add_argument('-l','--lower', action="store", dest="LOWER", type=float, help="lower threshold for overlay, default 2.3", default=2.3)
#     parser.add_argument('-u','--upper', action="store", dest="UPPER", type=float, help="upper threshold for overlay, default 4.5", default=4.5)
#     parser.add_argument('--ref', action="store", dest="REF", help="Reference image, default FSL MNI T1 2mm brain", default="${FSLDIR}/data/standard/MNI152_T1_2mm_brain")
#     parser.add_argument('--lut', action="store", dest="LUT", help="Colormap LUT, must be in $FSLDIR/etc/luts, default render1.lut", default="${FSLDIR}/etc/luts/render1.lut")
#     parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
#     parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)
#     options = parser.parse_args()

    

#     return options


# ******************* EVALUATE COMMAND LINE ARGUMENTS ********************
# def evaluate_args(options):
    
#     #SEARCHTABLE=None
#     groupIdFile = None    

#     if os.path.isfile(os.path.join(creds.dataDir,'rawdata','participants.tsv')):
#         groupIdFile = os.path.join(creds.dataDir,'rawdata','participants.tsv')

#     segstatsInputFile = os.path.join(creds.dataDir,'code',options.PROJECT + '_extract_segstats_input.json')
#     if not os.path.isfile(segstatsInputFile):
#         return

#     with open(segstatsInputFile) as j:
#         segstatsInput = json.load(j)


#     return groupIdFile, segstatsInput



# ******************* MAIN ********************
def main():
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json

    #get and evaluate options
    # options = parse_arguments()

    
        
    data, header = pyxdf.load_xdf('/resshare20/projects/2022_KBR_Cog_Neuro_2/fMRI_catalog/rawdata/sub-321104/ses-01/beh/20240100H_sub-321104_ses-01_desc-lsl_beh.xdf')
    ls_streams = ['Keyboard','psychopyStream','SerialPort']
    

    for d in data:
        # for stream in ls_streams:
        if 'Keyboard' in d['info']['name']:
            d_key = d
        elif 'psychopyStream' in d['info']['name']:
            d_psycho = d
        elif 'SerialPort' in d['info']['name']:
            d_serial = d

    
    #extracting keypress and timestamps
    df_key = pd.DataFrame(columns=['key','Lsl Time Stamp'])
    for count in range(len(d_key['time_series'])):
        tmp_df = pd.DataFrame([[d_key['time_series'][count][0], d_key['time_stamps'][count]]], columns=['key','Lsl Time Stamp'])
        df_key = pd.concat([df_key,tmp_df], ignore_index=True)


    #extract physio data
    s = ''
    endPattern = ',X,0.0\r\n'
    sampleWindow = endPattern
    for count in range(len(d_serial['time_series'])):
        c = chr(d_serial['time_series'][count][0])
        t = d_serial['time_stamps'][count]
        if sampleWindow == endPattern:
            s +=  '%.10f,' %t
        s += c

        sampleWindow = sampleWindow[1:] + c

    l = s.split(endPattern)
    l = l[1:]
    # print(port_df['Time'].iloc[0])
    print(l[0]) 

    df_physio = pd.DataFrame(columns=['Lsl Time Stamp','Date','Physio Time','HR','HR Source','z1','z2','z3','z4','z5','z6','z7','z8','z9','SpO2','RR','CO2','z21','z22','z23','z24','z25'])
    for f in l[:-1]:
        a = f.split(',')
        # if negTimeDiff:
        # a.append(datetime.datetime.strftime(datetime.datetime.strptime(a[1], '%H:%M:%S') - physioMriTimeDiff, '%H:%M:%S.%f'))
        # a.append(np.NaN)
        # else:
        #     a.append(datetime.datetime.strftime(datetime.datetime.strptime(a[1], '%H:%M:%S') + datetime.timedelta(physioMriTimeDiff), '%H:%M:%S.%f'))
        # print(a)
        df_physio.loc[len(df_physio)] = a


    #extracting psychopy markers
    # df_psycho = pd.DataFrame(columns=['Marker','Lsl Time Stamp','MRI Time'])
    # for count in range(len(d_psycho['time_series'])):
    #     tmp_df = pd.DataFrame([[d_psycho['time_series'][count][0], d_psycho['time_stamps'][count]]], columns=['Marker','Lsl Time Stamp'])
    #     df_psycho = pd.concat([df_psycho,tmp_df], ignore_index=True)
   
   
    print('test')


    #get first fmri TR pulse from lsl xdf file
    # taskPulseTime = df_key['Time'][df['Code'] == self.pulsecode].iloc[0]
    keyPulseTime = df_key['Lsl Time Stamp'][df_key['key'] == 'PLUS pressed'].iloc[0] #get first TR emulated keypress
    # df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
    # df['Duration'] /= 10000.0
    print('Task Pulse Time (lsl): ' + str(keyPulseTime))


    #GET MRI LOG FILE
    scanFile = glob(os.path.join('/resshare20/projects/2022_KBR_Cog_Neuro_2/fMRI_catalog/rawdata/sub-321104/ses-01/beh','*philips-scan-log.csv'))
    if len(scanFile) != 1:
        print('ERROR: more than 1 philips-scan-log found')
        return
    df_mri = pd.read_table(scanFile[0], 
                        sep=',', 
                        skiprows=0,skip_blank_lines=True)   


    ## GET MRI TIME OF FIRST fMRI TR PULSE (DYNAMIC)
    # extract scanlog components after first fMRI
    # startIdx = np.array(np.where(df2['marker'] == self.fmriMarker)[0])
    startIdx = np.array(np.where(df_mri['marker'] == 'fMRI base')[0])
    # startIdx = int(str(startIdx[0]).lstrip('[').rstrip(']'))
    startIdx = startIdx[0]
    # print(startIdx)
    tmp_dfmri = df_mri.iloc[startIdx:]

    # get MRI time of first dynamic
    mriPulseTime = tmp_dfmri['time'][tmp_dfmri['marker'] == 'Dynamic 1'].iloc[0]
    print('MRI first fmri dynamic time: ' + mriPulseTime)
    mriPulseTime = datetime.datetime.strptime(mriPulseTime, '%H:%M:%S.%f')

    ## GET TASK TIME OF START OF ALL SCANS
    #get mri time of start of all scans
    mriStartTime = df_mri['time'][df_mri['marker'] == 'Start Button'].iloc[0]
    print('MRI Start Time: ' + str(mriStartTime))
    mriStartTime = datetime.datetime.strptime(mriStartTime, '%H:%M:%S.%f')

    #convert start time from MRI clock to lsl time
    taskStartTime= (mriStartTime-mriPulseTime).total_seconds() + keyPulseTime
    if taskStartTime < 0:
        taskStartTime = 0.
    print('TASK START TIME: ' + str(taskStartTime))




    delta_pulse_t = mriPulseTime.timestamp() - keyPulseTime
    
    #add MRI Time to key and physio LSL time series
    tmp_df = pd.DataFrame(columns=['MRI Time'])
    for count in range(len(d_key['time_series'])):
        tmp_df.loc[len(tmp_df)] = datetime.datetime.fromtimestamp(d_key['time_stamps'][count] + delta_pulse_t).strftime("%H:%M:%S.%f")
    df_key = pd.concat([df_key,tmp_df],axis=1)

    tmp_df = pd.DataFrame(columns=['MRI Time'])
    for count in range(len(d_key['time_series'])):
        tmp_df.loc[len(tmp_df)] = datetime.datetime.fromtimestamp(float(df_physio['Lsl Time Stamp'][count]) + delta_pulse_t).strftime("%H:%M:%S.%f")
    df_physio = pd.concat([df_physio,tmp_df],axis=1)


    # df_physio.to_csv('/Export/DataTransfer/20240100H/test_physio.csv')
    df_physio.to_csv('/resshare20/projects/2022_KBR_Cog_Neuro_2/fMRI_catalog/rawdata/sub-321104/ses-01/beh/test_key.csv')

    # mriPulseTime = df2['time'][df2['marker'] == 'Dynamic 1'].iloc[1]
    # # df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
    # # df['Duration'] /= 10000.0
    # print(pulse_t)
    # mriPulseTime = datetime.strptime(pulse_t, '%H:%M:%S.%f')




    # pulse_t = df2['time'][df2['marker'] == 'Dynamic 1'].iloc[2]
    # # df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
    # # df['Duration'] /= 10000.0
    # print(pulse_t)
    # mr_time2 = datetime.strptime(pulse_t, '%H:%M:%S.%f')
    # print((mr_time2-mr_time1).total_seconds()*10000 + pulse_t2)
    # return new_df









    # to_write_list = []
    # # Loop over condition-codes to find indices/times/durations
    # # for i, code in enumerate(self.con_codes):
    l_uniqueMarkers = df_mri['marker'].unique().tolist()
    for x in ['Survey','Scan Complete','CDAS','New Exam','Start Button','Dynamic']:
        l_uniqueMarkers = [m for m in l_uniqueMarkers if x not in m]
    #for i, code in enumerate(l_uniqueMarkers):

        #1) Find "code" in df_mri
        #2) Find first scan complete after "code"
        #3) Is there a "Dynamic 1" between 1 & 2, grab last one
        #4) If no dynamic, grab last CDAS Scan Starts
        #5) convert times from 2 & 3/4 to LSL Time
        #6) Find first time > 3/4 (is there one?)
        #7) Find the last time < #2 (or first time > #3) (is there one?)
        #8) extract data between 5 &6
        #9) write segmented df_physio data to csv with appropriate sequence code to the derivatives participant/session beh folder


##########################################################################################################




 ## GET MRI TIME OF FIRST CDAS TR PULSE (DYNAMIC)
    # extract scanlog components after first fMRI
    # startIdx = np.array(np.where(df2['marker'] == self.fmriMarker)[0])
    startIdx = np.array(np.where(df_mri['marker'] == 'fMRI base')[0])
    # startIdx = int(str(startIdx[0]).lstrip('[').rstrip(']'))
    startIdx = startIdx[0]
    # print(startIdx)
    tmp_dfmri = df_mri.iloc[startIdx:]

    # get MRI time of first dynamic
    mriPulseTime = tmp_dfmri['time'][tmp_dfmri['marker'] == 'Dynamic 1'].iloc[0]
    print('MRI first fmri dynamic time: ' + mriPulseTime)
    mriPulseTime = datetime.datetime.strptime(mriPulseTime, '%H:%M:%S.%f')

    ## GET TASK TIME OF START OF ALL SCANS
    #get mri time of start of all scans
    mriStartTime = df_mri['time'][df_mri['marker'] == 'Start Button'].iloc[0]
    print('MRI Start Time: ' + str(mriStartTime))
    mriStartTime = datetime.datetime.strptime(mriStartTime, '%H:%M:%S.%f')

    #convert start time from MRI clock to lsl time
    taskStartTime= (mriStartTime-mriPulseTime).total_seconds() + keyPulseTime
    if taskStartTime < 0:
        taskStartTime = 0.
    print('TASK START TIME: ' + str(taskStartTime))




    delta_pulse_t = mriPulseTime.timestamp() - keyPulseTime
    
    #add MRI Time to key and physio LSL time series
    tmp_df = pd.DataFrame(columns=['MRI Time'])
    for count in range(len(d_key['time_series'])):
        tmp_df.loc[len(tmp_df)] = datetime.datetime.fromtimestamp(d_key['time_stamps'][count] + delta_pulse_t).strftime("%H:%M:%S.%f")
    df_key = pd.concat([df_key,tmp_df],axis=1)

    tmp_df = pd.DataFrame(columns=['MRI Time'])
    for count in range(len(d_key['time_series'])):
        tmp_df.loc[len(tmp_df)] = datetime.datetime.fromtimestamp(float(df_physio['Lsl Time Stamp'][count]) + delta_pulse_t).strftime("%H:%M:%S.%f")
    df_physio = pd.concat([df_physio,tmp_df],axis=1)





######################################################################################################



    #     to_write = pd.DataFrame()

    #     if type(code) == str:
    #         code = [code]

    #     if len(code) > 1:
    #         # Code is list of possibilities
    #         if all(isinstance(c, (int, np.int64)) for c in code):
    #             idx = df['Code'].isin(code)

    #         elif all(isinstance(c, str) for c in code):
    #             idx = [any(c in x for c in code)
    #                    if isinstance(x, str) else False
    #                    for x in df['Code']]
    #             idx = np.array(idx)

    #     elif len(code) == 1 and type(code[0]) == str:
    #         # Code is single string
    #         idx = [code[0] in x if type(x) == str
    #                else False for x in df['Code']]
    #         idx = np.array(idx)
    #     else:
    #         idx = df['Code'] == code

    #     if idx.sum() == 0:
    #         raise ValueError('No entries found for code: %r' % code)

    #     # Generate dataframe with time, duration, and weight given idx
    #     to_write['onset'] = df['Time'][idx]

    #     if self.con_duration is None:
    #         to_write['duration'] = df['Duration'][idx]
    #         n_nan = np.sum(np.isnan(to_write['duration']))
    #         if n_nan > 1:
    #             msg = ('In total, %i NaNs found for Duration. '
    #                    'Specify duration manually.' % n_nan)
    #             raise ValueError(msg)
    #         to_write['duration'] = [np.round(x, decimals=2)
    #                                 for x in to_write['duration']]
    #     else:
    #         to_write['duration'] = [self.con_duration[i]] * idx.sum()

    #     to_write['trial_type'] = [self.con_names[i] for j in range(idx.sum())]

    #     if self.write_code:
    #         to_write['code'] = df['Code'][idx]

    #     to_write_list.append(to_write)

    # events_df = pd.concat(to_write_list).sort_values(by='onset')

    # if self.write_tsv:
    #     outname = op.join(self.base_dir, op.basename(f).split('.')[0] + '.tsv')
    #     events_df.to_csv(outname, sep='\t', index=False)

    # return events_df
             

            

       
    

if __name__ == '__main__':
    main()
