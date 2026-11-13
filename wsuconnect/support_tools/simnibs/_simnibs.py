# _simnibs.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 12 Nov 2026
#
# Submit SimNIBS charm + brain_print HTCondor jobs for newly converted sessions and
# collect the results. Called from connect_pacs_dicom_grabber.py (which runs as root)
# and from connect_simnibs.py (by hand).
#
# Design:
#  * HTCondor will not run root-owned jobs, so jobs are submitted as an ordinary
#    account (st.creds.simnibs['condor_user']) by running condor_submit with that uid.
#  * No file transfer: /resshare* is mounted on every execute host. Root creates
#    <dataDir>/derivatives/sub-X/ses-Y/anat/charm (owned by the job account, storage
#    group, 2770) and the job runs charm_brain_print there in the simnibs image (docker
#    universe, storage mounted by +MOUNT_RESSHAREnn), reading
#    the T1/T2 straight from rawdata. Results land in anat/charm/m2m_<sub>_<ses>.
#  * The submit/log/output/error files and the job scripts go to
#    <dataDir>/code/processing_logs/connect_simnibs/<sub>_<ses>_<time>/.
#  * When a job finishes, root applies the CoNNECT permission rule (0770, storage group)
#    to the results.
#  * Job state lives in <STAGING_DIR>/<job>/state.json (local, root only), so nothing
#    is lost when the grabber restarts.

import glob
import json
import os
import pwd
import re
import shutil
import subprocess
import traceback
from datetime import datetime

#versioning
VERSION = '1.0.0'
DATE = '12 Nov 2026'

STAGING_DIR = '/var/lib/connect-simnibs'
EXPORT_LOG_DIR = os.path.join('/Export', 'data_transfer_progress')
JOB_NAME = 'simnibs'           # pycondor job name -> simnibs.submit/.log/.output/.error
STATUS_SUBMITTED = 'submitted'
STATUS_DONE = 'done'
STATUS_FAILED = 'failed'


# Job script, written to the job's log folder on /resshare and run in the simnibs image
# (docker universe; the +MOUNT_RESSHAREnn attributes mount the project storage). It cds
# to anat/charm, always leaves m2m_<id> with condor_exit_code behind, and runs
# charm_brain_print through its interpreter when the image installed it without the
# execute bit for other users.
CHARM_SCRIPT_NAME = 'run_charm.sh'
CHARM_SCRIPT = r"""#!/bin/bash
# usage: run_charm.sh WORKDIR SUBID T1 [T2] [charm_brain_print options]
cd "$1" || { echo "cannot cd to $1" >&2; exit 2; }
shift
# The container runs as the job account's uid, which has no home in the image.
export HOME=/tmp/home
export XDG_CACHE_HOME="$HOME/.cache" MPLCONFIGDIR="$HOME/.cache/matplotlib" \
       NUMBA_CACHE_DIR="$HOME/.cache/numba" XDG_RUNTIME_DIR="$HOME/.runtime" TMPDIR="$HOME/tmp"
mkdir -p "$MPLCONFIGDIR" "$NUMBA_CACHE_DIR" "$TMPDIR"; mkdir -p -m 700 "$XDG_RUNTIME_DIR"
export PATH="/opt/conda/envs/simnibs_env/bin:/opt/conda/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export LANG=C.UTF-8 LC_ALL=C.UTF-8 MPLBACKEND=Agg QT_QPA_PLATFORM=offscreen

sub="$1"
echo "[$(date '+%F %T')] in container uid=$(id -u) gid=$(id -g) pwd=$PWD"
cbp=$(command -v charm_brain_print)
for d in /usr/bin /usr/local/bin /opt/conda/envs/simnibs_env/bin /opt/conda/bin; do
    [ -n "$cbp" ] && break; [ -e "$d/charm_brain_print" ] && cbp="$d/charm_brain_print"
done
cbp=${cbp:-/usr/bin/charm_brain_print}
ls -l "$cbp"
echo "charm_brain_print $*"
if [ -x "$cbp" ]; then
    "$cbp" "$@"
elif [ -r "$cbp" ]; then
    interp=$(head -1 "$cbp" | sed -n 's/^#! *//p')
    echo "$cbp is not executable for uid $(id -u), running it with ${interp:-bash}" >&2
    ${interp:-bash} "$cbp" "$@"
else
    echo "$cbp is not readable for uid $(id -u); rebuild the image with chmod 755 on it" >&2
    false
fi
rc=$?
mkdir -p "m2m_$sub"
echo "$rc" > "m2m_$sub/condor_exit_code"
echo "[$(date '+%F %T')] charm_brain_print exit $rc"
exit "$rc"
"""


