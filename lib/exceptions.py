
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

class UserCancelledError(Exception):
    pass