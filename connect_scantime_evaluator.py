#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 24 Mar 2025
#
# Modified on 
VERSION = '2.0.0'
DATE = '10 November 2025'

import sys
import os
import argparse
import datetime
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from svglib.svglib import svg2rlg
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, KeepTogether, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics import renderPDF

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import calendar
import json
from pathlib import Path

#local import

REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-2]).resolve()
if not REALPATH in sys.path:
    sys.path.append(REALPATH)
    
import support_tools as st
from wsuconnect.data import load as load_data




parser = argparse.ArgumentParser('flirt.py: perform FLIRT registration between input and reference/standard brain images')

parser.add_argument('-m','--month', action='store',dest='YEARMONTH', help=' fullpath to a NIfTI file')
# parser.add_argument('DATA_DIR', help="fullpath to the project's data directory (project's 'dataDir' credential)")
# parser.add_argument('FLIRT_PARAMS', help="fullpath to project's FLIRT parameter control file")
# parser.add_argument('--bet-params',action='store',dest='BET_PARAMS', help="fullpath to project's BET parameter control file",default=None)
# parser.add_argument('--overwrite',action='store_true',dest='OVERWRITE',default=False, help='overwrite existing files')
parser.add_argument('--progress',action='store_true',dest='progress',default=False, help='verbose mode')



left_margin = 0.5 * inch
right_margin = 0.5 * inch

width, height = letter

def to_timedelta(dt):
    total_seconds = dt.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

def split_total_seconds(dt):
    hours, rem_minutes = divmod(scan_duration, 60)
    minutes, seconds = divmod(rem_minutes * 60, 60)
    return hours, minutes, seconds 

