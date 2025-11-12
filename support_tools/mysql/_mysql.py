# _mysql.py

# Copywrite Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 21 Jan 2021
#
# v3.0.0 on 1 April 2023
# Modified on 20 Oct 2021 - elimination of mysql database in supplement of list bucket from boto3
# modified on 21 Jan 2021

import sys
import os
import pymysql
import pymysql.cursors
import traceback
from pathlib import Path
import pandas as pd
from datetime import timedelta, datetime


#append path if necessary
REALPATH = Path(*Path(os.path.realpath(__file__)).parts[:-4]).resolve()
if not str(REALPATH) in sys.path:
    sys.path.append(REALPATH)
from wsuconnect import support_tools as st


VERSION = '4.0.0'
DATE = '5 April 2023'


def fix_time_str(x: str|timedelta|pd.Timedelta):
    """
    Format input for SQL Time field entry ('HH:MM:SS')

    Parameters
    ----------
    x : str | timedelta | pd.Timedelta
        time to format

    Returns
    -------
    str
        formatted time string for SQL Time field
    """
    # if x is None or pd.isna(x):
    #     return None  # preserve None
    if isinstance(x, (timedelta, pd.Timedelta)):
        # Convert to Python timedelta for consistent formatting
        py_td = x.to_pytimedelta() if isinstance(x, pd.Timedelta) else x
        return (datetime.min + py_td).time().strftime("%H:%M:%S")
    elif isinstance(x, str) and '0 days ' in x:
        # Parse the string into a timedelta safely
        parts = x.split('0 days ')[-1].strip()
        return parts  # or parse further if needed
    return x

# ******************* s3 bucket check ********************
def query_source_file(regex: str, returncol: str='fullpath', orderby: str='fullpath', inclusion: str|list=None, exclusion: str|list=None, progress: bool=False) -> str:
    """
    This function queries the sourcedata table specified in the 
    support_tools.creds.searchSourceTable object for a single file. 
    The fullpath to the single file is returned. If none or more
    than 1 file matches the criteria, None is returned.

    query_source_file(regex=regexStr,progress=False)

    Parameters
    ----------
    regex : str
        search string for query
    returncol : str, optional
        table column to return in query, defaults to 'fullpath'
    orderby : str, optional
        column to sort returns by, defaults to 'fullpath', by default 'fullpath'
    inclusion : str | list, optional
        string or list of strings that are additionally required for an item be returned, by default None
    exclusion : str | list, optional
        string or list of strings that will exclude items from being returned, by default None
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    -------
    str
        output table column from all items matching the specified search criteria
    """     


    outFileOrig = sql_query(database=st.creds.database,searchtable=st.creds.searchSourceTable,searchcol='fullpath',regex=regex,returncol=returncol,orderby=orderby,inclusion=inclusion,exclusion=exclusion,progress=progress) #only look on s3


    if len(outFileOrig) == 1: #if 1 file on database
        outFile = outFileOrig[0]
        
    elif len(outFileOrig) == 0:
        print('WARNING: no files found matching ' + regex + ' in ' + st.creds.searchSourceTable)
        outFile = None
    else:
        print('WARNING: more than 1 file found matching ' + regex + ' in ' + st.creds.searchSourceTable)
        outFile = None
        
        
    #sys.exit()
    return outFile


# ******************* s3 bucket check ********************
def query_file(regex: str, returncol: str='fullpath', orderby: str='fullpath', inclusion: str|list=None, exclusion: str|list=None, progress: bool=False) -> str:
    """
    This function queries the data table specified in the 
    support_tools.creds.searchTable object for a single file. 
    The fullpath to the single file is returned. If none or more
    than 1 file matches the criteria, None is returned.

    query_source_file(regex=regexStr,progress=False)

    Parameters
    ----------
    regex : str
        search string for query
    returncol : str, optional
        table column to return in query, defaults to 'fullpath'
    orderby : str, optional
        column to sort returns by, defaults to 'fullpath', by default 'fullpath'
    inclusion : str | list, optional
        string or list of strings that are additionally required for an item be returned, by default None
    exclusion : str | list, optional
        string or list of strings that will exclude items from being returned, by default None
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    -------
    str
        output table column from all items matching the specified search criteria
    """     


    outFileOrig = sql_query(database=st.creds.database,searchtable=st.creds.searchTable,searchcol='fullpath',regex=regex,returncol=returncol,orderby=orderby,inclusion=inclusion,exclusion=exclusion,progress=progress) #only look on s3


    if len(outFileOrig) == 1: #if 1 file on database
        outFile = outFileOrig[0]
        
    elif len(outFileOrig) == 0:
        print('WARNING: no files found matching ' + regex + ' in ' + st.creds.searchTable)
        outFile = None
    else:
        print('WARNING: more than 1 file found matching ' + regex + ' in ' + st.creds.searchTable)
        outFile = None
        
        
    #sys.exit()
    return outFile



