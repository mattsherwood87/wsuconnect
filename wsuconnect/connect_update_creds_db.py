#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 29 Oct 2026
#
# v1.0.0 on 29 Oct 2026 - initial release

import os
import sys
import datetime
import argparse

from pathlib import Path


REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-1]).resolve()

import wsuconnect.support_tools as st

# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '29 Oct 2026'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser(os.path.basename(REALPATH) + ' - Create or update the MySQL project credentials table from credentials.json')
parser.add_argument('-t','--table', action="store", dest="TABLE", help="target table in the database (default projects)", default='projects')
parser.add_argument('-d','--database', action="store", dest="DATABASE", help="target MySQL database (default CoNNECT)", default='CoNNECT')
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
parser.add_argument('--progress', help="Show progress (default FALSE)", action="store_true", dest="progress", default=False)


# ******************* EVALUATE INPUT ARGUMENTS ********************
def evaluate_args(options):

    #print version if selected
    if options.version:
        print(os.path.basename(REALPATH) + ' version {0}.'.format(VERSION)+" DATED: "+DATE)
        sys.exit(0)


# *******************  MAIN  ********************   
if __name__ == '__main__': 
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    evaluate_args(options)

    print('Updating MySQL table ' + options.DATABASE + '.' + options.TABLE + ' from credentials.json on ' + datetime.datetime.today().strftime('%Y%m%d @ %H:%M:%S'))

    #create/update table
    st.mysql.sql_credentials_set(table=options.TABLE, database=options.DATABASE, progress=options.progress)
    print('\nFinished updating table ' + options.TABLE + ' in database ' + options.DATABASE)