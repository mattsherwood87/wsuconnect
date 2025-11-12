#!/resshare/general_processing_codes/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Parses a Presentation (neurobs.com) logfile.

# Author: Lukas Snoek [lukassnoek.github.io]
# Contact: lukassnoek@gmail.com
# License: 3 clause BSD

from __future__ import division, print_function, absolute_import
from builtins import range
import os.path as op
import pandas as pd
import numpy as np
import datetime
import os
from glob import glob
import sys


class PresentationLogfileCrawler(object):
    """
    Logfile crawler for Presentation (Neurobs) files; cleans logfile,
    calculates event onsets and durations, and (optionally) writes out
    .bfsl files per condition.

    Parameters
    ----------
    in_file : str or list
        Absolute path to logfile (can be a list of paths).
    con_names : list
        List with names for each condition
    con_codes : list
        List with codes for conditions. Can be a single integer or string (in
        the latter case, it may be a substring) or a list with possible values.
    con_design : list or str
        Which 'design' to assume for events (if 'multivar', all events -
        regardless of condition - are treated as a separate
        condition/regressor; if 'univar', all events from a single condition
        are treated as a single condition). Default: 'univar' for all
        conditions.
    con_duration : list
        If the duration cannot be parsed from the logfile, you can specify them
        here manually (per condition).
    pulsecode : int
        Code with which the first (or any) pulse is logged.
    fmriMarker : str
        Marker with which the first fMRI is logged in the Philips scan log CSV file.
    write_bfsl : bool
        Whether to write out a .bfsl file per condition.
    verbose : bool
        Print out intermediary output.

    Attributes
    ----------
    df : Dataframe
        Dataframe with cleaned and parsed logfile.
    """

    def __init__(self, in_file, out_file, con_names, con_codes, fmriMarker,
                 con_duration=None, pulsecode=30, write_tsv=True,
                 verbose=True, write_code=False):

        if isinstance(in_file, str):
            in_file = [in_file]

        self.in_file = in_file
        self.out_file = out_file
        self.con_names = con_names
        self.con_codes = con_codes
        self.write_tsv = write_tsv
        self.write_code = write_code

        if con_duration is not None:

            if isinstance(con_duration, (int, float)):
                con_duration = [con_duration]

            if len(con_duration) < len(con_names):
                con_duration *= len(con_names)

        self.con_duration = con_duration
        self.pulsecode = pulsecode
        self.fmriMarker = fmriMarker
        self.verbose = verbose
        self.df = None
        self.to_write = None
        self.base_dir = None

    def _parse(self, f):
        try:

            if self.verbose:
                print('Processing %s' % f)

            self.base_dir = op.dirname(f)

            if self.df is not None:
                df = self.df
            else:
                df = pd.read_table(f, sep='\t', skiprows=3,
                                skip_blank_lines=True)
                

            # # Clean up unnecessary columns
            # to_drop = ['Uncertainty', 'Subject', 'Trial', 'Uncertainty.1',
            #            'ReqTime', 'ReqDur', 'Stim Type', 'Pair Index']
            # _ = [df.drop(col, axis=1, inplace=True)
            #      for col in to_drop if col in df.columns]

            # GET TIME OF FMRI TR PULSES
            # Ugly hack to find pulsecode, because some numeric codes are
            # written as str
            df = df.dropna(subset='Time')
            endIdx = np.where(df['Subject'] == 'Event Type')
            # print(endIdx)
            if np.size(endIdx):
                endIdx = int(str(endIdx[0]).lstrip('[').rstrip(']'))
                # print(endIdx)


                ### add handle for no endIdx
                df = df.iloc[:endIdx-1]
            df['Time'] = df['Time'].apply(pd.to_numeric)
            df['Code'] = df['Code'].astype(str)
            df['Code'] = [float(x) if x.isdigit() else x for x in df['Code']]
            # pulse_idx = np.where(df['Code'] == self.pulsecode)[0]

            # if len(pulse_idx) > 1:  # take first pulse if mult pulses are logged
            #     pulse_idx = int(pulse_idx[0])

            # pulse_t = absolute time of first pulse
            taskPulseTime = df['Time'][df['Code'] == self.pulsecode].iloc[0]
            # df['Time'] = (df['Time'] - float(pulse_t)) / 10000.0
            # df['Duration'] /= 10000.0
            print('Task Pulse Time: ' + str(taskPulseTime))




            # end_pulse_t2 = pulse_t2 + 5*60*10000
            # new_df = df[(df['Time'] >= pulse_t2) & (df['Time'] <= end_pulse_t2)]
            scanFile = glob(os.path.join(self.base_dir,'*philips-scan-log.csv'))
            if len(scanFile) != 1:
                print('ERROR: more than 1 philips-scan-log found')
                return
            df2 = pd.read_table(scanFile[0], 
                                sep=',', 
                                skiprows=0,skip_blank_lines=True)
            
            # df['Time'] = df['Code'].astype(str)
            # df['Code'] = [float(x) if x.isdigit() else x for x in df['Code']]
            # pulse_idx = np.where(df2['marker'] == 'Dynamic 1')

            # if len(pulse_idx) > 1:  # take first pulse if mult pulses are logged
            #     pulse_idx = int(pulse_idx[1])

            # pulse_t = absolute time of first pulse
            # searchStr = 'fMRI'
            # mriPulseTime = df2[df2['marker'] == self.fmriMarker].iloc[0]

            ## GET MRI TIME OF FIRST fMRI TR PULSE (DYNAMIC)
            # extract scanlog components after first fMRI
            startIdx = np.array(np.where(df2['marker'] == self.fmriMarker)[0])
            # startIdx = int(str(startIdx[0]).lstrip('[').rstrip(']'))
            startIdx = startIdx[0]
            # print(startIdx)
            tmp_df2 = df2.iloc[startIdx:]

            # get MRI time of first dynamic
            mriPulseTime = tmp_df2['time'][tmp_df2['marker'] == 'Dynamic 1'].iloc[0]
            print('MRI first fmri dynamic time: ' + mriPulseTime)
            mriPulseTime = datetime.datetime.strptime(mriPulseTime, '%H:%M:%S.%f')

            ## GET TASK TIME OF START OF ALL SCANS
            #get mri time of start of all scans
            mriStartTime = df2['time'][df2['marker'] == 'Start Button'].iloc[0]
            print('MRI Start Time: ' + str(mriStartTime))
            mriStartTime = datetime.datetime.strptime(mriStartTime, '%H:%M:%S.%f')

            #convert start time from MRI clock to task clock
            taskStartTime= (mriStartTime-mriPulseTime).total_seconds()*10000 + taskPulseTime
            if taskStartTime < 0:
                taskStartTime = 0.
            print('TASK START TIME: ' + str(taskStartTime))


            ## GET TASK TIME OF START OF ALL SCANS
            #get mri time of start of all scans
            mriEndTime = df2['time'][df2['marker'] == 'Scan Complete'].iloc[-1]
            print('MRI End Time: ' + str(mriEndTime))
            mriEndTime = datetime.datetime.strptime(mriEndTime, '%H:%M:%S.%f')


            #convert end time from MRI clock to task clock
            taskEndTime= (mriEndTime-mriPulseTime).total_seconds()*10000 + taskPulseTime
            print('TASK END TIME: ' + str(taskEndTime))



            ## GET TASK LOG DATA FROM ONLY SCAN PERIOD (taskStartTime TO taskEndTime)
            new_df = df[(df['Time'] >= taskStartTime) & (df['Time'] <= taskEndTime)]
            filter = new_df['Event Type'].str.contains('Port Input')
            port_df = new_df[filter]
            s = ''
            for index, row in port_df.iterrows():
                if isinstance(row['Code'],str):
                    if '.' in row['Code']:
                        s += chr(int(float(row['Code'])))
                    else:
                        s += chr(int(row['Code']))
                else:
                    s += chr(int(row['Code']))

            l = s.split(',X,0.0\r\n')
            # print(port_df['Time'].iloc[0])
            # print(l[0])
            taskPhysioDiff = int((taskPulseTime - port_df['Time'].iloc[0]) / 10000)
            try:
                physioStartTime = datetime.datetime.strptime(l[0].split(',')[1], '%H:%M:%S')
                startIdx = 0
            except:
                physioStartTime = datetime.datetime.strptime(l[1].split(',')[1], '%H:%M:%S')
                startIdx = 1
            physioPulseTime = physioStartTime + datetime.timedelta(seconds=taskPhysioDiff)
            physioMriTimeDiff = physioPulseTime - mriPulseTime
            negTimeDiff = False
            # if physioMriTimeDiff < 0:
            #     physioMriTimeDiff = (mriPulseTime - physioPulseTime).total_seconds()
            #     negTimeDiff = True


            new_port_df = pd.DataFrame(columns=['Date','Physio Time','HR','HR Source','z1','z2','z3','z4','z5','z6','z7','z8','z9','SpO2','RR','CO2','z21','z22','z23','z24','z25','MRI Time'])
            for f in l[startIdx:-1]:
                a = f.split(',')
                # if negTimeDiff:
                a.append(datetime.datetime.strftime(datetime.datetime.strptime(a[1], '%H:%M:%S') - physioMriTimeDiff, '%H:%M:%S.%f'))
                # else:
                #     a.append(datetime.datetime.strftime(datetime.datetime.strptime(a[1], '%H:%M:%S') + datetime.timedelta(physioMriTimeDiff), '%H:%M:%S.%f'))
                # print(a)
                new_port_df.loc[len(new_port_df)] = a
                

            # print(port_df['Time'].iloc[0])
            # print(l[0])    
            # print(mriPulseTime) 
            # print(physioPulseTime)




            print('MRI first fmri dynamic time: ' + str(mriPulseTime))
            print('Task Pulse Time: ' + str(taskPulseTime))
            print('Physio Start Time: ' + str(physioStartTime))
            print('Physio Pulse Time: ' + str(physioPulseTime))
            # print('Physio/MRI Pulse differential: ' + str(physioMriTimeDiff) + ' ' + str(negTimeDiff))

            new_port_df = new_port_df.drop(columns=['z1','z2','z3','z4','z5','z6','z7','z8','z9','z21','z22','z23','z24','z25'])
            new_port_df.to_csv(op.join(self.out_file),sep=',',escapechar='\\')
            print('SUCCESS: saved physio data to ' + self.out_file)

            return new_port_df













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
            # for i, code in enumerate(self.con_codes):

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
        except Exception as e:
            print('ERROR: processing ' + self.in_file[0])
            print("Error Message: {0}".format(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            return

    def parse(self):
        """
        Parses logfile, writes bfsl (optional), and return subject-info.

        Returns
        -------
        subject_info_list : Nilearn bunch object
            Bunch object to be used in Nipype pipelines.
        """
        subject_info_list = [self._parse(f) for f in self.in_file]
        return subject_info_list

        # if len(subject_info_list) == 1:
        #     return subject_info_list[0]
        # else:
        #     return subject_info_list


def parse_presentation_logfile(in_file, out_file, con_names, con_codes, fmriMarker, con_duration=None,
                               write_tsv=True, write_code=False, pulsecode=30):
    """
    Function-interface for PresentationLogfileCrawler. Can be used to create
    a Nipype node.

    Parameters
    ----------
    in_file : str or list
        Absolute path to logfile (can be a list of paths).
    con_names : list
        List with names for each condition
    con_codes : list
        List with codes for conditions. Can be a single integer or string (in
        the latter case, it may be a substring) or a list with possible values.
    con_design : list or str
        Which 'design' to assume for events (if 'multivar', all events -
        regardless of condition - are treated as a separate
        condition/regressor; if 'univar', all events from a single condition
        are treated as a single condition). Default: 'univar' for all
        conditions.
    con_duration : list
        If the duration cannot be parsed from the logfile, you can specify them
        here manually (per condition).
    pulsecode : int
        Code with which the first (or any) pulse is logged.
    """

    #from skbold.exp_model 
    #from test_exp_log_parser import PresentationLogfileCrawler

    plc = PresentationLogfileCrawler(in_file=in_file, out_file=out_file, 
                                     con_names=con_names,
                                     con_codes=con_codes,
                                     con_duration=con_duration,
                                     pulsecode=pulsecode, 
                                     fmriMarker=fmriMarker,
                                     write_tsv=write_tsv,
                                     write_code=write_code,
                                     verbose=True)

    
    subject_info_files = plc.parse()

    return subject_info_files