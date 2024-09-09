import threading
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
import torch
from pymongo import MongoClient

from lib.config import Config
from lib.med.event_detector import EventDetector
from lib.msc.species_classifier import SpeciesClassifier
from lib.storage.recording_storage import RecordingStorage
from lib.types import Environment


class Classifier:
    recording_storage: RecordingStorage
    event_detector: EventDetector
    species_classifier: SpeciesClassifier
    environment: Environment
    
    def __init__(self, environment: Environment):
        self.environment = environment
        self.data_source = RecordingStorage(environment.database_url)
        self.species_classifier = SpeciesClassifier()
        self.event_detector = EventDetector(model_path=environment.event_detector_model_path)
    
    def med_recording(
        self, 
        recording_id: str, 
        abort_signal: threading.Event | None = None,
        send_update_to_client: Callable[[float, str], None] | None = None,
        config: Config = Config.default()
    ) -> str:
        # Fetch the recording
        recording = self.data_source.fetch(recording_id, config)
        
        # Detect events in the recording
        events = self.event_detector.detect(recording.bytes, send_update_to_client, abort_signal)
        
        timestamp_df = events.get_data_frame_with_recording(config, recording)
        path_to_outputs = Path(self.environment.output_dir)
        wav_file_name = Path(path_to_outputs, f"{str(recording.id)}.wav")
        
        signal = recording.bytes.numpy()
        
        mozz_audio_list = [signal[0][int(float(row["med_start_time"]) * recording.sample_rate):int(float(row["med_stop_time"]) * recording.sample_rate)] for _, row in timestamp_df.iterrows()]
        sf.write(Path( wav_file_name), np.hstack(mozz_audio_list), recording.sample_rate)
        output_path = Path(path_to_outputs,f"{str(recording.id)}.csv")
        path_to_med_df = Path(path_to_outputs,f'{recording.id}.csv' )
        timestamp_df.to_csv(path_to_med_df, index=False)
        return timestamp_df,output_path
    
    def msc_recording(self, recording_id: str , config: Config = Config.default()) -> str:
        pass
        
    def med(self, bytes: np.ndarray, send_update_to_client: Callable[[float, str], None] | None = None, abort_signal: threading.Event | None = None ) -> str:
        return self.event_detector.detect(torch.FloatTensor(bytes), send_update_to_client, abort_signal)

    
    # def msc(self, bytes: np.ndarray, send_update_to_client: Callable[[float, str], None] | None = None, abort_signal: threading.Event | None = None, config: Config = Config.default()) -> str:
    #     events = self.event_detector.detect(torch.FloatTensor(bytes), send_update_to_client, abort_signal)
    #     data_frame = events.get_data_frame(config)
        
        
        