# ******************* QUERY OUTPUT DIRECTORIES FOR NIFTIS ********************
def sql_query_dir_check(regex: str, targetdir: str, progress: bool=False) -> bool:
    """
    This function ealuates the presence of files in a specified directory.

    Parameters
    ----------
    regex : str
        earch string to find matching files
    targetdi : str
        fullpath to a target directory
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    ----------
    bool
        presence (True) or absence (False) of files matching the search string in the specified directory
    """
    
    #connect to sql database
    fullpath = sql_query(database=st.creds.database,searchtable=st.creds.searchTable,returncol='fullpath',searchcol='fullpath',regex=regex,progress=progress,inclusion=targetdir)

    #remove directories from list (only keep files)
    for line in fullpath:
        if line[-1] == os.path.sep:
            fullpath.remove(line)


    #dont process if nifti's exist in associated processed_data directory
    if len(fullpath) > 0:
        return True
    else:
        return False

    


# ******************* QUERY FOR DIRECTORIES CONTAINING DICOMS ********************
def sql_query_dirs(regex: str,source: bool=False,inclusion: str|list=None, exclusion: str|list=None, progress: bool=False) -> list:
    """
    Find all unique directories containing files in a MySql table that match the specified search string regex.

    Parameters
    ----------
    regex : str
        string to match in query
    source : bool
        utilize searchSourceTable instead of searchTable support_tools.creds object, by default False
    inclusion : str | list, optional
        string or list of strings that are additionally required for an item be returned, by default None
    exclusion: str | list, optional
        string or list of strings that will exclude items from being returned, by default None
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    ----------
    list
        list of fullpath to unique directories containing files
    """     

    if isinstance(inclusion,str):
        inclusion = inclusion.split()
    if isinstance(exclusion,str):
        exclusion = exclusion.split()


    dirsToProcess = []
    tmp_dirsToProcess = []
    fullpath = []
    
    #connect to sql database
    if source:
        fullpath = sql_query(searchtable=st.creds.searchSourceTable,regex=regex,database=st.creds.database,returncol='fullpath',searchcol='fullpath',progress=progress,inclusion=inclusion,exclusion=exclusion)
    else:
        fullpath = sql_query(searchtable=st.creds.searchTable,regex=regex,database=st.creds.database,returncol='fullpath',searchcol='fullpath',progress=progress,inclusion=inclusion,exclusion=exclusion)

    fullpath.sort()
    for f in fullpath:
        if tmp_dirsToProcess:
            if not tmp_dirsToProcess[-1] in f:
                tmp_dirsToProcess.append(os.path.dirname(f))
        else:
            tmp_dirsToProcess.append(os.path.dirname(f))
    
    #remove duplicates and return
    dirsToProcess = list(set(tmp_dirsToProcess))
    return dirsToProcess



