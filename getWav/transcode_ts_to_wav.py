import datetime as dt
from pipeline import NoiseAnalysisPipeline
from hydrophone import Hydrophone
'''
    Extract ts segments for selected time interval and save as wav files
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
'''
wavDir = "/home/val/Documents/8_17_23_15:00_jkl_tst/"

pipeline = NoiseAnalysisPipeline(Hydrophone.ORCASOUND_LAB, pqt_folder='pqt', delta_f=10, bands=3, delta_t=1, no_auth=True)

pipeline.get_wav_files(wavDir, dt.datetime(2023, 8, 22, 12, 15), dt.datetime(2023, 8, 22, 12, 18))

