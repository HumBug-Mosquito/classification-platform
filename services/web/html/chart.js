function plotPredictions(events, species) {
  const presenceProbability = [];

  events.forEach((event, index) => {
    presenceProbability.push(event[1]);
  });

  renderChart(presenceProbability, species);
}

function renderChart(events, species) {
  renderEvents(events);
  if (species && species.length !== 0) renderSpecies(species);
}

/**
 *
 * @param {number[]} events
 */
function renderEvents(events) {
  const ctx = document.getElementById('eventsChart');

  // Destroy previous chart instance if it exists
  if (window.eventsChart instanceof Chart) {
    window.eventsChart.destroy();
  }

  const data = events.map((event, index) => ({
    x: (index + 1) * 1.92,
    y: event,
  }));

  data.unshift({ x: 0, y: 0 });
  // Create the chart with annotations
  window.eventsChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Probability of mosquito presence',
          data,
          borderColor: 'rgba(255, 99, 132, 1)',
          tension: 0.1,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Time (seconds)', // Updated label to reflect time
          },
          min: 0,
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
    },
  });
}

/**
 * @param {{start: number, end: number, species: string, predictions: Record<string, number>}[]} species
 */
function renderSpecies(species) {
  /**
   * @returns {{specie: string, predictions:{x:number, y:number}[]}[]}
   */
  function getSpeciesPredictions() {
    if (!species || species.length === 0) return [];

    const predictions = Object.keys(species[0]['predictions'])
      .flat()
      .map((specie) => ({
        specie: specie,
        predictions: species.map((detectedSpecies) => ({
          x: detectedSpecies.end,
          y: detectedSpecies.predictions[specie],
        })),
      }));

    return predictions;
  }

  function getSpeciesAnnotations() {
    const combinedSpecies = combineContiguousSpecies(species);

    // Create annotation objects based on detected species data
    return combinedSpecies.map((entry) => {
      return {
        type: 'box',
        xMin: entry.start, // / 1.92,
        xMax: entry.end, /// 1.92,
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
  }

  const ctx2 = document.getElementById('speciesChart');

  // Destroy previous chart instance if it exists
  if (window.speciesChart instanceof Chart) {
    window.speciesChart.destroy();
  }

  const detectedSpecies = getSpeciesPredictions();

  window.eventsChart = new Chart(ctx2, {
    type: 'line',
    data: {
      datasets: detectedSpecies.map((detectedSpecie, _) => ({
        label: `Probability for ${detectedSpecie.specie}`,
        data: detectedSpecie.predictions,
        borderColor: `#${Math.floor(Math.random() * 16777215)
          .toString(16)
          .padStart(6, '0')}`,
        tension: 0.5,
        fill: false,
      })),
    },
    options: {
      responsive: true,
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Time (seconds)', // Updated label to reflect time
          },
          min: 0,
        },
        y: {
          title: {
            display: true,
            text: 'Probability',
          },
          min: 0,
          max: 1.1,
        },
      },
      plugins: {
        annotation: {
          annotations: getSpeciesAnnotations(),
        },
      },
    },
  });
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

window.plotPredictions = plotPredictions;