# ******************* LOGGING ********************
def _stamp() -> str:
    return datetime.now().strftime('%m%d%Y %H:%M:%S')


def default_log(string_to_write: str):
    """
    Insert a line at the top of /Export/data_transfer_progress/connect_pacs_dicom_grabber-YYYYMM.log,
    the same way connect_pacs_dicom_grabber.write_log does. Used when the grabber's
    own write_log is not passed in (e.g. connect_simnibs.py).

    :param string_to_write: line to insert
    :type string_to_write: str
    """
    logfile = os.path.join(EXPORT_LOG_DIR, 'connect_pacs_dicom_grabber-' + datetime.now().strftime('%Y%m') + '.log')
    try:
        lines = []
        if os.path.isfile(logfile):
            with open(logfile, 'r') as f:
                lines = f.readlines()
        lines.insert(0, string_to_write + '\n')
        with open(logfile, 'w') as f:
            f.writelines(lines)
    except Exception:
        traceback.print_exc()
    print(string_to_write)


def _emit(log, msg: str):
    """Write one tab-indented, time-stamped line in the grabber's log format."""
    (log or default_log)(f'\t{msg} @ {_stamp()}')


# ******************* HELPERS ********************
def _clean(s: str) -> str:
    return re.sub(r'[^A-Za-z0-9_-]', '', s)


def _session_from_sourcedata(sourcedata_dir: str):
    """<dataDir>/sourcedata/sub-X/ses-Y -> ('sub-X', 'ses-Y')"""
    p = os.path.normpath(sourcedata_dir)
    ses = os.path.basename(p)
    sub = os.path.basename(os.path.dirname(p))
    if not sub.startswith('sub-') or not ses.startswith('ses-'):
        raise ValueError(f'expected .../sub-X/ses-Y, got {sourcedata_dir}')
    return sub, ses


def _run_number(path: str) -> int:
    m = re.search(r'_run-(\d+)', os.path.basename(path))
    return int(m.group(1)) if m else 0


def find_image(anat_dir: str, label: str, exclude=()) -> str:
    """
    Find one image in anat_dir whose filename ends with label. Nothing is added to the
    label: 'T1w.nii.gz' matches any *T1w.nii.gz, 'rec-ax_T1w.nii.gz' matches
    *rec-ax_T1w.nii.gz. A label without a .nii/.nii.gz extension matches either one.
    With several matches the highest run- (then newest file) wins.

    :param exclude: paths that may not be returned (e.g. the image already used as T2)
    :return: fullpath, or None when label is empty or nothing matches
    """
    label = (label or '').strip().lstrip('*')
    if not label:
        return None
    if label.endswith(('.nii.gz', '.nii')):
        patterns = [f'*{label}']
    else:
        patterns = [f'*{label}.nii.gz', f'*{label}.nii']
    skip = {os.path.realpath(f) for f in exclude if f}
    matches = set()
    for pat in patterns:
        matches.update(f for f in glob.glob(os.path.join(anat_dir, pat))
                       if os.path.realpath(f) not in skip)
    if not matches:
        return None
    return max(matches, key=lambda f: (_run_number(f), os.path.getmtime(f)))


def _makedirs_top(path: str) -> str:
    """os.makedirs(path) and return the highest folder it created (None if path existed)."""
    if os.path.isdir(path):
        return None
    top = path
    while not os.path.exists(os.path.dirname(top)):
        top = os.path.dirname(top)
    os.makedirs(path)
    return top


def _job_dirs(key: str = '*') -> list:
    return sorted(glob.glob(os.path.join(STAGING_DIR, f'{key}_*', 'state.json')))


