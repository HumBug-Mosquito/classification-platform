import json
import logging

import librosa

from lib.classifier import Classifier
from lib.config import Config
from lib.custom_types import (DetectedEvents, Environment,
                              SpeciesClassificationResponse)

logging.basicConfig(level=logging.INFO)


import matplotlib.pyplot as plt


def plot_predictions(predictions, species_annotations):
    # Extract the positive event probability and labels based on the predictions
    positive_event_probability = [prediction[1] for prediction in predictions]
    labels = [(index + 1) * 1.92 for index in range(len(predictions))]  # time labels based on 1.92s batch duration
    
    # Plotting the data
    plt.figure(figsize=(10, 6))
    plt.plot(labels, positive_event_probability, label='Probability of Presence', marker='o', linestyle='-', color='salmon')
    
    # Adding annotations for species events
    for annotation in species_annotations:
        plt.axvline(x=annotation, color='gray', linestyle='--', linewidth=0.5, label='Species Event' if annotation == species_annotations[0] else "")
    
    # Labels and title
    plt.xlabel('Time (seconds)')
    plt.ylabel('Probability')
    plt.title('Predicted Probability of Presence Over Time')
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    # Show plot
    plt.show()

def detect_species():
    classifier = Classifier(Environment({
        "DATABASE_URL": "localhost",
        "EVENT_DETECTOR_MODEL_PATH": "lib/med/model_presentation_draft_2022_04_07_11_52_08.pth",
        "SPECIES_CLASSIFIER_MODEL_PATH": "lib/msc/model_e186_2022_10_11_11_18_50.pth",
        "CLASSIFICATION_OUTPUT_DIR": "./output" ,
    }))

    file = 'lib/storage/test_audio_on_off.wav'

    signal, _ = librosa.load(file, sr=8000)

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

print(species.events.get_data_frame(Config.default()))

plot_predictions(species.events.predictions_array, [])
