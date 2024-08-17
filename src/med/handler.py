#!/usr/bin/env python

import itertools
import logging
import os
from json import dumps
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch
import torch.nn.functional as F
from IPython.display import display
from torch.functional import Tensor

from audio_recording import AudioRecording
from config import Config
from med.mids_med import MidsMEDModel
from utils import pad_mean

pre_processing_started: dict = {
   "status": "pre_processing_started",
   "message": "The preprocessing of the audio recording has started."
}

pre_processing_finished: dict = {
    "status": "pre_processing_finished",
    "message": "The preprocessing of the audio recording has finished."
}

classification_started : dict = {
    "status": "pre_processing_started",
    "message": "The classification of the audio recording has started.",
    "progress": 0,
}

def classification_progressed(batch_number, total_batches)-> dict:
    return {
        "status": "processed_batch",
        "message": f"Batch {batch_number} of the classification has finished.",
        "progress":f"{ batch_number / total_batches * 100:.2f}%",
    }

def classification_finished()-> dict:

    return {
        "status": "finished",
        "message": "The classification of the audio recording has finished.",
    }

class MedClassificationResult:
    def __init__(self, recording: AudioRecording,signal: np.ndarray, predictions_array:  np.ndarray, config: Config) -> None:
        self.recording = recording
        self.signal = signal
        self.predictions_array = predictions_array
        self.config = config
    
class MedHandler:
    def __init__(self) -> None:
        self.logger = logging.getLogger('MedHandler')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        pass

    """
    Loads the MED models
    """
    def load_model(self):
        path = "src/med/model_presentation_draft_2022_04_07_11_52_08.pth"

        model = MidsMEDModel()
        model.load_state_dict(torch.load(path, map_location=self.device))
        model.eval()
        self.model = model
        self.logger.info("MED model loaded successfully. Used checkpoint: {0}".format(path))

    def prepare(self, recording_bytes: np.ndarray, config: Config = Config.default()) -> torch.Tensor:
        if (recording_bytes.shape[1] < config.window_size * config.n_hop):
             return torch.tensor(np.array(pad_mean(  recording_bytes[0], config.window_size * config.n_hop))).unsqueeze(0)
        
        return torch.tensor(recording_bytes).float()

    """
    Classifies the received list of audio bytes and returns a list of predictions.

    """
    async def run(self,recording: AudioRecording, signal: np.ndarray, send_update_to_client, config: Config = Config.default()) -> MedClassificationResult:   
        padded_stepped_signal = torch.FloatTensor(signal).unfold(1, config.window_size * config.n_hop, config.step_size * config.n_hop).transpose(0, 1)
        predictions_array = await self.run_bytes(padded_stepped_signal, send_update_to_client, config)
     
        result= MedClassificationResult(
            recording,
            signal,
            predictions_array,
            config=config
        )

        return result
    
    async def run_bytes(self, signal: torch.FloatTensor,send_update_to_client, config: Config = Config.default()):
        # Add random padding to the signal 
        
        # pad_amt = (config.window_size - config.step_size) * config.n_hop
        # pad_l = torch.zeros(1, pad_amt) + (0.1**0.5) * torch.randn(1, pad_amt)
        # pad_r = torch.zeros(1, pad_amt) + (0.1**0.5) * torch.randn(1, pad_amt)
        # padded_signal = torch.cat([pad_l, torch.FloatTensor(signal), pad_r], dim=1)
    
        # Dict maps batch index to prediction
        predictions : dict= {}
        for batch_index, signal_window in enumerate(signal):
            predictions[batch_index] = self.classify_batch(signal_window)
            await send_update_to_client( batch_index / signal.shape[0] * 100, f"Batch {batch_index + 1} of {signal.shape[0]} has been classified.")

        self.logger.debug("Classification finished. Results: {0}".format(predictions))

        predictions_array = np.array([[pred["0"], pred["1"]] for _, pred in predictions.items()])
        await send_update_to_client(100, "Classification finished.")
        return predictions_array

    def classify_batch(self, batch_bytes: Tensor) :
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
    
    def generate_outputs(self, result: MedClassificationResult, config: Config = Config.default()):
        # Prepare a dataframe
        predictions_array = result.predictions_array
        predictions_array_samples = np.array([predictions_array[:-4], predictions_array[1:-3], predictions_array[2:-2]])
        frame_count = torch.Tensor(result.signal).unfold(1, config.window_size * config.n_hop, config.step_size * config.n_hop).shape[1]
        G_X, U_X, _ = active_BALD(np.log(predictions_array_samples), frame_count, 2)
        mean_predictions = np.mean(predictions_array_samples, axis=0)
        timestamp_df = _build_timestamp_df(mean_predictions, G_X, U_X, (config.n_hop * config.step_size / result.recording.sample_rate), config.det_threshold, result.recording)

        # Save the WAV file containing presence of mosquitos in recording
        path_to_outputs = Path(os.environ['CLASSIFICATION_OUTPUT_DIR'])
        wav_file_name = Path(path_to_outputs, f"{str(result.recording.id)}.wav", )
        mozz_audio_list = [result.signal[0][int(float(row["med_start_time"]) * result.recording.sample_rate):int(float(row["med_stop_time"]) * result.recording.sample_rate)] for _, row in timestamp_df.iterrows()]
        sf.write(Path( wav_file_name), np.hstack(mozz_audio_list), result.recording.sample_rate)

        df = pd.DataFrame(timestamp_df)
        output_path = Path(path_to_outputs,f"{str(result.recording.id)}.csv")
        path_to_med_df = Path(path_to_outputs,f'{result.recording.id}.csv' )
        df.to_csv(path_to_med_df, index=False)
        return df,output_path

        
