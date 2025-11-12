#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 10 Mar 2025
#
# v1.0.0 on 10 Mar 2025 - add utilization of instance_ids.json

import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from svglib.svglib import svg2rlg
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, KeepTogether, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics import renderPDF
import os
import sys
import argparse
import nibabel as nib
from nilearn import plotting
import glob
from nilearn.image import binarize_img, index_img, math_img, clean_img
from nilearn import masking
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image as PILImage
import xml.etree.ElementTree as ET
import pandas as pd

REALPATH = os.path.realpath(__file__)

sys.path.append(os.path.dirname(REALPATH))

import support_tools as st

# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '10 Mar 2025'


# Get the default style sheet
styles = getSampleStyleSheet()

# Clone the 'Normal' style and set a smaller font size
small_style = styles['Normal'].clone('SmallStyle')
small_style.fontSize = 6  # Set the font size to 6 (smaller than normal)

# ******************* PARSE COMMAND LINE ARGUMENTS ********************

#input argument parser
parser = argparse.ArgumentParser('connect_build_report.py: build a report')
parser.add_argument('-p','--project', required=True, action="store", dest="PROJECT", help="update the selected table: all " + ' '.join(st.creds.projects), default=None)
# parser.add_argument('-r','--raw', action="store_true", dest="RAW", help="Command line argument to update the raw_data table for the selected project (default FALSE)", default=False)
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
parser.add_argument('--progress', help="Show progress (default FALSE)", action="store_true", dest="progress", default=False)
# parser.add_argument('-s', '--sync', action="store_true", dest="SYNC", help="Sync the files to the local filesystem")


#set some parameters
left_margin = 0.5 * inch
right_margin = 0.5 * inch

width, height = letter
# width, height = landscape(letter)

# # Function to check if the SVG is multiframe
# def is_multiframe(svg_path):
#     tree = ET.parse(svg_path)
#     root = tree.getroot()
#     # Look for multiple <g> or <use> tags which might indicate multiple frames
#     background_group = root.find('.//{http://www.w3.org/2000/svg}g[@class="background-svg"]')
#     foreground_group = root.find('.//{http://www.w3.org/2000/svg}g[@class="foreground-svg"]')
#     return len(background_group) > 0 & len(foreground_group) > 0

# def split_svg(svg_path, pdf_path):
#     # Parse the SVG
#     tree = ET.parse(svg_path)
#     root = tree.getroot()

#     # Find the two groups based on the class names
#     background_group = root.find('.//{http://www.w3.org/2000/svg}g[@class="background-svg"]')
#     foreground_group = root.find('.//{http://www.w3.org/2000/svg}g[@class="foreground-svg"]')

#     # Process the background group
#     bg_svg_path = None
#     if background_group is not None:
#         # Create a new SVG with just the background group
#         new_svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg")
#         new_svg.append(background_group)  # Add background group to new SVG
#         new_tree = ET.ElementTree(new_svg)
#         bg_svg_path = "background.svg"
#         new_tree.write(bg_svg_path)

#     # Process the foreground group
#     fg_svg_path = None
#     if foreground_group is not None:
#         # Create a new SVG with just the foreground group
#         new_svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg")
#         new_svg.append(foreground_group)  # Add foreground group to new SVG
#         new_tree = ET.ElementTree(new_svg)
#         fg_svg_path = "foreground.svg"
#         new_tree.write(fg_svg_path)

#     return bg_svg_path, fg_svg_path

