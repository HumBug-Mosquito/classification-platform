import logging
import os
import pprint
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np
import torch
from bson.objectid import ObjectId
from pymongo import MongoClient

from audio_recording import AudioRecording, AudioRecordingDatabaseObject
from config import Config


class DescriptiveError(Exception):
    def __init__(self,id: str, error: str,description: str, status_code: int):
        self.id = id
        self.error = error
        self.description = description
        self.status_code = status_code
        super().__init__(description)

class RecordingNotFoundInDatabaseError(DescriptiveError):
    def __init__(self, recording_id: str):
        super( ).__init__(
            "recording_not_found",
            "Recording not found in database",
            "Could not find a recording in the database with id: {0}.".format(recording_id),
            404
        )

class AudioFileNotFoundError(DescriptiveError):
    def __init__(self):
        super().__init__(
            "audio_file_not_found",
            "Audio file not found",
            "Could not find a recording file at the path provided by the database object.",
            404
        )

class LoadingAudioBytesError(DescriptiveError):
    def __init__(self, error: Exception):
        super().__init__(
            "loading_audio_bytes_error",
            "Failed to load audio bytes",
            error.__str__(),
            500
        )

# The AudioDataSource class is a representation of the data source
# that is used to fetch audio recordings from the database.
class AudioDataSource:

    effects = [["remix", "1"],['gain', '-n'],["highpass", "200"]]

    def __init__(self, database: MongoClient):
        self.logger = logging.getLogger('main')
        self.database = database

    # Fetch an audio recording from the database given the id of the recording.
    #
    # Throws the following exceptions:
        # - RecordingNotFoundInDatabaseError: if the recording was not found in the database.
        # - AudioFileNotFoundError: if the audio file was not found at the path of the recording entry in the database.
        # - LoadingAudioBytesError: if there was an error loading the audio bytes for the recording, where the audio file can be found.
    def fetch(self, id: str) :

        # Fetch the audio recording from the database.
        database_object: AudioRecordingDatabaseObject = self.fetch_audio_recording_from_database(id)
        self.logger.debug("Database object found {0}".format(database_object))

        # Use the database object to load the recording.
        self.logger.debug("Loading audio recording from the path provided by the database object ... ")
        audio_bytes, rate = self.load_audio_bytes_for_recording(database_object)

        return AudioRecording(id=database_object.id, path=database_object.path, bytes=audio_bytes, datetime_recorded=database_object.datetime_recorded, sample_rate=rate)

    def fetch_audio_recording_from_database(self, id: str) -> AudioRecordingDatabaseObject:
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
        
    def load_med_output_for_recording(self, recording: AudioRecording, config: Config = Config.default()) -> np.ndarray:

        path = Path(os.environ['CLASSIFICATION_OUTPUT_DIR'],f'{recording.id}.wav')
        self.logger.debug("Loading audio file with path: {0}".format(path))
        try:
            signal, _ = librosa.load(path, sr=recording.sample_rate)
            return signal
        
        except FileNotFoundError:
            self.logger.error("Couldn't locate MED audio file, make sure MED has been performed before MSC".format(path))
            raise AudioFileNotFoundError()
        except Exception as e:
            self.logger.error("Failed to load the audio bytes for the recording.")
            self.logger.error("{0}. Reason: {1}".format(type(e),e))
            raise LoadingAudioBytesError(e)


    def load_audio_bytes_for_recording(self, audio_recording_database_object: AudioRecordingDatabaseObject) ->  Tuple[np.ndarray , float]:

        # Load the audio bytes from the file path.
        path = audio_recording_database_object.path.replace("data/MozzWear/", "")
        self.logger.debug("Loading audio file with path: {0}".format(path))
        try:
            signal, sr = librosa.load(audio_recording_database_object.path, sr=8000)
            print(signal)

            return np.array([signal]), sr
            # return torch.Tensor(signal).unsqueeze(0).float().numpy(), sr

        except FileNotFoundError:
            self.logger.error("Couldn't locate the audio file at the path {0}".format(path))
            raise AudioFileNotFoundError()
        except Exception as e:
            self.logger.error("Failed to load the audio bytes for the recording.")
            self.logger.error("{0}. Reason: {1}".format(type(e),e))
            raise LoadingAudioBytesError(e)
