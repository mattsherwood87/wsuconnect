#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.12.3 as the interpreter for this program
 
# Created by Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 29 Oct 2026
#
# v1.0.0 on 29 Oct 2026 - initial release
 
import os
import sys
import json
import shutil
import argparse
from datetime import datetime
 
from PyQt5 import QtWidgets
 
 
REALPATH = os.path.realpath(__file__)
 
# GLOBAL INFO
#versioning
VERSION = '1.0.0'
DATE = '29 Oct 2026'
 
DEFAULT_CREDS = os.path.join(os.path.dirname(REALPATH), 'data', 'credentials.json')
 
# (key, label, default, is_list) in the order written to credentials.json
FIELDS = [
    ('description', 'Description', '', False),
    ('title', 'Title', '', False),
    ('fund', 'Fund', '', False),
    ('org', 'Org', '', False),
    ('database', 'Database', 'CoNNECT', False),
    ('dataDir', 'Data directory', '', False),
    ('dicom_id', 'DICOM ID', 'IM_', False),
    ('examCardName', 'ExamCard name', '', False),
    ('instance_id', 'Instance ID (not used)', '', False),
    ('ipAddress', 'IP address (not used)', '', False),
    ('machineNames', 'Machine names (comma-separated)', 'afh2.nist.local', True),
    ('gpuMachineNames', 'GPU machine names (comma-separated)', 'npc-core-gpu1', True),
    ('project', 'Project identifier', '', False),
    ('searchTable', 'Search table', '', False),
    ('searchSourceTable', 'Search source table', '', False),
    ('dockerMountIf', 'Docker mount interface', '', False),
    ('contact', 'Contact emails (comma-separated)', '', True),
]
 
# keys kept in the entry (as empty strings) but not editable
UNUSED = ('instance_id', 'ipAddress')
 
MACHINE_NAMES = ['afh1.nist.local', 'afh2.nist.local', 'npc-core1a', 'npc-core1b', 'npc-core1C', 'npc-core1D', 'npc-core-gpu1']
 
 
# ******************* PARSE COMMAND LINE ARGUMENTS ********************
#input argument parser
parser = argparse.ArgumentParser(os.path.basename(REALPATH) + ' - GUI to add a project entry to credentials.json')
parser.add_argument('-c','--creds', action="store", dest="CREDS", help="fullpath to credentials.json (default: package data/credentials.json)", default=DEFAULT_CREDS)
parser.add_argument('-v', '--version', help="Display the current version", action="store_true", dest="version")
 
 
# ******************* UPDATE CREDENTIALS FILE ********************
def add_project_to_creds(credsFile: str, project: str, entry: dict) -> str:
    """
    Prepend a project to the "projects" list and insert its entry directly after the
    "master_machine_name" line of credentials.json. The rest of the file is left as written.
    A timestamped backup of the original file is created first.
 
    Parameters
    ----------
    credsFile : str
        fullpath to credentials.json
    project : str
        project identifier (key of the new entry)
    entry : dict
        project entry, in the order to write it
 
    Returns
    -------
    str
        fullpath to the backup file
    """
    with open(credsFile, 'r') as f:
        text = f.read()
    d_creds = json.loads(text)
 
    if project in d_creds or project in d_creds['projects']:
        raise ValueError('project ' + project + ' already exists in ' + credsFile)
 
    lines = text.splitlines(keepends=True)
    iProjects = next(i for i, l in enumerate(lines) if l.lstrip().startswith('"projects"'))
    iMaster = next(i for i, l in enumerate(lines) if l.lstrip().startswith('"master_machine_name"'))
 
    # prepend to the projects list
    lines[iProjects] = lines[iProjects].replace('[', '[' + json.dumps(project) + ',', 1)
 
    # build the entry block in the file's style
    entryLines = ['    ' + json.dumps(project) + ': {\n']
    items = list(entry.items())
    for j, (k, v) in enumerate(items):
        val = '[' + ','.join(json.dumps(x) for x in v) + ']' if isinstance(v, list) else json.dumps(v)
        entryLines.append('        ' + json.dumps(k) + ': ' + val + (',' if j < len(items) - 1 else '') + '\n')
    entryLines.append('    },\n')
 
    # insert after the master_machine_name line (keep the blank line before the first entry)
    lines[iMaster + 1:iMaster + 1] = ['\n'] + entryLines
    newText = ''.join(lines)
    json.loads(newText)  # validate before writing
 
    backup = credsFile + '.' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.bak'
    shutil.copy2(credsFile, backup)
    with open(credsFile, 'w') as f:
        f.write(newText)
    return backup
 
 
