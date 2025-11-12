#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 3 March 2025
#
# v

import os
import argparse
import sys
import json
import shutil 
import glob


#local import
REALPATH = os.path.realpath(__file__)

sys.path.append(os.path.dirname(REALPATH))
import support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '3 March 2025'



# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser("This program is the batch wrapper command to perform DICOM to NIfTI conversion using dcm2niix. The program searches the specified project's searchSourceTable for acquisition folders (acq-*) which contain DICOM images and runs wsuconnect.support_tools.convert_dicoms for each returned directory.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected project: " + ' '.join(st.creds.projects))
parser.add_argument('-t', '--test', action="store_true", dest="TEST", help="print conversion information only", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")
parser.add_argument('--progress', action="store_true", dest="progress", help="Show progress (default FALSE)", default=False)



# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    #read crendentials from $SCRATCH_DIR/instance_ids.json
    ls_updatedFiles = []
    ls_existingFiles = []

    #get and evaluate options
    options = parser.parse_args()
    
    if options.version:
        print('connect_dcm2nii.py version {0}.'.format(VERSION)+" DATED: "+DATE)
    
    # #determine if the project exists
    # if not options.PROJECT in st.creds.projects:
    #     if not options.version:
    #         print("ERROR: user must define a project using [-p|--project <project>]\n\n")
    #         parser.print_help()
    #     sys.exit()

    
    st.creds.read(options.PROJECT)

    for file in glob.glob(os.path.join(st.creds.dataDir,'derivatives','sub-*_aslprep.html')):
        subName = 'sub-' + file.split('sub-')[1].split('_')[0]


        figTypes = ['basil','basilGM','cbf','score','scrub']
        for figType in figTypes:
            head = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        @page {{
        size: 8.5in 11in; margin: 0.5in 0.5in 0.5in 0.5in;
        }}
            # newD.append('@media screen {{
            # newD.append('footer {{
            # newD.append('display: none; }}
            # newD.append('}}
        .tab {{
        display: inline-block;
        margin-left: 2em;
        }}
        .hidden-print {{
        display: none; }}
        header {{
        font-size: 9px;
            # newD.append('color: #f00;
        text-align: center;
        }}
        @media print {{
            @page {{
                margin: 1.5in 0.5in 1in 0.5in; /* Space for header */
            }}

            .print-table {{
                width: 100%;
                border-collapse: collapse;
            }}

            /* Ensures header repeats on every page */
            .print-header {{
                display: table-header-group;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
                background: white;
                padding: 0px;
                border-bottom: 1px solid black;
                line-height: 1; /* Decrease line height for more compact text */
            }}

            .print-content {{
                display: table-row-group;
                page-break-before: always; /* Force page break */
                page-break-inside: avoid; /* Prevents row from splitting */
            }}
            td {{
                page-break-inside: avoid;
                break-inside: avoid;  /* Prevents cell content from breaking */
            }}
            img.svg-reportlet {{
                width: 100%;  /* Ensures the image does not exceed the container's width */
                height: auto;  /* Maintain aspect ratio */
            }}
            .header-line {{
                display: block;
                line-height: 1.2;  /* Controls the line spacing */
                margin-bottom: 2px;  /* Adjust the space between header lines */
            }}
        }}
    </style>
    <title>{subName}_aslprep_{figType}</title>
</head>

<body style="font-family: helvetica;">
    <button class="hidden-print" onClick="window.print()">Print</button>
    <table class="print-table">
        <thead>
            <tr class="print-header">
                <th>
                    <div class="header-line">Wright State University | Center of Neuroimaging and Neuro-Evaluation of Cognitive Technologies</div>
                    <div class="header-line">ASLPrep {figType} report for {subName}</div>
                </th>
            </tr>
        </thead>
        <tbody>

            """


            svgFiles = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=f'desc-{figType}_cbf.svg',exclusion=['bak'],inclusion=['derivatives',f'{subName}','figures'])
            count = 1
            for svgFile in sorted(svgFiles):
                lbls = st.bids.get_bids_labels(svgFile)
                st.subject.get_id(svgFile)
                h2str = 'Reports for: '
                if st.subject.sesNum:
                    h2str += f' session <span class="bids-entity">{st.subject.sesNum}</span>'

                d_keys = ['acquisition','run','task']
                for k in d_keys:
                    if k in lbls.keys():
                        h2str += f', {k} <span class="bids-entity">{lbls[k]}</span>'
                h2str += ''

                    
                head += f"""
        <tr class="print-content">
            <td>
                <div class="content-block">
                    <p>
                        <h3 class="run-title mt-3">{h2str}</h3>
                        <small>
                            The maps plot cerebral blood flow (CBF) for {figType}-estimated CBF.
                            The unit is mL/100 g/min. 
                        </small>
                        <img class="svg-reportlet" src="{svgFile.replace(os.path.join(st.creds.dataDir,'Derivatives'),'.')}" style="width: 100%" />
                        <small>File: <a href="{svgFile.replace(os.path.join(st.creds.dataDir,'derivatives'),'.')}" target="_blank">{svgFile.replace(os.path.join(st.creds.dataDir,'derivatives') + os.path.sep,'')}</a></small>
                    </p>
                </div>
            </td>
        </tr>
                """
                


            #end file loop
            head += f"""
<!-- </div> -->


        </tbody>
    </table>

<script type="text/javascript">
function toggle(id) {{
    var element = document.getElementById(id);
    if(element.style.display == 'block')
        element.style.display = 'none';
    else
        element.style.display = 'block';
}}
</script>
</body>
</html>
            """


            with open(file.replace("aslprep",f"aslprep_{figType}"), "w") as f:
                f.write(head)
        print(f"Finished Subject: {subName}")
            # os.system('wkhtmltopdf --enable-local-file-access -O Portrait ' + file.replace("aslprep",f"aslprep_{figType}") + ' ' + file.replace("aslprep.html",f"aslprep_{figType}.pdf"))