def _read_state(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _write_state(path: str, state: dict):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def parse_job_log(log_path: str) -> dict:
    """
    Read an HTCondor user log and summarise the job's state.

    :return: {'state': 'running'|'done'|'aborted'|'held', 'exit': int or None, 'hold_reason': str}
    """
    out = {'state': 'running', 'exit': None, 'hold_reason': ''}
    if not os.path.isfile(log_path):
        return out
    with open(log_path) as f:
        events = f.read().split('...\n')
    held = False
    for ev in events:
        ev = ev.strip()
        code = ev[:3]
        if code == '005':          # terminated
            m = re.search(r'return value (-?\d+)', ev)
            out['exit'] = int(m.group(1)) if m else -1   # abnormal termination (signal)
            out['state'] = 'done'
        elif code == '009':        # aborted (condor_rm / periodic_remove)
            out['state'] = 'aborted'
        elif code == '012':        # held
            held = True
            lines = ev.splitlines()
            out['hold_reason'] = lines[1].strip() if len(lines) > 1 else ''
        elif code == '013':        # released
            held = False
    if held and out['state'] == 'running':
        out['state'] = 'held'
    return out


# ******************* SESSION SELECTION ********************
def _ses_key(x) -> str:
    """0, '0', 'ses-0' -> '0'"""
    x = str(x).strip()
    return x[4:] if x.startswith('ses-') else x


def session_selected(cfg: dict, ses: str) -> bool:
    """
    Whether the "simnibs" settings select this session: it must be in include_sessions
    ("*" = every session) and not in exclude_sessions. Entries may be numbers or strings,
    with or without "ses-" (0, "0" and "ses-0" all match ses-0). An empty
    include_sessions selects nothing, so simnibs is off for the project.

    :param cfg: the project's simnibs settings (st.creds.simnibs)
    :param ses: session folder name, e.g. 'ses-0'
    """
    include = {_ses_key(s) for s in (cfg.get('include_sessions') or [])}
    exclude = {_ses_key(s) for s in (cfg.get('exclude_sessions') or [])}
    key = _ses_key(ses)
    return ('*' in include or key in include) and key not in exclude


# ******************* SUBMIT ********************
def submit_session(project: str, sourcedata_dir: str, patient: str = '', log=None) -> int:
    """
    Submit a SimNIBS charm + brain_print job for one subject/session, if the project's
    "simnibs" settings in credentials.json select the session (include_sessions /
    exclude_sessions, see session_selected) and it wasn't done before.

    :param project: project identifier in credentials.json
    :type project: str

    :param sourcedata_dir: <dataDir>/sourcedata/sub-X/ses-Y (the grabber's row['sourcedataDir'])
    :type sourcedata_dir: str

    :param patient: DICOM patient name, only used in log lines, defaults to ''
    :type patient: str, optional

    :param log: function taking one string, e.g. the grabber's write_log; defaults to default_log
    :type log: callable, optional

    :return: HTCondor cluster id, or None when nothing was submitted
    :rtype: int
    """
    import wsuconnect.support_tools as st
    from wsuconnect.support_tools.set_connect_perms import set_connect_perms, storage_gid

    st.creds.read(project)
    cfg = st.creds.simnibs
    sub, ses = _session_from_sourcedata(sourcedata_dir)
    if not session_selected(cfg, ses):
        return None
    label = f'{project} {sub}/{ses}'
    data_dir = st.creds.dataDir
    dest = os.path.join(data_dir, 'derivatives', sub, ses, 'anat', 'charm')
    key = _clean(f'{project}_{sub}_{ses}')
    charm_id = _clean(f'{sub}_{ses}')
    m2m = os.path.join(dest, f'm2m_{charm_id}')

    # already done, or already queued (a session's DICOMs can arrive in two batches)
    if os.path.isfile(os.path.join(m2m, 'brain_print.3mf')):
        _emit(log, f"charm skipped for {label}: already done ({os.path.join(m2m, 'brain_print.3mf')} exists)")
        return None
    for sf in _job_dirs(key):
        status = _read_state(sf).get('status')
        if status in (STATUS_SUBMITTED, STATUS_DONE):
            _emit(log, f"charm skipped for {label}: job already {status} (state in {os.path.dirname(sf)})")
            return None

    # images
    anat = os.path.join(data_dir, 'rawdata', sub, ses, 'anat')
    # labels are filename endings ('' T1 = any *T1w.nii.gz, '' T2 = no second image);
    # the T2 is found first so a broad T1 label can't pick the same file
    t1_label = cfg.get('t1_label') or 'T1w.nii.gz'
    t2_label = cfg.get('t2_label') or ''
    t2 = find_image(anat, t2_label)
    t1 = find_image(anat, t1_label, exclude=[t2])
    if not t1:
        _emit(log, f"charm skipped for {label}: no file matching '*{t1_label}' in {anat}")
        return None
    if t2_label and not t2:
        _emit(log, f"charm for {label}: no file matching '*{t2_label}' in {anat}, running T1 only")

    # job account
    user = cfg.get('condor_user')
    if not user or user == 'root':
        _emit(log, f'charm skipped for {label}: simnibs condor_user must be a non-root account')
        return None
    pw = pwd.getpwnam(user)
    as_root = os.geteuid() == 0
    if not as_root and os.geteuid() != pw.pw_uid:
        raise PermissionError(f'run as root or as {user} to submit SimNIBS jobs')

    def job_perms(path):
        """owned by the job account, storage group, setgid so new files keep the group"""
        if not as_root:
            return []
        return set_connect_perms(path, uid=pw.pw_uid, group_path=data_dir, mode=0o770, dir_mode=0o2770)

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    # output folder in derivatives; a leftover m2m from a failed run is kept aside
    if os.path.isdir(m2m):
        os.rename(m2m, f'{m2m}.prev_{stamp}')
    top = _makedirs_top(dest)
    bad = job_perms(top or dest)

    # log folder: submit file, HTCondor log/output/error and the job scripts
    logdir = os.path.join(data_dir, 'code', 'processing_logs', 'connect_simnibs', f'{charm_id}_{stamp}')
    top = _makedirs_top(logdir)
    charm_script = os.path.join(logdir, CHARM_SCRIPT_NAME)
    with open(charm_script, 'w') as f:
        f.write(CHARM_SCRIPT)
    os.chmod(charm_script, 0o770)
    bad += job_perms(top or logdir)
    if bad:
        _emit(log, f'charm permissions for {label}: could not change {len(bad)} path(s), e.g. {bad[0]}')

    args = ' '.join([dest, charm_id, t1, *([t2] if t2 else []), cfg.get('extra_args', '')]).strip()
    job = st.condor.create_bin_condor_job(
        JOB_NAME, CHARM_SCRIPT_NAME, cfg.get('machines') or st.creds.machineNames,
        submit=logdir, error=logdir, output=logdir, log=logdir, dagman=None,
        docker=True, docker_image=cfg.get('image'), docker_mount_if=st.creds.dockerMountIf,
        request_cpus=cfg.get('request_cpus', 4), request_memory=cfg.get('request_memory', '16g'),
        requirements='(HasDocker =?= true)',
        extra_lines=[
            f'initialdir = {dest}',
            'should_transfer_files = NO',
            'transfer_executable = false',
            # a job held for 2 h is removed, so collect_finished always gets an end state
            'periodic_remove = (JobStatus == 5) && (time() - EnteredCurrentStatus > 7200)',
            f'batch_name = simnibs_{charm_id}',
        ])
    job.executable = charm_script
    job.add_arg(args)
    job.build(makedirs=False, fancyname=False)
    job_perms(job.submit_file)

    # state stays on local disk, readable by root only
    os.makedirs(STAGING_DIR, mode=0o700, exist_ok=True)
    jobdir = os.path.join(STAGING_DIR, f'{key}_{stamp}')
    os.makedirs(jobdir)
    state_file = os.path.join(jobdir, 'state.json')
    state = {
        'status': STATUS_FAILED, 'cluster': None, 'project': project, 'patient': patient,
        'subject': sub, 'session': ses, 'charm_id': charm_id, 'data_dir': data_dir,
        'dest': dest, 'm2m': m2m, 't1': t1, 't2': t2, 'jobdir': jobdir, 'logdir': logdir,
        'submitted': datetime.now().isoformat(timespec='seconds'), 'hold_logged': '',
    }
    _write_state(state_file, state)

    # submit as the job account
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': pw.pw_dir,
           'USER': pw.pw_name, 'LOGNAME': pw.pw_name}
    if os.environ.get('CONDOR_CONFIG'):
        env['CONDOR_CONFIG'] = os.environ['CONDOR_CONFIG']
    run_as = {}
    if as_root:
        run_as = {'user': pw.pw_uid, 'group': pw.pw_gid,
                  'extra_groups': os.getgrouplist(pw.pw_name, pw.pw_gid)}
    try:
        res = subprocess.run(['condor_submit', '-terse', job.submit_file], cwd=logdir, env=env,
                             capture_output=True, text=True, timeout=120, **run_as)
        m = re.match(r'\s*(\d+)', res.stdout or '')
        if res.returncode != 0 or not m:
            raise RuntimeError((res.stderr or res.stdout or f'exit {res.returncode}').strip().splitlines()[-1])
    except Exception as e:
        _emit(log, f'charm submit FAILED for {label}: {e} (see {logdir})')
        return None

    state['cluster'] = int(m.group(1))
    state['status'] = STATUS_SUBMITTED
    _write_state(state_file, state)
    images = ', '.join(os.path.basename(f) for f in (t1, t2) if f)
    _emit(log, f"charm started for {label} images {images} (cluster {state['cluster']}) -> {m2m}")
    return state['cluster']