# ******************* GUI ********************
class CredsDialog(QtWidgets.QDialog):
    def __init__(self, credsFile: str):
        super().__init__()
        self.credsFile = credsFile
        self.setWindowTitle('Add project to credentials.json')
        self.setMinimumWidth(900)
 
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.keyEdit = QtWidgets.QLineEdit()
        self.keyEdit.setPlaceholderText('IRB protocol number, e.g. 2026-0001')
        form.addRow('Project key *', self.keyEdit)
 
        self.edits = {}
        for key, label, default, isList in FIELDS:
            edit = QtWidgets.QLineEdit(default)
            self.edits[key] = edit
            if key in UNUSED:
                edit.setEnabled(False)
                edit.setPlaceholderText('not used (saved empty)')
            if key in ('machineNames', 'gpuMachineNames'):
                edit.setToolTip('Available machines:\n' + '\n'.join(MACHINE_NAMES))
            if key == 'dockerMountIf':
                edit.setToolTip('Mounted resshare name, e.g. resshare20')
            if key == 'project':
                edit.setToolTip('Filled in from the project key')
            if key in ('searchTable', 'searchSourceTable'):
                edit.setToolTip('Filled in from the project key (- replaced by _)')
            if key == 'dataDir':
                browse = QtWidgets.QPushButton('Browse...')
                browse.clicked.connect(self.browse_data_dir)
                row = QtWidgets.QHBoxLayout()
                row.addWidget(edit)
                row.addWidget(browse)
                form.addRow(label, row)
            else:
                form.addRow(label, edit)
 
        # fill project and table names from the project key unless edited
        self.keyEdit.textChanged.connect(self.fill_from_key)
 
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
 
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('File: ' + credsFile))
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._lastAuto = {}
 
    def browse_data_dir(self):
        # the dialog's New Folder button can be used to create the project folder
        start = self.edits['dataDir'].text().strip() or os.getcwd()
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select or create the project data directory', start)
        if d:
            self.edits['dataDir'].setText(d)
 
    def fill_from_key(self, key: str):
        auto = {'project': key,
                'searchTable': key.replace('-', '_'),
                'searchSourceTable': key.replace('-', '_') + '_sourcedata'}
        for k, v in auto.items():
            if self.edits[k].text() in ('', self._lastAuto.get(k, '')):
                self.edits[k].setText(v)
        self._lastAuto = auto
 
    def entry(self) -> dict:
        d = {}
        for key, label, default, isList in FIELDS:
            text = '' if key in UNUSED else self.edits[key].text().strip()
            d[key] = [x.strip() for x in text.split(',') if x.strip()] if isList else text
        return d
 
    def save(self):
        project = self.keyEdit.text().strip()
        if not project:
            QtWidgets.QMessageBox.warning(self, 'Missing project key', 'Enter a project key.')
            return
        entry = self.entry()
        preview = json.dumps({project: entry}, indent=4)
        if QtWidgets.QMessageBox.question(self, 'Confirm', 'Add this entry to ' + self.credsFile + '?\n\n' + preview) != QtWidgets.QMessageBox.Yes:
            return
        try:
            backup = add_project_to_creds(self.credsFile, project, entry)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', str(e))
            return
        QtWidgets.QMessageBox.information(self, 'Saved', 'Added ' + project + '.\nBackup: ' + backup)
        self.accept()
 
 
# *******************  MAIN  ********************
if __name__ == '__main__':
    """
    The entry point of this program.
    """
    options = parser.parse_args()
    if options.version:
        print(os.path.basename(REALPATH) + ' version {0}.'.format(VERSION)+" DATED: "+DATE)
        sys.exit(0)
 
    app = QtWidgets.QApplication(sys.argv)
    dlg = CredsDialog(options.CREDS)
    dlg.show()
    sys.exit(app.exec_())
 