class SVGImage(Flowable):
    def __init__(self, svg_path, max_width=None, max_height=height-(2*inch), left_margin=left_margin, right_margin=right_margin):
        Flowable.__init__(self)
        drawing = svg2rlg(svg_path)
        
        # Default maximum width is the page width minus left and right margins
        if max_width is None:
            # page_width, _ = landscape(letter)
            page_width, _ = letter
            max_width = page_width - left_margin - right_margin
        
        # Get the original width and height of the drawing
        width, height = drawing.width, drawing.height
        
        # Ensure dimensions are positive before scaling
        width = max(width, 1)
        height = max(height, 1)
        
        scale_factor = min(max_width / width, max_height / height)
        drawing.scale(scale_factor, scale_factor)  # Apply scale to drawing
        self.drawing = drawing
        self.width = width * scale_factor
        self.height = height * scale_factor
    
    def draw(self):
        renderPDF.draw(self.drawing, self.canv, -0.1 * inch, 0)  # Corrected drawing method

def draw_header_footer(canvas, doc, title):
    """Draws header and footer on each page."""
    canvas.saveState()

    
    # Header
    canvas.setFont("Helvetica-Bold", 12)
    if not title:
        header_text =  "WSU Center of Neuroimaging and Neuro-Evaluation of Cognitive Technologies"
    else:
        header_text = title
    header_width = canvas.stringWidth(header_text, "Helvetica-Bold", 12)
    canvas.drawString((width - header_width) / 2, height - 0.5 * inch, header_text)
    
    # Footer (center text and right-aligned page number)
    canvas.setFont("Helvetica", 10)
    
    # First line of footer text (centered)
    footer_text_1 = "Wright State University | CoNNECT"
    footer_width_1 = canvas.stringWidth(footer_text_1, "Helvetica", 8)
    canvas.drawString((width - footer_width_1) / 2, 0.5 * inch, footer_text_1)
    
    # # Second line of footer text (centered)
    # footer_text_2 = "Wright State University"
    # footer_width_2 = canvas.stringWidth(footer_text_2, "Helvetica", 8)
    # canvas.drawString((width - footer_width_2) / 2, 0.5 * inch - 10, footer_text_2)  # Adjust y-position for second line

    # Page number (right-aligned)
    page_number = f"Page {doc.page}"
    page_number_width = canvas.stringWidth(page_number, "Helvetica", 8)
    canvas.drawString(width - right_margin - page_number_width, 0.5 * inch, page_number)  # Right-aligned page number


    # Page number (right-aligned)
    today = datetime.datetime.today()
    formatted_date = today.strftime("%A %b. %d, %Y")  # Format: "Sunday Feb. 9, 2025"
    
    # Draw date, centered footer, and page number
    canvas.drawString(left_margin, 0.5 * inch, formatted_date)  # Right-aligned page number    # Get today's date in the desired format
    
    
    canvas.restoreState()


def get_scaled_image(image_path, max_width):
    """Returns a ReportLab Image object scaled to fit within max_width while maintaining aspect ratio."""
    img = PILImage.open(image_path)
    img_width, img_height = img.size
    aspect_ratio = img_height / img_width

    new_width = min(max_width, img_width)  # Ensure it doesn't exceed max_width
    new_height = new_width * aspect_ratio  # Maintain aspect ratio

    return Image(image_path, width=new_width, height=new_height)