# ******************* COLLECT ********************
def collect_finished(log=None) -> list:
    """
    Check every submitted job; set permissions on finished results in
    <dataDir>/derivatives/sub-X/ses-Y/anat/charm/m2m_<id> and log the outcome. Cheap when
    nothing is pending, so the grabber can call it on every loop.

    :param log: function taking one string, e.g. the grabber's write_log; defaults to default_log
    :type log: callable, optional

    :return: states of the jobs that finished (done or failed) during this call
    :rtype: list
    """
    from wsuconnect.support_tools.set_connect_perms import set_connect_perms

    finished = []
    for state_file in _job_dirs():
        try:
            state = _read_state(state_file)
            if state.get('status') != STATUS_SUBMITTED:
                continue
            label = f"{state['project']} {state['subject']}/{state['session']}"
            jobdir = state['jobdir']
            ev = parse_job_log(os.path.join(state.get('logdir') or jobdir, f'{JOB_NAME}.log'))

            if ev['state'] in ('running',):
                continue
            if ev['state'] == 'held':
                if state.get('hold_logged') != ev['hold_reason']:
                    _emit(log, f"charm on hold for {label} (cluster {state['cluster']}): {ev['hold_reason']}")
                    state['hold_logged'] = ev['hold_reason']
                    _write_state(state_file, state)
                continue

            def perms(p):
                return set_connect_perms(p, uid=0, group_path=state['data_dir'])

            # jobs submitted before the switch to in-place runs kept m2m in the job folder
            m2m = state.get('m2m') or os.path.join(jobdir, f"m2m_{state['charm_id']}")
            logdir = state.get('logdir') or jobdir
            ok = ev['state'] == 'done' and ev['exit'] == 0 and os.path.isfile(os.path.join(m2m, 'brain_print.3mf'))
            bad = [p for p in (m2m, logdir) if os.path.exists(p) for p in perms(p)]
            if bad:
                _emit(log, f'charm results permissions for {label}: could not change {len(bad)} path(s), e.g. {bad[0]}')
            if ok:
                state['status'] = STATUS_DONE
                _emit(log, f'charm finished for {label} -> {m2m}')
            else:
                state['status'] = STATUS_FAILED
                why = f"exit {ev['exit']}" if ev['state'] == 'done' else 'removed from the queue'
                if ev['state'] == 'aborted' and state.get('hold_logged'):
                    why += f" after hold: {state['hold_logged']}"
                _emit(log, f"charm FAILED for {label} ({why}), see {logdir}/{JOB_NAME}.error and "
                           f"{m2m}/charm_brain_print.log")
            state['finished'] = datetime.now().isoformat(timespec='seconds')
            _write_state(state_file, state)
            finished.append(state)
        except Exception as e:
            traceback.print_exc()
            _emit(log, f'charm collect error for {state_file}: {e}')
    return finished