# ******************* QUERY FOR DIRECTORIES CONTAINING DICOMS ********************
def sql_query(searchtable: str, regex: str, database: str='CoNNECT', returncol: str='fullpath', searchcol: str='filename', orderby: str='fullpath', inclusion: str|list=None, exclusion: str|list=None, orinclusion: str|list=None, progress: bool=False) -> str:
    """
    Find all items in a MySql table that match the specified search string regex.

    Parameters
    ----------
    searchtable : str
        MySql table inside of the specified database
    regex : str
        string to match in query
    database : str, optional
        MySql database containing table, by default 'CoNNECT'
    returncol : str, optional
        table column to return in query, by default 'fullpath'
    searchcol : str, optional
        table column to perform query, by default 'filename'
    orderby : str, optional
        column to sort returns by, by default 'fullpath'
    inclusion : str | list, optional
        string or list of strings that are additionally required for an item be returned, by default None
    exclusion : str | list, optional
        string or list of strings that will exclude items from being returned, by default None
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    ----------
    list
        output table column from all items matching the specified search criteria
    """    

    if isinstance(inclusion,str):
        inclusion = inclusion.split()
    if isinstance(exclusion,str):
        exclusion = exclusion.split()
    if isinstance(orinclusion,str):
        orinclusion = orinclusion.split()

    # if st == None or regex == None:
    #     print("ERROR: must define searchtable AND regex")
    
    #connect to sql database
    sqlConnection = create_mysql_connection(host_name='10.11.0.31',user_name='ubuntu',user_password='neuroscience',db_name=database,progress=progress)
    sqlCursor = sqlConnection.cursor()


    if sql_check_table_exists(sqlCursor,searchtable):

        #create query
        if regex == '':
            sqlQuery ="""SELECT %s FROM %s WHERE %s ORDER BY %s;""" % (returncol,searchtable,searchcol,orderby)
        else:
            sqlQuery ="""SELECT %s FROM %s WHERE %s REGEXP "%s" """ % (returncol,searchtable,searchcol,regex)
            if inclusion:
                for inc in inclusion:
                    sqlQuery += """AND %s REGEXP "%s" """ % (searchcol,inc)
            if exclusion:
                for exc in exclusion:
                    sqlQuery += """AND %s NOT REGEXP "%s" """ % (searchcol,exc)
            if orinclusion:

                sqlQuery += """AND (%s REGEXP "%s" """% (searchcol,orinclusion[0])
                for or_inc in orinclusion[1:]:
                    sqlQuery += """OR %s REGEXP "%s" """ % (searchcol,or_inc)
                sqlQuery = sqlQuery[:-1]
                sqlQuery += """) """ 
            sqlQuery +="ORDER BY %s;" % (orderby)
    else:
        sqlConnection.close()
        return []
    
    # run quory
    # print(sqlQuery)
    sqlCursor.execute(sqlQuery)
    sqlConnection.close()

    #get sql returned list
    # tmp_fullpath = sqlCursor.fetchall()
    return [f[0] for f in sqlCursor.fetchall()]


# ******************* QUERY FOR DIRECTORIES CONTAINING DICOMS ********************
def sql_multiple_query(searchtable: str, regex: str, database: str='CoNNECT', returncol: str='fullpath', searchcol: str='filename', orderby: str='fullpath', progress: bool=False) -> str:
    """
    Find all items in a MySql table that match the specified search string regex.

    Parameters
    ----------
    searchtable : str
        MySql table inside of the specified database
    regex : str
        string to match in query
    database : str, optional
        MySql database containing table, by default 'CoNNECT'
    returncol : str, optional
        table column to return in query, by default 'fullpath'
    searchcol : str, optional
        table column to perform query, by default 'filename'
    orderby : str, optional
        column to sort returns by, by default 'fullpath'
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    ----------
    list
        output table column from all items matching the specified search criteria
    """    

    if searchtable == None or regex == None:
        print("ERROR: must define searchtable AND regex")
    
    #connect to sql database
    sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',database,progress)
    sqlCursor = sqlConnection.cursor()

    if sql_check_table_exists(sqlCursor,searchtable):

        #create query
        sqlQuery ="""SELECT %s FROM %s WHERE %s REGEXP "%s" ORDER BY %s""" % (returncol,searchtable,searchcol,regex,orderby)
        
        #sqlConnection.query(sqlQuery)
        sqlCursor.execute(sqlQuery)    

    else:
        sqlConnection.close()
        return None

    #get sql returned list
    fullpath = sqlCursor.fetchall()

    #sqlConnection.cursor.close()
    sqlConnection.close()

    return fullpath



