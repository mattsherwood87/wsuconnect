#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.10 as the interpreter for this program

# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 16 Sept 2021
#
# 

import os
import sys

#local import
import support_tools as st


def get_spec_base(specFile):
    """
    Get metadata from a MRS file

    This program returns the MRS file information into the custom specBase class, which should be imported prior to calling get_sspec_base

    get_spec_base(specFile)

    Arguments:

        specFile (str): target MRS file

    Returns:
        None
    """

    st.specBase.outBase = os.path.splitext(os.path.basename(specFile))[0]
    base = st.specBase.outBase.split('sub-').split()
    st.specBase.subName = st.specBase.outBase.split('sub-')[1].split('_')[0]
    st.specBase.session = st.specBase.outBase.split('ses-')[1].split('_')[0]
    st.specBase.spectraName = st.specBase.outBase.split('acq-')[1].split('_')[0]
    