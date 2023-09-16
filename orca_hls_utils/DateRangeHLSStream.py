import math
import os
import shutil

# import sys
import time
from datetime import datetime  # , timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import logging

import ffmpeg
import m3u8

# from botocore import UNSIGNED
# from botocore.config import Config
from pytz import timezone

from . import datetime_utils, s3_utils, scraper


def get_readable_clipname(hydrophone_id, cliptime_utc):
    # cliptime is of the form 2020-09-27T00/16/55.677242Z
    cliptime_utc = timezone("UTC").localize(cliptime_utc)
    date = cliptime_utc.astimezone(timezone("US/Pacific"))
    date_format = "%Y_%m_%d_%H_%M_%S_%Z"
    clipname = date.strftime(date_format)
    return hydrophone_id + "_" + clipname, date


# TODO: Handle date ranges that don't exist
class DateRangeHLSStream:
    """
    stream_base = 'https://s3-us-west-2.amazonaws.com/streaming-orcasound-net/rpi_orcasound_lab' # noqa
    polling_interval = 60 sec
    start_unix_time
    end_unix_time
    wav_dir
    overwrite_output: allows ffmpeg to overwrite output, default is False
    quiet_ffmpeg: Passed to ffmpeg.run quiet argument. Set true to print ffmpeg logs to stdout and stderr
    real_time: if False, get data as soon as possible, if true wait for
                polling interval before pulling
    """

    def __init__(
        self,
        stream_base,
        polling_interval,
        start_unix_time,
        end_unix_time,
        wav_dir,
        overwrite_output=False,
        quiet_ffmpeg=False,
        real_time=False,
    ):
        """ """

        self.logger = logging.getLogger("DateRangeHLSStream")

        # Get all necessary data and create index
        self.stream_base = stream_base
        self.polling_interval_in_seconds = polling_interval
        self.start_unix_time = start_unix_time
        self.end_unix_time = end_unix_time
        self.wav_dir = wav_dir
        self.overwrite_output = overwrite_output
        self.real_time = real_time
        self.is_end_of_stream = False
        self.quiet_ffmpeg = quiet_ffmpeg

        # Create wav dir if necessary
        Path(self.wav_dir).mkdir(parents=True, exist_ok=True)

        # query the stream base for all m3u8 files between the timestamps

        # split the stream base into bucket and folder
        # eg.
        # 'https://s3-us-west-2.amazonaws.com/streaming-orcasound-net/rpi_orcasound_lab' # noqa
        # would be split into s3_bucket = 'streaming-orcasound-net' and
        # folder_name = 'rpi_orcasound_lab'

        bucket_folder = self.stream_base.split(
            "https://s3-us-west-2.amazonaws.com/"
        )[1]
        tokens = bucket_folder.split("/")
        self.s3_bucket = tokens[0]
        self.folder_name = tokens[1]
        prefix = self.folder_name + "/hls/"

        # returns folder names corresponding to epochs, this grows as more
        # data is added, we should probably maintain a list of
        # hydrophone folders that exist
        all_hydrophone_folders = s3_utils.get_all_folders(
            self.s3_bucket, prefix=prefix
        )
        self.logger.info(
            "Found {} folders in all for hydrophone".format(
                len(all_hydrophone_folders)
            )
        )

        self.valid_folders = s3_utils.get_folders_between_timestamp(
            all_hydrophone_folders, self.start_unix_time, self.end_unix_time
        )
        self.logger.info("Found {} folders in date range".format(len(self.valid_folders)))

        self.current_folder_index = 0
        self.current_clip_start_time = self.start_unix_time

    def get_next_clip(self, current_clip_name=None):
        # Get current folder
        current_folder = int(self.valid_folders[self.current_folder_index])
        (
            clipname,
            clip_start_time,
        ) = datetime_utils.get_clip_name_from_unix_time(
            self.folder_name.replace("_", "-"), self.current_clip_start_time
        )

        # if real_time execution mode is specified
        if self.real_time:
            # sleep till enough time has elapsed

            now = datetime.utcnow()
            time_to_sleep = (current_clip_name - now).total_seconds()

            if time_to_sleep < 0:
                self.logger.warning("Issue with timing")

            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

        # read in current m3u8 file
        # stream_url for the current AWS folder
        stream_url = "{}/hls/{}/live.m3u8".format(
            (self.stream_base), (current_folder)
        )
        stream_obj = m3u8.load(stream_url)
        num_total_segments = len(stream_obj.segments)
        if num_total_segments == 0:
            self.current_folder_index += 1
            self.current_clip_start_time = self.valid_folders[
                self.current_folder_index
            ]
            return None, None, None
        target_duration = (
            sum([item.duration for item in stream_obj.segments])
            / num_total_segments
        )
        num_segments_in_wav_duration = math.ceil(
            self.polling_interval_in_seconds / target_duration
        )

        # calculate the start index by computing the current time - start of
        # current folder
        segment_start_index = math.ceil(
            datetime_utils.get_difference_between_times_in_seconds(
                self.current_clip_start_time, current_folder
            )
            / target_duration
        )
        segment_end_index = segment_start_index + num_segments_in_wav_duration

        if segment_end_index > num_total_segments:
            if self.current_folder_index + 1 >= len(self.valid_folders):
                # Something went wrong, we'll just return the current data
                self.logger.warn("Missing data, returning truncated file.")
                self.logger.debug(f"Start index is {segment_start_index}")
                self.logger.debug(f"Adjusting end index from {segment_end_index} to {num_total_segments}")
                segment_end_index = num_total_segments
                if segment_end_index < segment_start_index:
                    self.logger.warn("No data found")
                    self.current_clip_start_time = self.end_unix_time
                    return None, None, None
            else:
                # move to the next folder and increment the
                # current_clip_start_time to the new
                self.current_folder_index += 1
                self.current_clip_start_time = self.valid_folders[
                    self.current_folder_index
                ]
                return None, None, None

        # Can get the whole segment so update the clip_start_time for the next
        # clip
        # We do this before we actually do the pulling in case there is a
        # problem with this clip
        self.current_clip_start_time = (
            datetime_utils.add_interval_to_unix_time(
                self.current_clip_start_time, self.polling_interval_in_seconds
            )
        )

        # Create tmp path to hold .ts segments
        with TemporaryDirectory() as tmp_path:
            os.makedirs(tmp_path, exist_ok=True)

            file_names = []
            for i in range(segment_start_index, segment_end_index):
                audio_segment = stream_obj.segments[i]
                base_path = audio_segment.base_uri
                file_name = audio_segment.uri
                audio_url = base_path + file_name
                try:
                    scraper.download_from_url(audio_url, tmp_path)
                    file_names.append(file_name)
                    self.logger.debug(f"Adding file {file_name}")
                except Exception:
                    self.logger.warning("Skipping", audio_url, ": error.")

            # concatentate all .ts files
            self.logger.info(f"Files to concat = {file_names}")
            hls_file = os.path.join(tmp_path, Path(clipname + ".ts"))
            with open(hls_file, "wb") as wfd:
                for f in file_names:
                    with open(os.path.join(tmp_path, f), "rb") as fd:
                        shutil.copyfileobj(fd, wfd)

            # read the concatenated .ts and write to wav
            audio_file = clipname + ".wav"
            wav_file_path = os.path.join(self.wav_dir, audio_file)
            stream = ffmpeg.input(os.path.join(tmp_path, Path(hls_file)))
            stream = ffmpeg.output(stream, wav_file_path)
            try:
                ffmpeg.run(
                    stream, overwrite_output=self.overwrite_output, quiet=self.quiet_ffmpeg
                )
            except Exception as e:
                shutil.copyfile(hls_file, "ts/badfile.ts")
                raise e

        # If we're in demo mode, we need to fake timestamps to make it seem
        # like the date range is real-time
        if current_clip_name:
            clipname, _ = get_readable_clipname(
                self.folder_name.replace("_", "-"), current_clip_name
            )

            # rename wav file
            full_new_clip_path = os.path.join(self.wav_dir, clipname + ".wav")
            os.rename(wav_file_path, full_new_clip_path)
            wav_file_path = full_new_clip_path

            # change clip_start_time - this has to be in UTC so that the email
            # can be in PDT
            clip_start_time = current_clip_name.isoformat() + "Z"

        # Get new index
        return wav_file_path, clip_start_time, current_clip_name

    def is_stream_over(self):
        # returns true or false based on whether the stream is over
        return int(self.current_clip_start_time) >= int(self.end_unix_time)
