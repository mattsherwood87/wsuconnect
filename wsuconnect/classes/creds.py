# creds.py

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 23 Dec 2020

#versioning
_VERSION = '2.0.1'
_DATE = '21 Nov 2024'


import os as _os
from pathlib import Path as _Path
_REALPATH = _Path(_os.path.realpath(__file__)).parts[:-2]


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
                for k in fullCredentials[project].keys():
                    if not '__comment__' in k:
                        setattr(self,k,fullCredentials[project][k])
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

