function plotPredictions(predictions, detectedSpecies) {
  const positiveEventProbability = [];
  const labels = [];

  predictions.forEach((prediction, index) => {
    positiveEventProbability.push(prediction[1]);
    labels.push((index + 1) * 1.92); // Calculate time based on 1.92s batch duration
  });

  const combinedSpecies = combineContiguousSpecies(detectedSpecies);

  renderChart(labels, positiveEventProbability, combinedSpecies);
}

function combineContiguousSpecies(detectedSpecies) {
  const combinedSpecies = [];
  let currentEntry = null;
  let totalPresence = 0; // To accumulate the probabilities for mean calculation
  let segmentCount = 0; // Count of contiguous segments for calculating the mean

  detectedSpecies.forEach((entry) => {
    if (currentEntry && currentEntry.species === entry.species && currentEntry.end === entry.start) {
      // Extend the current entry if species matches and they are contiguous
      currentEntry.end = entry.end;

      // Update predictions by keeping the maximum probability for each species
      Object.keys(entry.predictions).forEach((key) => {
        currentEntry.predictions[key] = Math.max(currentEntry.predictions[key] || 0, entry.predictions[key]);
      });

      // Accumulate the probability for the mean presence calculation of the specific species
      totalPresence += entry.predictions[entry.species];
      segmentCount += 1;
    } else {
      // Finalize the mean presence for the last contiguous block if one exists
      if (currentEntry) {
        currentEntry.meanPresence = totalPresence / segmentCount;
        combinedSpecies.push(currentEntry);
      }

      // Start a new entry
      currentEntry = {
        start: entry.start,
        end: entry.end,
        species: entry.species,
        predictions: { ...entry.predictions }, // Shallow copy of predictions
        meanPresence: entry.predictions[entry.species], // Initialize mean with current entry's probability
      };

      // Reset the total presence and segment count
      totalPresence = entry.predictions[entry.species];
      segmentCount = 1;
    }
  });

  // Add the last contiguous block if it exists
  if (currentEntry) {
    currentEntry.meanPresence = totalPresence / segmentCount;
    combinedSpecies.push(currentEntry);
  }

  return combinedSpecies;
}

function renderChart(labels, class2Data, detectedSpecies) {
  const ctx = document.getElementById('predictionsChart').getContext('2d');

  // Destroy previous chart instance if it exists
  if (window.predictionsChart instanceof Chart) {
    window.predictionsChart.destroy();
  }

  // Create annotation objects based on detected species data
  const speciesAnnotations = detectedSpecies.map((entry, index) => {
    return {
      type: 'box',
      xMin: entry.start / 1.92,
      xMax: entry.end / 1.92,
      yMin: 0,
      yMax: 1,
      backgroundColor: 'rgba(54, 162, 235, 0.1)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 1,
      label: {
        content: entry.species,
        display: true,
        position: 'center',
        color: 'black',
        font: { weight: 'bold' },
      },
    };
  });

  // Create the chart with annotations
  window.predictionsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Probability of Presence',
          data: class2Data,
          borderColor: 'rgba(255, 99, 132, 1)',
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      scales: {
        x: {
          title: {
            display: true,
            text: 'Time (seconds)', // Updated label to reflect time
          },
          min: 0,
          max: labels[labels.length - 1],
        },
        y: {
          title: {
            display: true,
            text: 'Probability',
          },
          min: 0,
          max: 1,
        },
      },
      plugins: {
        annotation: {
          annotations: speciesAnnotations,
        },
      },
    },
  });
}

window.plotPredictions = plotPredictions;