def draw_header_footer(canvas, doc):
    """Draws header and footer on each page."""
    canvas.saveState()

    
    # Header
    # canvas.setFont("Helvetica-Bold", 12)
    # header_text =  "WSU Center of Neuroimaging and Neuro-Evaluation of Cognitive Technologies"
    # header_width = canvas.stringWidth(header_text, "Helvetica-Bold", 12)
    # canvas.drawString((width - header_width) / 2, height - 0.5 * inch, header_text)

    header_image_path = load_data("wsu_biplane.png")  # Update with the correct path to your PNG
    img_width, img_height = 106, 50  # Adjust width and height as needed

    # Get page width to center the header
    page_width, page_height = letter

    # Position the image at the top center
    img_x = (page_width - img_width) / 2  # Centering
    img_y = page_height - img_height - inch*0.25  # 10 pts margin from top

    # Draw image on canvas
    canvas.drawImage(header_image_path, img_x, img_y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
    
    # # Footer (center text and right-aligned page number)
    canvas.setFont("Helvetica-Bold", 10)
    
    # First line of footer text (centered)
    footer_text_1 = "WSU Center of Neuroimaging and Neuro-Evaluation of Cognitive Technologies"
    footer_width_1 = canvas.stringWidth(footer_text_1, "Helvetica-Bold", 10)
    canvas.drawString((width - footer_width_1) / 2, 0.5 * inch, footer_text_1)
    
    # Second line of footer text (centered)
    canvas.setFont("Helvetica", 10)
    footer_text_2 = "3640 Colonel Glenn Highway • Dayton, OH 45435-0001 • 937-775-3904"
    footer_width_2 = canvas.stringWidth(footer_text_2, "Helvetica", 10)
    canvas.drawString((width - footer_width_2) / 2, 0.5 * inch - 12, footer_text_2)  # Adjust y-position for second line    
    
    canvas.restoreState()

def create_pdf(project, filtered_df, month) -> str:
    """Creates a PDF with SVG images and headers/footers."""
    # Set the left and right margins (in inches)
    st.creds.read(project)

    #look for a JSON invoice file
    inJsonFile = os.path.join('/resshare/scan_logs',month.strftime('%Y'),'invoices.json')
    if os.path.isfile(inJsonFile):
        with open(inJsonFile,'r') as j:
            d_invoices = json.load(j)
        lastInvoice = list(d_invoices.keys())[-1]
    else:
        d_invoices = {}
        lastInvoice = '0000-0000'
        
    i_nextInvoice = int(lastInvoice.split('-')[1]) + 1
    thisInvoice = f"{month.strftime('%Y')}-{i_nextInvoice:04d}"
    
    # Create a SimpleDocTemplate with custom margins
    outPdf = os.path.join('/resshare/scan_logs',month.strftime('%Y'),f"{thisInvoice}_{month.strftime('%b')}_CoNNECT_invoice.pdf")
    doc = SimpleDocTemplate(outPdf, pagesize=letter, leftMargin=left_margin, rightMargin=right_margin, topMargin=inch*1.25, bottomMargin=inch*0.5)
    # doc = SimpleDocTemplate(output_filename, pagesize=landscape(letter), leftMargin=left_margin, rightMargin=right_margin)
    styles = getSampleStyleSheet()
    elements = []

    # Data for the table
    data = [
        ["INVOICE", f"Invoice No. {thisInvoice}"],
        ["mriresearch@wright.edu", ""],
        ["937-775-3904", ""],
        ["", ""],
    ]
    
    # Create a table
    table_width = doc.width
    table = Table(data, colWidths=[table_width / len(data[0])] * len(data[0]))
    
    
    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left-align first column
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),  # Right-align last column
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('LEADING', (0, 0), (-1, -1), 10),  # Adjust line height for text in rows
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white)
    ])
    
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)


    elements.append(Paragraph(f'Description: MRI scans for project titled "{st.creds.title}"'))


    # Data for the table
    data = [
        ["Bill To:", "", "Remit To:"],
        ["Wright State University", "", "Wright State University"],
        ["Department: NCBP",  "", "CoNNECT MRI"],
        ["Contact Person: Matthew Sherwood",  "", "3640 Colonel Glenn Hwy"],
        ["Contact Email: matt.sherwood@wright.edu",  "", "Dayton, OH 45435"],
        ["Contact Phone: 937-524-3924",  "", "3640 Colonel Glenn Hwy"],
        [f"Fund: {st.creds.fund}",  "", ""],
        [f"Org: {st.creds.org}",  "", ""],
        ["Account: 731200",  "", ""],
        ["Program: 20052",  "", ""]
    ]
    
    # Create a table
    table = Table(data, colWidths=[table_width * 0.5, table_width * 0.1, table_width * 0.4])
    
    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),  # Header row background
        ('BACKGROUND', (-1, 0), (-1, 0), colors.lightgrey),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left-align first column
        ('ALIGN', (-1, 0), (-1, -1), 'LEFT'),  # Right-align last column
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Center-align middle column
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (1, 1), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # Reduced padding for data rows
        # ('BOTTOMPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        ('LEADING', (0, 0), (-1, -1), 10),  # Adjust line height for text in rows
        ('BOX', (0, 0), (0, -1), 1, colors.black),  # Left column outer grid
        ('BOX', (-1, 0), (-1, -1), 1, colors.black),  # Right column outer grid
        ('LINEABOVE', (0, 0), (0, 0), 1, colors.black),  # Top border
        ('LINEABOVE', (-1, 0), (-1, 0), 1, colors.black),  # Top border
    ])
    
    table.setStyle(style)
    
    # Add table to elements
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    _, last_day = calendar.monthrange(month.year, month.month)

    # Create a datetime object for the last day of the month
    last_day = datetime.date(month.year, month.month, last_day)

    data = [["FROM DATE","TO DATE",""],[last_day.replace(day=1).strftime('%m/%d/%Y'),last_day.strftime('%m/%d/%Y'),""]]
    
    table = Table(data, colWidths=[table_width*0.2, table_width*0.2, table_width*0.6])
    style = TableStyle([
        ('BACKGROUND', (2, 0), (-1, 0), colors.lightgrey),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center-align all columns excluding the last one for data rows
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (1, 1), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align to the middle
        ('TOPPADDING', (0, 0), (-1, -1), 5),  # Reduced padding for data rows
        # ('TOPPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        # ('BOTTOMPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        ('LEADING', (0, 0), (-1, -1), 10),  # Adjust line height for text in rows
        # ('BOX', (0, 0), (0, -1), 1, colors.black),  # Left column outer grid
        # ('BOX', (-1, 0), (-1, -1), 1, colors.black),  # Right column outer grid
        ('GRID', (2, 0), (-1, 0), 1, colors.black),  # Top border
        ('WORDWRAP', (0, 0), (-1, 0), True),  # Wrap text in the center column
        # ('LINEABOVE', (-1, 0), (-1, 0), 1, colors.black),  # Top border
    ])
    table.setStyle(style)
    

    df_subset = filtered_df[['date','arr. time','dep. time','sch. dur.','cancelled on','charged time','direct scan fee']].copy()
    df_subset['direct scan fee'] = df_subset['direct scan fee'].apply(lambda x: f"${x:,.2f}")
    df_subset['arr. time'] = df_subset['arr. time'].apply(lambda x: f"{x:04d}")
    df_subset['dep. time'] = df_subset['dep. time'].apply(lambda x: f"{x:04d}")
    data = [df_subset.columns.tolist()] + df_subset.values.tolist()


    
    table = Table(data, colWidths=[table_width*0.1, table_width*0.1, table_width*0.1, table_width*0.1, table_width*0.2, table_width*0.2, table_width*0.2])
    
    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center-align all header text
        ('ALIGN', (0, 1), (-2, -1), 'CENTER'),  # Center-align all columns excluding the last one for data rows
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (1, 1), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align to the middle
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # Reduced padding for data rows
        # ('TOPPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        # ('BOTTOMPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        ('LEADING', (0, 0), (-1, -1), 10),  # Adjust line height for text in rows
        # ('BOX', (0, 0), (0, -1), 1, colors.black),  # Left column outer grid
        # ('BOX', (-1, 0), (-1, -1), 1, colors.black),  # Right column outer grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Top border
        ('WORDWRAP', (0, 0), (-1, 0), True),  # Wrap text in the center column
        # ('LINEABOVE', (-1, 0), (-1, 0), 1, colors.black),  # Top border
    ])
    
    table.setStyle(style)
    elements.append(table)


    data = [["","","","","TOTAL",f"{filtered_df['charged time'].sum():,.2f}",f"${filtered_df['direct scan fee'].sum():,.2f}"]]
    
    
    #update and write invoice file
    d_invoices[thisInvoice] = {"project": project,
                               "charged_scan_time_mins": f"{filtered_df['charged time'].sum()*60:,.2f}",
                               "charged_scan_time_hrs": f"{filtered_df['charged time'].sum():,.2f}",
                               "total_scan_fee": f"{filtered_df['direct scan fee'].sum():,.2f}"
    }

    with open(inJsonFile,'w') as j:
        json.dump(d_invoices, j, indent='\t', sort_keys=True)
    

    table = Table(data, colWidths=[table_width*0.1, table_width*0.1, table_width*0.1, table_width*0.1, table_width*0.2, table_width*0.2, table_width*0.2])
    style = TableStyle([
        ('BACKGROUND', (-3, 0), (-1, 0), colors.lightgrey),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Center-align all header text
        ('ALIGN', (0, 1), (-3, -1), 'CENTER'),  # Center-align all columns excluding the last one for data rows
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (1, 1), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align to the middle
        ('TOPPADDING', (0, 0), (-1, -1), 5),  # Reduced padding for data rows
        # ('TOPPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        # ('BOTTOMPADDING', (1, 1), (-1, -1), 0),  # Reduced padding for data rows
        ('LEADING', (0, 0), (-1, -1), 10),  # Adjust line height for text in rows
        # ('BOX', (0, 0), (0, -1), 1, colors.black),  # Left column outer grid
        # ('BOX', (-1, 0), (-1, -1), 1, colors.black),  # Right column outer grid
        ('GRID', (-3, 0), (-1, 0), 1, colors.black),  # Top border
        ('WORDWRAP', (0, 0), (-1, 0), True),  # Wrap text in the center column
        # ('LINEABOVE', (-1, 0), (-1, 0), 1, colors.black),  # Top border
    ])
    table.setStyle(style)
    # table.hAlign = 'RIGHT'
    elements.append(table)

    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph("'arr. time' is the arrival time on the physical scan log"))
    elements.append(Paragraph("'dep. time' is the departure time on the physical scan log"))
    elements.append(Paragraph("'sch. dur.' is the scheduled duration in minutes"))
    elements.append(Paragraph("'charged time' is the greater of scheduled duration or actual duration in hours"))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("This invoice was produced using the scan rate of $272 per MRI hour in accordance with the CoNNECT MRI billing policy. The billing policy is available via www.wright.edu/connect-lab."))


    
    # # Add some text
    # elements.append(Paragraph("This is a sample document with an SVG image.", styles["Normal"]))
    
    # # Add SVG as a properly scaled flowable
    # elements.append(SVGImage(svg_path))


    # #image 2
    # elements.append(Spacer(1, 0.5 * inch))

    # elements.append(Paragraph("Image 2.", styles["Normal"]))
    # elements.append(Spacer(1, 0.1 * inch))

    # elements.append(SVGImage(svg_path))


    # elements.append(Spacer(1, 0.5 * inch))

    # #image 2
    # grouped_elements = KeepTogether([
    #     Paragraph("Image 3.", styles["Normal"]),
    #     Spacer(0.5, 0.1 * inch),
    #     SVGImage(svg_path)
    # ])


    # elements.append(grouped_elements)


    # plotting.plot_stat_map(stat_map_img, title="Stat Map", display_mode='ortho', draw_cross=True, output_file=output_path)
    # plt.close()  # Close the plot to avoid memory issues

    # # Add the image
    # elements.append(Image(stat_map_image_path, width=6*inch, height=4*inch))  # Adjust size as needed
    
    
    # Build PDF with header/footer
    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    return outPdf


