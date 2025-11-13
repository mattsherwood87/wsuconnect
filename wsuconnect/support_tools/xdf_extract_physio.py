#!/resshare/python3_venv/bin/python

from pathlib import Path
import datetime as dt
import pandas as pd
import pyxdf
import re
import os
from zoneinfo import ZoneInfo
from pprint import pprint

# XDF_PATH   = Path( "/home/nw036cjc/WORKSPACE/PhilipsLogParser/original/20240100H_sub-321104_ses-01_desc-lsl_beh.xdf" )
# PHILIPS_LOG_PATH = Path( "/home/nw036cjc/WORKSPACE/PhilipsLogParser/original/sub-321104_ses-01_philips-scan-log.csv" )
#OUTDIR     = Path( "/home/nw036cjc/WORKSPACE/PhilipsLogParser/out" )

OUTDIR     = Path( "./out" )
# OUTDIR.mkdir( parents=True , exist_ok=True )

EXCLUDE  = [ "Survey" , "Scan Complete" ,"CDAS" , "New Exam" ,"Start Button" , "Dynamic" ]
INCLUDE  = [ "Keyboard" ,"psychopyStream" , "SerialPort" ]
TERM     = ",X,0.0\r\n"


def _slugify(text):
	# text = text.lower()
	text = re.sub( r'\s+', '_', text )
	text = text.strip( '_' )
	return text


def _load_xdf( input_path_posix ):
	data , header = pyxdf.load_xdf( str( input_path_posix ) )
	result = {}
	for i , stream in enumerate( data ):
		l_name = stream.get( "info" , {} ).get( "name" )
		if not l_name or not isinstance( l_name , list ) or len( l_name ) < 1 or l_name[ 0 ] not in INCLUDE:
			continue
		result[ l_name[ 0 ] ] = stream
	return result


def _df_keyboard( stream ):
	return pd.DataFrame({
		"val": [ x[ 0 ] for x in stream[ "time_series" ] ] ,
		"lsl": stream[ "time_stamps" ] ,
	})


def _df_serial( stream , terminator=TERM ):
	buf, rows = "" , []
	sample = terminator
	for raw , ts in zip( stream[ "time_series" ] , stream[ "time_stamps" ] ):
		char = chr( int( raw[ 0 ] ) )
		if sample == terminator:
			buf += f"{ts:.10f}," # prepend LSL time once per sample
		buf += char
		sample = ( sample + char )[ -len( terminator ) : ]
		if sample == terminator:
			rows.append( buf.split( "," )[ :-1 ] ) # drop empty tail after split
			buf = ""
	df = pd.DataFrame( rows )
	df.rename( columns={ 0: "lsl" } , inplace=True )
	df[ "lsl" ] = df[ "lsl" ].astype( float )
	return df


def _get_mri_start_stop_times( df_mri, dynamic_exclusion ):
	result = []
	code = None
	first_dynamic_time = None
	for i , row in df_mri.iterrows():
		# ['Unnamed: 0', 'date', 'time', 'project', 'marker', 'event']
		if not any(keyword in row[ "marker"] for keyword in ['Scan Complete','CDAS','New Exam','Start Button','Dynamic']):
			code = row[ "marker"]

		if row[ "marker" ] != "Scan Complete":
			continue
		item = {
			"label": "" ,
			"start": {
				"date": None ,
				"time": None ,
			} ,
			"stop": {
				"date": row[ "date" ],
				"time": row[ "time" ],
			}
		}
		j = i - 1
		while j > -1:
			test = df_mri.loc[ j , "marker" ]
			if test == "Dynamic 1" or test == "CDAS Scan Starts":
				item[ "start" ][ "date" ] = df_mri.loc[ j , "date" ]
				item[ "start" ][ "time" ] = df_mri.loc[ j , "time" ]
				item[ "label" ] = code
				if dynamic_exclusion:
					if not first_dynamic_time and test == "Dynamic 1" and "fmri" in code.lower() and not dynamic_exclusion in code.lower():
					# if not first_dynamic_time and test == "Dynamic 1" and "fmri" in code.lower():
						first_dynamic_time = item["start"]["time"]
					break
				else:
					if not first_dynamic_time and test == "Dynamic 1" and "fmri" in code.lower():# and not "rsfmri" in code.lower():
					# if not first_dynamic_time and test == "Dynamic 1" and "fmri" in code.lower():
						first_dynamic_time = item["start"]["time"]
					break
			else:
				j = j - 1
		result.append( item )
	return first_dynamic_time, result

def _get_file_name(philips_file):
	parts = os.path.basename(philips_file).split( '_' )
	subject_session = '_'.join( parts[ : 2 ])
	return subject_session


