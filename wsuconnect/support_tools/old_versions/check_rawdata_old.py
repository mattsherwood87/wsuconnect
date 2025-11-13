#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 25 Feb 2025
#
# 

import os
import sys
import json
import pandas as pd
import numpy as np

#local import

REALPATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REALPATH = os.path.join('/resshare','wsuconnect')
sys.path.append(REALPATH)

import support_tools as st


# ******************* Function to apply colors *****************
def _color_cells(val):
    if val == 1:
        return "background-color: green; color: white;"
    elif val == 0:
        return "background-color: red; color: white;"
    else:
        return "background-color: white; color: black;"



# ******************* MAIN ********************
def check_rawdata(project: str, progress: bool = False):
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json
    st.creds.read(project)
    if os.path.isfile(os.path.join(st.creds.dataDir,'code',project + '_scan_id.json')):
        scanIdFile = os.path.join(st.creds.dataDir,'code',project + '_scan_id.json')

    if os.path.isfile(os.path.join(st.creds.dataDir,'rawdata','participants.tsv')):
        groupIdFile = os.path.join(st.creds.dataDir,'rawdata','participants.tsv')

    try:
        #read scan ids
        with open(scanIdFile) as j:
            scanIds = json.load(j)
            if '__general_comment__' in scanIds.keys():
                scanIds.pop('__general_comment__')

        #read participants tsv file
        df_participants = pd.read_csv(groupIdFile, sep='\t')
   
    except FileNotFoundError as e:
        print("Error Message: {0}".format(e))
        sys.exit()

    #sort participants
    df_participants.sort_values(by=['participant_id'])

    #skip any participants?
    if 'discard' in df_participants.columns:
        df_participants = df_participants[~df_participants['discard']]

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

        if progress:
            print(subName)

        # if df_participants[df_participants['participant_id'] == subName].discard.item():
        #     continue
        subFilesToProcess = [x for x in allFilesToProcess if subName in x]
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
            if progress:
                print('\tses-' + fullSesNum)
            filesToProcess = [x for x in subFilesToProcess if fullSesNum in x]
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

            # d_dataMatrix['group'] = 

            #look for raw nifti's
            for k in scanIds:
                if not isinstance(scanIds[k],dict):
                    continue

                if not 'BidsDir' in scanIds[k].keys():
                    continue

                if 'bids_labels' in scanIds[k].keys():
                    scanName = st.bids.get_bids_filename(**scanIds[k]['bids_labels'])[1:]
                    match = [x for x in filesToProcess if scanName + '.nii.gz' in x]

                    if not sesNum in scanIds[k]['sessions']:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = np.NaN")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = np.NaN
                    elif len(match) > 0:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = 1")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = 1
                    else:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[scanName] = 0")
                        d_dataMatrix[scanIds[k]['BidsDir']][scanName] = 0


                elif 'regex' in scanIds[k].keys():
                    # str.contains(r'(?=.*{})'.format(scanIds[k]['BidsDir']), regex=True)
                    match = [x for x in filesToProcess if set([ele for ele in scanIds[k]['regex'] if ele in x]) == set(scanIds[k]['regex'])]
                
                    if not sesNum in scanIds[k]['sessions']:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = np.NaN")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = np.NaN
                    elif len(match) > 0:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = 1")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = 1
                    else:
                        # exec(f"d_{scanIds[k]['BidsDir']}Matrix[k] = 0")
                        d_dataMatrix[scanIds[k]['BidsDir']][k] = 0

            # elif isinstance(scanIds[k],str):
            #     match = [x for x in filesToProcess if scanIds[k] in x]
                
            #     # if sesNum in scanIds[k]['sessions']:
            #     #     d_dataMatrix[k] = np.NaN
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