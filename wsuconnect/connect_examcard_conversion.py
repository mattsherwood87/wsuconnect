#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 April 2024
#
# v2.0.0 on 1 April 2023 -

import os
import sys
import datetime
import argparse
import re
import html
from itertools import zip_longest
from glob import glob as glob


# REALPATH = os.path.realpath(__file__)
# sys.path.append(os.path.dirname(REALPATH))

REALPATH = os.path.dirname(os.path.realpath(__file__))

import wsuconnect.support_tools as st

# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '23 April 2024'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser(description="Convert a project's Philips ExamCard text exports (listed in scanorder.txt) to MySQL tables and an examcard.html summary.")
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="load the selected projects examcards from scanorder.txt (project identifier in credentials.json)", default=None)
# parser.add_argument('-r','--raw', action="store_true", dest="RAW", help="Command line argument to update the raw_data table for the selected project (default FALSE)", default=False)
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
parser.add_argument('-i', '--in-dir', help="Use a specific directory rather than a project directory", action="store", default=None, dest="INDIR")
parser.add_argument('--progress', help="Show progress (default FALSE)", action="store_true", dest="progress", default=False)


# parameters shown indented under their parent parameter (older exports did not indent these)
SUBKEYS = ['(mm)','(ms)','P (mm)','A (mm)','F (mm)','(pixels)','AP (mm)','FH (mm)','RL (mm)','slices','Slices','slice gap','slice orientation',
           'fold-over direction','fat shift direction','Modified SE','MB Factor','MB Shift','partial echo','shifted echo','factor',
           'oversample factor','technique','3D view','shot mode','startup echoes','profile order','turbo direction','DRIVE',
           '3D non-select','partial echoes','strength','offset','dyn scans','dyn scan times','fov time mode','dummy scans',
           'immediate subtraction','fast next scan','synch. ext. device','dyn stabilization','prospect. motion corr.',
           'label type','label distance (mm)','label location','label duration','post label delay (ms)','normalized',
           'phases','start at dyn.','interval (dyn)','images','calculated images','frequency offset','offset (Hz)',
           'orientation','type','resuse memory','delay','PSIR','echo time (ms)','refocusing pulses','fid reduction',
           'angle (deg.)','gradient expert mode','gradient overplus','directional resolution','modified SE','SMART',
           'acquire during delay','dual','power','ultrashort','fid reduction extra strong','Offc. AP (P=+mm)','RL (L=+mm)',
           'FH (H=+mm)','reuse memory','radial axis','radial angle (deg)']


def header_cell(title: str) -> str:
    """Return the HTML for a green ExamCard section header cell."""
    return '<td bgcolor="#046A38" colspan="2" style="font-weight:bold; text-align: center; vertical-align: middle;"> <font color="#FFFFFF" size="2">' + title + '</td>'


# ******************* SORT REQUESTED TABLES ********************
def evaluate_args(options):

    #print version if selected
    if options.version:
        print(os.path.basename(REALPATH) + ' version {0}.'.format(VERSION)+" DATED: "+DATE)