def create_pdf(output_filename, subName):
    """Creates a PDF with SVG images and headers/footers."""
    # Set the left and right margins (in inches)
    
    # Create a SimpleDocTemplate with custom margins
    doc = SimpleDocTemplate(output_filename, pagesize=letter, leftMargin=left_margin, rightMargin=right_margin, topMargin=0.5*inch, bottomMargin=0.5*inch)
    # doc = SimpleDocTemplate(output_filename, pagesize=landscape(letter), leftMargin=left_margin, rightMargin=right_margin)
    styles = getSampleStyleSheet()
    elements_bidir = []
    elements_pos = []
    elements_neg = []
    elements = None

    

    # for subName in subNames:

    figTypes = ['basil'] #['basil','basilGM','cbf','score','scrub']
    for figType in figTypes:

    
        # Add some text
        elements_bidir.append(Paragraph(f"Baseline subracted maps of CBF from the {figType} algorithm. Below are bi-directional changes in perfusion. CBF units are mL/100 g/min.", styles["Normal"]))
        # elements_bidir.append(Paragraph(f"CBF units are mL/100 g/min.", style=small_style))
        elements_bidir.append(Spacer(1, 0.1 * inch))
        elements_pos.append(Paragraph(f"Baseline subracted maps of CBF from the {figType} algorithm. Below are images only indicating <i>increased</i> perfusion from baseline. CBF units are mL/100 g/min.", styles["Normal"]))
        # elements_pos.append(Paragraph(f"CBF units are mL/100 g/min.", style=small_style))
        elements_pos.append(Spacer(1, 0.1 * inch))
        elements_neg.append(Paragraph(f"Baseline subracted maps of CBF from the {figType} algorithm. Below are images only indicating <i>decreased</i> perfusion from baseline. CBF units are mL/100 g/min.", styles["Normal"]))
        # elements_neg.append(Paragraph(f"CBF units are mL/100 g/min.", style=small_style))
        elements_neg.append(Spacer(1, 0.1 * inch))
        
        if figType == 'cbf':
            niiFiles = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=f'space-MNI152NLin2009cAsym_res-2_cbf.nii.gz',exclusion=['bak','desc'],inclusion=['derivatives',f'{subName}','perf'])
        else:
            niiFiles = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=f'space-MNI152NLin2009cAsym_res-2_desc-{figType}_cbf.nii.gz',exclusion=['bak'],inclusion=['derivatives',f'{subName}','perf'])
        


        b_start = True
        for niiFile in sorted(niiFiles):
            # print(niiFile)
            try:
                if b_start:

                    #get baseline CBF image and convert to numpy.array
                    baseCbfImg = nib.load(niiFile)
                    d_baseCbfImg = np.squeeze(baseCbfImg.get_fdata())
                    d_baseCbfImg = np.where(d_baseCbfImg > 1, d_baseCbfImg, np.nan)

                    #get anatomical image and mask
                    anatFiles = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=f'space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz',exclusion=['bak'],inclusion=['derivatives',f'{subName}','anat'])
                    bgImg =nib.load(anatFiles[0])
                    anatFiles = st.mysql.sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=f'space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz',exclusion=['bak'],inclusion=['derivatives',f'{subName}','anat'])
                    bgImgMask = nib.load(anatFiles[0])
                    d_bgImgMask = np.squeeze(bgImgMask.get_fdata())

                    # mask baseline CBF image with brain and create an image mask
                    d_baseCbfImg = np.where(d_bgImgMask > 0, d_baseCbfImg, np.nan)
                    # d_baseCbfMask = np.logical_and(d_bgImgMask > 0, d_baseCbfImg > 1)
                    b_start = False

                else:
                    #load CBF image and mask
                    newCbfImg = nib.load(niiFile)
                    d_newCbfImg = np.squeeze(newCbfImg.get_fdata())
                    d_newCbfImg = np.where(d_newCbfImg > 1, d_newCbfImg, np.nan)
                    d_newCbfImg = np.where(d_bgImgMask > 0, d_newCbfImg, np.nan)

                    d_diffCbfImg = ((d_newCbfImg - d_baseCbfImg) / d_baseCbfImg) * 100
                    diffCbfImg = nib.Nifti1Image(d_diffCbfImg, bgImg.affine, bgImg.header)

                    # # newCbfImg = masking.apply_mask(newCbfImg, bgImgMask)
                    # newCbfImg = math_img("img[..., 0] * mask", img=newCbfImg, mask=bgImgMask)
                    # newCbfMask = math_img("(img1 > 1)", img1=newCbfImg)
                    # andMask = math_img("(img1 > 0) & (img2 > 0)", img1=baseCbfMask, img2=newCbfMask)
                    # andMask = math_img("img * mask", img=andMask, mask=bgImgMask)
                    # # diffCbfImg = math_img("(img1 - img2)", img1=newCbfImg, img2=baseCbfImg)
                    # diffCbfImg = math_img("(((img1 - img2) / img2) * 100) * mask", img1=newCbfImg, img2=baseCbfImg, mask=andMask)
                    # # diffCbfImg = masking.apply_mask(diffCbfImg, andMask)
                    # # diffCbfImg = apply_mask(diffCbfImg, bgImgMask, dtype='f', smoothing_fwhm=None, ensure_finite=True)

                    # # unionMask = index_img(unionMask, 0)
                    # xorMask = math_img("(mask1 <= 1) | (mask2 <= 1)", mask1=baseCbfImg, mask2=newCbfImg)
                    # # xorMask = masking.apply_mask(xorMask, bgImgMask)
                    # xorMask = binarize_img(xorMask, two_sided=False, mask_img=bgImgMask, copy_header=True)


                    # Ensure NaNs are treated as 0 (if you consider them non-active)
                    map1 = np.nan_to_num(d_diffCbfImg) != 0
                    d_xorMask = np.where(d_bgImgMask > 0, (~map1).astype(float), np.nan)
                    xorMask = nib.Nifti1Image(d_xorMask, bgImg.affine, bgImg.header)

                    d_labels = st.bids.get_bids_labels(niiFile)
                    d_labels['description'] = figType
                    d_labels['suffix'] = 'deltacbf'
                    d_labels['extension'] = 'png'

                    st.subject.get_id(niiFile)
                    outPng = st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**d_labels)
                    outPng = os.path.join('/resshare','tmp',outPng)
                    # outPng = os.path.join(os.path.dirname(niiFile),outPng)
                    print(outPng)

                    # elements_bidir.append(Paragraph(f"Subject: {subName}, Session: ses-{st.subject.sesNum}, Acquisition: {niiFile.split('acq-')[1].split('_')[0]}, Run: {niiFile.split('run-')[1].split('_')[0]}", style=small_style))
                    disp = plotting.plot_stat_map(
                        diffCbfImg,
                        bg_img = bgImg,
                        cut_coords = np.arange(-30,75,15),
                        display_mode="z",
                        title=None,#f"ses-{niiFile.split('_ses-')[1].split('_')[0]}_{niiFile.split('_acq-')[1].split('_')[0]} - base",
                        vmin=-30,
                        vmax=30,
                        cmap='bwr',#'seismic', #'bwr'
                        radiological=True,
                        transparency=0.4,
                        #output_file=outPng,
                    )
                    # Overlay the mask in green
                    disp.add_overlay(
                        xorMask,
                        cmap=plotting.cm.black_green,   # built-in nilearn colormap
                        transparency=0.9                 # adjust transparency
                    )
                    disp.savefig(outPng)
                    plt.close()
                    # elements.append(Image(outPng, width=6*inch, height=4*inch))
                    scaled_img = get_scaled_image(outPng, width - left_margin - right_margin)
                    grouped_elements = KeepTogether([
                        Paragraph(f"Subject: {subName}, Session: ses-{st.subject.sesNum}, Acquisition: {niiFile.split('acq-')[1].split('_')[0]}, Run: {niiFile.split('run-')[1].split('_')[0]}", style=small_style),
                        scaled_img,
                        Spacer(1, 0.1 * inch)
                    ])
                    elements_bidir.append(grouped_elements)


                    d_labels['suffix'] = 'deltaposcbf'
                    outPng = st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**d_labels)
                    outPng = os.path.join('/resshare',outPng)
                    plotting.plot_stat_map(
                        diffCbfImg,
                        bg_img = bgImg,
                        cut_coords = np.arange(-30,75,15),
                        display_mode="z",
                        title=None,#f"ses-{niiFile.split('_ses-')[1].split('_')[0]}_{niiFile.split('_acq-')[1].split('_')[0]} - base",
                        vmin=0,
                        vmax=30,
                        cmap='red_transparent_full_alpha_range',#'seismic', #'bwr'
                        radiological=True,
                        transparency=0.5,
                        output_file=outPng,
                    )
                    plt.close()
                    # elements.append(Image(outPng, width=6*inch, height=4*inch))
                    scaled_img = get_scaled_image(outPng, width - left_margin - right_margin)
                    grouped_elements = KeepTogether([
                        Paragraph(f"Subject: {subName}, Session: ses-{st.subject.sesNum}, Acquisition: {niiFile.split('acq-')[1].split('_')[0]}, Run: {niiFile.split('run-')[1].split('_')[0]}", style=small_style),
                        scaled_img,
                        Spacer(1, 0.1 * inch)
                    ])
                    elements_pos.append(grouped_elements)


                    d_labels['suffix'] = 'deltanegcbf'
                    outPng = st.bids.get_bids_filename(subject=st.subject.id,session=st.subject.sesNum,**d_labels)
                    outPng = os.path.join('/resshare',outPng)
                    diffCbfImg = math_img("(-1 * img1)", img1=diffCbfImg)

                    plotting.plot_stat_map(
                        diffCbfImg,
                        bg_img = bgImg,
                        cut_coords = np.arange(-30,75,15),
                        display_mode="z",
                        title=None,#f"ses-{niiFile.split('_ses-')[1].split('_')[0]}_{niiFile.split('_acq-')[1].split('_')[0]} - base",
                        vmin=0,
                        vmax=30,
                        cmap='blue_transparent_full_alpha_range',#'seismic', #'bwr'
                        radiological=True,
                        transparency=0.5,
                        output_file=outPng,
                    )
                    plt.close()
                    # elements.append(Image(outPng, width=6*inch, height=4*inch))
                    scaled_img = get_scaled_image(outPng, width - left_margin - right_margin)
                    grouped_elements = KeepTogether([
                        Paragraph(f"Subject: {subName}, Session: ses-{st.subject.sesNum}, Acquisition: {niiFile.split('acq-')[1].split('_')[0]}, Run: {niiFile.split('run-')[1].split('_')[0]}", style=small_style),
                        scaled_img,
                        Spacer(1, 0.1 * inch)
                    ])
                    elements_neg.append(grouped_elements)

                    elements = (elements_bidir + [PageBreak()] + elements_pos + [PageBreak()] + elements_neg)
                    # Draw the image
                    # canvas.drawImage(f"{'_'.join(niiFile.split('_')[0:2])}_space-MNI152NLin2009cAsym_desc-{figType}_deltacbf.png", left_margin, height - new_height - 60,  # Adjust Y position
                    #                 width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(e)



    # plotting.plot_stat_map(stat_map_img, title="Stat Map", display_mode='ortho', draw_cross=True, output_file=output_path)
    # plt.close()  # Close the plot to avoid memory issues

    # # Add the image
    # elements.append(Image(stat_map_image_path, width=6*inch, height=4*inch))  # Adjust size as needed
    
    
    # Build PDF with header/footer
    if elements:
        doc.build(elements, onFirstPage=lambda canvas, doc: draw_header_footer(canvas, doc, f"\u0394CBF[{figType}] Report for {subName}"), onLaterPages=lambda canvas, doc: draw_header_footer(canvas, doc, f"\u0394CBF[{figType}] Report for {subName}"))


# Example usage
# *******************  MAIN  ********************
if __name__ == '__main__':    
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    st.creds.read(options.PROJECT)
    #grab particiapnts to use in analysis
    inputTsv = os.path.join(st.creds.dataDir,'rawdata','participants.tsv')
    with open(inputTsv) as f:
        df_participants = pd.read_csv(f,delimiter='\t')

    if 'discard' in df_participants.columns:
        df_participants = df_participants[~df_participants['discard']]

    #extract relevant columns
    df_data = df_participants
    for index, row in df_data.iterrows():
        subName = row['participant_id']
        # subName = 'sub-351303'
        create_pdf(os.path.join(st.creds.dataDir,'derivatives',f"output_{subName}.pdf"), subName)
