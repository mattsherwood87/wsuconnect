# prepare_exampcard_html.py

# Copywrite:= Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 24 April 2024
#
# 



def prepare_examcard_html():
    """
    Prepares the html header for the examcard html file when converting examcards from txt to html.
    """
    newD = f"""
<!DOCTYPE html>
<html>
<head>
<style>

    footer {{
    font-size: 9px;
    text-align: center;
    }}

    header {{
    font-size: 9px;
    text-align: center;
    }}

    @page {{s
    size: 8.5in 11in; margin: 0.5in 0.5in 0.5in 0.5in;
    }}
    .tab {{
    display: inline-block;
    margin-left: 2em;
    }}

    @media print {{
    table {{
    page-break-inside: avoid; empty-cells: hide; }}
    .pagebreak {{
    page-break-before: always; }}
    footer {{
    position: fixed; bottom: 0; }}
    header {{
    position: fixed; top: 0; overflow: avoid; text-align: center; }}
    .content-block, p {{
    page-break-inside: avoid;
    position: relative;
    width: 100%;
    left:0px;
    right:0px; }}
    html, body {{
    width: 8.5in; height: 11in; }}

    .hidden-print {{
    display: none; }}
    }}

    .border-none td {{
    border: 1px solid black;
    }} 

    body {{
    font-size: 10px; font-family: arial;
    }}
</style>
</head>
<body>
<button class="hidden-print" onClick="window.print()">Print</button>

<header><font face="arial" size="+1">Wright State University | Center of Neuroimaging and Neuro-Evaluation of Cognitive Technology<br></br></font></header>
"""
                            
    return newD