# *******************  MAIN  ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    evaluate_args(options)

    print('Creating ExamCard tables on ' + datetime.datetime.today().strftime('%Y%m%d @ %H:%M:%S'))


    #create tables
    st.creds.read(options.PROJECT)

    if options.PROJECT:
        ecardDir = os.path.join(st.creds.dataDir,'ExamCards')
    else:
        ecardDir = options.INDIR


    # setup HTML headers
    newD = st.prepare_examcard_html()
    newD = newD.split("\n")


    # inFiles = glob(os.path.join(ecardDir, '*.txt'))
    if not os.path.isfile(os.path.join(ecardDir,'scanorder.txt')):
        print('ERROR: cannot find scanorder.txt in  examcard directory - ' + ecardDir)
        sys.exit()
    f = open(os.path.join(ecardDir,'scanorder.txt'), 'r')

    # reading the file
    data = f.read()

    # replacing end splitting the text
    # when newline ('\n') is seen.
    pgbreak_flag = False
    ls_inFiles = [s.strip() for s in data.splitlines()]

    newD.append('<div>')
    newD.append('<p>')

    #newD.append('<div id="page" class="page" style = "background-color:#FFFFFF; height: 100%; width: 100%;">')
    # newD.append('<div class="header">')
    # # newD.append('<font face="Arial"><h1>' + seq + '</h1> </font>')
    # newD.append('</div>')

    #newD.append('<table style="width: 8.5in; height: 9in;">')
    newD.append('<table width="60%" border="1" cellspacing="0" cellpadding="2" align="Left" bordercolor="#000000">')
    # newD.append('<table width="100%" border="0" cellspacing="0" cellpadding="2" align="Left">')
    # newD.append('<table class="border-none">')


    newD.append('<colgroup>')
    newD.append('<col span="1" style="width: 30%;">')
    newD.append('<col span="1" style="width: 70%;">')
    newD.append('</colgroup>')

    newD.append('<br>')
    newD.append('<br>')
    newD.append('<tr>')
    newD.append('<td><font size="2">Sequence Number</td>')
    newD.append('<td><font size="2">Sequence Name</td>')
    newD.append('</tr>')
    c = 1
    for inFile in ls_inFiles:
        if not inFile:
            continue



        newD.append('<tr>')
        newD.append('<td><font size="2">' + str(c) + '</td>')
        newD.append('<td><font size="2">' + inFile.split('.')[0] + '</td>')
        newD.append('</tr>')
        c += 1

    newD.append('</table>')
    newD.append('</font>')

    newD.append('</p>')
    newD.append('</div>')

    c = 1
    for inFile in ls_inFiles:
        if not inFile:
            continue



        d_dict = {'inf_t': [],'inf_c': [],'inf_v': [],
                'geo_t': [],'geo_c': [],'geo_v': [],
                'con_t': [],'con_c': [],'con_v': [],
                'mot_t': [],'mot_c': [],'mot_v': [],
                'dyn_t': [],'dyn_c': [],'dyn_v': [],
                'pro_t': [],'pro_c': [],'pro_v': []
                }
        seq = os.path.basename(inFile).split('.')[0].replace('_',' ')

        if options.progress:
            print('Processing sequence: ' + seq)

        #continue header
        # if pgbreak_flag:
        newD.append('<div class="pagebreak"> </div>')
        # else:
            # pgbreak_flag = True


        # newD.append('<section>'10
        # newD.append('<h2><font face="arial" size="+1">Wright State University | Center of Neuroimaging and Neuro-Evaluation of Cognitive Technology</font></h2>')
        # newD.append('</section>')
        newD.append('<div>')
        newD.append('<p>')

        #newD.append('<div id="page" class="page" style = "background-color:#FFFFFF; height: 100%; width: 100%;">')
        # newD.append('<div class="header">')
        # # newD.append('<font face="Arial"><h1>' + seq + '</h1> </font>')
        # newD.append('</div>')

        #newD.append('<table style="width: 8.5in; height: 9in;">')
        newD.append('<table width="100%" border="1" cellspacing="0" cellpadding="2" align="Left" bordercolor="#000000">')
        # newD.append('<table width="100%" border="0" cellspacing="0" cellpadding="2" align="Left">')
        # newD.append('<table class="border-none">')


        newD.append('<colgroup>')
        newD.append('<col span="1" style="width: 20%;">')
        newD.append('<col span="1" style="width: 12.33%;">')
        newD.append('<col span="1" style="width: 1%;">')
        newD.append('<col span="1" style="width: 20%;">')
        newD.append('<col span="1" style="width: 12.33%;">')
        newD.append('<col span="1" style="width: 1%;">')
        newD.append('<col span="1" style="width: 20%;">')
        newD.append('<col span="1" style="width: 13.33%;">')
        newD.append('</colgroup>')
        #newD.append('<font face="arial" size="1">')

        #newD.append('<table width="90%" border="1" cellspacing="0" cellpadding="2" align="Left" bordercolor="#000000">')


        # reading the file (ExamCard exports use Windows line endings)
        with open(os.path.join(ecardDir,inFile), 'r', errors='replace') as f:
            ls_data = f.read().splitlines()


        # Parse the input file
        strCat = 'geo'
        skipLines = 0
        for k in ls_data:
            if not k.strip():
                continue

            # sub-parameters are indented in the export (spaces, or a tab inside a Stack block)
            bIndented = k[:1] in (' ', '\t')

            # reformat data into two-column list [key, value]
            k = k.strip()
            k = k.replace('\t','')
            k = k.replace(';','')
            k = k.replace('"','')
            if not ' =' in k:
                continue
            a = k.split(' =', 1)
            a = [a[0].strip(), a[1].strip()]

            if skipLines > 0:
                skipLines -= 1
                continue

            # off-centre and angulation values (and the lines that follow them) are not reported
            if ('Stack Offc.' in a[0] or "Ang." in a[0]) or 'VOI offc' in a[0] or 'VOI ang' in a[0] or 'Shim  Size' in a[0] or ("Offc." in a[0] and not 'Angio' in a[0]):
                skipLines = 2
                continue
            elif a[0] in ['EX_single_scan_id','Coil 1  (exclude)','compacted','compacted coils','compacted conns','stacks channels','clinical modes','Patient weight [kg]','SmartSelect','Coil 1 (exclude)',
                          'Large table movement','Patient position','Patient body position','Patient orientation','Patient orientations','Patient body orientation','SAR allow first level','Patient pregnancy','Patient WB SAR [W/kg]',
                          'Patient Head SAR [W/kg]','Patient max. dB/dt [T/s]','Max slewrate [T/m/s]','Max. B1+rms [uT]','2nd VOI lat. offc. (mm)','2nd VOI offc. axis','IF_info_seperator','IF.info_seperator','Free rotatable']:
                # the info separator marks the start of the info page
                if 'info_seperator' in a[0]:
                    strCat = 'inf'
                continue
            elif 'EX_GEO' in a[0]:
                continue


            # choose the ExamCard tab (category) for this parameter
            if 'Uniformity' in a[0] and not 'correction' in a[0]:
                strCat = 'geo'
            elif 'Scan type' in a[0]:
                strCat = 'con'
            elif 'Cardiac synchronization' in a[0]:
                strCat = 'mot'
            elif ('Manual start' in a[0] or "Contrast enh." in a[0]) and not 'dyn' in strCat:
                strCat = 'dyn'
            elif ('Preparation phases' in a[0] or a[0] == 'Images') and not 'pro' in strCat and not 'inf' in strCat:
                strCat = 'pro'
            elif 'Total scan duration' in a[0] or (a[0].startswith('Act. TR') and not bIndented):
                strCat = 'inf'
            elif a[0] in ['Stack','Beam','Shim volume'] and not bIndented:
                # newer software exports the stack geometry at the end of the file
                strCat = 'geo'


            # indent sub-parameters
            sKey = html.escape(a[0])
            if a[0] in ['gap (mm)']:
                sKey = '<span class="tab"></span><span class="tab"></span>' + sKey
            elif bIndented or a[0] in SUBKEYS or 'P reduction' in a[0] or 'S reduction' in a[0]:
                sKey = '<span class="tab"></span>' + sKey


            d_dict[strCat + '_c'].append(strCat)
            d_dict[strCat + '_t'].append(sKey)
            d_dict[strCat + '_v'].append(html.escape(a[1]))



        # write values to table
        # newD.append('INFO PAGE\t\tGEOMETRY\t\tCONTRAST')
        newD.append('<br>')
        newD.append('<br>')
        newD.append('<tr>')
        newD.append('<td colspan="8" style="border: none; border-collapse: collapse; font-weight:bold; text-align: center"> <font size="5">' + str(c) + ', ' +  seq + '</td>')
        newD.append('</tr>')
        c += 1
        newD.append('<tr>')
        newD.append(header_cell('INFO PAGE'))
        newD.append('<td></td>')
        newD.append(header_cell('GEOMETRY'))
        newD.append('<td></td>')
        newD.append(header_cell('CONTRAST'))
        newD.append('</tr>')

        # column 1: INFO PAGE then POST/PROC; column 2: GEOMETRY, MOTION, DYN/ANG; column 3: CONTRAST
        # each cell is either a (key, value) pair or a section header string
        col1 = list(zip(d_dict['inf_t'], d_dict['inf_v']))
        if d_dict['pro_t']:
            col1 += ['POST/PROC'] + list(zip(d_dict['pro_t'], d_dict['pro_v']))
        col2 = list(zip(d_dict['geo_t'], d_dict['geo_v']))
        if d_dict['mot_t']:
            col2 += ['MOTION'] + list(zip(d_dict['mot_t'], d_dict['mot_v']))
        if d_dict['dyn_t']:
            col2 += ['DYN/ANG'] + list(zip(d_dict['dyn_t'], d_dict['dyn_v']))
        col3 = list(zip(d_dict['con_t'], d_dict['con_v']))

        for cell1, cell2, cell3 in zip_longest(col1, col2, col3):
            newD.append('<tr>')
            for iCol, cell in enumerate([cell1, cell2, cell3]):
                if cell is None:
                    newD.append('<td></td>')
                    newD.append('<td></td>')
                elif isinstance(cell, str):
                    newD.append(header_cell(cell))
                else:
                    newD.append('<td>' + cell[0] + '</td>')
                    newD.append('<td>' + cell[1] + '</td>')
                if iCol < 2:
                    newD.append('<td></td>')
            newD.append('</tr>')


        newD.append('</table>')
        newD.append('</font>')

        newD.append('</p>')
        newD.append('</div>')


    newD.append('<footer>Created by connect_examcard_conversion.py on ' + datetime.datetime.today().strftime('%B %d, %Y @ %H:%M:%S') + '</footer>')





    newD.append('</body>')
    newD.append('</html>')

    with open(os.path.join(ecardDir, 'examcard.html'), 'w') as f:
        for line in newD:
            f.write(f"{line}\n")

    # os.system('wkhtmltopdf --enable-local-file-access -O Portrait ' + os.path.join(ecardDir, 'examcard.html') + ' ' + os.path.join(ecardDir, 'examcard.pdf'))







