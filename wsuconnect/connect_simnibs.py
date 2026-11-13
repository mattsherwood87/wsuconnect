#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
#
# v1.0.0 on 12 Nov 2026


import os
import sys
import glob
import argparse
from pathlib import Path


#local import
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-2]).resolve()
if not any(Path(p).resolve() == str(REALPATH) for p in sys.path if Path(p).exists()):
    sys.path.append(str(REALPATH))
import wsuconnect.support_tools as st


# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '12 Nov 2026'


# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser(description="Submit SimNIBS charm + brain_print HTCondor jobs for a project's sessions, or collect finished ones. "
                                             "connect_pacs_dicom_grabber.py does both automatically for projects with \"simnibs\": {\"enabled\": true} in credentials.json; "
                                             "use this by hand to test, to backfill older sessions, or to collect results. Run as root (or as the project's simnibs condor_user).")
parser.add_argument('-p','--project', action="store", dest="PROJECT", help="select a project (project identifier in credentials.json)", default=None)
parser.add_argument('--subjects', action='store', dest='SUBJECTS', default=None, nargs='+', help='subject identifier(s), e.g. sub-1106 (default: every sub-* in rawdata)')
parser.add_argument('--sessions', action='store', dest='SESSIONS', default=None, nargs='+', help='session identifier(s), e.g. ses-20240610-1A (default: every ses-* of each subject)')
parser.add_argument('--collect', action="store_true", dest="COLLECT", help="collect finished jobs (all projects) instead of submitting", default=False)
parser.add_argument('-v', '--version', action="store_true", dest="version", help="Display the current version")


# ******************* MAIN ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    options = parser.parse_args()

    if options.version:
        print('connect_simnibs.py version {0}.'.format(VERSION)+" DATED: "+DATE)
        sys.exit(0)

    if options.COLLECT:
        finished = st.simnibs.collect_finished()
        print(f'{len(finished)} job(s) finished')
        sys.exit(0)

    if not options.PROJECT:
        parser.error('-p/--project is required unless --collect is given')

    if not st.creds.read(options.PROJECT):
        sys.exit(1)
    if not st.creds.simnibs.get('enabled'):
        print(f'simnibs is not enabled for {options.PROJECT} in credentials.json ("simnibs": {{"enabled": true}})')
        sys.exit(1)
    dataDir = st.creds.dataDir

    subjects = options.SUBJECTS or sorted(os.path.basename(d) for d in glob.glob(os.path.join(dataDir, 'rawdata', 'sub-*')) if os.path.isdir(d))
    for sub in subjects:
        sub = sub if sub.startswith('sub-') else f'sub-{sub}'
        sessions = options.SESSIONS or sorted(os.path.basename(d) for d in glob.glob(os.path.join(dataDir, 'rawdata', sub, 'ses-*')) if os.path.isdir(d))
        for ses in sessions:
            ses = ses if ses.startswith('ses-') else f'ses-{ses}'
            # submit_session takes the grabber's sourcedata path and reads the images from rawdata
            cluster = st.simnibs.submit_session(options.PROJECT, os.path.join(dataDir, 'sourcedata', sub, ses), f'{sub} {ses}')
            print(f'{sub}/{ses}: ' + (f'submitted cluster {cluster}' if cluster else 'not submitted (reason above and in the grabber log)'))
