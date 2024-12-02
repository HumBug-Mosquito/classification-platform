import json
import logging

import librosa

from lib.classifier import Classifier
from lib.config import Config
from lib.custom_types import Environment, SpeciesClassificationResponse
from testing.graphs import plot_predictions, plot_species_predictions

logging.basicConfig(level=logging.INFO)

RECORDING_PRESENCE = "lib/storage/test_audio_on_off.wav"
RECORDING_NO_PRESENCE = "lib/storage/test_no_presence.wav"

    
def detect_species():
    classifier = Classifier(Environment({
        "DATABASE_URL": "localhost",
        "EVENT_DETECTOR_MODEL_PATH": "lib/med/model_presentation_draft_2022_04_07_11_52_08.pth",
        "SPECIES_CLASSIFIER_MODEL_PATH": "lib/msc/model_e186_2022_10_11_11_18_50.pth",
        "CLASSIFICATION_OUTPUT_DIR": "./output" ,
    }))

    signal, _ = librosa.load(RECORDING_PRESENCE, sr=8000)

    def output_progress(progress , message):
        print(f"{progress}%: {message}")

    response = classifier.msc(signal,send_update_to_client=output_progress)
    with open('events.json', 'w') as f:
        f.write(json.dumps(response.__dict__(), indent=4))
        f.close()
    print("Events written to events.json")
        
    return response


def load_stored_events():
    with open('events.json', 'r') as f:
        string = f.read()
        f.close()
        return SpeciesClassificationResponse.from_dict(json.loads(string)) 

FULL_RUN = True

species = detect_species() if FULL_RUN else load_stored_events()

plot_predictions(species.events.predictions_array)

plot_species_predictions( species.detected_species)
