#!/resshare/general_processing_codes/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 16 Sept 2021
#
# 

import os
import sys
import json
import subprocess
import argparse
from glob import glob as glob

#local import

# REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
# sys.path.append(REALPATH)
REALPATH = os.path.join('/resshare','general_processing_codes')
sys.path.append(REALPATH)

from support_tools.creds import *
from helper_functions.bids_commands import *
from helper_functions.get_dir_identifiers import *
from helper_functions.read_credentials import *
from helper_functions.mysql_commands import *
from helper_functions.id_check import *

# FSLDIR = os.environ["FSLDIR"]
FSLDIR = '/usr/local/fsl'
os.environ["FSLDIR"] = '/usr/local/fsl'
os.system('FSLDIR=' + os.environ["FSLDIR"])
# os.system('source /etc/profile.d/fsl.sh')


roiPath = os.path.join('/resshare/projects/2022_KBR_Cog_Neuro_2/measurement_stability/derivatives/group_feat_cluster-roi')

# regexStr = 'zstat1.nii.gz'
regexStr = 'desc-percent-signal-change_cope1.nii.gz'


filesToProcess = sql_query(database='CoNNECT',searchtable='2022_184',searchcol='fullpath',regex=regexStr,inclusion=['bold.feat','reg_standard'],progress=False)



# loop throught files
read_credentials('2022-184')
filesToProcess.sort()
inTargFiles = glob(os.path.join(roiPath,'*.nii.gz'))

for inTargFile in inTargFiles:
    os.system('echo -n "subject,v1,v2,v3" > ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))
    # proc = subprocess.check_output(os.path.join(FSLDIR,'bin','fslstats') + ' ' + inTargFile + ' -V', shell=True,encoding='utf-8')
    # roiVol = proc.split(' ')[1]

    lastSub = None
    nextSes = '1'
    for f in filesToProcess:
        subName, sesNum = get_dir_identifiers(os.path.dirname(f))
        if not id_check(subName) :
            continue

            
        print('SUBJECT: ' + subName + ' SESSION: ' + sesNum)
        print('\t' + f)
        if subName != lastSub:
            os.system('echo -n "\n' + subName + '" >> ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))
        lastSub = subName
        
        os.system('echo -n "," >> ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))
        # os.system('fslstats ' + f + ' -k ' + inTargFile + ' -l 1.76 -V | tr -d "\n" >> ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))
        proc = subprocess.check_output(os.path.join(FSLDIR,'bin','fslstats') + ' ' + f + ' -k ' + inTargFile + ' -l 0.01 -M', shell=True,encoding='utf-8')
        actVol = proc.split(' ')[0]
        # os.system('echo -n "' + str(float(actVol)/float(roiVol)*100) + '" >> ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))
        os.system('echo -n "' + actVol + '" >> ' + os.path.join(roiPath,inTargFile.split('.')[0] + '.csv'))