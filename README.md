# ts_audio_downloader
Run python script: <B>transcode_ts_to_wav.py</B> in the transcode_ts directory

Gather ts audio segments from selected datetime range and download to local computer as wav files.

    Extract ts segments for selected time interval and save on local computer as wav files
    Code is extracted from https://github.com/orcasound/ambient-sound-analysis
    The procedure get_wav_files was added to the students' pipeline
        Note that pipeline.py, hydrophone.py, file_connector.py and acoustic_util.py are stored in this folder
    Thanks go Dr. Valentina Staneva and her U W Masters students:  
        Caleb Case
        Mitch Haldeman
        Grant Savage
    Make sure that the needed dependencies are installed  pip install -r requirements.txt    
        or by running python3 -m pip install xxxx  for each library in the requirements.txt file
    Specify directory for the wav files and start/stop datetimes

    There is often a few hours delay before this program can access the very recent segments.
    I (Val) am guessing that some database of S3 bucket files is not updated too frequently.


