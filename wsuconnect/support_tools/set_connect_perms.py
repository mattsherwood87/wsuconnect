# set_connect_perms.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 12 Nov 2026
#
# Same permission rule as connect_neuro_db_update.py (mode 0770, group named after
# the top-level storage folder, e.g. /resshare/... -> group "resshare"), as one
# reusable function that always sets both mode and ownership.

import os
import grp

#versioning
VERSION = '1.0.0'
DATE = '12 Nov 2026'


def storage_gid(path: str) -> int:
    """
    Group id for a storage location: the group named after the first path component.

    /resshare/projects/... -> gid of group "resshare" (as in connect_neuro_db_update.py)

    :param path: absolute path on the storage location
    :type path: str

    :raises KeyError: if no group of that name exists
    :return: group id
    :rtype: int
    """
    return grp.getgrnam(os.path.abspath(path).split(os.sep)[1]).gr_gid


def set_connect_perms(path: str, uid: int = 0, gid: int = None, group_path: str = None,
                      mode: int = 0o770, dir_mode: int = None, recursive: bool = True) -> list:
    """
    Apply the CoNNECT permission rule to path (and everything under it).

    Mode and ownership are always both set, even when the mode is already right.
    Symlinks are skipped.

    :param path: file or directory to fix
    :type path: str

    :param uid: owner uid, defaults to 0 (root)
    :type uid: int, optional

    :param gid: group id; if None it comes from group_path, or from path itself
    :type gid: int, optional

    :param group_path: take the storage group from this path instead of path (e.g. a
        project's dataDir when path is a local staging folder), defaults to None
    :type group_path: str, optional

    :param mode: mode for files (and directories unless dir_mode is given), defaults to 0o770
    :type mode: int, optional

    :param dir_mode: mode for directories, e.g. 0o2770 to add setgid, defaults to None (= mode)
    :type dir_mode: int, optional

    :param recursive: also apply to everything under path, defaults to True
    :type recursive: bool, optional

    :return: paths that could not be changed (with the error), empty when all succeeded
    :rtype: list
    """
    if gid is None:
        gid = storage_gid(group_path if group_path else path)
    if dir_mode is None:
        dir_mode = mode

    failed = []

    def _apply(p: str, is_dir: bool):
        if os.path.islink(p):
            return
        try:
            os.chown(p, uid, gid)
            os.chmod(p, dir_mode if is_dir else mode)
        except OSError as e:
            failed.append((p, str(e)))

    _apply(path, os.path.isdir(path))
    if recursive and os.path.isdir(path) and not os.path.islink(path):
        for root, dirs, files in os.walk(path):
            for d in dirs:
                _apply(os.path.join(root, d), True)
            for f in files:
                _apply(os.path.join(root, f), False)
    return failed
