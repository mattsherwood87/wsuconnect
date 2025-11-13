#!/resshare/python3_venv/bin/python
# the command above ^^^ sets python 3.10.9 venv as the interpreter for this program

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 10 July 2023
#
# Modified on 
VERSION = '1.0.0'
DATE = '10 July 2023'

import argparse

#input argument parser
# ******************* PARSE COMMAND LINE ARGUMENTS ********************
parser = argparse.ArgumentParser('connect_neuro_db_query.py: Query tables in the MySQL databases to search the AWS S3 bucket for specific files.')
parser.add_argument('-i','--in-dir', required=True, nargs='+', dest="INDIR", help="input directories to copy. multiple inputs accepted through space delimiter", default=None)
parser.add_argument('-o','--out-dir', required=True,action="store", dest="OUTDIR", help="destination directory to copy inputs to", default=None)
parser.add_argument('-m','--move', action='store_true', dest='MOVE', help='move files instead of copy',default=False)



# *******************  MAIN  ********************    
def copy_dirs(INDIR: str|list,OUTDIR: str,*args,**kwargs): 
    """ 
    This function moves or copies input (source) directories to a single output directory.

    :param INDIR: fullpath to input (source) directory (str) or list of directories
    :type INDIR: str | list

    :param OUTDIR: fullpath to an output (destination) directory
    :type OUTDIR: str

    :param move: flag to perform a move instead of a copy, defaults to False
    :type move: bool, optional
    """   
    import traceback
    import os 
    import sys 
    import shutil

    try:
        moveFiles = kwargs.get('move',False)
        if type(INDIR) == list:
            for inDir in INDIR:
                if moveFiles:
                    if not os.path.isdir(os.path.dirname(OUTDIR)):
                        os.makedirs(OUTDIR)
                    os.system('mv ' + inDir + ' ' + OUTDIR)
                    # shutil.rmtree(inDir)
                    # shutil.move(inDir,OUTDIR)
                else:
                    if not os.path.isdir(OUTDIR):
                        os.makedirs(OUTDIR)
                    print('cp -RL ' + inDir + ' ' + OUTDIR)
                    os.system('cp -RL ' + inDir + ' ' + OUTDIR)


        else:
            if moveFiles:
                shutil.move(INDIR,OUTDIR)
            else:
                os.system('cp -RL ' + inDir + ' ' + OUTDIR)


    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        print(f"Exception occurred in file: {filename}, line: {lineno}")
        print(f"\tException type: {exc_type.__name__}")
        print(f"\tException message: {e}")
        traceback.print_exc()
        return


if __name__ == '__main__':
    """
    The entry point of this program for command-line utilization.
    """

    options = parser.parse_args()
    copy_dirs(options.INDIR,options.OUTDIR,move=options.MOVE)