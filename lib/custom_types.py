

import numpy as np
import pandas as pd

from lib.config import Config
from lib.storage.recording_storage import AudioRecording


class Environment: 
    database_url: str
    output_dir: str
    event_detector_model_path: str
    species_classifier_model_path: str
    
    def __init__(self, env: dict):
        self.database_url = env.get("DATABASE_URL")
        self.event_detector_model_path = env.get("EVENT_DETECTOR_MODEL_PATH")
        self.species_classifier_model_path = env.get("SPECIES_CLASSIFIER_MODEL_PATH")
        self.output_dir = env.get("CLASSIFICATION_OUTPUT_DIR")
    
    def __str__(self):
        return f"Environment(database_url={self.database_url}, output_dir={self.output_dir}, event_detector_model_path={self.event_detector_model_path}, species_classifier_model_path={self.species_classifier_model_path})"

class DetectedEvents:
    def __init__(self, predictions_array: np.ndarray, model: str):
        self.predictions_array = predictions_array
        self.model = model
        
    def __dict__(self):
        return {
            "predictions": self.predictions_array.tolist(),
            "model": self.model
        }
        
    def has_events(self, detect_threshold: float):
        return True in (self.predictions_array[:, 1] > detect_threshold)
        
    @staticmethod
    def from_dict(data: dict):
        return DetectedEvents(np.array(data["predictions"]), data["model"])
        
    def get_data_frame(self, config: Config)-> pd.DataFrame:
        predictions_array = self.predictions_array
        predictions_array_samples = np.array([predictions_array[:-4], predictions_array[1:-3], predictions_array[2:-2]])
        mean_predictions = np.mean(predictions_array_samples, axis=0)
        return self._build_timestamp_df(mean_predictions, config.min_length, config.det_threshold)
    
    # def get_data_frame_with_recording(self, config: Config, recording: AudioRecording) -> pd.DataFrame:
    #     predictions_array = self.predictions_array
    #     predictions_array_samples = np.array([predictions_array[:-4], predictions_array[1:-3], predictions_array[2:-2]])
    #     mean_predictions = np.mean(predictions_array_samples, axis=0)
    #     return self._build_timestamp_df(mean_predictions, (config.n_hop * config.step_size / 8000), config.det_threshold, recording)
        
    def _build_timestamp_df(self,predictions, time_to_sample, det_threshold, recording: AudioRecording | None = None) -> pd.DataFrame:
        """Use the predictions to build an array of contiguous timestamps where the
        probability of detection is above threshold"""
        # find where the average 2nd element (positive score) is > threshold
        condition = predictions[:, 1] > det_threshold
        if (condition.size == 0):
            return pd.DataFrame([])

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
                "med_stop_time": str(end_time),
                "med_prob": "{:.4f}".format(np.mean(predictions[start:stop][:, 1])),
                "msc_start_time": current_offset,
                "msc_stop_time": current_offset + (end_time - start_time),
            })
            current_offset += (end_time - start_time)

        return pd.DataFrame(preds_list)

    def _contiguous_regions(self,condition):
        """Finds contiguous True regions of the boolean array "condition". Returns
        a 2D array where the first column is the start index of the region and the
        second column is the end index."""

        # Find the indices of changes in "condition"
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

class DetectedSpecies:

    # The start time of the original audio that was classified (in seconds)
    start: float
    
    # The end time of the segment of the original audio that was classified (in seconds)
    end: float
    
    # Helper: The name of the species that was identified.
    species: str
    
    # All of the probabilities for each species
    predictions: dict
    
    def __init__(self, start: float, end: float, predictions: dict[str, float]):
        self.start = start
        self.end = end
        self.predictions = predictions
        self.species = max(predictions, key=predictions.get)
        
    def __dict__(self):
        return {
            "start": self.start,
            "end": self.end,
            "species": self.species,
            "predictions": self.predictions
        }   
        
    @staticmethod
    def from_dict(data: dict):
        return DetectedSpecies(
            start=data["start"],
            end=data["end"],
            predictions=data["predictions"]
        )
        

    
class SpeciesClassificationResult:
       # The model used to classify the species
    model: str
    
    predictions: dict
    
    def __init__(self, model: str):
        self.model = model
        
    
class SpeciesClassificationResponse:
    detected_species: list[DetectedSpecies]
    model: str
    events: DetectedEvents


    def __init__(self, detected_species: list[DetectedSpecies], model: str, events: DetectedEvents):
        self.detected_species = detected_species
        self.model = model
        self.events = events
        
    def __dict__(self):
        return {
            'species': {
                "model": self.model,
                "detected_species": [species.__dict__() for species in self.detected_species],
            },
            "events": self.events.__dict__()
        }
        
    @staticmethod
    def no_events_detected(events: DetectedEvents, model: str):
        return SpeciesClassificationResponse([], model=model, events=events)
        
    @staticmethod
    def from_dict(data: dict):
        return SpeciesClassificationResponse(
            detected_species=[DetectedSpecies.from_dict(species) for species in data["species"]["detected_species"]],
            model=data["species"]["model"],
            events=DetectedEvents.from_dict(data["events"])
        )
    
    @staticmethod
    def from_events_and_species_classification(events: DetectedEvents, species_predictions: dict[int, dict[str, float]], model: str, config: Config):
        df = events.get_data_frame(config=config)
        rows: list[list[float, float]] = [
                    [float(row["med_start_time"]), float(row["med_stop_time"])]
            for _, row in df.iterrows()
        ]
        
        counter = 0
        detected_species: list[DetectedSpecies] =[]
        for _, row in enumerate(rows):
            start = row[0]
            end = row[1]
            increment = config.min_length  # increment as a float

            # Initialize the current value to the start
            current = start

            # Loop until we reach or exceed the end
            while current < end:
                detected_species.append( DetectedSpecies(
                    start= current,
                    end= current + config.min_length,
                    predictions=species_predictions[counter]
                ))
                counter += 1
                current += increment
                
            
        return SpeciesClassificationResponse(detected_species, model=model, events=events)


    
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
        