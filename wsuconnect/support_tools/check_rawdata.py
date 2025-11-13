#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 25 Feb 2025
#
#

# ******************* Function to apply colors *****************
def _color_cells(val):
    if val == 1:
        return "background-color: green; color: white;"
    elif val == 0:
        return "background-color: red; color: white;"
    else:
        return "background-color: white; color: black;"



# ******************* MAIN ********************
def check_rawdata(project: str, progress: bool = False, date: str = None):
    """
    The entry point of this program.
    """
    import os
    import sys
    import json
    import pandas as pd
    import numpy as np
    import datetime
    import smtplib
    from email.mime.text import MIMEText
    import traceback
    from wsuconnect.data import load as load_data
    from pathlib import Path
    from json import loads

    #local import
    REALPATH = Path('/resshare')
    if not str(REALPATH) in sys.path:
        sys.path.append(REALPATH)

    from wsuconnect import support_tools as st

    today = datetime.date.today()
    if not date:
        yesterday = today - datetime.timedelta(days=1)
    else:
        yesterday = datetime.datetime.strptime(date,'%Y%m%d')

    #load scan data
    # try:
    #     d_scanDates = loads(load_data.readable(yesterday.strftime('%Y'),f"{yesterday.strftime('%Y%m')}_scan_dates.json").read_text())
    # except FileNotFoundError:
    #     d_scanDates = None


    #read crendentials from $SCRATCH_DIR/instance_ids.json
    print(f"Project: {project}")
    b_ValidProject = st.creds.read(project)
    if not b_ValidProject:
        return

    print('\tValid')
    scanIdFile = ""
    if os.path.isfile(os.path.join(st.creds.dataDir,'code',project + '_scan_id.json')):
        scanIdFile = os.path.join(st.creds.dataDir,'code',project + '_scan_id.json')

    if os.path.isfile(os.path.join(st.creds.dataDir,'rawdata','participants.tsv')):
        groupIdFile = os.path.join(st.creds.dataDir,'rawdata','participants.tsv')

    try:
        #read scan ids
        if not os.path.isfile(scanIdFile):
            return

        with open(scanIdFile) as j:
            scanIds = json.load(j)
            if '__general_comment__' in scanIds.keys():
                scanIds.pop('__general_comment__')

        #read participants tsv file
        df_participants = pd.read_csv(groupIdFile, sep='\t')
        
    except FileNotFoundError as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        print(f"Exception occurred in file: {filename}, line: {lineno}")
        print(f"\tException type: {exc_type.__name__}")
        print(f"\tException message: {e}")
        traceback.print_exc()
        return


    #load any participants with missing data
    df_prevMissing = st.mysql.sql_mri_tracking_query(regex=False, searchcol='all_data')

    dirs = os.listdir(os.path.join(st.creds.dataDir,'rawdata'))
    for d in dirs:
        if not 'sub-' in d:
            continue

        if not df_participants['participant_id'].str.contains(d).any():
            if 'discard' in df_participants.columns:
                df_participants = pd.concat([df_participants,pd.DataFrame([[d,False]],columns=["participant_id","discard"])], ignore_index=True)
            else:
                df_participants = pd.concat([df_participants,pd.DataFrame([[d]],columns=["participant_id"])], ignore_index=True)
            df_participants.to_csv(groupIdFile,sep='\t',index=False)



    # print(df_participants['participant_id'])

    #skip any participants?
    if 'discard' in df_participants.columns:
        df_participants = df_participants[~df_participants['discard']]


    #sort participants
    df_participants = df_participants.sort_values(by=['participant_id'])

    #write csv header
    outputCsv = os.path.join(st.creds.dataDir,'code','processing_logs',project + '_rawdata_check.csv')
    if not os.path.isdir(os.path.dirname(outputCsv)):
        os.makedirs(os.path.dirname(outputCsv))
    else:
        if os.path.isfile(outputCsv):
            os.remove(outputCsv)

    # with open(outputCsv,'w') as csvFile:
    #     csvWriter = csv.writer(csvFile,delimiter=',')
    #     headerList = ['participant_id','session']
    #     for k in scanIds:
    #         headerList = headerList + scanIds[k]['ScanName']
    #     # if d
    #     #     headerList = headerList + scanIds['raw_nifti']
    #     # if 'raw_rda' in scanIds:
    #     #     headerList = headerList + scanIds['raw_rda']
    #     # if 'processed_T1_files' in scanIds:
    #     #     headerList = headerList + scanIds['processed_T1_files']
    #     # if 'processed_asl_files' in scanIds:
    #     #     headerList = headerList + scanIds['processed_asl_files']
    #     # if 'processed_mrs_files' in scanIds:
    #     #     headerList = headerList + scanIds['processed_mrs_files']
    #     csvWriter.writerow(headerList)

    #search each raw directory
    allFilesToProcess = st.mysql.sql_query(regex='rawdata',searchtable=st.creds.searchTable,searchcol='fullpath',progress=False,exclusion=['rawdata.bak'])
    # df_completeData = pd.DataFrame()

    
    d_bidsDirs = {'anat': "Anatomical",
                  'beh': "Behavioral",
                  'fmap': "Echo Planar Imaging and B0 Mapping",
                  'func': "Functional",
                  'perf': "Perfusion",
                  'dwi': "Diffusion",
                  'apt': "APTw"
    }
    styled_df = pd.DataFrame()
    d_completeData = {}
    for k in d_bidsDirs.keys():
        # exec(f"df_{k}Data = pd.DataFrame()")
        d_completeData[k] = pd.DataFrame()


    for subName in df_participants.participant_id:

        #return just the subject files
        if type(subName) is int:
            subName = str(subName)

        # if progress:
        #     print(subName)

        # if df_participants[df_participants['participant_id'] == subName].discard.item():
        #     continue
        subFilesToProcess = [x for x in allFilesToProcess if f"{subName}/" in x] #only look in subject directory
        if not subFilesToProcess:
            continue

        #get unique session names for this particular subject
        tmp_ls = [i.split('ses-')[1] for i in subFilesToProcess]
        tmp_ls = ['ses-' + i.split(os.sep)[0] for i in tmp_ls]
        tmp_np = np.array(tmp_ls)
        tmp_np = np.unique(tmp_np)
        tmp_np = np.sort(tmp_np)

        #loop over sorted sessions
        for fullSesNum in tmp_np:
            d_dataMatrix = {}
            l_missingFiles = []
            l_foundFiles = []
            # if progress:
            #     print('\t' + fullSesNum)
            filesToProcess = [x for x in subFilesToProcess if f"{fullSesNum}/" in x] #only look in session directory
            if not filesToProcess:
                continue

            #Create data matrices:
            for k in d_bidsDirs.keys():
                d_dataMatrix[k] = {}
                d_dataMatrix[k]['participant_id'] = subName
                d_dataMatrix[k]['session'] = fullSesNum
                # exec(f"d_{k}Matrix = {{}}")
                # exec(f"d_{k}Matrix['participant_id'] = subName")
                # exec(f"d_{k}Matrix['session'] = fullSesNum")
            sesNum = fullSesNum.split('-')[-1]

            #check if subject was ran yesterday
            # b_newSubject = False
            # print(d_scanDates[yesterday.strftime('%Y%m%d')])
            df_scanLog = st.mysql.sql_mri_tracking_query(regex=yesterday.strftime('%Y-%m-%d'), searchcol='date',project=project,subject=subName, session=f"ses-{sesNum}")
            b_newSubject = not df_scanLog.empty
            # if d_scanDates:
            #     if yesterday.strftime('%Y%m%d') in d_scanDates.keys():
            #         if f"{subName}_ses-{sesNum}" in d_scanDates[yesterday.strftime('%Y%m%d')]:
            #             b_newSubject = True


            #see if subjects/session needs rechecked
            matching_idx = pd.Index([])
            if not b_newSubject:
                mask = (df_prevMissing["uuid"] == df_scanLog.loc[0,'uuid']) #(df_prevMissing["project"] == project) & (df_prevMissing["subject"] == subName) & (df_prevMissing["session"] == f"ses-{sesNum}")
                matching_idx = df_prevMissing.index[mask]
                if not matching_idx.empty:
                    b_newSubject = True



            #look for raw nifti's
            b_allData = np.nan
            for k in scanIds:
                if not isinstance(scanIds[k],dict):
                    continue

                if not 'BidsDir' in scanIds[k].keys():
                    continue

                if 'bids_labels' in scanIds[k].keys():
                    # print(scanIds[k]['bids_labels'])
                    scanName = st.bids.get_bids_filename(**scanIds[k]['bids_labels'])[1:]
                    match = [x for x in filesToProcess if scanName + '.nii.gz' in x]
                    matchJson = [x for x in filesToProcess if scanName + '.json' in x]

                    if not sesNum in scanIds[k]['sessions']:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = np.nan")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = np.nan
                    elif len(match) > 0 and len(matchJson) > 0:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = 1")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = 1
                        l_foundFiles.append(os.path.basename(match[0]))
                        l_foundFiles.append(os.path.basename(matchJson[0]))
                        if b_allData == np.nan:
                            b_allData = True
                    else:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = 0")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = 0
                        if 'raw' in scanIds[k]:
                            if scanIds[k]['raw']:
                                b_allData = False
                                if len(match) == 0 and len(matchJson) == 0:
                                    l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.nii.gz")
                                    l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.json")
                                elif len(match) == 0:
                                    l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.nii.gz")
                                    l_foundFiles.append(f"{subName}_ses-{sesNum}_{scanName}.json")
                                elif len(matchJson) == 0:
                                    l_foundFiles.append(f"{subName}_ses-{sesNum}_{scanName}.nii.gz")
                                    l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.json")
                        else:
                            b_allData = False
                            l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.nii.gz")
                            l_missingFiles.append(f"{subName}_ses-{sesNum}_{scanName}.json")



                elif 'regex' in scanIds[k].keys():
                    # str.contains(r'(?=.*{})'.format(scanIds[k]['BidsDir']), regex=True)
                    match = [x for x in filesToProcess if set([ele for ele in scanIds[k]['regex'] if ele in x]) == set(scanIds[k]['regex'])]
                
                    if not sesNum in scanIds[k]['sessions']:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = np.nan")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = np.nan
                    elif len(match) > 0:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = 1")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = 1
                        l_foundFiles.append(os.path.basename(match[0]))
                        if b_allData == np.nan:
                            b_allData = True
                    else:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = 0")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = 0
                        if 'raw' in scanIds[k]:
                            if scanIds[k]['raw']:
                                b_allData = False
                                l_missingFiles.append(f"*{'*'.join(scanIds[k]['regex'])}*")
                        else:
                            b_allData = False
                            l_missingFiles.append(f"*{'*'.join(scanIds[k]['regex'])}*")

            # elif isinstance(scanIds[k],str):
            #     match = [x for x in filesToProcess if scanIds[k] in x]
                
            #     # if sesNum in scanIds[k]['sessions']:
            #     #     d_dataMatrix[k] = np.nan
            #     if len(match) > 0:
            #         d_dataMatrix[k] = 1
            #     else:
            #         d_dataMatrix[k] = 0

            # if 'BidsDir' in scanIds[k].keys():

            for k in d_bidsDirs.keys():
                if not set(d_dataMatrix[k].keys()) <= set(['participant_id','session']):
                    df_dataMatrix = pd.DataFrame(d_dataMatrix[k], index=[0])
                    d_completeData[k] = pd.concat([d_completeData[k],df_dataMatrix], ignore_index=True)



            #NEED TO DO SOMETHING WITH MRS DATA
            #NEED TO DO SOMETHING WITH BEHAVIORAL/PHILIPS LOG DATA



            
            # #look for raw rda's
            # if 'raw_rda' in scanIds:
            #     for f in scanIds['raw_rda']:
            #         match = [x for x in filesToProcess if f + '.rda' in x]
            #         if len(match) > 0:
            #             dataMatrix.append(1)
            #         else:
            #             dataMatrix.append(0)
            
            # #look for processed_T1_files
            # if 'processed_T1_files' in scanIds:
            #     for f in scanIds['processed_T1_files']:
            #         if not 'highres2' in f:
            #             match = [x for x in filesToProcess if f + '.nii.gz' in x]
            #         else:
            #             match = [x for x in filesToProcess if f + '.mat' in x]
            #         if len(match) > 0:
            #             dataMatrix.append(1)
            #         else:
            #             dataMatrix.append(0)
            
            # #look for processed_asl_files
            # if 'processed_asl_files' in scanIds:
            #     for f in scanIds['processed_asl_files']:
            #         if 'asl2' in f:
            #             match = [x for x in filesToProcess if f + '.mat' in x]
            #         elif 'perfusion_calib' in f:
            #             match = [x for x in filesToProcess if f + '.nii.gz' in x]
            #             match = [x for x in match if 'std_space' in x]
            #         else:
            #             match = [x for x in filesToProcess if f + '.nii.gz' in x]
            #         if len(match) > 0:
            #             dataMatrix.append(1)
            #         else:
            #             dataMatrix.append(0)
            
            # #look for processed_mrs_files
            # if 'processed_mrs_files' in scanIds:
            #     for f in scanIds['processed_mrs_files']:
            #         match = [x for x in filesToProcess if f + '.ps' in x]
            #         if len(match) > 0:
            #             dataMatrix.append(1)
            #         else:
            #             dataMatrix.append(0)

            
    #         df_dataMatrix = pd.DataFrame(d_dataMatrix, index=[0])
    #         #write dataframe to csv
    #         if os.path.isfile(outputCsv):
    #             df_dataMatrix.to_csv(outputCsv, mode='a', index=False, header=False)
    #         else:
    #             df_dataMatrix.to_csv(outputCsv, mode='a', index=False)

    #         df_completeData = pd.concat([df_completeData,df_dataMatrix], ignore_index=True)


            #do something for completed data
            if b_newSubject:
                print(f"{subName}\t{fullSesNum}")
                print(f"\t{b_newSubject}")
                print(l_foundFiles)
                print(l_missingFiles)
                if b_allData:
                    if not matching_idx.empty:
                        df_prevMissing.loc[matching_idx,'all_data'] = True
                        st.mysql.sql_mri_tracking_set(df_prevMissing)

                    format_str = '\t' + '\n\t'.join(l_foundFiles)

                    msgSubject = f"All Data Found: {subName} ses-{sesNum}"
                    msgPriority = "3"
                    msgBody = f"""
Project: {st.creds.project}
Date: {yesterday.strftime('%Y%m%d')}
Subject: {subName}
Session: ses-{sesNum}

Missing Data: None

Found Files:
{format_str}


This automated message was sent by the CoNNECT NPC check_rawdata support tool. 

DISCLAIMER: You must still confirm all data was transferred prior to source removal. 

You're Welcome


Sincerely,
Wright State CoNNECT Team
                    """
                elif not matching_idx.empty:
                    #update number of checks
                    num_checks = df_prevMissing.loc[matching_idx, "num_checks"].iloc[0]
                    df_prevMissing.loc[matching_idx, "num_checks"] = num_checks + 1
                    st.mysql.sql_mri_tracking_set(df_prevMissing)

                    #format some email text
                    format_str = '\t' + '\n\t'.join(l_missingFiles)
                    format_str2 = '\t' + '\n\t'.join(l_foundFiles)


                    msgSubject = f"MISSING DATA: {subName} ses-{sesNum}"
                    msgPriority = "1"
                    msgBody = f"""
Project: {st.creds.project}
Date: {yesterday.strftime('%Y%m%d')}
Subject: {subName}
Session: ses-{sesNum}

Missing Data: 
{format_str}

Found Files: 
{format_str2}


This automated message was sent by the CoNNECT NPC check_rawdata support tool. 

DISCLAIMER: You must still confirm all data was transferred prior to source removal. 



You're Welcome,

Matthew Sherwood, PhD
Director, CoNNECT
                    """

                #send EMAIL message
                msg = MIMEText(msgBody)
                msg["Subject"] = msgSubject
                msg["From"] = "mriresearch@wright.edu"
                msg["To"] = "matt.sherwood@wright.edu"
                if len(st.creds.contact) > 1:
                    msg["CC"] = ', '.join(st.creds.contact[1:])
                msg["X-Priority"] = msgPriority
                with smtplib.SMTP("localhost") as server:
                    server.sendmail("mriresearch@wright.edu", st.creds.contact, msg.as_string())



                # #update file
                # with open(str(load_data(f"{yesterday.strftime('%Y')}/{yesterday.strftime('%Y%m')}_checks.txt")),'a+') as f:
                #     if l_missingFiles and l_foundFiles:
                #         f.write(f"{yesterday.strftime('%Y%m%d')},{st.creds.project},{subName},ses-{sesNum},complete={b_allData},missing={' '.join(l_missingFiles)},files={' '.join(l_foundFiles)}\n")
                #     elif l_missingFiles:
                #         f.write(f"\n{yesterday.strftime('%Y%m%d')},{st.creds.project},{subName},ses-{sesNum},complete={b_allData},missing={' '.join(l_missingFiles)},files=None\n")
                #     elif l_foundFiles:
                #         f.write(f"\n{yesterday.strftime('%Y%m%d')},{st.creds.project},{subName},ses-{sesNum},complete={b_allData},missing=None,files={' '.join(l_foundFiles)}\n")
            



    # # Apply styling 
    # styled_df = df_completeData.style.applymap(color_cells)
    # # html_output = styled_df.render()
    # html_table = styled_df.to_html()
    main_html_output = f"""
    <html>
    <head>
        <title>Table Navigation</title>
        <style>
            
            button {{
                margin: 10px;
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                border: none;
                background-color: #007bff;
                color: white;
                border-radius: 5px;
            }}
                button:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
        <h1>Rawdata Tables Navigation</h1>
        <button onclick=printPage()">Print</button>
        <button onclick="window.location.href='{outputCsv.replace(".csv",".html")}'">Home</button>
    """


    html_output = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        .button-container {{
            margin: 20px 0;
        }}
        button {{
            margin: 10px;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            background-color: #007bff;
            color: white;
            border-radius: 5px;
        }}
        button:hover {{
            background-color: #0056b3;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            position: relative;
        }}
        th, td {{
            border: 1px solid black; 
            padding: 5px;
            text-align: center;
            white-space: nowrap;
        }}
        th:nth-child(1), td:nth-child(1) {{
            position: sticky;
            left: 0;
            background-color: #fff; /* Optional: Background color for sticky columns */
            z-index: 2;
        }}
        thead {{
            background-color: #f8f8f8;position: sticky;
            top: 0;
            z-index: 3; /* Keeps header above other elements */
        }}
    /* Make first column sticky */
    
        .dataframe-container {{
            max-height: 1000px;
            overflow-y: auto;
            overflow-x: auto;
        }}
    
        .section-text {{
            font-size: 18px;
            font-weight: bold;
            margin: 10px 0;
            text-align: center;
        }}
        /* Print styles */
        @media print {{
            body * {{
                visibility: visible !important;
                overflow: visible !important;
            }}
            .dataframe-container {{
                overflow: visible !important;
                max-height: none !important;
            }}
        }}
    </style>
    </head>
    <body>
        <h1>Rawdata Tables Navigation</h1>
        <button onclick="printTable()">Print</button>
        <button onclick="window.location.href='{outputCsv.replace(".csv",".html")}'">Home</button>
    """
    for k in d_bidsDirs.keys():
        if not d_completeData[k].empty:
            html_output += f"""
                <button onclick="window.location.href='{outputCsv.replace(".csv",f"_{k}.html")}'">{d_bidsDirs[k]}</button>
            """

    for k in d_bidsDirs.keys():
        new_html_output = ""
        if not d_completeData[k].empty:
            styled_df = d_completeData[k].style.applymap(_color_cells)
            html_table = styled_df.to_html(index=False)

            new_html_output = html_output + f"""
            </div>
            <div class="section-text">{d_bidsDirs[k]} Rawdata Table</div>
            <div class="dataframe-container">
            {html_table}
            </div>
            <br>
            <script>
                function printTable() {{
                    window.print();
                }}
            </script>
            """
            # count += 1

            main_html_output += f"""
                <button onclick="window.location.href='{outputCsv.replace(".csv",f"_{k}.html")}'">{d_bidsDirs[k]}</button>
            """
    
        new_html_output += f"""
        </body>
        </html>
        """

        # Write to an HTML file
        with open(outputCsv.replace('.csv',f'_{k}.html'), "w") as f:
            f.write(new_html_output)

    print(f"HTML file generated: {outputCsv.replace('.csv',f'_{k}.html')}")

    # print('SUCCESS: output saved to ' + outputCsv)

    main_html_output += f"""
    </body>
    </html>
    """
    
    with open(outputCsv.replace('.csv',f'.html'), "w") as f:
        f.write(main_html_output)