
import json

import librosa
import numpy as np
from torch import FloatTensor

from lib.config import Config
from lib.custom_types import DetectedEvents
from lib.msc.species_classifier import SpeciesClassifier
from lib.utils import get_audio_with_events

MODEL_PATH = "lib/msc/model_e186_2022_10_11_11_18_50.pth"
RECORDING_PATH= "lib/storage/test_audio_on_off.wav"

def load_stored_events():
    with open('events.json', 'r') as f:
        string = f.read()
        f.close()
        return DetectedEvents.from_dict(json.loads(string)["events"]) 

def load_recording():
    signal, _ = librosa.load(RECORDING_PATH, sr=8000)
    return signal


events: DetectedEvents = load_stored_events()
signal = load_recording()

audio = get_audio_with_events(signal, events, Config.default())

classifier = SpeciesClassifier(MODEL_PATH)

species = classifier.classify(
    events_audio=FloatTensor(np.array(audio)),
    send_update_to_client=(lambda progress, message: None),
    detected_events=events,
)

with open('species1.json', 'w') as f:
    f.write(json.dumps(species.__dict__(), indent=4))
    f.close()
    