# ******************* CREATE TABLES FOR A NEW PROJECT ********************
def sql_create_project_tables(progress: bool=False):
    """
    This function creates the searchTable and searchSourceTable tables in the database for a given project, all specified in support_tools.creds object.

    :param progress: flag to display command line output providing additional details on the processing status, defaults to False
    :type progress: bool, optional
    """    
    
    #connect to sql database
    sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',st.creds.database,progress)
    sqlCursor = sqlConnection.cursor()

    #create table
    if not sql_check_table_exists(sqlConnection.cursor(),st.creds.searchTable):
        sqlCMD ="""CREATE TABLE %s ( fullpath char(255), filename varchar(255), basename varchar(255), extension varchar(48) );""" % (st.creds.searchTable)

        #run command
        sqlCursor.execute(sqlCMD)
    else:
        print('WARNING: table ' + st.creds.searchTable + ' already exists')

    #create sourcedata table
    if not sql_check_table_exists(sqlConnection.cursor(),st.creds.searchSourceTable):
        sqlCMD ="""CREATE TABLE %s ( fullpath char(255), filename varchar(255) );""" % (st.creds.searchSourceTable)
        sqlCursor.execute(sqlCMD)
    else:
        print('WARNING: table ' + st.creds.searchSourceTable + ' already exists')

    sqlConnection.commit()
    sqlConnection.close()



# ******************* APPEND ITEM(S) TO TABLE ********************
def sql_table_insert(table: str,item: dict,progress: bool=False):
    """
    This function inserts entry(ies) from item into table from the 
    database specified in support_tools.creds object. 

    sql_table_remove(table,item,progress=True)

    Parameters
    ----------
    table : str
        target table in the database
    :item : str
        dictionary containing the table elements of the item(s) to remove
    progress : bool
        flag to display command line output providing additional details on the processing status, by default False
    :type progress: bool, optional
    """
    
    #connect to sql database
    sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',st.creds.database,progress)
    sqlCursor = sqlConnection.cursor()

    if sql_check_table_exists(sqlCursor,table):

        #create query
        if 'sourcedata' in table:
            if type(item['fullpath']) == list:
                for r in range(len(item['fullpath'])):
                    f = query_source_file(item['fullpath'][r])
                    if f is None:
                        sqlCMD ="""INSERT INTO %s (fullpath, filename) VALUES ('%s', '%s')""" % (table, item['fullpath'][r], item['filename'][r])
                        sqlCursor.execute(sqlCMD)

            else:
                f = query_source_file(item['fullpath'])
                if f is None:
                    sqlCMD ="""INSERT INTO %s (fullpath, filename) VALUES ('%s', '%s')""" % (table, item['fullpath'], item['filename'])
                    sqlCursor.execute(sqlCMD)

        else:
            if type(item['fullpath']) == list:
                for r in range(len(item['fullpath'])):
                    f = query_file(item['fullpath'][r])
                    if f is None:
                        sqlCMD ="""INSERT INTO %s (fullpath, filename, basename, extension) VALUES ('%s', '%s', '%s', '%s')""" % (table, item['fullpath'][r], item['filename'][r], item['basename'][r], item['extension'][r])
                        sqlCursor.execute(sqlCMD)

            else:
                f = query_file(item['fullpath'])
                if f is None:
                    sqlCMD ="""INSERT INTO %s (fullpath, filename, basename, extension) VALUES ('%s', '%s', '%s', '%s')""" % (table, item['fullpath'], item['filename'], item['basename'], item['extension'])
                    sqlCursor.execute(sqlCMD)
    
    # commit changes and close connection
    sqlConnection.commit()
    sqlConnection.close()


