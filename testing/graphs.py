import random

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches

from lib.custom_types import DetectedSpecies


def plot_predictions(predictions: np.ndarray):
    # Extract the positive event probability and labels based on the predictions
    positive_event_probability = [prediction[1] for prediction in predictions]
    labels = [(index + 1) * 1.92 for index in range(len(predictions))]  # time labels based on 1.92s batch duration
    
    # Plotting the data
    plt.figure(figsize=(10, 6))
    plt.plot(labels, positive_event_probability, label='Probability of Presence', marker='o', linestyle='-', color='salmon')
    
    # Labels and title
    plt.xlabel('Time (seconds)')
    plt.ylabel('Probability')
    plt.title('Predicted Probability of Presence Over Time')
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    # Show plot
    plt.show()


def plot_species_predictions(species: list[DetectedSpecies]):
    def get_species_predictions():
        if not species or len(species) == 0:
            return []
        
        predictions = [
            {
                "specie": specie,
                "predictions": [{"x": entry.__dict__()["end"], "y": entry.__dict__()["predictions"][specie]} for entry in species],
            }
            for specie in species[0].__dict__()["predictions"].keys()
        ]
        
        return predictions

    def combine_contiguous_species(detected_species: list[DetectedSpecies]):
        combined_species = []
        current_entry = None
        total_presence = 0
        segment_count = 0

        for entry in detected_species:
            entry = entry.__dict__()
            if (
                current_entry
                and current_entry["species"] == entry["species"]
                and current_entry["end"] == entry["start"]
            ):
                current_entry["end"] = entry["end"]
                for key in entry["predictions"].keys():
                    current_entry["predictions"][key] = max(
                        current_entry["predictions"].get(key, 0), entry["predictions"][key]
                    )
                total_presence += entry["predictions"][entry["species"]]
                segment_count += 1
            else:
                if current_entry:
                    current_entry["mean_presence"] = total_presence / segment_count
                    combined_species.append(current_entry)
                current_entry = {
                    "start": entry["start"],
                    "end": entry["end"],
                    "species": entry["species"],
                    "predictions": entry["predictions"].copy(),
                    "mean_presence": entry["predictions"][entry["species"]],
                }
                total_presence = entry["predictions"][entry["species"]]
                segment_count = 1

        if current_entry:
            current_entry["mean_presence"] = total_presence / segment_count
            combined_species.append(current_entry)

        return combined_species

    def get_species_annotations():
        combined_species = combine_contiguous_species(species)
        return [
            {
                "x_min": entry["start"],
                "x_max": entry["end"],
                "y_min": 0,
                "y_max": 1,
                "label": entry["species"],
            }
            for entry in combined_species
        ]

    # Generate species predictions
    detected_species = get_species_predictions()

    # Generate random colors for each species
    colors = [
        "#%06x" % random.randint(0, 0xFFFFFF) for _ in range(len(detected_species))
    ]

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Add line plots for each species
    for index, specie_data in enumerate(detected_species):
        x_values = [point["x"] for point in specie_data["predictions"]]
        y_values = [point["y"] for point in specie_data["predictions"]]
        ax.plot(
            x_values,
            y_values,
            label=f"Probability for {specie_data['specie']}",
            color=colors[index],
        )

    # Add annotations
    annotations = get_species_annotations()
    for annotation in annotations:
        rect = patches.Rectangle(
            (annotation["x_min"], annotation["y_min"]),
            annotation["x_max"] - annotation["x_min"],
            annotation["y_max"] - annotation["y_min"],
            linewidth=1,
            edgecolor="blue",
            facecolor="lightblue",
            alpha=0.3,
        )
        ax.add_patch(rect)
        ax.text(
            (annotation["x_min"] + annotation["x_max"]) / 2,
            annotation["y_max"] + 0.02,
            annotation["label"],
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    # Configure plot
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Probability")
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.grid(True)

    # Show the plot
    plt.show()