def xdf_extract_physio(xdf_file: str, philips_file: str, out_dir: Path, overwrite: bool=False, dynamic_exclusion: str = None, ):
	OUTDIR.mkdir( parents=True , exist_ok=True )

	mri = pd.read_table( philips_file , sep="," , skiprows=0 , skip_blank_lines=True )
	streams = _load_xdf( xdf_file )
	keyboard = _df_keyboard( streams[ "Keyboard" ] )
	physiology = _df_serial( streams[ "SerialPort" ] )

	first_mri_time, start_stop_times = _get_mri_start_stop_times( mri, dynamic_exclusion )
	print( "Start and Stop Times :" )
	pprint( start_stop_times )

	first_mri_time = dt.datetime.strptime(
		f"{first_mri_time}" , "%H:%M:%S.%f"
	).replace( tzinfo=ZoneInfo( "America/New_York" ) )
	print( "First MRI Time ===" , first_mri_time )


#Handle weird stuff for rsfmri on 20240100H
	# next_event = keyboard['val'].shift(-1)

	# # Condition: RETURN released followed by 1 pressed
	# mask = (keyboard['val'] == "RETURN released") & (next_event == "1 pressed")
	# idx = keyboard.index[mask].tolist()[0]

	sub_df = keyboard
	# next_event = sub_df['val'].shift(-1)
	# mask = (sub_df['val'] == "RETURN released") & (next_event == "PLUS pressed")
	mask = (sub_df['val'] == "PLUS pressed")
	idx = sub_df.index[mask].tolist()[0]
	# first_keyboard_time = sub_df['lsl'].loc[idx+1]
	first_keyboard_time = sub_df['lsl'].loc[idx]

	mask = (sub_df['val'] == "PLUS pressed")
	idx = sub_df.index[mask].to_list()
	TR = sub_df['lsl'].loc[idx[1]] - sub_df['lsl'].loc[idx[0]]
	print(f"Repetition Time (TR) = {TR}s")

	# first_keyboard_time = keyboard['lsl'][keyboard['val'] == 'PLUS pressed'].iloc[0] #get first TR emulated keypress
	# first_keyboard_time = keyboard[ "lsl" ].iloc[ 0 ]
	print( "First Keyboard Time ===" , first_keyboard_time )

	clock_delta = first_mri_time.timestamp() - first_keyboard_time
	print( "Clock Delta ===" , clock_delta )

	first_mri_time_lsl = first_mri_time.timestamp() - clock_delta
	print( "First MRI as LSL ===" , first_mri_time_lsl )

	# build and add column of lsl equivalent times
	mri_lsl_times = []
	for i , row in mri.iterrows():
		nyc_time = dt.datetime.strptime(
			f"{row['time']}" , "%H:%M:%S.%f"
		).replace( tzinfo=ZoneInfo( "America/New_York" ) )
		lsl_time = nyc_time.timestamp() - clock_delta
		mri_lsl_times.append( lsl_time )
	mri.insert( 3 , "lsl" , mri_lsl_times )
	# pprint( mri )


	#get basename for output files and save keyboard CSV
	out_file_name_part = _get_file_name(philips_file)
	if not out_dir.joinpath(f"{out_file_name_part}_keyboard.csv").exists or overwrite:
		keyboard.to_csv(out_dir.joinpath(f"{out_file_name_part}_keyboard.csv"))

	for i , session in enumerate( start_stop_times ):
		_i = str(i+1).zfill( 3 )
		out_file_path = out_dir.joinpath( f"{out_file_name_part}_{_i}_{_slugify(session['label'])}.csv" )

		start_time = dt.datetime.strptime(
			f"{session['start']['time']}" , "%H:%M:%S.%f"
		).replace( tzinfo=ZoneInfo( "America/New_York" ) )
		start_lsl_time = start_time.timestamp() - clock_delta
		print(f"{_slugify(session['label'])}")
		print(f"\tStart Time: \n\t{start_time}\n\t{start_lsl_time}")

		stop_time = dt.datetime.strptime(
			f"{session['stop']['time']}" , "%H:%M:%S.%f"
		).replace( tzinfo=ZoneInfo( "America/New_York" ) )
		stop_lsl_time = stop_time.timestamp() - clock_delta
		print(f"\tStop Time: \n\t{stop_time}\n\t{stop_lsl_time}")

		# pprint(physiology)
		physiology_filtered = physiology[ ( physiology[ "lsl" ] >= start_lsl_time ) & ( physiology[ "lsl" ] <= stop_lsl_time ) ].copy()
		physiology_filtered["mri"] = physiology_filtered["lsl"] + clock_delta
		physiology_filtered["mri"] = physiology_filtered["mri"].apply(
			lambda ts: dt.datetime.fromtimestamp(ts, tz=ZoneInfo("America/New_York"))
		)
		# pprint(physiology_filtered)

		if not out_file_path.exists or overwrite:
			print("\tWriting: " , str( out_file_path ) )
			out_dir.mkdir( parents=True , exist_ok=True )
			physiology_filtered.to_csv( str( out_file_path ) , index=False )
		else:
			print("\tOutput exists - skipping...")