# ******************* APPEND ITEM(S) TO TABLE ********************
def sql_table_remove(table: str,item: dict,progress: bool=False):
    """
    This function deletes an entry table from the database specified in support_tools.creds object. 

    sql_table_remove(table,item,progress=True)

    Parameters
    ----------
    table : str
        target table in the database
    item : dict
        dictionary containing the table elements of the item(s) to remove
    """
    
    #connect to sql database
    sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',st.creds.database,progress)
    sqlCursor = sqlConnection.cursor()

    if sql_check_table_exists(sqlCursor,table):

        # create query
        if 'sourcedata' in table:
            if type(item['fullpath']) == list:
                for r in range(len(item['fullpath'])):
                    f = query_source_file(item['fullpath'][r])
                    if f is not None:
                        sqlCMD ="""DELETE FROM %s WHERE fullpath REGEXP '%s'""" % (table, item['fullpath'][r])
                        sqlCursor.execute(sqlCMD)

            else:
                f = query_source_file(item['fullpath'])
                if f is not None:
                    sqlCMD ="""DELETE FROM %s WHERE fullpath REGEXP '%s'""" % (table, item['fullpath'])
                    sqlCursor.execute(sqlCMD)

        else:
            if type(item['fullpath']) == list:
                for r in range(len(item['fullpath'])):
                    f = query_source_file(item['fullpath'][r])
                    if f is not None:
                        sqlCMD ="""DELETE FROM %s WHERE fullpath REGEXP '%s'""" % (table, item['fullpath'][r])
                        sqlCursor.execute(sqlCMD)

            else:
                f = query_source_file(item['fullpath'])
                if f is not None:
                    sqlCMD ="""DELETE FROM %s WHERE fullpath REGEXP '%s'""" % (table, item['fullpath'])
                    sqlCursor.execute(sqlCMD)
    
    # commit changes and close connection
    sqlConnection.commit()
    sqlConnection.close()


def sql_check_table_exists(sqlCursor: pymysql.cursors.Cursor, table: str) -> bool:
    """
    This function checks the database pointed to by the pymysql.cursors.Cursor 
    object for the requested table.

    Parameters
    ----------
    sqlCursor : pymysql.cursors.Cursor
        open cursor opbject to the database
    table : str
        target table in the database

    Returns
    -------
    bool
        flag to identify the presence (True) or absence (False) of the specified table in the databaase
    """

    sqlCursor.execute("""SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '%s'""" % (table))
    if sqlCursor.fetchone()[0] == 1:
        return True

    return False


# ******************* CREATE CONNECTION TO MYSQL DATABASE ********************
def create_mysql_connection(host_name: str, user_name:str , user_password: str, db_name: str = "CoNNECT", progress: bool = False) -> pymysql.connections.Connection:
    """
    This function creates a MySql connection via pymysql. 

    Parameters
    ----------
    host_name : str
        mysql host's hostname
    user_name : str
        mysql username
    user_password : str
        mysql user password
    db_name : str, optional
        _description_, by default 'CoNNECT'
    progress : bool, optional
        flag to display command line output providing additional details on the processing status, by default False

    Returns
    -------
    pymysql.connections.Connection
        _description_
    """
    connection = None

    try:
        # Get credentials
        # credentials = _get_credentials('client')
        connection = pymysql.connect(
            host=host_name,#credentials.get('host','localhost'),
            user=user_name,#credentials.get('user'),
            passwd=user_password,#credentials.get('password'),
            ssl={'ssl': {'ca': '/etc/mysql/ssl/ca-cert.pem', # Path to CA certificate
                         'cert': '/etc/mysql/ssl/client-cert.pem', # Path to client certificate (optional)
                         'key': '/etc/mysql/ssl/client-key.pem'
                         }
                },
            # ssl_ca="/etc/mysql/ssl/ca-cert.pem",
            db=db_name,
            port=3306
            # unix_socket=unix_socket
        )
        if progress:
            print("Connection to MySQL DB successful")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = exc_tb.tb_frame.f_code.co_filename
        lineno = exc_tb.tb_lineno
        print(f"Exception occurred in file: {filename}, line: {lineno}")
        print(f"\tException type: {exc_type.__name__}")
        print(f"\tException message: {e}")
        traceback.print_exc()

    return connection


# # Function to extract credentials from a login path
# def _get_credentials(login_path):
#     try:
#         # Run mysql_config_editor to get login path details
#         result = subprocess.run(
#             ["mysql_config_editor", "print", f"--login-path={login_path}"],
#             capture_output=True,
#             text=True,
#             check=True
#         )
        
#         # Parse the output
#         credentials = {}
#         for line in result.stdout.splitlines():
#             if "=" in line:
#                 key, value = line.split("=", 1)
#                 credentials[key.strip()] = value.strip()
        
#         return credentials
#     except subprocess.CalledProcessError as e:
#         print(f"Error fetching login path: {e}")
#         return None

