# creds.py

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 Dec 2020

#versioning
_VERSION = '2.1.0'
_DATE = '12 Nov 2026'


import copy as _copy
import os as _os
from pathlib import Path as _Path
_REALPATH = _Path(_os.path.realpath(__file__)).parts[:-2]


# Defaults for a project's optional "simnibs" block in credentials.json (SimNIBS
# charm + brain_print HTCondor jobs submitted by connect_pacs_dicom_grabber.py).
# A project only lists the keys it changes, e.g. "simnibs": {"include_sessions": [0]}.
_SIMNIBS_DEFAULTS = {
    'include_sessions': [],                 # sessions to run, e.g. [0] or [1, 2] (= ses-0 / ses-1, ses-2); ["*"] = all; [] = simnibs off
    'exclude_sessions': [],                 # sessions never to run, e.g. with ["*"] above
    'condor_user': 'nw028mss',              # non-root account that owns the HTCondor jobs
    't1_label': 'T1w.nii.gz',               # filename ending, nothing added: 'rec-ax_T1w.nii.gz' -> *rec-ax_T1w.nii.gz; '' = any *T1w.nii.gz
    't2_label': '',                         # filename ending of a 2nd charm image, e.g. 'acq-fracture_T1w.nii.gz'; '' = none
    'machines': ['npc-core-gpu1'],          # execute hosts that have the image loaded
    'image': 'wsuconnect/simnibs:4.6.0',    # docker image with charm_brain_print in /usr/bin
    'extra_args': '',                       # extra charm_brain_print args, e.g. '--skull -- --brainstem'
    'request_cpus': 4,
    'request_memory': '16g',
    'request_disk': '30GB',
}


class _InvalidProjectError(Exception):
    "Raised when the selected project is not found in the list of defined projects (credentials.json)"
    pass


class creds:
    """
    Global Class Pattern:
    Declare globals here.
    """

    def __init__(self):

        self.projects = ""
        self.masterMachineName = ""
        self.database = "CoNNECT"
        self.dataDir = ""
        self.dataPath = _Path()
        self.dicom_id = ""
        self.examCardName = ""
        self.fund = ""
        self.gpuMachineNames = ""
        self.gpuTempStorage = ""
        self.instance_id = ""
        self.ipAddress = ""
        self.machineNames = ""
        self.org = ""
        self.project = ""
        self.searchSourceTable = ""
        self.searchTable = ""
        self.dockerMountIf = ""
        self.simnibs = _copy.deepcopy(_SIMNIBS_DEFAULTS)
        self.contact = ["matt.sherwood@wright.edu","kelsie.pyle@wright.edu"]
        # self.read()

    def read(self, project: str) -> bool:
        """
        Read the user's credential file 'credentials.json' loacted in the wsuconnect module directory.

        This program returns the Project credentials into the custom creds class inside of the support_tools module, which should be imported prior to calling read().

        import support_tools as st
        st.creds.read(project)

        :param project: target Project's <project identifier>, defaults to None
        :type project: str

        :raises FileNotFoundError: when credentials.json cannot be read from disk
        """
        import traceback as _traceback
        import sys as _sys
        from wsuconnect.data import load as load_data
        from json import loads

        #read credentials.json
        fullCredentials = loads(load_data.readable('credentials.json').read_text())
        setattr(self,'projects',fullCredentials['projects'])

        #find project credentials
        try: 
            if project in self.projects:
                # reset per-project optional settings so one project's values never
                # carry over to the next project read through this shared object
                self.simnibs = _copy.deepcopy(_SIMNIBS_DEFAULTS)
                for k in fullCredentials[project].keys():
                    if not '__comment__' in k:
                        if k == "simnibs":
                            self.simnibs.update({sk: sv for sk, sv in fullCredentials[project][k].items() if sk in _SIMNIBS_DEFAULTS})
                            continue
                        setattr(self,k,fullCredentials[project][k])
                        if k == "dataDir":
                            setattr(self, "dataPath", _Path(fullCredentials[project][k]))
            else:
                raise _InvalidProjectError
            return True
    
        except FileNotFoundError as e:
            exc_type, exc_obj, exc_tb = _sys.exc_info()
            filename = exc_tb.tb_frame.f_code.co_filename
            lineno = exc_tb.tb_lineno
            print(f"Exception occurred in file: {filename}, line: {lineno}")
            print(f"\tException type: {exc_type.__name__}")
            print(f"\tException message: {e}")
            _traceback.print_exc()
            # _sys.exit()
            return False
        except _InvalidProjectError as e:
            exc_type, exc_obj, exc_tb = _sys.exc_info()
            filename = exc_tb.tb_frame.f_code.co_filename
            lineno = exc_tb.tb_lineno
            print(f"Exception occurred in file: {filename}, line: {lineno}")
            print(f"\tException type: {exc_type.__name__}")
            print(f"\tException message: {e}")
            _traceback.print_exc()
            # _sys.exit()
            return False

