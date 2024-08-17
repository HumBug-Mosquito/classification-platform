import librosa
import numpy as np
import torch
import torch.nn.functional as F

from src.med.mids_med import MidsMEDModel


class Config:
    def __init__(
        self,
        min_length = 1.92,
        window_size = 30,
        n_hop = 512,
        step_size = 10,
        det_threshold = 0.5,
    ) -> None:
        self.min_length = min_length
        self.window_size = window_size
        self.step_size = step_size
        self.n_hop = n_hop
        self.det_threshold = det_threshold

    @staticmethod
    def default():
        return Config()

config = Config.default()

def pad_and_step_signal(padded_audio_bytes, config: Config):
    pad_amt = (config.window_size - config.step_size) * config.n_hop
    noise_std = np.sqrt(0.1)
    pad_l = np.zeros((1, pad_amt)) + noise_std * np.random.randn(1, pad_amt)
    pad_r = np.zeros((1, pad_amt)) + noise_std * np.random.randn(1, pad_amt)

    padded_audio = np.concatenate([pad_l, [padded_audio_bytes], pad_r], axis=1)
    step_size = config.step_size * config.n_hop
    window_size = config.window_size * config.n_hop
    num_steps = (padded_audio.shape[1] - window_size) // step_size + 1

    return  np.array([padded_audio[0, i*step_size:i*step_size+window_size] for i in range(num_steps)])


def pad_mean(x_temp: np.ndarray, sample_length: int) -> np.ndarray:
    x_mean = np.mean(x_temp)

    left_pad_amt = int((sample_length - x_temp.shape[0]) // 2)
    left_pad = np.zeros([left_pad_amt])
    left_pad_mean_add = left_pad + x_mean

    right_pad_amt = int(sample_length - x_temp.shape[0] - left_pad_amt)
    right_pad = np.zeros([right_pad_amt])
    right_pad_mean_add = right_pad + x_mean

    f = np.hstack([left_pad_mean_add, x_temp, right_pad_mean_add])
    return(f)
    

# ---------------- Data Source ----------------

signal, sr = librosa.load("test_audio_on_off.wav", sr=8000)
print(signal)

# This converts the signal into a 2 dimensional array with 1 element, the signal (confirm why this is the case??)
audio_bytes = (torch.Tensor(signal).unsqueeze(0).float().numpy())

# Shape [0] is the number of elements in the 2d array - this is always 1 at this point
# Shape [1] is the number of elements in the signal array

# ---------------- MED Handler .Prepare ----------------

min_required_length = config.window_size * config.n_hop

padded_audio_bytes = audio_bytes
if (audio_bytes.shape[1] < min_required_length):
        padded_audio_bytes = torch.tensor(np.array(pad_mean( audio_bytes[0], min_required_length))).unsqueeze(0).float()

# ---------------- MED Handler .Run ----------------

pad_amt = 0 # (config.window_size - config.step_size) * config.n_hop
pad_l = torch.zeros(1, pad_amt) + (0.1**0.5) * torch.randn(1, pad_amt)
pad_r = torch.zeros(1, pad_amt) + (0.1**0.5) * torch.randn(1, pad_amt)
# padded_stepped_signal = torch.cat([pad_l, torch.FloatTensor(padded_audio_bytes), pad_r], dim=1).unfold(
#     1, config.window_size * config.n_hop, config.step_size * config.n_hop)

padded_stepped_signal = torch.cat([pad_l, torch.FloatTensor(padded_audio_bytes), pad_r], dim=1).unfold(
    1, config.window_size * config.n_hop, config.step_size * config.n_hop).transpose(0, 1)

print(padded_stepped_signal.shape)

# ---------------- MED Load Model ----------------

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
path = "src/med/model_presentation_draft_2022_04_07_11_52_08.pth"

model = MidsMEDModel()
model.load_state_dict(torch.load(path, map_location=device))
model.eval()

# ---------------- MED Handler .ClassifyBytes ----------------
import time

# get the start time
st = time.time()
predictions : dict= {}
for batch_index, signal_window in enumerate(padded_stepped_signal):
    with torch.no_grad():
        results = model(signal_window)['prediction']
        softmax = F.softmax(results, dim=1)
    probs, classes = torch.topk(softmax, 2, dim=1)

    probs = probs.tolist()
    classes = classes.tolist()
    print(classes)
    results = [
        {
            str(lbl_class): prob
            for lbl_class, prob in zip(*row)
        }
        for row in zip(classes, probs)
    ]

        # print(results[0].__len__())


# get the end time
et = time.time()
res = et - st
print('CPU Execution time:', res, 'seconds')