# __init__.py
import os as _os
import sys as _sys
import json as _json
from pathlib import Path as _Path
from json import loads

#set log level
_os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

#append path if necessary
_REALPATH = _Path(*_Path(_os.path.realpath(__file__)).parts[:-3]).resolve()
if not any(_Path(p).resolve() == str(_REALPATH) for p in _sys.path if _Path(p).exists()):
    _sys.path.append(str(_REALPATH))

from ..data import load as load_data
_fullCredentials = loads(load_data.readable('credentials.json').read_text())

# from .get_dir_identifiers_new import get_dir_identifiers_new
from wsuconnect.classes.creds import creds as _cred
from wsuconnect.classes.subject import subject as _sub
creds = _cred()
subject = _sub()
creds.projects = _fullCredentials['projects']
creds.masterMachineName = _fullCredentials['master_machine_name']


#import modules
from wsuconnect.support_tools import bids
from wsuconnect.support_tools import condor
from wsuconnect.support_tools import RestToolbox

from .apply_brainmask import apply_brainmask
from .check_rawdata import check_rawdata
from .compute_segstats import compute_segstats
from .convert_dicoms import convert_dicoms
from .copy_dirs import copy_dirs
from .dti_flirt import dti_flirt
from .evaluate_source_file_transfer import evaluate_source_file_transfer
from .feat_full_firstlevel import feat_full_firstlevel
from .flirt_pngappend import flirt_pngappend
from .fmriprep_clean_workdir import fmriprep_clean_workdir
#from .fsreconall_stage1_wf import fsreconall_stage1
#from .fsreconall_stage2_wf import fsreconall_stage2
from .get_scan_id import get_scan_id
from . import mysql
from .move_html import move_html
from .prepare_examcard_html import prepare_examcard_html
from .remove_dirs import remove_dirs
from .xdf_extract_physio import xdf_extract_physio



class specBase:

    def __init__(self):
        self.spectraName = ""
        self.subName = ""
        self.session = ""
        self.outBase = ""

    def get(self, specFile: str):
        """
        Get metadata from a MRS file

        This program returns the MRS file information into the custom specBase class inside of the support_tools module, which should be imported prior to calling read().

        import support_tools as st
        get_spec_base(specFile)

        :param specFile: fullpath to target MRS file
        :type specFile: str
        """

        self.outBase = _os.path.splitext(_os.path.basename(specFile))[0]
        base = self.outBase.split('sub-').split()
        self.subName = self.outBase.split('sub-')[1].split('_')[0]
        self.session = self.outBase.split('ses-')[1].split('_')[0]
        self.spectraName = self.outBase.split('acq-')[1].split('_')[0]


def import_flirt():
    from .flirt import flirt

def import_dti_preprocess_wf():
    from .dti_preprocess_wf import dti_preprocess


# st.creds = st.creds()
specBase = specBase()


__all__ = ['apply_brainmask','bids','check_rawdata','compute_segstats','convert_dicoms','copy_dirs','condor','dti_flirt','evaluate_source_file_transfer','feat_full_firstlevel','flirt_pngappend','fmriprep_clean_workdir','fsreconall_stage1','fsreconall_stage2','get_scan_id','import_flirt','import_dti_preprocess','mysql','prepare_examcard_html','remove_dirs','RestToolbox','creds','subject','specBase','xdf_extract_physio']