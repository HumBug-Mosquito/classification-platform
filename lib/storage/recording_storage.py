import datetime
import logging
import os
from typing import Tuple

import librosa
import numpy as np
import torch
from bson.objectid import ObjectId
from pymongo import MongoClient

from lib.config import Config
from lib.exceptions import (AudioFileNotFoundError, LoadingAudioBytesError,
                            RecordingNotFoundInDatabaseError)
from lib.utils import pad_mean


# An AudioRecording is a representation of an audio recording that has been fetched from the database.
# This has the following properties:
# - id: a unique identifier for the audio recording fetched from the database.
# - path: the path of the audio recording.
# - bytes: the audio recording in bytes.
# - datetime_recorded: the date and time the audio recording was recorded.
class AudioRecording:
    bytes: torch.FloatTensor
    sample_rate: int
    datetime_recorded: datetime.datetime
    id: ObjectId
    path: str


    def __init__(self, id, path, bytes:  torch.FloatTensor, datetime_recorded: datetime.datetime, sample_rate: int = 8000):
        self.id = id
        self.path = path
        self.sample_rate = sample_rate
        self.bytes = bytes
        self.datetime_recorded = datetime_recorded  # type: datetime.datetime

# An AudioRecordingDatabaseObject is the data that is fetched from the database given the id of an audio recording.
class AudioRecordingDatabaseObject:
    def __init__(self, id: ObjectId, path: str, datetime_recorded: datetime.datetime):
        self.id = id
        self.path = path
        self.datetime_recorded = datetime_recorded

    @staticmethod
    def test(presence: bool = True):
        if (presence):
            path = os.path.join(os.path.dirname(__file__), './test_audio_on_off.wav')
        else:
            path = os.path.join(os.path.dirname(__file__), './test_no_presence.wav')

        return AudioRecordingDatabaseObject(
            id=ObjectId("55cb4efb7cdf33532641047d"),
            path=path,
            datetime_recorded=datetime.datetime.now()
        )

    @staticmethod
    def fromJson(json: dict):
        id = ObjectId(json["_id"])
        return AudioRecordingDatabaseObject(
            id=id,
            path=json.get('path').__str__(),
        )


class RecordingStorage:
    effects = [["remix", "1"],['gain', '-n'],["highpass", "200"]]

    def __init__(self, database_url: str):
        self.logger = logging.getLogger('recording_storage')
        self.database = MongoClient(database_url)

    # Fetch an audio recording from the database given the id of the recording.
    #
    # Throws the following exceptions:
        # - RecordingNotFoundInDatabaseError: if the recording was not found in the database.
        # - AudioFileNotFoundError: if the audio file was not found at the path of the recording entry in the database.
        # - LoadingAudioBytesError: if there was an error loading the audio bytes for the recording, where the audio file can be found.
    def fetch(self, id: str, config: Config = Config.default()) -> AudioRecording:

        # Fetch the audio recording from the database.
        database_object: AudioRecordingDatabaseObject = self._fetch_audio_recording_from_database(id)
        self.logger.debug("Database object found {0}".format(database_object))

        # Use the database object to load the recording.
        self.logger.debug("Loading audio recording from the path provided by the database object ... ")
        audio_bytes, rate = self._load_audio_bytes_for_recording(database_object)
        
        audio_bytes = self._ensure_min_length(audio_bytes, min_length=config.single_batch_length())

        batches = self._group_signal_into_batches(audio_bytes, batch_size=config.single_batch_length(), step_size=config.step_size * config.n_hop)

        return AudioRecording(id=database_object.id, path=database_object.path, bytes=batches, datetime_recorded=database_object.datetime_recorded, sample_rate=rate)


    # Queries the database for the audio recording with the given id.
    def _fetch_audio_recording_from_database(self, id: str) -> AudioRecordingDatabaseObject:
        if(id == "test"):
            # Fetch the audio recording from the database.
            return AudioRecordingDatabaseObject.test()
        elif(id == "test_no_presence"):
            # Fetch the audio recording from the database.
            return AudioRecordingDatabaseObject.test(presence=False)

        query = {"_id": ObjectId(id)}
        try:
            result = self.database.backend_upload.reports.find_one(query)
            if result is None:
                raise RecordingNotFoundInDatabaseError(id)

            return AudioRecordingDatabaseObject.fromJson(result)
        except Exception as e:
            self.logger.error("Failed to fetch the audio recording from the database.")
            self.logger.error("Reason: {0}".format(e))
            raise RecordingNotFoundInDatabaseError(id)


    # Load the audio bytes from the file path.
    # Also perform effects on the audio bytes.
    def _load_audio_bytes_for_recording(self, audio_recording_database_object: AudioRecordingDatabaseObject) ->  Tuple[np.ndarray , float]:

        # Load the audio bytes from the file path.
        path = audio_recording_database_object.path.replace("data/MozzWear/", "")
        self.logger.debug("Loading audio file with path: {0}".format(path))
        try:
            signal, sr = librosa.load(audio_recording_database_object.path, sr=8000)
            print(signal)

            return np.array([signal]), sr

        except FileNotFoundError:
            self.logger.error("Couldn't locate the audio file at the path {0}".format(path))
            raise AudioFileNotFoundError()
        except Exception as e:
            self.logger.error("Failed to load the audio bytes for the recording.")
            self.logger.error("{0}. Reason: {1}".format(type(e),e))
            raise LoadingAudioBytesError(e)
        
    def _ensure_min_length(self, signal: np.ndarray, min_length: int):
        if(signal.shape[1] < min_length):
            return torch.FloatTensor(np.array(pad_mean(  signal[0], min_length))).unsqueeze(0)
        
        return torch.FloatTensor(signal)
    
    def _group_signal_into_batches(self, signal: torch.FloatTensor, batch_size: int, step_size: int):
        return signal.unfold(1, batch_size, step_size).transpose(0, 1)