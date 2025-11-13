#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 18 Sep 2025
#
# Modified on 
VERSION = '1.0.0'
DATE = '18 September 2025'

import argparse

#input argument parser
parser = argparse.ArgumentParser('Moves or copies input (source) directories to a single output directory.')
parser.add_argument('-s','--seg', required=True,action='store', dest="INSEG", help="input directories to copy", default=None)
parser.add_argument('-i','--in-file', required=True,action='store', dest="INFILE", help="input directories to copy", default=None)
parser.add_argument('-o','--out-dir', required=True,action='store', dest="OUTDIR", help="input directories to copy", default=None)
parser.add_argument('--overwrite', action='store_true', dest="OVERWRITE", help="input directories to copy", default=False)
   


# *******************  MAIN  ********************    
def compute_segstats(in_file: str, in_seg: str, out_dir: str, overwrite: str=False): 
    """
    Moves or copies input (source) directories to a single output directory.

    :param INDIR: fullpath to input (source) directory(ies)
    :type INDIR: str

    :raises Exception: generic error from attenpted deletion
    """    
    import os
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    outFile = in_file.replace('space-','space-FS')
    if not os.path.isfile(outFile):
        vol2volCmd = 'mri_vol2vol --mov ' + in_file + ' --targ ' + os.path.join(os.path.dirname(in_seg),'T1.mgz') + ' --regheader --o ' + outFile + ' --no-save-reg'
        os.system(vol2volCmd)
        print('SUCCESS: moved input file to ' + os.path.join(os.path.dirname(in_seg),'T1.mgz'))



    if not os.path.isfile(os.path.join(out_dir,os.path.basename(outFile).replace('.nii.gz','.dat'))) or overwrite:
        os.system('mri_segstats --seg ' + in_seg + ' --nonempty --ctab-default --in ' + outFile + ' --sum ' + os.path.join(out_dir,os.path.basename(outFile).replace('.nii.gz','.dat')))
        print(f"Output stats saved to: {os.path.join(out_dir,os.path.basename(outFile).replace('.nii.gz','.dat'))}")


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """

    options = parser.parse_args()
    compute_segstats(options.INFILE,options.INSEG,options.OUTDIR,options.OVERWRITE)