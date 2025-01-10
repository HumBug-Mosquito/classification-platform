import threading
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
import torch

from lib.config import Config
from lib.custom_types import (DetectedEvents, Environment,
                              SpeciesClassificationResponse)
from lib.med.event_detector import EventDetector
from lib.msc.species_classifier import SpeciesClassifier
from lib.storage.recording_storage import RecordingStorage
from lib.utils import get_audio_with_events, prepare


class Classifier:
    recording_storage: RecordingStorage
    event_detector: EventDetector
    species_classifier: SpeciesClassifier
    environment: Environment

    def __init__(self, environment: Environment):
        print("Initializing classifier with Environment: ", environment.__str__())
        self.environment = environment
        self.data_source = RecordingStorage(environment.database_url)
        self.species_classifier = SpeciesClassifier(model_path=environment.species_classifier_model_path)
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

    def med(self, bytes: np.ndarray, send_update_to_client: Callable[[float, str], None] | None = None, abort_signal: threading.Event | None = None, config: Config = Config.default() ) -> DetectedEvents:
        return self.event_detector.detect(torch.FloatTensor(prepare(bytes, config)), send_update_to_client, abort_signal)

    def msc(self, bytes: np.ndarray, send_update_to_client: Callable[[float, str], None] | None = None, abort_signal: threading.Event | None = None, config: Config = Config.default()) -> SpeciesClassificationResponse:

        print("Detecting events first")
        events = self.med(bytes, send_update_to_client, abort_signal)        
        if not events.has_events(detect_threshold=config.det_threshold):
            return SpeciesClassificationResponse.no_events_detected(events, self.species_classifier.model_checkpoint)

        print("detected events! ")
        events_audio = get_audio_with_events(bytes, events, config)
        return self.species_classifier.classify(torch.FloatTensor(events_audio), send_update_to_client=send_update_to_client,detected_events=events, abort_signal=abort_signal, config=config)    

