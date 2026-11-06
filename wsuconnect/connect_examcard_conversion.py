#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 April 2024
#
# v2.0.0 on 6 November 2026 - handle the new scanner software export format; write examcard.pdf with reportlab

import os
import sys
import datetime
import argparse
import html
from itertools import zip_longest

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak, KeepInFrame


REALPATH = os.path.dirname(os.path.realpath(__file__))

import wsuconnect.support_tools as st

# GLOBAL INFO
#versioning
VERSION = '2.0.0'
DATE = '6 November 2026'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser(description="Convert a project's Philips ExamCard text exports (listed in scanorder.txt) to an examcard.pdf and examcard.html summary.")
parser.add_argument('-p','--project', action="store", dest="PROJECT", help="load the selected projects examcards from scanorder.txt (project identifier in credentials.json)", default=None)
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
parser.add_argument('-i', '--in-dir', help="Use a specific directory rather than a project directory", action="store", default=None, dest="INDIR")
parser.add_argument('-f', '--format', help="Output file(s) to write: pdf, html, or both (default both)", action="store", choices=['pdf','html','both'], default='both', dest="FORMAT")
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

# parameters that are not reported
SKIPKEYS = ['EX_single_scan_id','Coil 1  (exclude)','compacted','compacted coils','compacted conns','stacks channels','clinical modes','Patient weight [kg]','SmartSelect','Coil 1 (exclude)',
            'Large table movement','Patient position','Patient body position','Patient orientation','Patient orientations','Patient body orientation','SAR allow first level','Patient pregnancy','Patient WB SAR [W/kg]',
            'Patient Head SAR [W/kg]','Patient max. dB/dt [T/s]','Max slewrate [T/m/s]','Max. B1+rms [uT]','2nd VOI lat. offc. (mm)','2nd VOI offc. axis','IF_info_seperator','IF.info_seperator','Free rotatable']

TITLE = 'Wright State University | Center of Neuroimaging and Neuro-Evaluation of Cognitive Technology'
GREEN = '#046A38'



# ******************* SORT REQUESTED TABLES ********************
def evaluate_args(options):

    #print version if selected
    if options.version:
        print(os.path.basename(REALPATH) + ' version {0}.'.format(VERSION)+" DATED: "+DATE)



# ******************* PARSE ONE EXAMCARD ********************
def parse_examcard(filepath: str) -> dict:
    """
    Parse one ExamCard text export into the ExamCard tabs.

    :param filepath: path to the ExamCard .txt export
    :type filepath: str
    :return: dictionary with keys inf, geo, con, mot, dyn, pro; each is a list of (parameter, value, indent level)
    :rtype: dict
    """
    d_dict = {'inf': [], 'geo': [], 'con': [], 'mot': [], 'dyn': [], 'pro': []}

    # ExamCard exports use Windows line endings
    with open(filepath, 'r', errors='replace') as f:
        ls_data = f.read().splitlines()

    strCat = 'geo'
    skipLines = 0
    for k in ls_data:
        if not k.strip():
            continue

        # sub-parameters are indented in the export (spaces, or a tab inside a Stack block)
        bIndented = k[:1] in (' ', '\t')

        # reformat data into two-column list [key, value]
        k = k.strip().replace('\t','').replace(';','').replace('"','')
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
        elif a[0] in SKIPKEYS:
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
        elif ('Manual start' in a[0] or "Contrast enh." in a[0]) and strCat != 'dyn':
            strCat = 'dyn'
        elif ('Preparation phases' in a[0] or a[0] == 'Images') and strCat not in ['pro','inf']:
            strCat = 'pro'
        elif 'Total scan duration' in a[0] or (a[0].startswith('Act. ') and not bIndented):
            strCat = 'inf'
        elif a[0] in ['Stack','Beam','Shim volume'] and not bIndented:
            # newer software exports the stack geometry at the end of the file
            strCat = 'geo'

        # indent sub-parameters
        if a[0] in ['gap (mm)']:
            level = 2
        elif bIndented or a[0] in SUBKEYS or 'P reduction' in a[0] or 'S reduction' in a[0]:
            level = 1
        else:
            level = 0

        d_dict[strCat].append((a[0], a[1], level))

    return d_dict