# ******************* APPEND ITEM(S) TO TABLE ********************
def sql_mri_tracking_insert(subject: str, session: str, project: str, date: str, all_data: bool=None, number_checks: int=0, scan_start_time: str=None, scan_end_time: str=None, arrival_time: str=None, departure_time: str=None, scheduled_duration: str=None, scan_duration: str=None, charged_time: str=None, direct_fee: str=None, table: str='mri_tracking'):
    """
    insert new row into the SQL table for mri usage tracking

    Parameters
    ----------
    subject : str
        unique subject identifier in bids format (sub-XXX)
    session : str
        session identifier in bids format (ses-YYY)
    project : str
        project identifier
    date : str
        date in format '%Y-%m-%d' (YYYY-MM-DD)
    all_data : bool, optional
        flag to indicate all project scans exist in rawdata upon transfer checking, by default None
    number_checks : int, optional
        count of the number of transfer checks performed, by default 0
    scan_start_time : str, optional
        time the scans started for this session (HH:MM:SS), by default None
    scan_end_time : str, optional
        time the scans ended for this session (HH:MM:SS), by default None
    arrival_time : str, optional
        subject arrival time for this session (HH:MM:SS), by default None
    departure_time : str, optional
        subject departure time for this session (HH:MM:SS), by default None
    scheduled_duration : str, optional
        scheduled duration (HH:MM:SS), by default None
    scan_duration : str, optional
        scan duration (HH:MM:SS), by default None
    charged_time : str, optional
        time scanner was occupied (HH:MM:SS), by default None
    direct_fee : str, optional
        direct fees charged for this scan, by default None
    table : str, optional
        mysql table name for MRI tracking, by default 'mri_tracking'
    """
    
    #connect to sql database
    try:
        sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',st.creds.database,False)
        sqlCursor = sqlConnection.cursor()

        if sql_check_table_exists(sqlCursor,table):
            uid = generate_unique_id(subject, session, date)
            sqlCMD =f"INSERT INTO `{table}` (uuid, subject, session, project, date, all_data, number_checks, scan_start_time, scan_end_time, arrival_time, departure_time, scheduled_duration, scan_duration, charged_time, direct_fee) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            # print(sqlCMD)
            sqlCursor.execute(sqlCMD, (uid, subject, session, project, date, all_data, number_checks, scan_start_time, scan_end_time, arrival_time, departure_time, scheduled_duration, scan_duration, charged_time, direct_fee))
        
        # commit changes and close connection
        sqlConnection.commit()
        sqlConnection.close()
    except pymysql.err.IntegrityError as e:
        print(f"ERROR: Skipping duplicate: {e}")
    
    
# ******************* APPEND ITEM(S) TO TABLE ********************
def sql_mri_tracking_set(entries: pd.DataFrame, table: str='mri_tracking'):
    """
    This function inserts entry(ies) into the specified table.

    Parameters
    ----------
    entries : pd.DataFrame
        dataframe containing the table elements of the item(s) to update
    table : str, optional
        target table in the database, by default 'mri_tracking'
    """    
    #connect to sql database
    sqlConnection = create_mysql_connection('10.11.0.31','ubuntu','neuroscience',st.creds.database,False)
    sqlCursor = sqlConnection.cursor()

    cols_to_fix = ['scan_start_time','scan_end_time','arrival_time','departure_time','scheduled_duration','scan_duration','charged_time']
    entries = entries.copy()  # make sure it’s independent

    for col in cols_to_fix:
        # cast column to object so it can hold strings
        if col in entries.columns:
            entries[col] = entries[col].astype(object).apply(fix_time_str)
    

    if sql_check_table_exists(sqlCursor,table) and 'uuid' in entries.columns:
        for _, row in entries.iterrows():
            # Columns to update (exclude UUID)
            update_cols = [col for col in entries.columns if col != 'uuid']
            
            # Build the SET clause dynamically
            set_clause = ', '.join([f"{col} = %s" for col in update_cols])
            
            # Values to update, plus the UUID for the WHERE clause
            values = tuple(row[col] for col in update_cols) + (row['uuid'],)
            
            sqlCmd = f"UPDATE {table} SET {set_clause} WHERE uuid = %s"
            # parts = sqlCmd.split(", ")
            # for part in parts:
            #     print(part + ",")  # keep commas
            sqlCursor.execute(sqlCmd, values)

    else:
        print(f"WARNING: did not update the table {table} - does not exists or uuid not in entries")    
    
    # commit changes and close connection
    sqlConnection.commit()
    sqlConnection.close()


