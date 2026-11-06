# prepare_exampcard_html.py

# Copywrite:= Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 24 April 2024
#
#



def prepare_examcard_html():
    """
    Prepares the html header for the examcard html file when converting examcards from txt to html.

    The stylesheet prints each sequence on its own portrait letter page, repeats the table
    title and column headers if a table runs onto a second page, and avoids blank pages.

    :return: html document header, through the opening <body> and page header
    :rtype: str
    """
    newD = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ExamCard</title>
<style>
    @page { size: letter portrait; margin: 0.4in; }

    body { font-family: Arial, Helvetica, sans-serif; font-size: 9px; margin: 0; }
    header { font-size: 12px; text-align: center; margin-bottom: 8px; }
    footer { font-size: 8px; text-align: center; margin-top: 8px; }

    table { border-collapse: collapse; }
    td, th { padding: 1px 3px; vertical-align: middle; }

    table.order { width: 60%; font-size: 12px; margin-bottom: 12px; }
    table.order td, table.order th { border: 1px solid #000; text-align: left; }
    table.order th { background: #E6E6E6; }

    table.examcard { width: 100%; table-layout: fixed; }
    table.examcard col.k { width: 19.5%; }
    table.examcard col.v { width: 12.5%; }
    table.examcard col.gap { width: 1%; }
    table.examcard td { border: 1px solid #000; word-wrap: break-word; }
    table.examcard td.gap, table.examcard td.empty { border: none; }
    table.examcard th.title { font-size: 16px; padding: 6px; border: none; }
    table.examcard th.sect { background: #046A38; color: #FFFFFF; border: 1px solid #000; font-size: 10px; }
    td.lvl1 { padding-left: 2em; }
    td.lvl2 { padding-left: 4em; }

    section.sequence { margin-top: 16px; }

    @media print {
        * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        body { font-size: 7.5px; }
        table.examcard th.title { font-size: 13px; padding: 3px; }
        .hidden-print { display: none; }
        section.sequence { break-before: page; margin-top: 0; }
        thead { display: table-header-group; }
        tr { break-inside: avoid; }
        header, footer { display: none; }
    }
</style>
</head>
<body>
<button class="hidden-print" onClick="window.print()">Print</button>

<header>Wright State University | Center of Neuroimaging and Neuro-Evaluation of Cognitive Technology</header>
"""

    return newD
