import logging
import os
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from IPython.display import display

from audio_recording import AudioRecording
from config import Config
from msc.mids_msc import MidsMSCModel
from utils import pad_mean

index_to_class={
 "0":"an arabiensis",
 "1":"culex pipiens complex",
 "2":"ae aegypti",
 "3":"an funestus ss",
 "4":"an squamosus",
 "5":"an coustani",
 "6":"ma uniformis",
 "7":"ma africanus"
}


def classification_progressed(batch_number, total_batches)-> dict:
    return {
        "status": "processed_batch",
        "message": f"Batch {batch_number} of the classification has finished.",
        "progress":f"{ batch_number / total_batches * 100:.2f}%",
    }


class MscClassificationResults:
    def __init__(self, species: str) -> None:
        self.species = species
        pass

    def save(self):

        pass

class MscHandler:

    def __init__(self) -> None:
        self.logger = logging.getLogger('MscHandler')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        pass

    """
    Loads the MED models
    """
    def load_model(self):
        path = "src/msc/model_e186_2022_10_11_11_18_50.pth"
        model = MidsMSCModel()
        model.load_state_dict(torch.load(path, map_location=self.device))
        model.eval()
        self.model = model
        self.logger.info("MSC model loaded successfully. Used checkpoint: {0}".format(path))
        
    async def run(self, recording: AudioRecording, signal: np.ndarray, send_update_to_client,config: Config = Config.default())->dict:
        batch ={}
        sample_length = int(config.min_length * recording.sample_rate)
        for index in range(0, signal.shape[0], sample_length):

            signal_window = signal[index:index + sample_length]
            # check is sample is of minimum length
            # if it's too short but > 20% of min length then use mean paddding
            if signal_window.shape[0] < sample_length and signal_window.shape[0] > sample_length * 0.2:
                signal_window = pad_mean(signal_window, sample_length)
                
            if signal_window.shape[0] == sample_length: 
                batch[index] = self.classify_batch(signal_window)
                await send_update_to_client(index / signal.shape[0] * 100,  f"Batch {(index / sample_length) + 1} of {(signal.shape[0] // sample_length)} has been classified.")

        await send_update_to_client(100, "Classification finished.")
        return batch
    
    def generate_outputs(self, recording: AudioRecording, result: Dict, config: Config = Config.default()) -> str:
        path_to_outputs = Path(os.environ['CLASSIFICATION_OUTPUT_DIR'])
        med_csv_path = Path(path_to_outputs,f"{recording.id}.csv")
        msc_csv_path = Path(path_to_outputs,f"{recording.id}_msc.csv")
        df = batch_to_metrics_csv(med_csv_path, result, recording.sample_rate, config.min_length)

        df.to_csv(msc_csv_path, index=False)
        return msc_csv_path.absolute().as_uri()


    def classify_batch(self, batch_bytes: torch.Tensor):
        # res = requests.post("http://localhost:8080/predictions/midsmscmodel",
        #     data=batch_bytes.tobytes())
    
        # return res.json()
        with torch.no_grad():
            results = self.model(torch.Tensor(batch_bytes))['prediction']

        softmax = F.softmax(results, dim=1)
        probs, classes = torch.topk(softmax, 8, dim=1)
        probs = probs.tolist()
        classes = classes.tolist()
        results = [
            {
                (index_to_class[str(lbl_class)]): prob
                for lbl_class, prob in zip(*row)
            }
            for row in zip(classes, probs)
        ]

        return results[0]

def batch_to_metrics_csv(med_csv_filename, batch: Dict, rate: int, min_duration: float) -> pd.DataFrame:
    offsets = sorted([int(k) for k in batch.keys()])
    med_df = pd.read_csv(med_csv_filename)
    rows = []
    for offset in offsets:
        row = {}
        med_row_for_timestamp = med_df[(med_df["msc_start_time"] <= round(offset / rate, 2)) & (med_df["msc_stop_time"] >= round(offset / rate,2))].iloc[0]
        row["uuid"] = med_row_for_timestamp["uuid"]
        row["datetime_recorded"] = med_row_for_timestamp["datetime_recorded"]
        row["med_start_time"] = med_row_for_timestamp["med_start_time"] + round(offset / rate, 2)
        row["med_prob"] = med_row_for_timestamp["med_prob"]
        row["msc_start_time"] = round(offset / rate, 2)
        row["msc_end_time"] = round(offset / rate, 2) + min_duration
        row["med_start_time"] = med_row_for_timestamp["med_start_time"] + round(offset / rate, 2) - round(med_row_for_timestamp["msc_start_time"], 2)
        row["med_stop_time"] = row["med_start_time"] + min_duration
        species_list = sorted(batch[offset].keys())
        for species in species_list:
            row[species] = batch[offset][species]
        rows.append(row)

    return pd.DataFrame(rows)