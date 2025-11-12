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


FSLDIR = os.environ["FSLDIR"]


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
    df_key = pd.DataFrame(columns=['key','Lsl Time Stamp','MRI Time'])
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

    df_physio = pd.DataFrame(columns=['Lsl Time Stamp','Date','Physio Time','HR','HR Source','z1','z2','z3','z4','z5','z6','z7','z8','z9','SpO2','RR','CO2','z21','z22','z23','z24','z25','MRI Time'])
    for f in l[:-1]:
        a = f.split(',')
        # if negTimeDiff:
        # a.append(datetime.datetime.strftime(datetime.datetime.strptime(a[1], '%H:%M:%S') - physioMriTimeDiff, '%H:%M:%S.%f'))
        a.append(np.NaN)
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
    df_physio.to_csv('/Export/DataTransfer/20240100H/test_physio.csv')
    df_key.to_csv('/Export/DataTransfer/20240100H/test_key.csv')

                                  
         


             

            

       
    

if __name__ == '__main__':
    main()
