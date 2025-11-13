#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 16 Sept 2021
#
# v2.0.0 on 1 April 2023 - simplify code

import os
import re

import support_tools as st

def get_dir_identifiers_new(singleDir):
    """
    Get subject and session identifiers from a BIDS filepath, and updates the helper_functions 'subject' class

    Arguments:
        singleDir (str): BIDS-compliant filepath

    Returns:
        None
    """

    st.subject.id = re.split(os.sep + '|_',singleDir.split('sub-')[1])[0]
    st.subject.fullSesNum = re.split(os.sep + '|_',singleDir.split('ses-')[1])[0]
    if '-' in st.subject.fullSesNum:
        st.subject.sesNum = st.subject.fullSesNum.split('-')[1]
    else:
        st.subject.sesNum = st.subject.fullSesNum

    #return subjectName,sessionNum