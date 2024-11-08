# This function pads a short-audio tensor with its mean to ensure that it becomes a 1.92 sec long audio equivalent
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

from lib.config import Config


def ensure_minimum_length(signal: np.ndarray, config: Config) -> np.ndarray:
    desired_length = 8000 * config.min_length
    x_mean = np.mean(signal)

    left_pad_amt = int((desired_length - len(signal)) // 2)
    right_pad_amt = int(desired_length - len(signal) - left_pad_amt)
    
    left_pad_mean_add = np.full(left_pad_amt, x_mean, dtype=np.float32)
    right_pad_mean_add = np.full(right_pad_amt, x_mean, dtype=np.float32)
    
    return np.concatenate([left_pad_mean_add, signal, right_pad_mean_add])

def pad_and_step_signal(signal: np.ndarray, config: Config) -> np.ndarray:
    batch_size =  int(8000 * config.min_length)
    batches = []
    for i in range(0, len(signal), batch_size):
        batch = signal[i:i + batch_size]
        if len(batch) < batch_size:
            batch = ensure_minimum_length(batch, config)
        batches.append(batch)
    return batches

def prepare(signal: np.ndarray, config: Config) -> np.ndarray:
    batch_size =  8000 * config.min_length
    if len(signal) < batch_size:
        signal = ensure_minimum_length(signal, config)
    return pad_and_step_signal(signal, config)

    

def pad_mean(x_temp: np.ndarray, sample_length: int) -> np.ndarray:
    logging.debug("inside padding mean...")
    x_mean = np.mean(x_temp)

    logging.debug("X_mean = " + str(x_mean))
    left_pad_amt = int((sample_length - x_temp.shape[0]) // 2)
    logging.debug("left_pad_amt = " + str(left_pad_amt))
    left_pad = np.zeros([left_pad_amt])
    logging.debug("left_pad shape = " + str(left_pad.shape))
    left_pad_mean_add = left_pad + x_mean
    logging.debug("left_pad_mean shape = " + str(left_pad_mean_add))
    logging.debug("sum of left pad mean add = " + str(np.sum(left_pad_mean_add)))

    right_pad_amt = int(sample_length - x_temp.shape[0] - left_pad_amt)
    right_pad = np.zeros([right_pad_amt])
    logging.debug("right_pad shape = " + str(right_pad.shape))
    right_pad_mean_add = right_pad + x_mean
    logging.debug("right_pad_mean shape = " + str(right_pad_mean_add))
    logging.debug("sum of right pad mean add = "  + str(np.sum(right_pad_mean_add)))

    f = np.hstack([left_pad_mean_add, x_temp, right_pad_mean_add])
    return(f)

def get_offsets_df(df: pd.DataFrame, short_audio=False, config: Config=Config.default()):
    audio_offsets = []

    rate = 8000
    min_length = (config.window_size * config.n_hop) / rate
    step_frac = config.step_size/ config.window_size
    stride = step_frac * min_length
    for _,row in df.iterrows():
        #processed_data keeps track of the tensor_values processed thus far
        if row['length'] > min_length:
            processed_data = 0
            #total_data is the total tensor present in the audio
            total_data = rate * row['length']
            label_ind = row['sound_type']
            if label_ind == 'mosquito':
                label_ind =1
            else:
                label_ind = 0
            count = 0
            inner_loop_flag = False
            while(processed_data < total_data):
                start = count*stride * rate
                #now find out the row_len
                if total_data - (start + min_length * rate) >= 0:
                    row_len = min_length
                    end = start + row_len * rate
                    audio_offsets.append({'id':row['uuid'],'species': row['species'],'med_start':int(start),'med_end':int(end)})
                    count+=1
                    processed_data = (count*stride) * rate
                    
                else:
                    inner_loop_flag = True
                    break
                    
                                                       
            #for processing residual data
            if(inner_loop_flag):
                start = count * stride * rate
                resid_durn = round((total_data - processed_data) / rate, 2)
                end = total_data
                audio_offsets.append({'id':row['id'], 'offset':count, 'length':resid_durn ,'specie_ind': label_ind,'start':int(start),'end':int(end)})
            
        elif short_audio:
            label_ind = row['sound_type']
            if label_ind == 'mosquito':
                label_ind =1
            else:
                label_ind = 0
            start = 0
            end = row['length'] * rate
            audio_offsets.append({'id':row['id'], 'offset':0,'length': row['length'],'specie_ind': label_ind,'start':0 , 'end':int(end)})
    return pd.DataFrame(audio_offsets)


def get_audio_with_events(recording_bytes, events, config: Config) -> np.ndarray:
    df = events.get_data_frame(config=config)
    print("Data frame: \n", df)

    signal = recording_bytes
    return prepare(np.hstack([signal[
            int(float(row["med_start_time"]) * config.sample_rate):
            int(float(row["med_stop_time"]) * config.sample_rate)
    ] for _, row in df.iterrows()]), config)