def active_BALD(out, X, n_classes):
    if type(X) == int:
        frame_cnt = X
    else:
        frame_cnt = X.shape[0]

    log_prob = np.zeros((out.shape[0], frame_cnt, n_classes))
    score_All = np.zeros((frame_cnt, n_classes))
    All_Entropy = np.zeros((frame_cnt,))
    for d in range(out.shape[0]):
        log_prob[d] = out[d]
        soft_score = np.exp(log_prob[d])
        score_All = score_All + soft_score
        # computing F_X
        soft_score_log = np.log2(soft_score + 10e-15)
        Entropy_Compute = - np.multiply(soft_score, soft_score_log)
        Entropy_Per_samp = np.sum(Entropy_Compute, axis=1)
        All_Entropy = All_Entropy + Entropy_Per_samp

    Avg_Pi = np.divide(score_All, out.shape[0])
    Log_Avg_Pi = np.log2(Avg_Pi + 10e-15)
    Entropy_Avg_Pi = - np.multiply(Avg_Pi, Log_Avg_Pi)
    Entropy_Average_Pi = np.sum(Entropy_Avg_Pi, axis=1)
    G_X = Entropy_Average_Pi
    Average_Entropy = np.divide(All_Entropy, out.shape[0])
    F_X = Average_Entropy
    U_X = G_X - F_X
    return G_X, U_X, log_prob


def _build_timestamp_df(mean_predictions, G_X, U_X, time_to_sample, det_threshold, recording: AudioRecording) -> pd.DataFrame:
    """Use the predictions to build an array of contiguous timestamps where the
    probability of detection is above threshold"""

    # find where the average 2nd element (positive score) is > threshold
    condition = mean_predictions[:, 1] > det_threshold
    preds_list = []
    current_offset = 0
    for start, stop in _contiguous_regions(condition):
        # start and stop are frame indexes
        # so multiply by n_hop and step_size samples
        # then div by sample rate to get seconds
        start_time = round(start * time_to_sample,2)
        end_time = round(stop * time_to_sample,2)
        preds_list.append({
            "uuid": recording.id,
            "datetime_recorded": recording.datetime_recorded,
            "med_start_time": str(start_time), 
            "med_prob": "{:.4f}".format(np.mean(mean_predictions[start:stop][:, 1])), 
            "msc_start_time": current_offset,
            "msc_stop_time": current_offset + (end_time - start_time),
            "med_stop_time": str(end_time),
        })
        current_offset += (end_time - start_time)

    return pd.DataFrame(preds_list)


def _contiguous_regions(condition):
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