def build_columns(d_dict: dict) -> list:
    """
    Arrange the ExamCard tabs into the three report columns.

    Column 1 is INFO PAGE then POST/PROC, column 2 is GEOMETRY, MOTION, DYN/ANG, and column 3 is CONTRAST.
    Each cell is a (parameter, value, indent level) tuple, a section title string, or None (empty).

    :param d_dict: output of parse_examcard()
    :type d_dict: dict
    :return: list of rows, each a list of three cells
    :rtype: list
    """
    col1 = ['INFO PAGE'] + d_dict['inf']
    if d_dict['pro']:
        col1 += ['POST/PROC'] + d_dict['pro']
    col2 = ['GEOMETRY'] + d_dict['geo']
    if d_dict['mot']:
        col2 += ['MOTION'] + d_dict['mot']
    if d_dict['dyn']:
        col2 += ['DYN/ANG'] + d_dict['dyn']
    col3 = ['CONTRAST'] + d_dict['con']

    return [list(r) for r in zip_longest(col1, col2, col3)]



# ******************* PDF OUTPUT ********************
def write_pdf(outFile: str, ls_seq: list):
    """
    Write the ExamCard report as a PDF (letter, portrait) using reportlab.

    The first page lists the scan order, then each sequence gets one page. A sequence with
    too many parameters to fit is scaled down to fit its page.

    :param outFile: output PDF filename
    :type outFile: str
    :param ls_seq: list of (sequence name, rows) where rows is the output of build_columns()
    :type ls_seq: list
    """
    created = datetime.datetime.today().strftime('%B %d, %Y @ %H:%M:%S')
    pagesize = letter
    margin = 0.4*inch
    width = pagesize[0] - 2*margin

    sKey = ParagraphStyle('key', fontName='Helvetica', fontSize=6.5, leading=7.5)
    sVal = ParagraphStyle('val', parent=sKey)
    sHead = ParagraphStyle('head', parent=sKey, fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white, alignment=1)
    sTitle = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1)
    sOrder = ParagraphStyle('order', fontName='Helvetica', fontSize=10, leading=12)

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawCentredString(pagesize[0]/2, pagesize[1] - 0.3*inch, TITLE)
        canvas.setFont('Helvetica', 7)
        canvas.drawString(margin, 0.25*inch, 'Created by connect_examcard_conversion.py on ' + created)
        canvas.drawRightString(pagesize[0] - margin, 0.25*inch, 'Page %d' % doc.page)
        canvas.restoreState()

    doc = SimpleDocTemplate(outFile, pagesize=pagesize, leftMargin=margin, rightMargin=margin,
                            topMargin=0.5*inch, bottomMargin=0.45*inch,
                            title='ExamCard', author='connect_examcard_conversion.py')
    frameHeight = doc.height - 12  # leave room for the frame padding
    story = []

    # scan order page
    orderRows = [[Paragraph('<b>Sequence Number</b>', sOrder), Paragraph('<b>Sequence Name</b>', sOrder)]]
    for i, (seq, _) in enumerate(ls_seq, start=1):
        orderRows.append([Paragraph(str(i), sOrder), Paragraph(html.escape(seq), sOrder)])
    tOrder = Table(orderRows, colWidths=[1.5*inch, 5*inch], repeatRows=1, hAlign='LEFT')
    tOrder.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black),
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E6E6E6')),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(Paragraph('Scan Order', sTitle))
    story.append(tOrder)

    # one table per sequence: param, value, spacer x3
    gap = 0.08*inch
    pw = (width - 2*gap) / 3
    colWidths = [pw*0.6, pw*0.4, gap, pw*0.6, pw*0.4, gap, pw*0.6, pw*0.4]
    for i, (seq, rows) in enumerate(ls_seq, start=1):
        story.append(PageBreak())
        data = [[Paragraph(str(i) + ', ' + html.escape(seq), sTitle)] + ['']*7]
        style = [('SPAN', (0,0), (-1,0)),
                 ('FONTSIZE', (0,0), (-1,-1), 6.5), ('LEADING', (0,0), (-1,-1), 7.5),
                 ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                 ('TOPPADDING', (0,1), (-1,-1), 1), ('BOTTOMPADDING', (0,1), (-1,-1), 1),
                 ('LEFTPADDING', (0,1), (-1,-1), 2), ('RIGHTPADDING', (0,1), (-1,-1), 2),
                 ('BOTTOMPADDING', (0,0), (-1,0), 6)]
        for r, row in enumerate(rows, start=1):
            line = []
            for c, cell in enumerate(row):
                c0 = c*3
                if cell is None:
                    line += ['', '']
                elif isinstance(cell, str):
                    line += [Paragraph(cell, sHead), '']
                    style += [('SPAN', (c0,r), (c0+1,r)), ('BACKGROUND', (c0,r), (c0+1,r), colors.HexColor(GREEN)),
                              ('BOX', (c0,r), (c0+1,r), 0.5, colors.black)]
                else:
                    indent = '&nbsp;'*4*cell[2]
                    line += [Paragraph(indent + html.escape(cell[0]), sKey), Paragraph(html.escape(cell[1]), sVal)]
                    style += [('GRID', (c0,r), (c0+1,r), 0.5, colors.black)]
                if c < 2:
                    line.append('')
            data.append(line)
        t = Table(data, colWidths=colWidths)
        t.setStyle(TableStyle(style))
        # keep each sequence on one page, shrinking a long one to fit
        story.append(KeepInFrame(width, frameHeight, [t], mode='shrink'))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)