def generate_unique_id(subject: str, session: str, date: str) -> str:
    """
    Generates a unique ID by combining a subject number, session number,
    and date.

    Parameters
    ----------
    subject : str
        The subject's identifier.
    session : str
        session (str): The session's identifier.
    date : str
        Date of subject/session (YYYY-MM-DD).

    Returns
    -------
    str
        A unique ID string.
    """
    import hashlib
    base_str = f"{subject}-{session}-{date}"
    return hashlib.sha1(base_str.encode()).hexdigest()


# ******************* QUERY FOR DIRECTORIES CONTAINING DICOMS ********************
def sql_mri_tracking_query(returncol: str='*', searchcol: str='date', orderby: str='date', subject: str=None, session: str=None, project: str=None, regex: str=None, year: str=None, month: str=None, day: str=None, table: str='mri_tracking') -> pd.DataFrame:
    """
    Find all items in a MySql table that match the specified search string regex.

    
    Parameters
    ----------
    returncol : str 
        column to return, by default '*'
    searchcol : str
        column to search, by default 'date'
    orderby : str
        column to order the query by, by default 'date'
    subject : str
        restrict the query in the subject column to a specific subject, by default None
    session : str
        restrict the query in the session column to a specific session, by default None
    project : str
        restrict the query in the project column to a specific project, by default None
    regex : str
        string to search the specified column searchcol, by default None
    year : str
        restrict the query in date column to a specific year, by default None
    month : str
        restrict the query in date column to a specific month, by default None
    day : str
        restrict the query in date column to a specific day of the month, by default None
    table : str
        mysql table to query, by default 'mri_tracking'

    Returns
    -------
    pandas.DataFrame
        output dataframe containing all items matching the specified search criteria
    """
    
    #connect to sql database
    sqlConnection = create_mysql_connection(host_name='10.11.0.31',user_name='ubuntu',user_password='neuroscience',db_name=st.creds.database,progress=False)
    sqlCursor = sqlConnection.cursor()


    if sql_check_table_exists(sqlCursor,table):

        #create query
        if regex:
            sqlQuery = """SELECT %s FROM %s WHERE %s REGEXP "%s" """ % (returncol,table,searchcol,regex)
            if subject:
                sqlQuery +=  """and subject = "%s" """ % (subject)
            if session:
                sqlQuery +=  """and session = "%s" """ % (session)
            if project:
                sqlQuery +=  """and project = "%s" """ % (project)

            sqlQuery += "ORDER BY %s;" % (orderby)
        elif year or month:
            sqlQuery = """SELECT %s FROM %s WHERE """ % (returncol,table)
            if year:
                sqlQuery +=  "YEAR(date) = %s " % (year)
            if month:
                if year:
                    sqlQuery += "and "
                sqlQuery +=  "MONTH(date) = %s " % (month)
            if day:
                if year or month:
                    sqlQuery += "and "
                sqlQuery +=  "DAY(date) = %s " % (day)
            if subject:
                sqlQuery +=  """and subject = "%s" """ % (subject)
            if session:
                sqlQuery +=  """and session = "%s" """ % (session)
            if project:
                sqlQuery +=  """and project = "%s" """ % (project)
            sqlQuery += "ORDER BY %s;" % (orderby)
        elif isinstance(regex, bool):
            sqlQuery = "SELECT %s FROM %s WHERE %s = %s and number_checks > 5 " % (returncol,table,searchcol,regex)
            if subject:
                sqlQuery +=  """and subject = "%s" """ % (subject)
            if session:
                sqlQuery +=  """and session = "%s" """ % (session)
            if project:
                sqlQuery +=  """and project = "%s" """ % (project)
            sqlQuery += "ORDER BY %s;" % (orderby)

    else:
        sqlConnection.close()
        columns = [desc[0] for desc in sqlCursor.description]
        df = pd.DataFrame(columns=columns)
        return df
    
    # run quory
    # print(sqlQuery)
    sqlCursor.execute(sqlQuery)
    # Get column names
    columns = [desc[0] for desc in sqlCursor.description]

    # Convert to DataFrame
    rows = sqlCursor.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    sqlConnection.close()

    #get sql returned list
    return df