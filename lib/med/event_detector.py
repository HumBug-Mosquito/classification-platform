import logging
import threading

import numpy as np
import torch
import torch.nn.functional as F

from lib.custom_types import DetectedEvents
from lib.exceptions import UserCancelledError
from lib.med.mids_med import MidsMEDModel


class EventDetector:
    model: MidsMEDModel

    def __init__(self, model_path: str):
        self.logger = logging.getLogger('EventDetector')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        model = MidsMEDModel()
        print("Loading MED model from {0}".format(model_path))
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.eval()
        self.model = model

        self.model_checkpoint = model_path.split("/")[-1]
        self.logger.info("MED model loaded successfully. Used checkpoint: {0}".format(model_path))

    """
    Detects events in the given audio bytes.
       - bytes: the audio bytes to detect events in
       - send_update_to_client: a function to send updates to the client. (float progress, string message)
       - abort_signal: a signal to abort the detection.
    Returns a list of detected events.
    """
    def detect(self, signal: torch.FloatTensor, send_update_to_client, abort_signal=threading.Event()) -> DetectedEvents:
        # Dict maps batch index to prediction
        predictions : dict= {}
        for batch_index, signal_window in enumerate(signal):
            if abort_signal and abort_signal.is_set():
                self.logger.info("Classification cancelled.")
                raise UserCancelledError()
            predictions[batch_index] = self.classify_batch(signal_window)
            send_update_to_client( batch_index / signal.shape[0] * 100, f"Batch {batch_index + 1} of {signal.shape[0]} has been classified.")

        self.logger.debug("Classification finished. Results: {0}".format(predictions))

        predictions_array = np.array([[pred["0"], pred["1"]] for _, pred in predictions.items()])
        send_update_to_client(100, "Classification finished.")
        return DetectedEvents(predictions_array, self.model_checkpoint)


    def classify_batch(self, batch_bytes: torch.FloatTensor):
        with torch.no_grad():
            results = self.model(batch_bytes)['prediction']
            softmax = F.softmax(results, dim=1)
        probs, classes = torch.topk(softmax, 2, dim=1)
        probs = probs.tolist()
        classes = classes.tolist()

        results = [
            {
                str(lbl_class): prob
                for lbl_class, prob in zip(*row)
            }
            for row in zip(classes, probs)
        ]

        return results[0]
