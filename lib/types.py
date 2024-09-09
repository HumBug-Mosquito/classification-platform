import asyncio
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

import numpy as np
import pandas as pd

from lib.config import Config
from lib.storage.recording_storage import AudioRecording


class Environment: 
    database_url: str
    output_dir: str
    event_detector_model_path: str
    def __init__(self, env: dict):
        self.database_url = env.get("DATABASE_URL")
        self.event_detector_model_path = env.get("EVENT_DETECTOR_MODEL_PATH")
        self.output_dir = env.get("CLASSIFICATION_OUTPUT_DIR")

class DetectedEvents:
    def __init__(self, predictions_array: np.ndarray, model: str):
        self.predictions_array = predictions_array
        self.model = model
        
    def get_data_frame(self, config: Config)-> pd.DataFrame:
        predictions_array = self.predictions_array
        predictions_array_samples = np.array([predictions_array[:-4], predictions_array[1:-3], predictions_array[2:-2]])
        mean_predictions = np.mean(predictions_array_samples, axis=0)
        return self._build_timestamp_df(mean_predictions, (config.n_hop * config.step_size / 8000), config.det_threshold)
    
    def get_data_frame_with_recording(self, config: Config, recording: AudioRecording) -> pd.DataFrame:
        predictions_array = self.predictions_array
        predictions_array_samples = np.array([predictions_array[:-4], predictions_array[1:-3], predictions_array[2:-2]])
        mean_predictions = np.mean(predictions_array_samples, axis=0)
        return self._build_timestamp_df(mean_predictions, (config.n_hop * config.step_size / 8000), config.det_threshold, recording)
        

    def _build_timestamp_df(self,mean_predictions, time_to_sample, det_threshold, recording: AudioRecording | None = None) -> pd.DataFrame:
        """Use the predictions to build an array of contiguous timestamps where the
        probability of detection is above threshold"""

        # find where the average 2nd element (positive score) is > threshold
        print(f"mean_predictions: {mean_predictions} ")
        condition = mean_predictions[:, 1] > det_threshold
        preds_list = []
        current_offset = 0
        for start, stop in self._contiguous_regions(condition):
            # start and stop are frame indexes
            # so multiply by n_hop and step_size samples
            # then div by sample rate to get seconds
            start_time = round(start * time_to_sample,2)
            end_time = round(stop * time_to_sample,2)
            preds_list.append({
                "uuid": recording.id if recording else None,
                "datetime_recorded": recording.datetime_recorded if recording else None,
                "med_start_time": str(start_time),
                "med_prob": "{:.4f}".format(np.mean(mean_predictions[start:stop][:, 1])),
                "msc_start_time": current_offset,
                "msc_stop_time": current_offset + (end_time - start_time),
                "med_stop_time": str(end_time),
            })
            current_offset += (end_time - start_time)

        return pd.DataFrame(preds_list)


    def _contiguous_regions(self,condition):
        """Finds contiguous True regions of the boolean array "condition". Returns
        a 2D array where the first column is the start index of the region and the
        second column is the end index."""

        # Find the indicies of changes in "condition"
        d = np.diff(condition)
        idx, = d.nonzero()

        # We need to start things after the change in "condition". Therefore,
        # we'll shift the index by 1 to the right.
        idx += 1

        if condition[0]:
            # If the start of condition is True prepend a 0
            idx = np.r_[0, idx]

        if condition[-1]:
            # If the end of condition is True, append the length of the array
            idx = np.r_[idx, condition.size]  # Edit

        # Reshape the result into two columns
        idx.shape = (-1, 2)
        return idx

        

class IdentifiedSpecies:
    def __init__(self):
        pass
    

# ProcessingType = TypeVar("ProcessingType")
# PendingType = TypeVar("PendingType")
# class Queue[ProcessingType, PendingType]:
#     queue: deque[PendingType]
#     processing: ProcessingType | None
#     queue_thread: ThreadPoolExecutor

#     def __init__(self):
#         self.queue = deque[PendingType]()
#         self.processing = None
#         self.queue_thread = ThreadPoolExecutor()
    
#     def add(self, item: ProcessingType):
#         pass
    
#     def process(self):
#         if self.processing is not None or len(self.queue) == 0:
#             return
        
#         item = self.queue.popleft()
#         abort_signal = threading.Event()
        
#         task = asyncio.get_event_loop().run_in_executor(
#             self.queue_thread, self.perform_task, item, abort_signal 
#         )
        
#         self.processing = self.pending_to_processing(item, abort_signal, task)
        
#     def process_item(self, item: ProcessingType, abort_signal: threading.Event, task, ):
#         pass
    
    
#     def pending_to_processing(self, item: PendingType, abort_signal: threading.Event, task: asyncio.Future) -> ProcessingType:
#         pass
        