if __name__ == '__main__':
    #get arguments
    options = parser.parse_args()

    #identify target scan log file
    month = datetime.datetime.strptime(options.YEARMONTH,'%Y%m')
    inLogFile = os.path.join('/resshare/scan_logs',month.strftime('%Y'),f"{options.YEARMONTH}_scan_log.csv")

    #exit if no file
    if not os.path.isfile(inLogFile):
        print(f'ERROR: did not find the associated scan log file {inLogFile}')
        sys.exit()

    #read scan log file
    df_scanLog = pd.read_csv(inLogFile)
    print(df_scanLog)

    
    #loop over scan files to compute duration
    for index, row in df_scanLog.iterrows():
        db_idx = None
        if row['arr. time'] != 0:
            dt = datetime.datetime.strptime(row['date'], "%m/%d/%y")
            df_db = st.mysql.sql_mri_tracking_query(regex=dt.strftime("%Y-%m-%d"), searchcol='date',project=row['project'])


            arrival = datetime.datetime.strptime(f"{row['date']} {row['arr. time']:04}", "%m/%d/%y %H%M")
            departure = datetime.datetime.strptime(f"{row['date']} {row['dep. time']:04}", "%m/%d/%y %H%M")
            scan_duration = (departure - arrival).total_seconds() / 60
            scan_duration = int((scan_duration + 14) // 15 * 15)

            if not df_db.empty:
                if len(df_db) == 1:
                    db_idx = 0
                    print('found 1 row')
                else:
                    print('found >1 row')
                    arr = datetime.datetime.strptime(f"{row['arr. time']:04}", "%H%M")
                    arr = datetime.timedelta(hours=arr.hour, minutes=arr.minute)
                    df_tmp = df_db[['scan_start_time']].copy()
                    df_tmp["scan_td"] = df_tmp["scan_start_time"].apply(to_timedelta)
                    df_tmp["diff"] = (df_tmp["scan_td"] - arr).abs()
                    df_db = df_db.loc[[df_tmp["diff"].idxmin()]].copy()
                    # print(df_db)
                    db_idx = 0
                    df_db.reset_index(drop=True, inplace=True)

                print('setting arrival/departure time and scan duration')
                df_db.loc[db_idx,'arrival_time'] = arrival.strftime('%H:%M:%S')
                df_db.loc[db_idx,'departure_time'] = departure.strftime('%H:%M:%S')
                hours, minutes, seconds = split_total_seconds(scan_duration)
                df_db.loc[db_idx,'scan_duration'] = f"{hours:02}:{minutes:02}:{seconds:02}"
                hours, minutes, seconds = split_total_seconds(row['sch. dur.'] / 60)
                df_db.loc[db_idx,'scheduled_duration'] = f"{hours:02}:{minutes:02}:{seconds:02}"
                print(df_db)
                print(f'values set {df_db.loc[0,'arrival_time']} {df_db.loc[0,'departure_time']} {df_db.loc[0,'scan_duration']}')

        else:
            scan_duration = 0
            df_db = pd.DataFrame()
        df_scanLog.loc[index,'scan duration'] = scan_duration

        if row['cancelled'] and row['cancelled on time']:
            charge = 0
        else:
            charge = max(scan_duration,row['sch. dur.']) / 60
            if charge > 8:
                charge = 8
        
        print(f"{dt.strftime("%Y-%m-%d")} {arrival.strftime('%H:%M:%S')} {departure.strftime('%H:%M:%S')} {scan_duration} {charge}")
        print(db_idx)




        hours, minutes, seconds = split_total_seconds(charge / 60)
        df_scanLog.loc[index,'charged time'] = charge
        df_scanLog.loc[index,'direct scan fee'] = 272 * charge

        
        if not df_db.empty:
            # print(df_db)
            df_db.loc[db_idx,'charged_time'] = f"{hours:02}:{minutes:02}:{seconds:02}"
            df_db.loc[db_idx,'direct_fee'] = 272 * charge

            print(df_db.iloc[0])
            st.mysql.sql_mri_tracking_set(df_db)


    projects = sorted(df_scanLog['project'].unique())
    df_scanLog.to_csv(inLogFile.replace('.csv','_processed.csv'), index=False)

    msgStr = ""
    l_invoicePdfs = []
    for project in projects:
        filtered_df = df_scanLog[df_scanLog['project'] == project]
        invoicePdf = create_pdf(project, filtered_df, month)
        msgStr += f"Project: {project}, Invoice: {os.path.basename(invoicePdf)}, Total Direct Fee: ${filtered_df['direct scan fee'].sum()}\n"
        l_invoicePdfs.append(invoicePdf)

    print('done')


    #format email body
    msgSubject = f"Scan Fees"
    msgPriority = "1"
    msgBody = f"""
{msgStr}
This automated message was sent by the CoNNECT Scantime Evaluator. 

DISCLAIMER: The generated invoice should be reviewed prior to submission. 


You're Welcome,

Matthew Sherwood, PhD
Director, CoNNECT
                    """

    #prepare EMAIL message
    msg = MIMEMultipart()
    msg.attach(MIMEText(msgBody))
    msg["Subject"] = msgSubject
    msg["From"] = "mriresearch@wright.edu"
    msg["To"] = "matt.sherwood@wright.edu"
    msg["CC"] = 'kelsie.pyle@wright.edu'
    msg["X-Priority"] = msgPriority
    

    #loop over attachments to add
    for invoicePdf in l_invoicePdfs:
        with open(invoicePdf,'rb') as file:
            # Attach the file with filename to the email
            msg.attach(MIMEApplication(file.read(), Name=os.path.basename(invoicePdf)))

    #send email
    with smtplib.SMTP("localhost") as server:
        server.sendmail("mriresearch@wright.edu", ["matt.sherwood@wright.edu", "kelsie.pyle@wright.edu"], msg.as_string())


    



    

