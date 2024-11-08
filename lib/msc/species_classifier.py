import logging
import threading

import numpy as np
import torch
import torch.nn.functional as F

from lib.config import Config
from lib.custom_types import (DetectedEvents, DetectedSpecies,
                              SpeciesClassificationResponse)
from lib.exceptions import UserCancelledError
from lib.msc.mids_msc import MidsMSCModel

mapping: dict  = {
 "0":"an arabiensis",
 "1":"culex pipiens complex",
 "2":"ae aegypti",
 "3":"an funestus ss",
 "4":"an squamosus",
 "5":"an coustani",
 "6":"ma uniformis",
 "7":"ma africanus"
}

"""
To use the Species Classifier, you need to do the following steps:

1. Given raw audio bytes, 
"""
class SpeciesClassifier: 
    model: MidsMSCModel

    def __init__(self, model_path: str):
        self.logger = logging.getLogger('SpeciesClassifier')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        model = MidsMSCModel()
        print("Loading MSC model from {0}".format(model_path))
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.eval()
        self.model = model

        self.model_checkpoint = model_path.split("/")[-1]
        self.logger.info("MSC model loaded successfully. Used checkpoint: {0}".format(model_path))

    
    def classify(self, events_audio: torch.FloatTensor,send_update_to_client,detected_events: DetectedEvents, abort_signal=threading.Event(), config=Config.default()) -> SpeciesClassificationResponse:
        # Batch index to species predictions which is dict of species to probabilities
        predictions : dict[int,dict[str,float]] = {}
        for batch_index, signal_window in enumerate(events_audio):
            print("Processing batch {0} of {1}".format(batch_index + 1, events_audio.shape[0]))
            if abort_signal and abort_signal.is_set():
                self.logger.info("Classification cancelled.")
                raise UserCancelledError()
            
            predictions[batch_index] = self.classify_batch(signal_window)
            send_update_to_client( batch_index / events_audio.shape[0] * 100, f"Batch {batch_index + 1} of {events_audio.shape[0]} has been classified.")
            
        send_update_to_client(100, "Classification finished.")
        
        
        return SpeciesClassificationResponse.from_events_and_species_classification(
            model=self.model_checkpoint,
            events=detected_events, 
            species_predictions=predictions,
            config=config,
        )

    
    def classify_batch(self, batch_bytes: torch.FloatTensor):
        with torch.no_grad():

            results = self.model(batch_bytes)['prediction']
            softmax = F.softmax(results, dim=1)
            
        probs, classes = torch.topk(softmax, 8, dim=1)
        probs = probs.tolist()
        classes = classes.tolist()

        results = [
            {
                mapping[str(lbl_class)] : prob
                for lbl_class, prob in zip(*row)
            }
            for row in zip(classes, probs)
        ]

        return results[0]
    