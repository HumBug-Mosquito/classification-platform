import datetime
import os
import pprint

import numpy as np
from bson.objectid import ObjectId


# An AudioRecording is a representation of an audio recording that has been fetched from the database.
# This has the following properties:
# - id: a unique identifier for the audio recording fetched from the database.
# - path: the path of the audio recording.
# - bytes: the audio recording in bytes.
# - datetime_recorded: the date and time the audio recording was recorded.
class AudioRecording:
    def __init__(self, id, path, bytes:  np.ndarray, datetime_recorded: datetime.datetime, sample_rate: int = 8000):
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
            path = os.path.join(os.path.dirname(__file__), '../test_audio_on_off.wav')
        else:
            path = os.path.join(os.path.dirname(__file__), '../test_no_presence.wav')

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