# ******************* HTML OUTPUT ********************
def write_html(outFile: str, ls_seq: list):
    """
    Write the ExamCard report as HTML. Each sequence prints on its own page and the
    column headers repeat if a table runs onto a second printed page.

    :param outFile: output HTML filename
    :type outFile: str
    :param ls_seq: list of (sequence name, rows) where rows is the output of build_columns()
    :type ls_seq: list
    """
    newD = st.prepare_examcard_html().split('\n')

    # scan order table
    newD.append('<table class="order">')
    newD.append('<thead><tr><th>Sequence Number</th><th>Sequence Name</th></tr></thead>')
    for i, (seq, _) in enumerate(ls_seq, start=1):
        newD.append('<tr><td>' + str(i) + '</td><td>' + html.escape(seq) + '</td></tr>')
    newD.append('</table>')

    for i, (seq, rows) in enumerate(ls_seq, start=1):
        newD.append('<section class="sequence">')
        newD.append('<table class="examcard">')
        newD.append('<colgroup><col class="k"><col class="v"><col class="gap"><col class="k"><col class="v"><col class="gap"><col class="k"><col class="v"></colgroup>')
        newD.append('<thead>')
        newD.append('<tr><th colspan="8" class="title">' + str(i) + ', ' + html.escape(seq) + '</th></tr>')
        # the first row holds the three column headers, so it repeats with the title on each printed page
        hdr = rows[0]
        newD.append('<tr>' + '<td class="gap"></td>'.join('<th colspan="2" class="sect">' + h + '</th>' for h in hdr) + '</tr>')
        newD.append('</thead>')
        newD.append('<tbody>')
        for row in rows[1:]:
            cells = []
            for cell in row:
                if cell is None:
                    cells.append('<td class="empty"></td><td class="empty"></td>')
                elif isinstance(cell, str):
                    cells.append('<th colspan="2" class="sect">' + cell + '</th>')
                else:
                    cells.append('<td class="lvl' + str(cell[2]) + '">' + html.escape(cell[0]) + '</td><td>' + html.escape(cell[1]) + '</td>')
            newD.append('<tr>' + '<td class="gap"></td>'.join(cells) + '</tr>')
        newD.append('</tbody>')
        newD.append('</table>')
        newD.append('</section>')

    newD.append('<footer>Created by connect_examcard_conversion.py on ' + datetime.datetime.today().strftime('%B %d, %Y @ %H:%M:%S') + '</footer>')
    newD.append('</body>')
    newD.append('</html>')

    with open(outFile, 'w') as f:
        for line in newD:
            f.write(f"{line}\n")



# *******************  MAIN  ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    evaluate_args(options)

    if options.INDIR:
        ecardDir = options.INDIR
    elif options.PROJECT:
        st.creds.read(options.PROJECT)
        ecardDir = os.path.join(st.creds.dataDir,'ExamCards')
    else:
        parser.error('one of -p/--project or -i/--in-dir is required')

    print('Creating ExamCard tables on ' + datetime.datetime.today().strftime('%Y%m%d @ %H:%M:%S'))

    if not os.path.isfile(os.path.join(ecardDir,'scanorder.txt')):
        print('ERROR: cannot find scanorder.txt in  examcard directory - ' + ecardDir)
        sys.exit()
    with open(os.path.join(ecardDir,'scanorder.txt'), 'r') as f:
        ls_inFiles = [s.strip() for s in f.read().splitlines() if s.strip()]

    # parse each ExamCard in scan order
    ls_seq = []
    for inFile in ls_inFiles:
        seq = os.path.splitext(os.path.basename(inFile))[0]
        if options.progress:
            print('Processing sequence: ' + seq)
        if not os.path.isfile(os.path.join(ecardDir, inFile)):
            print('WARNING: cannot find ' + inFile + ' in examcard directory - skipping')
            continue
        ls_seq.append((seq, build_columns(parse_examcard(os.path.join(ecardDir, inFile)))))

    if options.FORMAT in ['pdf','both']:
        write_pdf(os.path.join(ecardDir, 'examcard.pdf'), ls_seq)
        print('Wrote ' + os.path.join(ecardDir, 'examcard.pdf'))
    if options.FORMAT in ['html','both']:
        write_html(os.path.join(ecardDir, 'examcard.html'), ls_seq)
        print('Wrote ' + os.path.join(ecardDir, 'examcard.html'))
